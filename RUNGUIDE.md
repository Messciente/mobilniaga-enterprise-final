# RUNGUIDE MobilNiaga Enterprise Multi-Company

## 1. Extract ZIP

Extract project ke folder, contoh:

```cmd
C:\Users\kukuh\Downloads\mobilniaga_enterprise_final
```

## 2. Buka VS Code

Open Folder ke folder hasil extract.

## 3. Pastikan MySQL XAMPP Running

Di XAMPP, MySQL harus hijau/running. Jika port MySQL kamu 3307, `.env` sudah sesuai.

## 4. Buat Virtual Environment

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

Jika berhasil, terminal menjadi:

```cmd
(venv) C:\Users\kukuh\Downloads\mobilniaga_enterprise_final>
```

## 5. Install Library

```cmd
pip install -r requirements.txt
```

## 6. Buat Database dan Seed Data

```cmd
python setup_mysql.py
```

Output berhasil:

```txt
Database berhasil dibuat ulang.
```

## 7. Jalankan 4 API

Gunakan terminal berbeda untuk setiap command.

### Terminal 1

```cmd
venv\Scripts\activate.bat
python -m uvicorn marketplace_api:app --port 8001 --reload
```

### Terminal 2

```cmd
venv\Scripts\activate.bat
python -m uvicorn seller_api:app --port 8002 --reload
```

### Terminal 3

```cmd
venv\Scripts\activate.bat
python -m uvicorn payment_api:app --port 8003 --reload
```

### Terminal 4

```cmd
venv\Scripts\activate.bat
python -m uvicorn delivery_api:app --port 8004 --reload
```

## 8. Jalankan 4 UI

Gunakan terminal berbeda untuk setiap command.

### Buyer Marketplace

```cmd
venv\Scripts\activate.bat
python -m streamlit run app_marketplace.py --server.port 8501
```

### Seller Center

```cmd
venv\Scripts\activate.bat
python -m streamlit run app_seller.py --server.port 8502
```

### Payment Gateway

```cmd
venv\Scripts\activate.bat
python -m streamlit run app_payment_gateway.py --server.port 8503
```

### Delivery Center

```cmd
venv\Scripts\activate.bat
python -m streamlit run app_delivery.py --server.port 8504
```

## 9. Link yang Dibuka

- Buyer Marketplace: http://localhost:8501
- Seller Center: http://localhost:8502
- Payment Gateway: http://localhost:8503
- Delivery Center: http://localhost:8504
- Marketplace API Docs: http://127.0.0.1:8001/docs
- Seller API Docs: http://127.0.0.1:8002/docs
- Payment API Docs: http://127.0.0.1:8003/docs
- Delivery API Docs: http://127.0.0.1:8004/docs

## 10. Alur Testing yang Disarankan

1. Login Buyer di port 8501.
2. Buka katalog dan pilih mobil.
3. Checkout dan pilih VA/QRIS.
4. Setelah VA/QRIS muncul, klik **Saya sudah bayar, proses pesanan**.
5. Login Seller di port 8502, cek Order Masuk.
6. Login Payment di port 8503, cek transaksi sudah `PAID`.
7. Login Delivery di port 8504, cek tracking dan update status.
8. Kembali ke Buyer, buka Tracking Pesanan.

## Akun Demo Cepat

Buyer: `anne@mail.com` / `anne123`

Seller:
- Auto2000: `sales@auto2000.co.id` / `seller123`
- Honda: `sales@honda.co.id` / `seller123`
- Mitsubishi: `sales@mitsubishi.co.id` / `seller123`
- Hyundai: `sales@hyundai.co.id` / `seller123`
- Suzuki: `sales@suzuki.co.id` / `seller123`
- Wuling: `sales@wuling.co.id` / `seller123`

Payment:
- DANA: `dana@mobilniaga.id` / `dana123`
- Bank Kirana: `bank@mobilniaga.id` / `bank123`
- GoPay: `gopay@mobilniaga.id` / `gopay123`

Delivery:
- SkySend: `skysend@mobilniaga.id` / `sky123`
- NeoRush: `neorush@mobilniaga.id` / `neo123`
- OrionCargo: `orion@mobilniaga.id` / `orion123`
