# MobilNiaga Enterprise Multi-Company

MobilNiaga adalah simulasi marketplace kendaraan berbasis **microservice** dengan UI yang dipisahkan berdasarkan peran perusahaan. Sistem ini dirancang untuk menggambarkan alur pembelian kendaraan secara digital, mulai dari marketplace pembeli, seller center, payment gateway, hingga delivery center.

## Informasi Kelompok

**Implementasi MobilNiaga**
Marketplace Kendaraan Berbasis Microservice
Workshop Implementasi Rancangan Perangkat Lunak

| Nama                          | NIM                |
| ----------------------------- | ------------------ |
| Kukuh Agus Hermawan           | 24/533395/PA/22573 |
| Erdziah Ghodi Al Haidar       | 24/537670/PA/22787 |
| Ivan Zuhri Ramadhani Syahrial | 24/540342/PA/22939 |
| Giganus Revo                  | 24/541359/PA/22965 |
| Muhammad Dzaky Ar-Rasyid      | 24/543165/PA/23067 |
| Ifham Syafwan Fikri           | 24/545184/PA/23161 |

## Peran UI

| Peran               | File UI                  | Port | Isi                                                                              |
| ------------------- | ------------------------ | ---: | -------------------------------------------------------------------------------- |
| Buyer / Marketplace | `app_marketplace.py`     | 8501 | login/register, katalog kendaraan, checkout, VA/QRIS, konfirmasi bayar, tracking |
| Seller Center       | `app_seller.py`          | 8502 | login seller, inventory, order masuk, pengiriman, profit, pelanggan              |
| Payment Gateway     | `app_payment_gateway.py` | 8503 | login DANA/Bank/GoPay, transaksi, VA/QRIS, konfirmasi pembayaran, settlement     |
| Delivery Center     | `app_delivery.py`        | 8504 | login SkySend/NeoRush/OrionCargo, shipment aktif, update tracking, timeline      |

## Service API

| Service         | File                 | Port |
| --------------- | -------------------- | ---: |
| Marketplace API | `marketplace_api.py` | 8001 |
| Seller API      | `seller_api.py`      | 8002 |
| Payment API     | `payment_api.py`     | 8003 |
| Delivery API    | `delivery_api.py`    | 8004 |

## Database

Project memakai konsep **database-per-service**. Setiap service memiliki database sendiri agar alur microservice lebih jelas.

Database yang digunakan:

* `mobilniaga_master`
* `seller_auto2000_db`
* `seller_honda_db`
* `seller_mitsubishi_db`
* `seller_hyundai_db`
* `seller_suzuki_db`
* `seller_wuling_db`
* `payment_gateway_db`
* `delivery_gateway_db`

## Alur Pembelian

1. Buyer login/register ke Marketplace.
2. Buyer memilih mobil dari katalog.
3. Buyer mengisi alamat pengiriman.
4. Buyer memilih payment provider dan delivery provider.
5. Sistem membuat instruksi pembayaran VA/QRIS.
6. Buyer klik **Saya sudah bayar**.
7. Payment Gateway mengubah status pembayaran menjadi `PAID`.
8. Seller menerima order dan stok kendaraan berkurang.
9. Delivery Center membuat tracking number.
10. Buyer dapat melihat status pengiriman melalui timeline tracking.

## Akun Demo untuk Presentasi

### Buyer / Marketplace

| Nama           | Email            | Password   |
| -------------- | ---------------- | ---------- |
| Anne Melanika  | `anne@mail.com`  | `anne123`  |
| Soni Mahardika | `soni@mail.com`  | `soni123`  |
| Raka Pratama   | `raka@mail.com`  | `raka123`  |
| Nadia Putri    | `nadia@mail.com` | `nadia123` |

### Seller Center

| Seller                   | Email                    | Password    |
| ------------------------ | ------------------------ | ----------- |
| Auto2000 Official        | `sales@auto2000.co.id`   | `seller123` |
| Honda Prospect Motor     | `sales@honda.co.id`      | `seller123` |
| Mitsubishi Motors        | `sales@mitsubishi.co.id` | `seller123` |
| Hyundai Motors Indonesia | `sales@hyundai.co.id`    | `seller123` |
| Suzuki Indomobil         | `sales@suzuki.co.id`     | `seller123` |
| Wuling Motors            | `sales@wuling.co.id`     | `seller123` |

