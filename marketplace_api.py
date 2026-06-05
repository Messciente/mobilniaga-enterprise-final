
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime as dt
import os
import requests
from dotenv import load_dotenv
from pathlib import Path
from db_common import query, one, execute

load_dotenv(Path(__file__).resolve().parent / ".env")
SELLER_API_URL = os.getenv("SELLER_API_URL", "http://127.0.0.1:8002")
PAYMENT_API_URL = os.getenv("PAYMENT_API_URL", "http://127.0.0.1:8003")
DELIVERY_API_URL = os.getenv("DELIVERY_API_URL", "http://127.0.0.1:8004")

SELLER_ADDRESS = {
    "SELLER-A2000": {"origin_city":"Sleman", "seller_address":"Auto2000 Yogyakarta, Jl. Magelang Km 7, Sinduadi, Mlati, Sleman, DI Yogyakarta"},
    "SELLER-HONDA": {"origin_city":"Semarang", "seller_address":"Honda Prospect Semarang, Jl. Setiabudi No. 88, Banyumanik, Semarang, Jawa Tengah"},
    "SELLER-MITSUBISHI": {"origin_city":"Surabaya", "seller_address":"Mitsubishi Motors Surabaya, Jl. Ahmad Yani No. 120, Surabaya, Jawa Timur"},
    "SELLER-HYUNDAI": {"origin_city":"Bandung", "seller_address":"Hyundai Motors Bandung, Jl. Soekarno Hatta No. 501, Bandung, Jawa Barat"},
    "SELLER-SUZUKI": {"origin_city":"Surakarta", "seller_address":"Suzuki Indomobil Solo, Jl. Adi Sucipto No. 45, Surakarta, Jawa Tengah"},
    "SELLER-WULING": {"origin_city":"Jakarta Barat", "seller_address":"Wuling Motors Jakarta Barat, Jl. Daan Mogot No. 77, Jakarta Barat, DKI Jakarta"},
}
CITY_ZONE = {
    "Jakarta": 1, "Jakarta Barat": 1, "Bekasi": 1, "Tangerang": 1,
    "Bandung": 2, "Semarang": 3, "Surakarta": 3, "Solo": 3, "Yogyakarta": 3, "Sleman": 3,
    "Surabaya": 4,
}

app = FastAPI(title="MobilNiaga Marketplace API", version="4.0")

class RegisterRequest(BaseModel):
    full_name: str
    phone: str
    email: str
    password: str
    city: str
    address: str

class LoginRequest(BaseModel):
    email: str
    password: str

class BuyRequest(BaseModel):
    customer_global_id: str
    listing_id: str
    qty: int = 1
    payment_provider: str
    payment_channel: str = "AUTO"
    delivery_partner: str
    destination_city: str
    destination_address: str = ""

class ConfirmPaymentRequest(BaseModel):
    order_global_id: str

class CancelRequest(BaseModel):
    order_global_id: str

@app.get("/")
def root():
    return {"service":"Marketplace API", "message":"MobilNiaga Marketplace API aktif"}

@app.get("/partners")
def partners():
    return query("mobilniaga_master", "SELECT * FROM partners ORDER BY partner_type, partner_name")

@app.post("/auth/register")
def register(payload: RegisterRequest):
    cid="CUST-"+dt.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
    execute("mobilniaga_master", "INSERT INTO customers VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())", (cid,payload.full_name,payload.phone,payload.email,payload.password,payload.city,payload.address))
    return {"message":"Register berhasil", "customer_global_id":cid, "full_name":payload.full_name}

@app.post("/auth/login")
def login(payload: LoginRequest):
    cust=one("mobilniaga_master", "SELECT * FROM customers WHERE email=%s AND password=%s", (payload.email,payload.password))
    if not cust:
        raise HTTPException(401,"Email atau password salah")
    return {"message":"Login berhasil", "customer":cust}

@app.get("/catalog")
def catalog(keyword: str = "", seller_code: str = "", fuel_type: str = ""):
    sql="""
      SELECT mp.*, p.partner_name AS seller_name, p.city AS seller_city, p.brand_color
      FROM marketplace_products mp JOIN partners p ON p.partner_code=mp.seller_code
      WHERE mp.status='ACTIVE'
    """
    params=[]
    if keyword:
        sql += " AND (mp.brand LIKE %s OR mp.model LIKE %s OR mp.vehicle_type LIKE %s)"
        like=f"%{keyword}%"; params += [like,like,like]
    if seller_code:
        sql += " AND mp.seller_code=%s"; params.append(seller_code)
    if fuel_type:
        sql += " AND mp.fuel_type=%s"; params.append(fuel_type)
    sql += " ORDER BY mp.seller_code, mp.price"
    rows = query("mobilniaga_master", sql, tuple(params))
    for r in rows:
        origin = SELLER_ADDRESS.get(r["seller_code"], {"origin_city":r.get("seller_city","Jakarta"), "seller_address":r.get("seller_city", "Jakarta")})
        r["origin_city"] = origin["origin_city"]
        r["seller_address"] = origin["seller_address"]
    return rows

