
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime as dt
from db_common import query, execute, one

app = FastAPI(title="MobilNiaga Payment Gateway API", version="4.0")

class PayRequest(BaseModel):
    order_global_id: str
    provider_code: str
    customer_name: str
    amount: int
    payment_channel: str = "AUTO"

class ConfirmRequest(BaseModel):
    transaction_global_id: str

class PaymentLoginRequest(BaseModel):
    provider_code: str
    email: str
    password: str

@app.get("/")
def root():
    return {"service":"Payment Gateway", "message":"DANA / Bank Kirana / GoPay aktif"}

@app.get("/providers")
def providers():
    return query("payment_gateway_db", "SELECT * FROM payment_providers ORDER BY provider_name")

@app.post("/auth/login")
def login(payload: PaymentLoginRequest):
    user = one("payment_gateway_db", "SELECT user_id, provider_code, provider_name, full_name, email, role, status FROM payment_users WHERE provider_code=%s AND email=%s AND password=%s AND status='ACTIVE'", (payload.provider_code, payload.email, payload.password))
    if not user:
        raise HTTPException(401, "Akun payment company tidak valid")
    provider = one("payment_gateway_db", "SELECT * FROM payment_providers WHERE provider_code=%s", (payload.provider_code,))
    return {"message":"Login payment company berhasil", "user":user, "provider":provider}

def build_instruction(payload: PayRequest):
    provider = one("payment_gateway_db", "SELECT * FROM payment_providers WHERE provider_code=%s", (payload.provider_code,)) or {}
    stamp = dt.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
    ref = "TRX-" + payload.provider_code + "-" + stamp
    fee = int(payload.amount * 0.015)
    channel = payload.payment_channel
    if channel == "AUTO":
        if payload.provider_code == "FIN-BANK": channel = "Virtual Account"
        elif payload.provider_code in ("FIN-DANA", "FIN-GOPAY"): channel = "QRIS"
        else: channel = "Payment Gateway"
    va_number = None
    qris_code = None
    if channel == "Virtual Account":
        va_number = "8808" + stamp[-10:]
        instruction = f"Transfer tepat Rp {payload.amount:,} ke Virtual Account {va_number}.".replace(',', '.')
    elif channel in ("QRIS", "Wallet Payment"):
        qris_code = "QRIS-MN-" + stamp[-10:]
        instruction = f"Scan QRIS dan bayar tepat Rp {payload.amount:,}.".replace(',', '.')
        channel = "QRIS"
    else:
        instruction = f"Selesaikan pembayaran melalui {provider.get('provider_name','payment gateway')}."
    return provider, ref, fee, channel, va_number, qris_code, instruction

@app.post("/payments/create")
def create_payment(payload: PayRequest):
    provider, ref, fee, channel, va_number, qris_code, instruction = build_instruction(payload)
    execute("payment_gateway_db", """INSERT INTO payment_transactions
      (transaction_global_id, order_global_id, provider_code, customer_name, amount, fee, net_amount, payment_status, risk_score, payment_channel, virtual_account, qris_code, customer_instruction, expires_at, created_at)
      VALUES (%s,%s,%s,%s,%s,%s,%s,'PENDING',12,%s,%s,%s,%s,DATE_ADD(NOW(), INTERVAL 24 HOUR),NOW())""",
      (ref,payload.order_global_id,payload.provider_code,payload.customer_name,payload.amount,fee,payload.amount-fee,channel,va_number,qris_code,instruction))
    execute("payment_gateway_db", "INSERT INTO payment_logs(provider_code, endpoint, status_code, message, created_at) VALUES (%s,'/payments/create',200,'Payment instruction generated',NOW())", (payload.provider_code,))
    return {
        "message":"Instruksi pembayaran berhasil dibuat",
        "transaction_global_id":ref,
        "provider_name": provider.get("provider_name", payload.provider_code),
        "payment_channel":channel,
        "virtual_account":va_number,
        "qris_code":qris_code,
        "amount":payload.amount,
        "fee":fee,
        "payment_status":"PENDING",
        "instruction":instruction,
        "expires_at":"24 jam dari pembuatan transaksi"
    }

@app.post("/payments/pay")
def pay_alias(payload: PayRequest):
    # Backward compatible endpoint. It now creates a pending instruction, not an instant paid transaction.
    return create_payment(payload)

@app.post("/payments/confirm")
def confirm_payment(payload: ConfirmRequest):
    trx = one("payment_gateway_db", "SELECT * FROM payment_transactions WHERE transaction_global_id=%s", (payload.transaction_global_id,))
    if not trx:
        raise HTTPException(404, "Transaksi pembayaran tidak ditemukan")
    execute("payment_gateway_db", "UPDATE payment_transactions SET payment_status='PAID' WHERE transaction_global_id=%s", (payload.transaction_global_id,))
    execute("payment_gateway_db", "INSERT INTO payment_logs(provider_code, endpoint, status_code, message, created_at) VALUES (%s,'/payments/confirm',200,'Payment confirmed by user simulation',NOW())", (trx["provider_code"],))
    return {"message":"Pembayaran berhasil dikonfirmasi", "transaction_global_id":payload.transaction_global_id, "payment_status":"PAID", "provider_code":trx["provider_code"]}

@app.get("/payments")
def payments():
    return query("payment_gateway_db", """SELECT pt.*, pp.provider_name, pp.provider_type
        FROM payment_transactions pt JOIN payment_providers pp ON pp.provider_code=pt.provider_code
        ORDER BY pt.created_at DESC""")

@app.get("/settlements")
def settlements():
    return query("payment_gateway_db", """SELECT ps.*, pp.provider_name FROM provider_settlements ps JOIN payment_providers pp ON pp.provider_code=ps.provider_code ORDER BY ps.created_at DESC""")

@app.get("/logs")
def logs():
    return query("payment_gateway_db", "SELECT * FROM payment_logs ORDER BY created_at DESC LIMIT 150")
