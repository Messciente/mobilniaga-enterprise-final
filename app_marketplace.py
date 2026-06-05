from __future__ import annotations

import datetime as dt
import html
from pathlib import Path

import pandas as pd
import streamlit as st

from db_common import query, one, execute, SELLER_DBS
from ui_style import (
    setup_page, hero, kpi, money, section, df_table, info_card,
    amount_row, badge, status_badge, SELLER_ADDRESS, sidebar_brand,
    sidebar_user, demo_credentials, step_pills
)

ROOT = Path(__file__).resolve().parent
MASTER_DB = "mobilniaga_master"
PAYMENT_DB = "payment_gateway_db"
DELIVERY_DB = "delivery_gateway_db"

setup_page("MobilNiaga Marketplace", "🚗")

CITY_ZONE = {
    "Jakarta": 1, "Jakarta Barat": 1, "Bekasi": 1, "Tangerang": 1,
    "Bandung": 2,
    "Semarang": 3, "Surakarta": 3, "Solo": 3, "Yogyakarta": 3, "Sleman": 3,
    "Surabaya": 4,
}


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]


def safe_city(value: str) -> str:
    return (value or "").strip().title()


def get_seller_origin(seller_code: str, seller_city: str | None = None) -> dict:
    addr = SELLER_ADDRESS.get(seller_code, {})
    return {
        "origin_city": addr.get("city") or seller_city or "Jakarta",
        "seller_address": addr.get("address") or seller_city or "Seller Warehouse Jakarta",
        "seller_display_name": addr.get("name") or seller_code,
    }


def estimate_shipping(origin_city: str, destination_city: str, delivery_code: str, vehicle_type: str) -> tuple[int, int]:
    oz = CITY_ZONE.get(safe_city(origin_city), 2)
    dz = CITY_ZONE.get(safe_city(destination_city), 3)
    distance_zone = abs(oz - dz)

    base = 350000 if distance_zone == 0 else 650000 + distance_zone * 450000

    if delivery_code == "DEL-NEO":
        base += 550000
    if delivery_code == "DEL-ORI":
        base += 1600000
    if "SUV" in str(vehicle_type or "").upper() or "EV" in str(vehicle_type or "").upper():
        base += 300000

    eta = 2 + distance_zone
    if delivery_code == "DEL-NEO":
        eta = max(1, eta - 1)
    if delivery_code == "DEL-ORI":
        eta += 2

    return int(base), int(eta)


def get_partners_df() -> pd.DataFrame:
    rows = query(MASTER_DB, "SELECT * FROM partners ORDER BY partner_type, partner_name")
    return pd.DataFrame(rows)


def get_catalog_df(keyword: str = "", seller_code: str = "", fuel_type: str = "") -> pd.DataFrame:
    sql = """
        SELECT mp.*, p.partner_name AS seller_name, p.city AS seller_city, p.brand_color
        FROM marketplace_products mp
        JOIN partners p ON p.partner_code = mp.seller_code
        WHERE mp.status = 'ACTIVE'
    """
    params = []

    if keyword:
        sql += " AND (mp.brand LIKE %s OR mp.model LIKE %s OR mp.vehicle_type LIKE %s)"
        like = f"%{keyword}%"
        params.extend([like, like, like])

    if seller_code:
        sql += " AND mp.seller_code = %s"
        params.append(seller_code)

    if fuel_type:
        sql += " AND mp.fuel_type = %s"
        params.append(fuel_type)

    sql += " ORDER BY mp.seller_code, mp.price"

    rows = query(MASTER_DB, sql, tuple(params))

    for row in rows:
        origin = get_seller_origin(row.get("seller_code"), row.get("seller_city"))
        row["origin_city"] = origin["origin_city"]
        row["seller_address"] = origin["seller_address"]

    return pd.DataFrame(rows)


def login_customer(email: str, password: str):
    return one(
        MASTER_DB,
        "SELECT * FROM customers WHERE email = %s AND password = %s",
        (email, password),
    )


def register_customer(full_name: str, phone: str, email: str, password: str, city: str, address: str):
    cid = "CUST-" + now_stamp()

    execute(
        MASTER_DB,
        """
        INSERT INTO customers
        (customer_global_id, full_name, phone, email, password, city, address, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """,
        (cid, full_name, phone, email, password, city, address),
    )

    return {"customer_global_id": cid, "full_name": full_name}


