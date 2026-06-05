
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime as dt
from db_common import query, one, execute

app = FastAPI(title="MobilNiaga Delivery Gateway API", version="4.0")

class ShipmentRequest(BaseModel):
    order_global_id: str
    delivery_code: str
    buyer_name: str
    origin_city: str
    destination_city: str
    origin_address: str = ""
    destination_address: str = ""
    eta_days: int = 5

class StatusUpdate(BaseModel):
    tracking_number: str
    status: str
    location: str
    note: str = "Status updated"

class DeliveryLoginRequest(BaseModel):
    delivery_code: str
    email: str
    password: str

@app.get("/")
def root():
    return {"service":"Delivery Gateway", "message":"SkySend / NeoRush / OrionCargo aktif"}

@app.get("/partners")
def partners():
    return query("delivery_gateway_db", "SELECT * FROM delivery_partners ORDER BY delivery_name")

@app.post("/auth/login")
def login(payload: DeliveryLoginRequest):
    user = one("delivery_gateway_db", "SELECT user_id, delivery_code, delivery_name, full_name, email, role, status FROM delivery_users WHERE delivery_code=%s AND email=%s AND password=%s AND status='ACTIVE'", (payload.delivery_code, payload.email, payload.password))
    if not user:
        raise HTTPException(401, "Akun delivery company tidak valid")
    partner = one("delivery_gateway_db", "SELECT * FROM delivery_partners WHERE delivery_code=%s", (payload.delivery_code,))
    return {"message":"Login delivery company berhasil", "user":user, "delivery":partner}

@app.post("/shipments")
def create(payload: ShipmentRequest):
    stamp=dt.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
    sid="SHIP-"+stamp
    trk="TRK-MN-"+stamp[-8:]
    current = payload.origin_address or payload.origin_city
    eta = max(2, min(14, int(payload.eta_days or 5)))
    execute("delivery_gateway_db", """INSERT INTO delivery_shipments(shipment_global_id, order_global_id, delivery_code, buyer_name, origin_city, destination_city, tracking_number, shipment_status, current_location, estimated_arrival, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,'READY_TO_SHIP',%s,DATE_ADD(CURDATE(), INTERVAL %s DAY),NOW())""", (sid,payload.order_global_id,payload.delivery_code,payload.buyer_name,payload.origin_city,payload.destination_city,trk,current,eta))
    execute("delivery_gateway_db", "INSERT INTO tracking_events(tracking_number, status, location, note, created_at) VALUES (%s,'READY_TO_SHIP',%s,'Unit kendaraan sudah siap dipickup dari alamat seller',NOW())", (trk,current))
    execute("delivery_gateway_db", "INSERT INTO delivery_logs(delivery_code, endpoint, status_code, message, created_at) VALUES (%s,'/shipments',200,'Shipment created from marketplace order',NOW())", (payload.delivery_code,))
    return {"message":"Shipment berhasil dibuat", "shipment_global_id":sid, "tracking_number":trk, "shipment_status":"READY_TO_SHIP", "estimated_days":eta}

@app.get("/shipments")
def shipments():
    return query("delivery_gateway_db", """SELECT ds.*, dp.delivery_name, dp.service_type FROM delivery_shipments ds JOIN delivery_partners dp ON dp.delivery_code=ds.delivery_code ORDER BY ds.created_at DESC""")

@app.get("/tracking/{order_global_id}")
def tracking(order_global_id: str):
    ship=one("delivery_gateway_db", "SELECT * FROM delivery_shipments WHERE order_global_id=%s", (order_global_id,))
    if not ship:
        return {"shipment":None, "events":[]}
    ev=query("delivery_gateway_db", "SELECT * FROM tracking_events WHERE tracking_number=%s ORDER BY created_at", (ship["tracking_number"],))
    return {"shipment":ship, "events":ev}

@app.put("/shipments/status")
def update(payload: StatusUpdate):
    ship = one("delivery_gateway_db", "SELECT * FROM delivery_shipments WHERE tracking_number=%s", (payload.tracking_number,))
    if not ship:
        raise HTTPException(404, "Tracking number tidak ditemukan")
    execute("delivery_gateway_db", "UPDATE delivery_shipments SET shipment_status=%s, current_location=%s WHERE tracking_number=%s", (payload.status,payload.location,payload.tracking_number))
    execute("delivery_gateway_db", "INSERT INTO tracking_events(tracking_number, status, location, note, created_at) VALUES (%s,%s,%s,%s,NOW())", (payload.tracking_number,payload.status,payload.location,payload.note))
    execute("delivery_gateway_db", "INSERT INTO delivery_logs(delivery_code, endpoint, status_code, message, created_at) VALUES (%s,'/shipments/status',200,'Tracking updated',NOW())", (ship["delivery_code"],))
    return {"message":"Tracking berhasil diperbarui"}

@app.get("/logs")
def logs():
    return query("delivery_gateway_db", "SELECT * FROM delivery_logs ORDER BY created_at DESC LIMIT 150")
