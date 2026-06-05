
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime as dt
from db_common import query, one, execute, SELLER_DBS

app = FastAPI(title="MobilNiaga Seller API", version="2.0")

class AddVehicle(BaseModel):
    seller_code: str
    vehicle_code: str
    brand: str
    model: str
    vehicle_type: str = "MPV"
    year: int = 2024
    fuel_type: str = "Bensin"
    transmission: str = "Automatic"
    selling_price: int
    unit_cost: int
    stock: int = 1
    image_path: str = "assets/cars/toyota_avanza.jpg"

class StockUpdate(BaseModel):
    seller_code: str
    vehicle_code: str
    added_stock: int

class PriceUpdate(BaseModel):
    seller_code: str
    vehicle_code: str
    new_price: int

class DeductRequest(BaseModel):
    seller_code: str
    vehicle_code: str
    order_global_id: str
    customer_global_id: str
    customer_name: str
    phone: str | None = None
    city: str | None = None
    qty: int = 1
    amount: int

class RestoreRequest(BaseModel):
    seller_code: str
    vehicle_code: str
    order_global_id: str

class StatusUpdate(BaseModel):
    seller_code: str
    order_global_id: str
    new_status: str
    shipment_status: str = "ON_DELIVERY"

class RestockRequest(BaseModel):
    seller_code: str
    supplier_code: str
    vehicle_code: str
    qty: int

class SellerLoginRequest(BaseModel):
    seller_code: str
    email: str
    password: str


def db_for(code: str):
    if code not in SELLER_DBS:
        raise HTTPException(404, f"Seller {code} tidak ditemukan")
    return SELLER_DBS[code]

@app.get("/")
def root():
    return {"service":"Seller API", "message":"Seller API multi-company aktif"}

@app.get("/sellers")
def sellers():
    return query("mobilniaga_master", "SELECT partner_code AS seller_code, partner_name, city, brand_color FROM partners WHERE partner_type='SELLER' ORDER BY partner_name")

@app.post("/auth/login")
def login(payload: SellerLoginRequest):
    db = db_for(payload.seller_code)
    user = one(db, "SELECT user_id, seller_code, full_name, email, role, status FROM seller_users WHERE seller_code=%s AND email=%s AND password=%s AND status='ACTIVE'", (payload.seller_code, payload.email, payload.password))
    if not user:
        raise HTTPException(401, "Akun seller tidak valid untuk perusahaan ini")
    prof = one(db, "SELECT * FROM seller_profile WHERE seller_code=%s", (payload.seller_code,))
    return {"message":"Login seller berhasil", "user":user, "seller":prof}

@app.get("/seller/{seller_code}/profile")
def profile(seller_code: str):
    db=db_for(seller_code)
    return one(db, "SELECT * FROM seller_profile WHERE seller_code=%s", (seller_code,))

@app.get("/seller/{seller_code}/inventory")
def inventory(seller_code: str):
    db=db_for(seller_code)
    return query(db, """
      SELECT v.*, i.stock_available, i.reserved_stock, i.warehouse, i.last_updated
      FROM vehicles v JOIN seller_inventory i ON i.vehicle_code=v.vehicle_code
      ORDER BY v.brand, v.model
    """)

@app.get("/seller/{seller_code}/orders")
def orders(seller_code: str):
    db=db_for(seller_code)
    return query(db, """
      SELECT so.*, v.brand, v.model, v.image_path
      FROM seller_orders so LEFT JOIN vehicles v ON v.vehicle_code=so.vehicle_code
      ORDER BY so.created_at DESC
    """)

@app.get("/seller/{seller_code}/profit")
def profit(seller_code: str):
    db=db_for(seller_code)
    return query(db, """
      SELECT sr.recap_date, v.brand, v.model, sr.qty_sold, sr.revenue, sr.cost, sr.gross_profit
      FROM sales_recap sr JOIN vehicles v ON v.vehicle_code=sr.vehicle_code
      ORDER BY sr.recap_date
    """)

@app.get("/seller/{seller_code}/customers")
def customers(seller_code: str):
    db=db_for(seller_code)
    return query(db, "SELECT * FROM seller_customers ORDER BY total_spend DESC")

@app.post("/inventory/add")
def add_vehicle(payload: AddVehicle):
    db=db_for(payload.seller_code)
    execute(db, "INSERT INTO vehicles VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE')", (payload.vehicle_code,payload.seller_code,payload.brand,payload.model,payload.vehicle_type,payload.year,payload.fuel_type,payload.transmission,payload.selling_price,payload.unit_cost,payload.image_path))
    execute(db, "INSERT INTO seller_inventory(vehicle_code, stock_available, reserved_stock, warehouse) VALUES (%s,%s,0,%s)", (payload.vehicle_code,payload.stock,"Gudang Utama"))
    return {"message":"Kendaraan berhasil ditambahkan", "vehicle_code":payload.vehicle_code}