def get_customer_orders(customer_global_id: str) -> pd.DataFrame:
    rows = query(
        MASTER_DB,
        """
        SELECT
            o.*,
            p.partner_name AS seller_name,
            mp.brand,
            mp.model,
            mp.image_path,
            ps.provider_code,
            ps.provider_name,
            ps.payment_reference,
            ss.delivery_code,
            ss.delivery_name,
            ss.tracking_number,
            ss.current_location,
            ss.estimated_arrival
        FROM orders o
        LEFT JOIN partners p ON p.partner_code = o.seller_code
        LEFT JOIN marketplace_products mp ON mp.listing_id = o.listing_id
        LEFT JOIN payments_summary ps ON ps.order_global_id = o.order_global_id
        LEFT JOIN shipments_summary ss ON ss.order_global_id = o.order_global_id
        WHERE o.customer_global_id = %s
        ORDER BY o.created_at DESC
        """,
        (customer_global_id,),
    )

    return pd.DataFrame(rows)


def create_payment_instruction(
    order_id: str,
    provider_code: str,
    customer_name: str,
    amount: int,
    payment_channel: str,
) -> dict:
    provider = one(MASTER_DB, "SELECT * FROM partners WHERE partner_code = %s", (provider_code,)) or {}

    stamp = now_stamp()
    trx_id = f"TRX-{provider_code}-{stamp}"
    fee = int(amount * 0.015)
    net_amount = int(amount - fee)
    expires_at = (dt.datetime.now() + dt.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

    is_va = "BANK" in provider_code or "Virtual" in payment_channel
    virtual_account = "8808" + stamp[-10:] if is_va else None
    qris_code = None if is_va else "QRIS-MN-" + stamp[-8:]
    final_channel = "Virtual Account" if is_va else payment_channel

    execute(
        PAYMENT_DB,
        """
        INSERT INTO payment_transactions
        (transaction_global_id, order_global_id, provider_code, customer_name, amount, fee, net_amount,
         payment_status, risk_score, payment_channel, virtual_account, qris_code, customer_instruction, expires_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', %s, %s, %s, %s, %s, %s, NOW())
        """,
        (
            trx_id,
            order_id,
            provider_code,
            customer_name,
            amount,
            fee,
            net_amount,
            25,
            final_channel,
            virtual_account,
            qris_code,
            "Bayar sesuai nominal, lalu klik Saya sudah bayar di halaman marketplace.",
            expires_at,
        ),
    )

    return {
        "transaction_global_id": trx_id,
        "provider_code": provider_code,
        "provider_name": provider.get("partner_name", provider_code),
        "amount": amount,
        "payment_status": "PENDING",
        "payment_channel": final_channel,
        "virtual_account": virtual_account,
        "qris_code": qris_code,
        "expires_at": expires_at,
    }


def create_checkout(
    customer: dict,
    listing_id: str,
    qty: int,
    payment_provider: str,
    payment_channel: str,
    delivery_partner: str,
    destination_city: str,
    destination_address: str,
) -> dict:
    prod = one(
        MASTER_DB,
        "SELECT * FROM marketplace_products WHERE listing_id = %s AND status = 'ACTIVE'",
        (listing_id,),
    )

    if not prod:
        raise RuntimeError("Produk tidak ditemukan.")

    if int(prod.get("stock_snapshot") or 0) < int(qty):
        raise RuntimeError("Stok marketplace tidak cukup.")

    stamp = now_stamp()
    order_id = "ORD-MN-" + stamp

    origin = get_seller_origin(prod["seller_code"])
    subtotal = int(prod["price"]) * int(qty)
    shipping_fee, eta_days = estimate_shipping(
        origin["origin_city"],
        destination_city,
        delivery_partner,
        prod.get("vehicle_type", ""),
    )
    admin_fee = 150000
    grand_total = subtotal + shipping_fee + admin_fee

    provider = one(
        MASTER_DB,
        "SELECT partner_name FROM partners WHERE partner_code = %s",
        (payment_provider,),
    ) or {"partner_name": payment_provider}

    courier = one(
        MASTER_DB,
        "SELECT partner_name FROM partners WHERE partner_code = %s",
        (delivery_partner,),
    ) or {"partner_name": delivery_partner}

    payment = create_payment_instruction(
        order_id,
        payment_provider,
        customer["full_name"],
        grand_total,
        payment_channel,
    )

    execute(
        MASTER_DB,
        """
        INSERT INTO orders
        (order_global_id, customer_global_id, buyer_name, seller_code, listing_id, vehicle_code, qty,
         subtotal, shipping_fee, discount_amount, grand_total, payment_method, payment_status,
         order_status, shipment_status, destination_city, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, 'PENDING',
                'WAITING_PAYMENT', 'PAYMENT_PENDING', %s, NOW())
        """,
        (
            order_id,
            customer["customer_global_id"],
            customer["full_name"],
            prod["seller_code"],
            prod["listing_id"],
            prod["external_vehicle_code"],
            qty,
            subtotal,
            shipping_fee,
            grand_total,
            provider["partner_name"],
            destination_city,
        ),
    )

    execute(
        MASTER_DB,
        """
        INSERT INTO order_status_history(order_global_id, status, note, created_at)
        VALUES (%s, 'ORDER_CREATED', 'Pesanan dibuat. Menunggu pembayaran dari pembeli.', NOW())
        """,
        (order_id,),
    )

    execute(
        MASTER_DB,
        """
        INSERT INTO payments_summary
        (order_global_id, provider_code, provider_name, payment_reference, amount, payment_status, paid_at)
        VALUES (%s, %s, %s, %s, %s, 'PENDING', NULL)
        """,
        (
            order_id,
            payment_provider,
            provider["partner_name"],
            payment["transaction_global_id"],
            grand_total,
        ),
    )

    execute(
        MASTER_DB,
        """
        INSERT INTO shipments_summary
        (order_global_id, delivery_code, delivery_name, tracking_number, destination_city,
         shipment_status, current_location, estimated_arrival, updated_at)
        VALUES (%s, %s, %s, '-', %s, 'PAYMENT_PENDING', %s, DATE_ADD(CURDATE(), INTERVAL %s DAY), NOW())
        """,
        (
            order_id,
            delivery_partner,
            courier["partner_name"],
            destination_city,
            origin["seller_address"],
            eta_days,
        ),
    )

    return {
        "message": "Instruksi pembayaran dibuat",
        "order_global_id": order_id,
        "buyer_name": customer["full_name"],
        "vehicle": {
            "brand": prod["brand"],
            "model": prod["model"],
            "seller_code": prod["seller_code"],
            "qty": qty,
        },
        "seller": {
            "seller_code": prod["seller_code"],
            "origin_city": origin["origin_city"],
            "seller_address": origin["seller_address"],
        },
        "price_summary": {
            "subtotal": subtotal,
            "admin_fee": admin_fee,
            "shipping_fee": shipping_fee,
            "discount": 0,
            "grand_total": grand_total,
            "estimated_days": eta_days,
        },
        "payment_instruction": payment,
        "delivery_plan": {
            "delivery_code": delivery_partner,
            "delivery_name": courier["partner_name"],
            "destination_city": destination_city,
            "destination_address": destination_address or destination_city,
            "eta_days": eta_days,
        },
    }


def confirm_payment(order_global_id: str) -> dict:
    order = one(MASTER_DB, "SELECT * FROM orders WHERE order_global_id = %s", (order_global_id,))

    if not order:
        raise RuntimeError("Order tidak ditemukan.")

    if order.get("payment_status") == "PAID":
        return {
            "message": "Pembayaran sudah pernah dikonfirmasi",
            "order_global_id": order_global_id,
        }

    prod = one(MASTER_DB, "SELECT * FROM marketplace_products WHERE listing_id = %s", (order["listing_id"],))
    cust = one(MASTER_DB, "SELECT * FROM customers WHERE customer_global_id = %s", (order["customer_global_id"],))
    pay_sum = one(MASTER_DB, "SELECT * FROM payments_summary WHERE order_global_id = %s", (order_global_id,))
    planned_ship = one(MASTER_DB, "SELECT * FROM shipments_summary WHERE order_global_id = %s", (order_global_id,))

    if not prod or not cust or not pay_sum:
        raise RuntimeError("Data order tidak lengkap.")

    delivery_code = planned_ship.get("delivery_code") if planned_ship else "DEL-NEO"
    origin = get_seller_origin(order["seller_code"])

    courier = one(
        MASTER_DB,
        "SELECT partner_name FROM partners WHERE partner_code = %s",
        (delivery_code,),
    ) or {"partner_name": delivery_code}

    _, eta_days = estimate_shipping(
        origin["origin_city"],
        order["destination_city"],
        delivery_code,
        prod.get("vehicle_type", ""),
    )

    tracking_number = "TRK-MN-" + now_stamp()[-8:]
    shipment_id = "SHIP-" + now_stamp()

    execute(
        PAYMENT_DB,
        "UPDATE payment_transactions SET payment_status = 'PAID' WHERE transaction_global_id = %s",
        (pay_sum["payment_reference"],),
    )

    seller_db = SELLER_DBS.get(order["seller_code"], "seller_auto2000_db")
    unit_cost = int(prod.get("unit_cost") or 0)
    revenue = int(order["subtotal"] or 0)
    gross_profit = revenue - (unit_cost * int(order["qty"] or 1))
    seller_order_id = "SO-" + order_global_id

    execute(
        seller_db,
        """
        UPDATE seller_inventory
        SET stock_available = GREATEST(stock_available - %s, 0),
            reserved_stock = reserved_stock + %s
        WHERE vehicle_code = %s
        """,
        (order["qty"], order["qty"], order["vehicle_code"]),
    )

    execute(
        seller_db,
        """
        INSERT INTO seller_orders
        (seller_order_global_id, marketplace_order_global_id, customer_global_id, customer_name, vehicle_code,
         qty, revenue, unit_cost, gross_profit, order_status, shipment_status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PROCESSING', 'READY_TO_SHIP', NOW())
        """,
        (
            seller_order_id,
            order_global_id,
            cust["customer_global_id"],
            cust["full_name"],
            order["vehicle_code"],
            order["qty"],
            revenue,
            unit_cost,
            gross_profit,
        ),
    )

    execute(
        seller_db,
        """
        INSERT INTO seller_customers(customer_global_id, customer_name, phone, city, total_spend)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            cust["customer_global_id"],
            cust["full_name"],
            cust["phone"],
            cust["city"],
            int(order["grand_total"] or 0),
        ),
    )

    execute(
        DELIVERY_DB,
        """
        INSERT INTO delivery_shipments
        (shipment_global_id, order_global_id, delivery_code, buyer_name, origin_city, destination_city,
         tracking_number, shipment_status, current_location, estimated_arrival, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'READY_TO_SHIP', %s, DATE_ADD(CURDATE(), INTERVAL %s DAY), NOW())
        """,
        (
            shipment_id,
            order_global_id,
            delivery_code,
            cust["full_name"],
            origin["origin_city"],
            order["destination_city"],
            tracking_number,
            origin["seller_address"],
            eta_days,
        ),
    )

    execute(
        DELIVERY_DB,
        """
        INSERT INTO tracking_events(tracking_number, status, location, note, created_at)
        VALUES (%s, 'READY_TO_SHIP', %s, 'Shipment dibuat setelah pembayaran terkonfirmasi.', NOW())
        """,
        (tracking_number, origin["seller_address"]),
    )

    execute(
        MASTER_DB,
        """
        UPDATE orders
        SET payment_status = 'PAID',
            order_status = 'PROCESSING',
            shipment_status = 'READY_TO_SHIP'
        WHERE order_global_id = %s
        """,
        (order_global_id,),
    )

    execute(
        MASTER_DB,
        "UPDATE payments_summary SET payment_status = 'PAID', paid_at = NOW() WHERE order_global_id = %s",
        (order_global_id,),
    )

    execute(
        MASTER_DB,
        "UPDATE marketplace_products SET stock_snapshot = GREATEST(stock_snapshot - %s, 0) WHERE listing_id = %s",
        (order["qty"], order["listing_id"]),
    )

    execute(
        MASTER_DB,
        """
        UPDATE shipments_summary
        SET tracking_number = %s,
            shipment_status = 'READY_TO_SHIP',
            current_location = %s,
            estimated_arrival = DATE_ADD(CURDATE(), INTERVAL %s DAY),
            updated_at = NOW()
        WHERE order_global_id = %s
        """,
        (
            tracking_number,
            origin["seller_address"],
            eta_days,
            order_global_id,
        ),
    )

    execute(
        MASTER_DB,
        """
        INSERT INTO order_status_history(order_global_id, status, note, created_at)
        VALUES
        (%s, 'PAYMENT_CONFIRMED', 'Pembeli mengonfirmasi pembayaran. Status transaksi menjadi PAID.', NOW()),
        (%s, 'SELLER_PROCESSING', 'Order masuk ke seller. Seller menyiapkan unit kendaraan.', NOW()),
        (%s, 'SHIPMENT_CREATED', 'Delivery partner membuat nomor tracking dan menunggu pickup.', NOW())
        """,
        (order_global_id, order_global_id, order_global_id),
    )

    fee = int(int(order["grand_total"] or 0) * 0.03)

    execute(
        MASTER_DB,
        """
        INSERT INTO settlements
        (settlement_id, order_global_id, seller_code, provider_code, gross_amount, marketplace_fee,
         seller_net_amount, settlement_status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', NOW())
        """,
        (
            "SET-" + order_global_id,
            order_global_id,
            order["seller_code"],
            pay_sum["provider_code"],
            order["grand_total"],
            fee,
            int(order["grand_total"] or 0) - fee,
        ),
    )

    return {
        "message": "Pembayaran dikonfirmasi. Pesanan diproses seller dan delivery.",
        "order_global_id": order_global_id,
        "payment_status": "PAID",
        "order_status": "PROCESSING",
        "tracking_number": tracking_number,
        "delivery_name": courier["partner_name"],
    }


def track_order(order_global_id: str) -> dict:
    order = one(MASTER_DB, "SELECT * FROM orders WHERE order_global_id = %s", (order_global_id,))
    history = query(
        MASTER_DB,
        "SELECT * FROM order_status_history WHERE order_global_id = %s ORDER BY created_at",
        (order_global_id,),
    )
    shipment = one(
        MASTER_DB,
        "SELECT * FROM shipments_summary WHERE order_global_id = %s",
        (order_global_id,),
    )

    events = []
    if shipment and shipment.get("tracking_number") and shipment.get("tracking_number") != "-":
        events = query(
            DELIVERY_DB,
            "SELECT * FROM tracking_events WHERE tracking_number = %s ORDER BY created_at",
            (shipment["tracking_number"],),
        )

    return {
        "order": order,
        "history": history,
        "shipment": shipment,
        "delivery_events": events,
    }


if "customer" not in st.session_state:
    st.session_state.customer = None
if "selected_listing" not in st.session_state:
    st.session_state.selected_listing = None
if "pending_payment" not in st.session_state:
    st.session_state.pending_payment = None
if "confirmed_order" not in st.session_state:
    st.session_state.confirmed_order = None

try:
    partners = get_partners_df()
    catalog = get_catalog_df()
except Exception as exc:
    st.error("Database belum siap. Pastikan DB online sudah diisi schema.sql dan Secrets sudah benar.")
    st.code(str(exc))
    st.stop()


with st.sidebar:
    sidebar_brand("MobilNiaga", "Marketplace kendaraan multi-company untuk pembeli", "🚘")

    if st.session_state.customer:
        sidebar_user(st.session_state.customer["full_name"], st.session_state.customer.get("email", ""))

        page = st.radio(
            "Menu",
            ["Dashboard", "Katalog Mobil", "Checkout", "Pembayaran Saya", "Tracking Pesanan", "Profil"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        if st.button("Logout", use_container_width=True):
            st.session_state.customer = None
            st.session_state.pending_payment = None
            st.session_state.confirmed_order = None
            st.rerun()
    else:
        page = "Login/Register"
        st.markdown(
            "<div class='demo-note'>Masuk sebagai pembeli untuk melihat katalog, checkout, VA/QRIS, dan tracking.</div>",
            unsafe_allow_html=True,
        )


if page == "Login/Register":
    hero(
        "MobilNiaga Marketplace",
        "Demo marketplace kendaraan multi-company: pembeli memilih mobil, membuat VA/QRIS, konfirmasi pembayaran, lalu order masuk ke seller dan delivery.",
    )

    step_pills(["1. Login/Register", "2. Pilih mobil", "3. Bayar VA/QRIS", "4. Konfirmasi bayar", "5. Tracking"])

    c1, c2 = st.columns([0.9, 1.1])

    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Login Pembeli")

        email = st.text_input("Email", value="anne@mail.com")
        password = st.text_input("Password", value="anne123", type="password")

        if st.button("Masuk", type="primary", use_container_width=True):
            cust = login_customer(email, password)
            if cust:
                st.session_state.customer = cust
                st.rerun()
            else:
                st.error("Email atau password salah.")

        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        demo_credentials(
            "Akun demo buyer",
            [
                ("Buyer", "Anne Melanika", "anne@mail.com", "anne123"),
                ("Buyer", "Soni Mahardika", "soni@mail.com", "soni123"),
                ("Buyer", "Raka Pratama", "raka@mail.com", "raka123"),
                ("Buyer", "Nadia Putri", "nadia@mail.com", "nadia123"),
            ],
        )

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Register Pembeli Baru")

        with st.form("register"):
            n = st.text_input("Nama lengkap")
            ph = st.text_input("No HP")
            em = st.text_input("Email baru")
            pw = st.text_input("Password", type="password")
            city = st.text_input("Kota", value="Yogyakarta")
            addr = st.text_area("Alamat lengkap")
            ok = st.form_submit_button("Buat akun", type="primary")

        if ok:
            try:
                register_customer(n, ph, em, pw, city, addr)
                st.success("Akun dibuat. Silakan login.")
            except Exception:
                st.error("Register gagal. Email mungkin sudah digunakan.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


orders = get_customer_orders(st.session_state.customer["customer_global_id"])


if page == "Dashboard":
    hero(
        f"Selamat datang, {st.session_state.customer['full_name'].split()[0]}",
        "Dashboard pembeli dibuat simpel: lihat katalog, pembayaran pending, dan tracking pesanan aktif.",
    )

    pending = int((orders.payment_status == "PENDING").sum()) if not orders.empty and "payment_status" in orders else 0
    active = int((orders.shipment_status != "DELIVERED").sum()) if not orders.empty and "shipment_status" in orders else 0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        kpi("Katalog Aktif", len(catalog), "unit multi-seller")
    with c2:
        kpi("Pesanan Saya", len(orders), "riwayat order")
    with c3:
        kpi("Menunggu Bayar", pending, "perlu konfirmasi")
    with c4:
        kpi("Pengiriman Aktif", active, "belum delivered")

    col1, col2 = st.columns([1.2, 0.8])

    with col1:
        section("Mobil rekomendasi")
        cards = st.columns(3)

        for i, row in catalog.head(3).iterrows():
            with cards[i % 3]:
                img = ROOT / row["image_path"]
                st.markdown("<div class='product'>", unsafe_allow_html=True)

                if img.exists():
                    st.image(str(img), use_container_width=True)

                st.markdown(
                    f"""
                    <div class='body'>
                        {badge(row['seller_name'], '#e0f2fe', '#075985')}
                        <div class='product-title'>{row['brand']} {row['model']}</div>
                        <div class='product-meta'>{row['year']} • {row['fuel_type']} • {row['transmission']}</div>
                        <div class='price'>{money(row['price'])}</div>
                    </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col2:
        section("Langkah pemesanan")
        info_card(
            "Alur singkat",
            "1. Pilih mobil dari katalog<br>2. Lengkapi alamat pengiriman<br>3. Pilih VA atau QRIS<br>4. Klik <b>Saya Sudah Bayar</b><br>5. Seller memproses unit<br>6. Kurir membuat tracking",
            "✅",
        )


elif page == "Katalog Mobil":
    hero(
        "Katalog Mobil Multi-Seller",
        "Produk dikelompokkan dari banyak seller resmi. Setiap mobil punya seller, alamat asal, ongkir estimasi, dan stok sendiri.",
    )

    sellers = partners[partners.partner_type == "SELLER"] if not partners.empty else pd.DataFrame()

    f1, f2, f3 = st.columns([1.4, 1, 1])

    with f1:
        keyword = st.text_input("Cari mobil", placeholder="Contoh: Avanza, Brio, Ioniq")

    with f2:
        seller_name = st.selectbox("Seller", ["Semua"] + (sellers.partner_name.tolist() if not sellers.empty else []))

    with f3:
        fuel = st.selectbox("Bahan bakar", ["Semua"] + (sorted(catalog.fuel_type.dropna().unique().tolist()) if not catalog.empty else []))

    seller_code = ""

    if seller_name != "Semua" and not sellers.empty:
        seller_code = sellers.loc[sellers.partner_name == seller_name, "partner_code"].iloc[0]

    data = get_catalog_df(keyword, seller_code, "" if fuel == "Semua" else fuel)

    cols = st.columns(3)

    for idx, row in data.reset_index(drop=True).iterrows():
        with cols[idx % 3]:
            addr = get_seller_origin(row.seller_code, row.seller_city)

            st.markdown("<div class='product'>", unsafe_allow_html=True)

            img = ROOT / row.image_path
            if img.exists():
                st.image(str(img), use_container_width=True)

            st.markdown(
                f"""
                <div class='body'>
                    {badge(row.seller_name, '#eef2ff', '#3730a3')}
                    {badge(row.vehicle_type, '#ecfeff', '#155e75')}
                    {badge(row.fuel_type, '#f0fdf4', '#166534')}
                    <div class='product-title'>{html.escape(str(row.brand))} {html.escape(str(row.model))}</div>
                    <div class='product-meta'>{row.year} • {row.transmission} • stok {row.stock_snapshot} unit</div>
                    <div class='price'>{money(row.price)}</div>
                    <div class='product-meta'><b>Asal pengiriman:</b><br>{html.escape(addr['seller_address'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("Beli mobil ini", key="buy_" + row.listing_id, type="primary", use_container_width=True):
                st.session_state.selected_listing = row.listing_id
                st.success("Mobil dipilih. Buka menu Checkout.")

            st.markdown("</div>", unsafe_allow_html=True)


elif page == "Checkout":
    hero(
        "Checkout Aman",
        "Lengkapi alamat, pilih kurir, pilih metode bayar. Setelah VA/QRIS muncul, klik konfirmasi bayar agar seller mulai memproses unit.",
    )

    if catalog.empty:
        st.info("Katalog kosong. Pastikan database sudah berisi data produk.")
    else:
        fintech = partners[partners.partner_type == "FINTECH"]
        delivery = partners[partners.partner_type == "DELIVERY"]

        labels = {
            f"{r.brand} {r.model} — {r.seller_name} — {money(r.price)}": r.listing_id
            for r in catalog.itertuples()
        }

        default = 0

        if st.session_state.selected_listing:
            for i, (_, v) in enumerate(labels.items()):
                if v == st.session_state.selected_listing:
                    default = i

        left, right = st.columns([1.05, 0.95])

        with left:
            section("1. Data mobil dan alamat")

            pick = st.selectbox("Pilih mobil", list(labels.keys()), index=default)
            selected = catalog[catalog.listing_id == labels[pick]].iloc[0]
            seller_addr = get_seller_origin(selected.seller_code, selected.seller_city)

            qty = st.number_input("Jumlah unit", 1, 3, 1)

            st.markdown(
                f"""
                <div class='soft-card'>
                    <b>{selected.brand} {selected.model}</b><br>
                    {selected.seller_name}<br>
                    <span style='color:#64748b'>{seller_addr['seller_address']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            name = st.text_input("Nama penerima", st.session_state.customer["full_name"])
            phone = st.text_input("Nomor HP", st.session_state.customer["phone"])
            city = st.text_input("Kota tujuan", st.session_state.customer["city"])
            address = st.text_area("Alamat lengkap pengiriman", st.session_state.customer["address"])

        with right:
            section("2. Pembayaran dan kurir")

            pay_map = {r.partner_name: r.partner_code for r in fintech.itertuples()}
            del_map = {r.partner_name: r.partner_code for r in delivery.itertuples()}

            pay = st.selectbox("Payment gateway", list(pay_map.keys()))
            channel = "Virtual Account" if "Bank" in pay else st.selectbox("Metode pembayaran", ["QRIS", "Wallet Payment"])
            dele = st.selectbox("Kurir kendaraan", list(del_map.keys()))

            subtotal = int(selected.price) * int(qty)
            visual_shipping, _ = estimate_shipping(seller_addr["origin_city"], city, del_map[dele], selected.vehicle_type)
            admin = 150000
            total = subtotal + visual_shipping + admin

            st.markdown(
                "<div class='card'>"
                + amount_row("Harga kendaraan", money(subtotal))
                + amount_row("Estimasi ongkir / handling unit", money(visual_shipping))
                + amount_row("Biaya admin", money(admin))
                + "<hr>"
                + amount_row("Estimasi total", money(total), True)
                + "</div>",
                unsafe_allow_html=True,
            )

            if st.button("Buat pembayaran", type="primary", use_container_width=True):
                try:
                    res = create_checkout(
                        st.session_state.customer,
                        labels[pick],
                        int(qty),
                        pay_map[pay],
                        channel,
                        del_map[dele],
                        city,
                        address,
                    )
                    st.session_state.pending_payment = res
                    st.session_state.confirmed_order = None
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        if st.session_state.pending_payment:
            res = st.session_state.pending_payment
            st.success("Instruksi pembayaran berhasil dibuat. Order ID: " + res["order_global_id"])

            payinfo = res["payment_instruction"]
            price = res["price_summary"]
            plan = res["delivery_plan"]
            seller = res["seller"]

            c1, c2, c3 = st.columns([1, 1, 1])

            with c1:
                info_card(
                    "Tagihan",
                    amount_row("Harga kendaraan", money(price["subtotal"]))
                    + amount_row("Ongkir", money(price["shipping_fee"]))
                    + amount_row("Admin", money(price["admin_fee"]))
                    + "<hr>"
                    + amount_row("Total bayar", money(price["grand_total"]), True),
                    "🧾",
                )

            with c2:
                if payinfo.get("virtual_account"):
                    body = (
                        f"Provider: <b>{payinfo['provider_name']}</b><br>"
                        f"Nomor VA:<br><b style='font-size:1.35rem'>{payinfo['virtual_account']}</b><br>"
                        f"Nominal: <b>{money(payinfo['amount'])}</b><br>"
                        f"Batas bayar: {payinfo['expires_at']}"
                    )
                    info_card("Virtual Account", body, "🏦", "pay-box")
                else:
                    st.markdown(
                        f"""
                        <div class='qris-box'>
                            <b>QRIS {html.escape(payinfo['provider_name'])}</b>
                            <div class='qris-grid'>▣ ▦ ▣<br>▦ ▣ ▦<br>▣ ▦ ▣</div>
                            <div><b>{html.escape(str(payinfo.get('qris_code', 'QRIS-MN')))}</b></div>
                            <small>Bayar tepat {money(payinfo['amount'])}</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            with c3:
                body = (
                    f"Seller asal:<br><b>{seller['origin_city']}</b><br>"
                    f"{html.escape(seller['seller_address'])}<br><br>"
                    f"Kurir: <b>{plan['delivery_name']}</b><br>"
                    f"Estimasi tiba: <b>{plan['eta_days']} hari</b><br>"
                    f"Tujuan: {html.escape(plan['destination_address'])}"
                )
                info_card("Pengiriman", body, "🚚")

            st.write("")

            if st.button("Saya sudah bayar, proses pesanan", type="primary", use_container_width=True):
                try:
                    conf = confirm_payment(res["order_global_id"])
                    st.session_state.confirmed_order = conf
                    st.success("Pembayaran berhasil dikonfirmasi. Seller mulai memproses pesanan.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        if st.session_state.confirmed_order:
            conf = st.session_state.confirmed_order
            info_card(
                "Pesanan diproses",
                f"Order <b>{conf['order_global_id']}</b> sudah PAID dan diproses seller.<br>"
                f"Tracking number: <b>{conf.get('tracking_number', '-')}</b><br>"
                f"Delivery: {conf.get('delivery_name', '-')}",
                "✅",
                "card",
            )


elif page == "Pembayaran Saya":
    hero("Pembayaran Saya", "Pantau status pembayaran dan lanjutkan konfirmasi jika masih pending.")

    my = get_customer_orders(st.session_state.customer["customer_global_id"])

    if my.empty:
        st.info("Belum ada pesanan.")
    else:
        show = my[
            [
                "order_global_id",
                "seller_name",
                "brand",
                "model",
                "grand_total",
                "payment_method",
                "payment_status",
                "order_status",
                "created_at",
            ]
        ].copy()

        show["grand_total"] = show["grand_total"].apply(money)
        df_table(show)

        pending = my[my.payment_status == "PENDING"]

        if not pending.empty:
            section("Konfirmasi pembayaran pending")
            oid = st.selectbox("Pilih order pending", pending.order_global_id.tolist())

            if st.button("Saya sudah bayar untuk order ini", type="primary"):
                try:
                    conf = confirm_payment(oid)
                    st.success("Pembayaran dikonfirmasi. Order diproses seller.")
                    st.session_state.confirmed_order = conf
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


elif page == "Tracking Pesanan":
    hero("Tracking Pesanan", "Tracking dibuat seperti timeline, bukan log teknis. Masukkan Order ID untuk melihat progres.")

    default = orders.order_global_id.iloc[0] if not orders.empty else ""
    oid = st.text_input("Order ID", value=default)

    if st.button("Lacak pesanan", type="primary") and oid:
        res = track_order(oid)

        if not res or not res.get("order"):
            st.warning("Order tidak ditemukan.")
        else:
            order = res["order"]
            ship = res.get("shipment") or {}

            c1, c2, c3 = st.columns(3)

            with c1:
                kpi("Status order", order["order_status"], order["order_global_id"])

            with c2:
                kpi("Pembayaran", order["payment_status"], money(order["grand_total"]))

            with c3:
                kpi("Pengiriman", ship.get("shipment_status", "-"), ship.get("tracking_number", "-"))

            section("Timeline order")
            st.markdown("<div class='timeline'>", unsafe_allow_html=True)

            for ev in res.get("history", []):
                st.markdown(
                    f"""
                    <div class='timeline-item'>
                        <b>{status_badge(ev['status'])}</b><br>
                        <span>{html.escape(str(ev['note']))}</span><br>
                        <small>{ev['created_at']}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            for ev in res.get("delivery_events", []):
                st.markdown(
                    f"""
                    <div class='timeline-item'>
                        <b>{status_badge(ev['status'])}</b><br>
                        <span>{html.escape(str(ev['note']))}</span><br>
                        <small>{ev['location']} • {ev['created_at']}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)


elif page == "Profil":
    hero("Profil Pembeli", "Data akun dan alamat utama pembeli.")

    c1, c2 = st.columns(2)

    with c1:
        info_card(
            "Akun",
            f"Nama: <b>{st.session_state.customer['full_name']}</b><br>"
            f"Email: {st.session_state.customer['email']}<br>"
            f"No HP: {st.session_state.customer['phone']}",
            "👤",
        )

    with c2:
        info_card(
            "Alamat",
            f"Kota: <b>{st.session_state.customer['city']}</b><br>"
            f"{html.escape(st.session_state.customer['address'])}",
            "📍",
        )