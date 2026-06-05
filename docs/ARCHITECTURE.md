# Arsitektur MobilNiaga Enterprise

```text
Buyer UI :8501 ──> Marketplace API :8001 ──┬──> Seller API :8002 ──> seller_*_db
                                           ├──> Payment API :8003 ──> payment_gateway_db
                                           └──> Delivery API :8004 ──> delivery_gateway_db

Marketplace API ──> mobilniaga_master
```

Prinsip yang digunakan:
- setiap company punya database sendiri,
- komunikasi antar-service lewat HTTP API,
- order memakai global business ID,
- marketplace hanya menyimpan summary, bukan menguasai seluruh data seller/payment/delivery.