@app.get("/orders")
def orders():
    return query("mobilniaga_master", """SELECT o.*, p.partner_name AS seller_name, mp.brand, mp.model, mp.image_path FROM orders o LEFT JOIN partners p ON p.partner_code=o.seller_code LEFT JOIN marketplace_products mp ON mp.listing_id=o.listing_id ORDER BY o.created_at DESC""")

@app.get("/orders/customer/{customer_global_id}")
def orders_customer(customer_global_id: str):
    return query("mobilniaga_master", """SELECT o.*, p.partner_name AS seller_name, mp.brand, mp.model, mp.image_path FROM orders o LEFT JOIN partners p ON p.partner_code=o.seller_code LEFT JOIN marketplace_products mp ON mp.listing_id=o.listing_id WHERE o.customer_global_id=%s ORDER BY o.created_at DESC""", (customer_global_id,))

@app.get("/orders/track/{order_global_id}")
def track(order_global_id: str):
    order=one("mobilniaga_master", "SELECT * FROM orders WHERE order_global_id=%s", (order_global_id,))
    history=query("mobilniaga_master", "SELECT * FROM order_status_history WHERE order_global_id=%s ORDER BY created_at", (order_global_id,))
    shipment=one("mobilniaga_master", "SELECT * FROM shipments_summary WHERE order_global_id=%s", (order_global_id,))
    events=[]
    try:
        rr=requests.get(f"{DELIVERY_API_URL}/tracking/{order_global_id}", timeout=8)
        if rr.ok:
            events=rr.json().get("events", [])
    except Exception:
        pass
    return {"order":order, "history":history, "shipment":shipment, "delivery_events":events}

def estimate_shipping(origin_city: str, destination_city: str, delivery_code: str, vehicle_type: str) -> tuple[int,int]:
    oz = CITY_ZONE.get(origin_city, 2)
    dz = CITY_ZONE.get(destination_city, 3)
    distance_zone = abs(oz-dz)
    base = 350000 if distance_zone == 0 else 650000 + distance_zone * 450000
    if delivery_code == "DEL-NEO": base += 550000
    if delivery_code == "DEL-ORI": base += 1600000
    if "SUV" in (vehicle_type or "") or "EV" in (vehicle_type or ""):
        base += 300000
    eta = 2 + distance_zone
    if delivery_code == "DEL-NEO": eta = max(1, eta-1)
    if delivery_code == "DEL-ORI": eta += 2
    return int(base), int(eta)

