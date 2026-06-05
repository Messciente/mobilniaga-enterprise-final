# MobilNiaga Enterprise Multi-Company

MobilNiaga adalah simulasi marketplace kendaraan berbasis microservice dengan UI yang dipisahkan berdasarkan peran perusahaan.

## Peran UI

| Peran | File UI | Port | Isi |
|---|---:|---:|---|
| Buyer / Marketplace | `app_marketplace.py` | 8501 | login/register, katalog, checkout, VA/QRIS, konfirmasi bayar, tracking |
| Seller Center | `app_seller.py` | 8502 | login per seller, inventory, order masuk, pengiriman, profit, pelanggan |
| Payment Gateway | `app_payment_gateway.py` | 8503 | login DANA/Bank/GoPay, transaksi, VA/QRIS, konfirmasi, settlement |
| Delivery Center | `app_delivery.py` | 8504 | login SkySend/NeoRush/OrionCargo, shipment aktif, update tracking, timeline |

## Service API

| Service | File | Port |
|---|---|---:|
| Marketplace API | `marketplace_api.py` | 8001 |
| Seller API | `seller_api.py` | 8002 |
| Payment API | `payment_api.py` | 8003 |
| Delivery API | `delivery_api.py` | 8004 |

## Database

Project memakai multi-database sesuai konsep database-per-service:

- `mobilniaga_master`
- `seller_auto2000_db`
- `seller_honda_db`
- `seller_mitsubishi_db`
- `seller_hyundai_db`
- `seller_suzuki_db`
- `seller_wuling_db`
- `payment_gateway_db`
- `delivery_gateway_db`

## Alur Pembelian

1. Buyer memilih mobil dari katalog.
2. Buyer mengisi alamat lengkap.
3. Buyer memilih payment provider dan delivery provider.
4. Sistem membuat instruksi pembayaran VA/QRIS.
5. Buyer klik **Saya sudah bayar**.
6. Payment gateway mengubah status menjadi `PAID`.
7. Seller menerima order dan stok berkurang.
8. Delivery membuat tracking number.
9. Buyer melihat tracking melalui timeline.

## Akun Demo

### Buyer
- Email: `anne@mail.com`
- Password: `anne123`

### Seller
- Auto2000: `sales@auto2000.co.id` / `seller123`
- Honda: `sales@honda.co.id` / `seller123`
- Mitsubishi: `sales@mitsubishi.co.id` / `seller123`
- Hyundai: `sales@hyundai.co.id` / `seller123`
- Suzuki: `sales@suzuki.co.id` / `seller123`
- Wuling: `sales@wuling.co.id` / `seller123`

### Payment
- DANA: `dana@mobilniaga.id` / `dana123`
- Bank Kirana: `bank@mobilniaga.id` / `bank123`
- GoPay: `gopay@mobilniaga.id` / `gopay123`

### Delivery
- SkySend: `skysend@mobilniaga.id` / `sky123`
- NeoRush: `neorush@mobilniaga.id` / `neo123`
- OrionCargo: `orion@mobilniaga.id` / `orion123`

## Cara Menjalankan Singkat

Pastikan XAMPP MySQL aktif. Port di `.env` default: `3307`.

```cmd
cd C:\Users\kukuh\Downloads\mobilniaga_enterprise_final
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python setup_mysql.py
```

Jalankan API di terminal berbeda:

```cmd
python -m uvicorn marketplace_api:app --port 8001 --reload
python -m uvicorn seller_api:app --port 8002 --reload
python -m uvicorn payment_api:app --port 8003 --reload
python -m uvicorn delivery_api:app --port 8004 --reload
```

Jalankan UI di terminal berbeda:

```cmd
python -m streamlit run app_marketplace.py --server.port 8501
python -m streamlit run app_seller.py --server.port 8502
python -m streamlit run app_payment_gateway.py --server.port 8503
python -m streamlit run app_delivery.py --server.port 8504
```

Buka:

- http://localhost:8501
- http://localhost:8502
- http://localhost:8503
- http://localhost:8504

## Akun Demo untuk Presentasi

### Buyer / Marketplace
- Anne Melanika: `anne@mail.com` / `anne123`
- Soni Mahardika: `soni@mail.com` / `soni123`
- Raka Pratama: `raka@mail.com` / `raka123`
- Nadia Putri: `nadia@mail.com` / `nadia123`

### Seller Center
- Auto2000 Official: `sales@auto2000.co.id` / `seller123`
- Honda Prospect Motor: `sales@honda.co.id` / `seller123`
- Mitsubishi Motors: `sales@mitsubishi.co.id` / `seller123`
- Hyundai Motors Indonesia: `sales@hyundai.co.id` / `seller123`
- Suzuki Indomobil: `sales@suzuki.co.id` / `seller123`
- Wuling Motors: `sales@wuling.co.id` / `seller123`

### Payment Gateway
- DANA Digital Wallet: `dana@mobilniaga.id` / `dana123`
- Bank Kirana Digital: `bank@mobilniaga.id` / `bank123`
- GoPay Financial Services: `gopay@mobilniaga.id` / `gopay123`

### Delivery Center
- SkySend Express: `skysend@mobilniaga.id` / `sky123`
- NeoRush Delivery: `neorush@mobilniaga.id` / `neo123`
- OrionCargo Logistics: `orion@mobilniaga.id` / `orion123`

Catatan UI: setiap halaman login sudah menampilkan kartu akun demo agar mudah dipakai saat presentasi.