### Payment Gateway

| Provider                 | Email                 | Password   |
| ------------------------ | --------------------- | ---------- |
| DANA Digital Wallet      | `dana@mobilniaga.id`  | `dana123`  |
| Bank Kirana Digital      | `bank@mobilniaga.id`  | `bank123`  |
| GoPay Financial Services | `gopay@mobilniaga.id` | `gopay123` |

### Delivery Center

| Delivery             | Email                   | Password   |
| -------------------- | ----------------------- | ---------- |
| SkySend Express      | `skysend@mobilniaga.id` | `sky123`   |
| NeoRush Delivery     | `neorush@mobilniaga.id` | `neo123`   |
| OrionCargo Logistics | `orion@mobilniaga.id`   | `orion123` |

## Konfigurasi Environment

Project menggunakan file `.env` untuk konfigurasi database.

Contoh isi `.env.example`:

```env
DB_HOST=your_database_host
DB_PORT=3306
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=mobilniaga_master
USE_SINGLE_DB=false
DB_SSL=true
```

Catatan:

* Untuk lokal dengan XAMPP, port MySQL dapat menggunakan `3307` sesuai konfigurasi XAMPP.
* Untuk deployment online, gunakan database online seperti Aiven MySQL.
* Jangan upload file `.env` ke GitHub karena berisi password database.

## Cara Menjalankan Lokal

Pastikan MySQL aktif. Jika memakai XAMPP, sesuaikan port di `.env`.

```cmd
cd C:\Users\kukuh\Downloads\mobilniaga_final_ui
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python setup_mysql.py
```

## Menjalankan Service API

Jalankan masing-masing API di terminal berbeda.

```cmd
python -m uvicorn marketplace_api:app --port 8001 --reload
```

```cmd
python -m uvicorn seller_api:app --port 8002 --reload
```

```cmd
python -m uvicorn payment_api:app --port 8003 --reload
```

```cmd
python -m uvicorn delivery_api:app --port 8004 --reload
```

## Menjalankan UI Streamlit

Jalankan masing-masing UI di terminal berbeda.

```cmd
python -m streamlit run app_marketplace.py --server.port 8501
```

```cmd
python -m streamlit run app_seller.py --server.port 8502
```

```cmd
python -m streamlit run app_payment_gateway.py --server.port 8503
```

```cmd
python -m streamlit run app_delivery.py --server.port 8504
```

Buka aplikasi melalui browser:

* Marketplace: `http://localhost:8501`
* Seller Center: `http://localhost:8502`
* Payment Gateway: `http://localhost:8503`
* Delivery Center: `http://localhost:8504`

## Deployment Online

Deployment online menggunakan alur:

```text
Streamlit Cloud UI → Vercel API → Aiven MySQL
```

Konfigurasi environment online perlu diisi di:

* **Vercel Environment Variables** untuk API.
* **Streamlit Secrets** untuk UI Streamlit.

Contoh Streamlit Secrets:

```toml
DB_HOST = "your_database_host"
DB_PORT = "your_database_port"
DB_USER = "your_database_user"
DB_PASSWORD = "your_database_password"
DB_NAME = "mobilniaga_master"
USE_SINGLE_DB = "false"
DB_SSL = "true"

MARKETPLACE_API_URL = "https://mobilniaga-enterprise-final.vercel.app/marketplace"
SELLER_API_URL = "https://mobilniaga-enterprise-final.vercel.app/seller"
PAYMENT_API_URL = "https://mobilniaga-enterprise-final.vercel.app/payment"
DELIVERY_API_URL = "https://mobilniaga-enterprise-final.vercel.app/delivery"
```

Setelah mengubah Secrets atau Environment Variables, lakukan reboot/redeploy agar konfigurasi terbaru terbaca.

## Catatan UI

Setiap halaman login sudah menampilkan kartu akun demo agar mudah digunakan saat presentasi. Dengan begitu, penguji atau presenter dapat langsung memilih akun demo tanpa harus mengingat email dan password secara manual.