@app.post("/orders/buy")
def buy(payload: BuyRequest):
    cust=one("mobilniaga_master", "SELECT * FROM customers WHERE customer_global_id=%s", (payload.customer_global_id,))
    prod=one("mobilniaga_master", "SELECT * FROM marketplace_products WHERE listing_id=%s AND status='ACTIVE'", (payload.listing_id,))
    if not cust: raise HTTPException(404,"Customer tidak ditemukan")
    if not prod: raise HTTPException(404,"Produk tidak ditemukan")
    if prod["stock_snapshot"] < payload.qty: raise HTTPException(400,"Stok snapshot marketplace tidak cukup")
    stamp=dt.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
    order_id="ORD-MN-"+stamp
    origin = SELLER_ADDRESS.get(prod["seller_code"], {"origin_city":"Jakarta", "seller_address":"Seller Warehouse Jakarta"})
    subtotal=int(prod["price"])*payload.qty
    shipping_fee, eta_days = estimate_shipping(origin["origin_city"], payload.destination_city, payload.delivery_partner, prod.get("vehicle_type", ""))
    admin_fee = 150000
    total=subtotal+shipping_fee+admin_fee
    payment_res=requests.post(f"{PAYMENT_API_URL}/payments/create", json={"order_global_id":order_id,"provider_code":payload.payment_provider,"customer_name":cust["full_name"],"amount":total,"payment_channel":payload.payment_channel}, timeout=20)
    if payment_res.status_code >= 400:
        raise HTTPException(400, payment_res.text)
    pay=payment_res.json()
    provider=one("mobilniaga_master", "SELECT partner_name FROM partners WHERE partner_code=%s", (payload.payment_provider,))
    courier=one("mobilniaga_master", "SELECT partner_name FROM partners WHERE partner_code=%s", (payload.delivery_partner,))
    execute("mobilniaga_master", """INSERT INTO orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s,'PENDING','WAITING_PAYMENT','WAITING_PAYMENT',%s,NOW())""", (order_id,cust["customer_global_id"],cust["full_name"],prod["seller_code"],prod["listing_id"],prod["external_vehicle_code"],payload.qty,subtotal,shipping_fee,total,provider["partner_name"],payload.destination_city))
    execute("mobilniaga_master", "INSERT INTO order_status_history(order_global_id,status,note,created_at) VALUES (%s,'ORDER_CREATED','Pesanan dibuat. Menunggu pembayaran dari pembeli.',NOW())", (order_id,))
    execute("mobilniaga_master", "INSERT INTO payments_summary(order_global_id,provider_code,provider_name,payment_reference,amount,payment_status,paid_at) VALUES (%s,%s,%s,%s,%s,'PENDING',NULL)", (order_id,payload.payment_provider,provider["partner_name"],pay["transaction_global_id"],total))
    execute("mobilniaga_master", "INSERT INTO shipments_summary(order_global_id,delivery_code,delivery_name,tracking_number,destination_city,shipment_status,current_location,estimated_arrival,updated_at) VALUES (%s,%s,%s,'-',%s,'PAYMENT_PENDING',%s,DATE_ADD(CURDATE(), INTERVAL %s DAY),NOW())", (order_id,payload.delivery_partner,courier["partner_name"],payload.destination_city,origin["seller_address"],eta_days))
    execute("mobilniaga_master", "INSERT INTO api_logs(service_name,endpoint,method,status_code,message,created_at) VALUES ('Marketplace Gateway','/orders/buy','POST',200,'Payment instruction created; waiting user confirmation',NOW())")
    return {
        "message":"Instruksi pembayaran dibuat",
        "order_global_id":order_id,
        "buyer_name":cust["full_name"],
        "vehicle":{"brand":prod["brand"],"model":prod["model"],"seller_code":prod["seller_code"],"qty":payload.qty},
        "seller":{"seller_code":prod["seller_code"], "origin_city":origin["origin_city"], "seller_address":origin["seller_address"]},
        "price_summary":{"subtotal":subtotal,"admin_fee":admin_fee,"shipping_fee":shipping_fee,"discount":0,"grand_total":total,"estimated_days":eta_days},
        "payment_instruction":pay,
        "delivery_plan":{"delivery_code":payload.delivery_partner, "delivery_name":courier["partner_name"], "destination_city":payload.destination_city, "destination_address":payload.destination_address or payload.destination_city, "eta_days":eta_days}
    }