@app.post("/inventory/stock")
def stock(payload: StockUpdate):
    db=db_for(payload.seller_code)
    execute(db, "UPDATE seller_inventory SET stock_available=stock_available+%s WHERE vehicle_code=%s", (payload.added_stock,payload.vehicle_code))
    execute("mobilniaga_master", "UPDATE marketplace_products SET stock_snapshot=stock_snapshot+%s WHERE external_vehicle_code=%s", (payload.added_stock,payload.vehicle_code))
    return {"message":"Stok berhasil diperbarui"}

@app.put("/inventory/price")
def price(payload: PriceUpdate):
    db=db_for(payload.seller_code)
    execute(db, "UPDATE vehicles SET selling_price=%s WHERE vehicle_code=%s", (payload.new_price,payload.vehicle_code))
    execute("mobilniaga_master", "UPDATE marketplace_products SET price=%s WHERE external_vehicle_code=%s", (payload.new_price,payload.vehicle_code))
    return {"message":"Harga berhasil diperbarui"}

@app.post("/inventory/deduct")
def deduct(payload: DeductRequest):
    db=db_for(payload.seller_code)
    vehicle=one(db, "SELECT * FROM vehicles WHERE vehicle_code=%s", (payload.vehicle_code,))
    inv=one(db, "SELECT * FROM seller_inventory WHERE vehicle_code=%s", (payload.vehicle_code,))
    if not vehicle or not inv:
        raise HTTPException(404,"Vehicle tidak ditemukan")
    if inv["stock_available"] < payload.qty:
        raise HTTPException(400,"Stok seller tidak cukup")
    execute(db, "UPDATE seller_inventory SET stock_available=stock_available-%s, reserved_stock=reserved_stock+%s WHERE vehicle_code=%s", (payload.qty,payload.qty,payload.vehicle_code))
    revenue=payload.amount
    unit_cost=int(vehicle["unit_cost"])*payload.qty
    profit=revenue-unit_cost
    sid="SO-"+payload.order_global_id
    now=dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    execute(db, """INSERT INTO seller_orders(seller_order_global_id, marketplace_order_global_id, customer_global_id, customer_name, vehicle_code, qty, revenue, unit_cost, gross_profit, order_status, shipment_status, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'PAID','READY_TO_SHIP',%s)""", (sid,payload.order_global_id,payload.customer_global_id,payload.customer_name,payload.vehicle_code,payload.qty,revenue,unit_cost,profit,now))
    execute(db, "INSERT INTO sales_recap(recap_date, vehicle_code, qty_sold, revenue, cost, gross_profit) VALUES (CURDATE(),%s,%s,%s,%s,%s)", (payload.vehicle_code,payload.qty,revenue,unit_cost,profit))
    execute(db, "INSERT INTO seller_customers(customer_global_id, customer_name, phone, city, total_spend) VALUES (%s,%s,%s,%s,%s)", (payload.customer_global_id,payload.customer_name,payload.phone or '-',payload.city or '-',revenue))
    return {"message":"Stok seller dikurangi dan order seller dibuat", "seller_order_global_id":sid, "gross_profit":profit}

@app.post("/inventory/restore")
def restore(payload: RestoreRequest):
    db=db_for(payload.seller_code)
    execute(db, "UPDATE seller_inventory SET stock_available=stock_available+1, reserved_stock=GREATEST(reserved_stock-1,0) WHERE vehicle_code=%s", (payload.vehicle_code,))
    execute(db, "UPDATE seller_orders SET order_status='CANCELLED', shipment_status='CANCELLED' WHERE marketplace_order_global_id=%s", (payload.order_global_id,))
    return {"message":"Stok seller dikembalikan"}

@app.put("/orders/status")
def update_status(payload: StatusUpdate):
    db=db_for(payload.seller_code)
    execute(db, "UPDATE seller_orders SET order_status=%s, shipment_status=%s WHERE marketplace_order_global_id=%s", (payload.new_status,payload.shipment_status,payload.order_global_id))
    return {"message":"Status seller order berhasil diperbarui"}

@app.post("/restock/request")
def restock(payload: RestockRequest):
    db=db_for(payload.seller_code)
    rid="RST-"+dt.datetime.now().strftime('%Y%m%d%H%M%S')
    execute(db, "INSERT INTO restock_requests VALUES (%s,%s,%s,%s,'PENDING',NOW())", (rid,payload.supplier_code,payload.vehicle_code,payload.qty))
    return {"message":"Restock request dibuat", "restock_id":rid}