@app.post("/orders/confirm-payment")
def confirm_payment(payload: ConfirmPaymentRequest):
    order=one("mobilniaga_master", "SELECT * FROM orders WHERE order_global_id=%s", (payload.order_global_id,))
    if not order: raise HTTPException(404,"Order tidak ditemukan")
    if order["payment_status"] == "PAID":
        return {"message":"Pembayaran sudah pernah dikonfirmasi", "order_global_id":payload.order_global_id}
    prod=one("mobilniaga_master", "SELECT * FROM marketplace_products WHERE listing_id=%s", (order["listing_id"],))
    cust=one("mobilniaga_master", "SELECT * FROM customers WHERE customer_global_id=%s", (order["customer_global_id"],))
    pay_sum=one("mobilniaga_master", "SELECT * FROM payments_summary WHERE order_global_id=%s", (payload.order_global_id,))
    planned_ship=one("mobilniaga_master", "SELECT * FROM shipments_summary WHERE order_global_id=%s", (payload.order_global_id,))
    delivery_partner=(planned_ship or {}).get("delivery_code") or "DEL-NEO"
    origin = SELLER_ADDRESS.get(order["seller_code"], {"origin_city":"Jakarta", "seller_address":"Seller Warehouse Jakarta"})
    if not prod or not cust or not pay_sum:
        raise HTTPException(400, "Data order tidak lengkap")
    conf=requests.post(f"{PAYMENT_API_URL}/payments/confirm", json={"transaction_global_id":pay_sum["payment_reference"]}, timeout=20)
    if conf.status_code >= 400:
        raise HTTPException(400, conf.text)
    seller_res=requests.post(f"{SELLER_API_URL}/inventory/deduct", json={
      "seller_code":order["seller_code"], "vehicle_code":order["vehicle_code"], "order_global_id":payload.order_global_id,
      "customer_global_id":cust["customer_global_id"], "customer_name":cust["full_name"], "phone":cust["phone"], "city":cust["city"], "qty":order["qty"], "amount":order["subtotal"]
    }, timeout=20)
    if seller_res.status_code >= 400:
        raise HTTPException(400, seller_res.text)
    courier=one("mobilniaga_master", "SELECT partner_name FROM partners WHERE partner_code=%s", (delivery_partner,)) or {"partner_name":delivery_partner}
    shipping_fee, eta_days = estimate_shipping(origin["origin_city"], order["destination_city"], delivery_partner, prod.get("vehicle_type", ""))
    delivery_res=requests.post(f"{DELIVERY_API_URL}/shipments", json={"order_global_id":payload.order_global_id,"delivery_code":delivery_partner,"buyer_name":cust["full_name"],"origin_city":origin["origin_city"],"destination_city":order["destination_city"],"origin_address":origin["seller_address"],"destination_address":cust["address"],"eta_days":eta_days}, timeout=20)
    if delivery_res.status_code >= 400:
        raise HTTPException(400, delivery_res.text)
    ship=delivery_res.json(); seller=seller_res.json()
    execute("mobilniaga_master", "UPDATE orders SET payment_status='PAID', order_status='PROCESSING', shipment_status='READY_TO_SHIP' WHERE order_global_id=%s", (payload.order_global_id,))
    execute("mobilniaga_master", "UPDATE payments_summary SET payment_status='PAID', paid_at=NOW() WHERE order_global_id=%s", (payload.order_global_id,))
    execute("mobilniaga_master", "UPDATE marketplace_products SET stock_snapshot=stock_snapshot-%s WHERE listing_id=%s", (order["qty"], order["listing_id"]))
    execute("mobilniaga_master", "INSERT INTO order_status_history(order_global_id,status,note,created_at) VALUES (%s,'PAYMENT_CONFIRMED','Pembeli mengonfirmasi pembayaran. Payment gateway menandai transaksi PAID.',NOW()),(%s,'SELLER_PROCESSING','Order diteruskan ke seller. Seller menyiapkan unit kendaraan.',NOW()),(%s,'SHIPMENT_CREATED','Delivery partner membuat nomor tracking dan menunggu pickup.',NOW())", (payload.order_global_id,payload.order_global_id,payload.order_global_id))
    execute("mobilniaga_master", "UPDATE shipments_summary SET tracking_number=%s, shipment_status='READY_TO_SHIP', current_location=%s, estimated_arrival=DATE_ADD(CURDATE(), INTERVAL %s DAY), updated_at=NOW() WHERE order_global_id=%s", (ship["tracking_number"], origin["seller_address"], eta_days, payload.order_global_id))
    fee=int(order["grand_total"]*0.03)
    execute("mobilniaga_master", "INSERT INTO settlements VALUES (%s,%s,%s,%s,%s,%s,%s,'PENDING',NOW())", ("SET-"+payload.order_global_id,payload.order_global_id,order["seller_code"],pay_sum["provider_code"],order["grand_total"],fee,order["grand_total"]-fee))
    execute("mobilniaga_master", "INSERT INTO api_logs(service_name,endpoint,method,status_code,message,created_at) VALUES ('Marketplace Gateway','/orders/confirm-payment','POST',200,'Payment confirmed; seller and delivery processing started',NOW())")
    return {"message":"Pembayaran dikonfirmasi. Pesanan diteruskan ke seller dan delivery.", "order_global_id":payload.order_global_id, "payment_status":"PAID", "order_status":"PROCESSING", "tracking_number":ship["tracking_number"], "seller_result":seller, "delivery_name":courier["partner_name"]}

@app.post("/orders/cancel")
def cancel(payload: CancelRequest):
    order=one("mobilniaga_master", "SELECT * FROM orders WHERE order_global_id=%s", (payload.order_global_id,))
    if not order: raise HTTPException(404,"Order tidak ditemukan")
    if order["order_status"] not in ("WAITING_PAYMENT", "PENDING_PAYMENT"):
        try:
            requests.post(f"{SELLER_API_URL}/inventory/restore", json={"seller_code":order["seller_code"],"vehicle_code":order["vehicle_code"],"order_global_id":payload.order_global_id}, timeout=20)
        except Exception:
            pass
    execute("mobilniaga_master", "UPDATE orders SET order_status='CANCELLED', shipment_status='CANCELLED' WHERE order_global_id=%s", (payload.order_global_id,))
    execute("mobilniaga_master", "INSERT INTO order_status_history(order_global_id,status,note,created_at) VALUES (%s,'CANCELLED','Pesanan dibatalkan.',NOW())", (payload.order_global_id,))
    return {"message":"Order berhasil dibatalkan"}

@app.get("/admin/settlements")
def settlements():
    return query("mobilniaga_master", """SELECT st.*, p.partner_name AS seller_name, fp.partner_name AS payment_provider FROM settlements st LEFT JOIN partners p ON p.partner_code=st.seller_code LEFT JOIN partners fp ON fp.partner_code=st.provider_code ORDER BY st.created_at DESC""")

@app.get("/admin/logs")
def logs():
    return query("mobilniaga_master", "SELECT * FROM api_logs ORDER BY created_at DESC LIMIT 150")
