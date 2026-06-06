from __future__ import annotations

import datetime as dt
import html
from pathlib import Path

import pandas as pd
import streamlit as st

from db_common import query, one, execute, SELLER_DBS
from ui_style import (
    setup_page, hero, kpi, money, section, df_table, info_card,
    SELLER_THEME, SELLER_ADDRESS, status_badge, sidebar_brand,
    sidebar_user, demo_credentials, step_pills
)

ROOT = Path(__file__).resolve().parent
MASTER_DB = "mobilniaga_master"
DELIVERY_DB = "delivery_gateway_db"

setup_page("MobilNiaga Seller Center", "🏢")

SELLER_CREDENTIALS = {
    "SELLER-A2000": ("sales@auto2000.co.id", "seller123"),
    "SELLER-HONDA": ("sales@honda.co.id", "seller123"),
    "SELLER-MITSUBISHI": ("sales@mitsubishi.co.id", "seller123"),
    "SELLER-HYUNDAI": ("sales@hyundai.co.id", "seller123"),
    "SELLER-SUZUKI": ("sales@suzuki.co.id", "seller123"),
    "SELLER-WULING": ("sales@wuling.co.id", "seller123"),
}


def now_text() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def seller_db_name(seller_code: str) -> str:
    return SELLER_DBS.get(seller_code, "seller_auto2000_db")


def table_has_column(db: str, table: str, column: str) -> bool:
    try:
        rows = query(db, f"SHOW COLUMNS FROM `{table}` LIKE %s", (column,))
        return bool(rows)
    except Exception:
        return False


def table_exists(db: str, table: str) -> bool:
    try:
        rows = query(db, "SHOW TABLES LIKE %s", (table,))
        return bool(rows)
    except Exception:
        return False


def get_seller_address(seller_code: str, fallback_city: str = "") -> dict:
    addr = SELLER_ADDRESS.get(seller_code, {})
    return {
        "address": addr.get("address") or fallback_city or "Seller Warehouse",
        "city": addr.get("city") or fallback_city or "Jakarta",
        "name": addr.get("name") or seller_code,
    }


def get_sellers_df() -> pd.DataFrame:
    rows = query(
        MASTER_DB,
        """
        SELECT
            partner_code AS seller_code,
            partner_name AS seller_name,
            partner_name,
            city,
            status,
            brand_color
        FROM partners
        WHERE partner_type = 'SELLER'
        ORDER BY partner_name
        """
    )
    return pd.DataFrame(rows)


def login_seller(seller_code: str, email: str, password: str):
    default_email, default_password = SELLER_CREDENTIALS.get(seller_code, ("", ""))

    if email != default_email or password != default_password:
        return None

    seller = one(
        MASTER_DB,
        """
        SELECT
            partner_code AS seller_code,
            partner_name AS seller_name,
            partner_name,
            city,
            status,
            brand_color
        FROM partners
        WHERE partner_code = %s
          AND partner_type = 'SELLER'
        """,
        (seller_code,)
    )

    if not seller:
        return None

    return {
        "seller": seller,
        "user": {
            "email": email,
            "role": "SELLER_ADMIN",
        }
    }


def seller_vehicle_codes(seller_code: str) -> list[str]:
    rows = query(
        MASTER_DB,
        """
        SELECT external_vehicle_code
        FROM marketplace_products
        WHERE seller_code = %s
        """,
        (seller_code,)
    )
    return [r["external_vehicle_code"] for r in rows if r.get("external_vehicle_code")]


def get_inventory_df(seller_code: str) -> pd.DataFrame:
    db = seller_db_name(seller_code)
    codes = seller_vehicle_codes(seller_code)

    if codes:
        placeholders = ",".join(["%s"] * len(codes))
        rows = query(
            db,
            f"""
            SELECT 
                v.*,
                i.inventory_id,
                i.stock_available,
                i.reserved_stock,
                i.warehouse,
                i.last_updated
            FROM vehicles v
            LEFT JOIN seller_inventory i 
                ON i.vehicle_code = v.vehicle_code
            WHERE v.vehicle_code IN ({placeholders})
            ORDER BY v.brand, v.model
            """,
            tuple(codes),
        )
    else:
        rows = query(
            db,
            """
            SELECT 
                v.*,
                i.inventory_id,
                i.stock_available,
                i.reserved_stock,
                i.warehouse,
                i.last_updated
            FROM vehicles v
            LEFT JOIN seller_inventory i 
                ON i.vehicle_code = v.vehicle_code
            WHERE v.seller_code = %s
            ORDER BY v.brand, v.model
            """,
            (seller_code,),
        )

    return pd.DataFrame(rows)


def get_orders_df(seller_code: str, inventory: pd.DataFrame) -> pd.DataFrame:
    db = seller_db_name(seller_code)
    has_seller_code = table_has_column(db, "seller_orders", "seller_code")

    if has_seller_code:
        rows = query(
            db,
            """
            SELECT *
            FROM seller_orders
            WHERE seller_code = %s
            ORDER BY created_at DESC
            """,
            (seller_code,)
        )
    else:
        codes = inventory["vehicle_code"].dropna().astype(str).tolist() if not inventory.empty and "vehicle_code" in inventory else []

        if codes:
            placeholders = ",".join(["%s"] * len(codes))
            rows = query(
                db,
                f"""
                SELECT *
                FROM seller_orders
                WHERE vehicle_code IN ({placeholders})
                ORDER BY created_at DESC
                """,
                tuple(codes)
            )
        else:
            rows = []

    orders = pd.DataFrame(rows)

    if orders.empty:
        return orders

    if not inventory.empty and "vehicle_code" in inventory:
        product_cols = [
            c for c in [
                "vehicle_code", "brand", "model", "year", "vehicle_type",
                "fuel_type", "transmission", "image_path"
            ]
            if c in inventory.columns
        ]

        orders = orders.merge(
            inventory[product_cols].drop_duplicates("vehicle_code"),
            on="vehicle_code",
            how="left",
        )

    return orders


def get_profit_df(orders: pd.DataFrame) -> pd.DataFrame:
    if orders.empty:
        return pd.DataFrame(columns=["recap_date", "vehicle_code", "revenue", "cost", "gross_profit"])

    data = orders.copy()

    if "created_at" in data.columns:
        data["recap_date"] = pd.to_datetime(data["created_at"]).dt.date.astype(str)
    else:
        data["recap_date"] = dt.date.today().isoformat()

    data["revenue"] = pd.to_numeric(data.get("revenue", 0), errors="coerce").fillna(0)
    data["unit_cost"] = pd.to_numeric(data.get("unit_cost", 0), errors="coerce").fillna(0)
    data["qty"] = pd.to_numeric(data.get("qty", 1), errors="coerce").fillna(1)
    data["cost"] = data["unit_cost"] * data["qty"]

    if "gross_profit" not in data.columns:
        data["gross_profit"] = data["revenue"] - data["cost"]

    data["gross_profit"] = pd.to_numeric(data["gross_profit"], errors="coerce").fillna(0)

    return data[["recap_date", "vehicle_code", "revenue", "cost", "gross_profit"]]


def get_customers_df(seller_code: str, orders: pd.DataFrame) -> pd.DataFrame:
    db = seller_db_name(seller_code)
    has_seller_code = table_has_column(db, "seller_customers", "seller_code")

    if has_seller_code:
        rows = query(
            db,
            """
            SELECT *
            FROM seller_customers
            WHERE seller_code = %s
            ORDER BY total_spend DESC
            """,
            (seller_code,)
        )
        return pd.DataFrame(rows)

    if orders.empty or "customer_global_id" not in orders.columns:
        return pd.DataFrame()

    customer_ids = orders["customer_global_id"].dropna().astype(str).unique().tolist()

    if not customer_ids:
        return pd.DataFrame()

    placeholders = ",".join(["%s"] * len(customer_ids))

    try:
        rows = query(
            db,
            f"""
            SELECT *
            FROM seller_customers
            WHERE customer_global_id IN ({placeholders})
            ORDER BY total_spend DESC
            """,
            tuple(customer_ids)
        )
    except Exception:
        rows = []

    return pd.DataFrame(rows)


def update_order_status(seller_code: str, order_id: str, new_status: str, shipment_status: str) -> str:
    db = seller_db_name(seller_code)
    addr = get_seller_address(seller_code)

    execute(
        db,
        """
        UPDATE seller_orders
        SET order_status = %s,
            shipment_status = %s
        WHERE marketplace_order_global_id = %s
        """,
        (new_status, shipment_status, order_id)
    )

    execute(
        MASTER_DB,
        """
        UPDATE orders
        SET order_status = %s,
            shipment_status = %s
        WHERE order_global_id = %s
          AND seller_code = %s
        """,
        (new_status, shipment_status, order_id, seller_code)
    )

    execute(
        MASTER_DB,
        """
        UPDATE shipments_summary
        SET shipment_status = %s,
            current_location = %s,
            updated_at = NOW()
        WHERE order_global_id = %s
        """,
        (shipment_status, addr["address"], order_id)
    )

    execute(
        MASTER_DB,
        """
        INSERT INTO order_status_history(order_global_id, status, note, created_at)
        VALUES (%s, %s, %s, NOW())
        """,
        (
            order_id,
            new_status,
            f"Seller {seller_code} mengubah status order menjadi {new_status}.",
        )
    )

    shipment = one(
        MASTER_DB,
        """
        SELECT tracking_number
        FROM shipments_summary
        WHERE order_global_id = %s
        """,
        (order_id,)
    )

    if shipment and shipment.get("tracking_number") and shipment["tracking_number"] != "-":
        try:
            execute(
                DELIVERY_DB,
                """
                UPDATE delivery_shipments
                SET shipment_status = %s,
                    current_location = %s
                WHERE order_global_id = %s
                """,
                (shipment_status, addr["address"], order_id)
            )

            execute(
                DELIVERY_DB,
                """
                INSERT INTO tracking_events(tracking_number, status, location, note, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (
                    shipment["tracking_number"],
                    shipment_status,
                    addr["address"],
                    f"Seller memperbarui status menjadi {shipment_status}.",
                )
            )
        except Exception:
            pass

    return "Status order berhasil diperbarui."


def restock_inventory(seller_code: str, supplier_code: str, vehicle_code: str, qty: int) -> str:
    db = seller_db_name(seller_code)

    execute(
        db,
        """
        UPDATE seller_inventory
        SET stock_available = stock_available + %s
        WHERE vehicle_code = %s
        """,
        (qty, vehicle_code)
    )

    execute(
        MASTER_DB,
        """
        UPDATE marketplace_products
        SET stock_snapshot = stock_snapshot + %s
        WHERE seller_code = %s
          AND external_vehicle_code = %s
        """,
        (qty, seller_code, vehicle_code)
    )

    if table_exists(db, "supplier_restock_requests"):
        try:
            execute(
                db,
                """
                INSERT INTO supplier_restock_requests
                (supplier_code, vehicle_code, qty, status, created_at)
                VALUES (%s, %s, %s, 'COMPLETED', NOW())
                """,
                (supplier_code, vehicle_code, qty)
            )
        except Exception:
            pass

    return f"Restock {qty} unit berhasil ditambahkan ke inventory."


if "seller_auth" not in st.session_state:
    st.session_state.seller_auth = None


def login_screen():
    hero(
        "Seller Center Multi-Company",
        "Setiap perusahaan seller login sendiri. Data inventory, order masuk, profit, dan pelanggan otomatis difilter sesuai company yang aktif.",
    )

    step_pills(["Login company", "Kelola katalog", "Proses order paid", "Update pengiriman", "Pantau profit"])

    try:
        sellers = get_sellers_df()
    except Exception as exc:
        st.error("Database belum siap. Pastikan Streamlit Secrets dan schema database sudah benar.")
        st.code(str(exc))
        st.stop()

    if sellers.empty:
        st.info("Data seller belum tersedia di database.")
        st.stop()

    c1, c2 = st.columns([0.9, 1.1])

    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Login Seller")

        seller_name = st.selectbox("Pilih company seller", sellers.seller_name.tolist())
        seller_code = sellers.loc[sellers.seller_name == seller_name, "seller_code"].iloc[0]

        email_default, pass_default = SELLER_CREDENTIALS.get(seller_code, ("", ""))

        email = st.text_input("Email company", value=email_default)
        password = st.text_input("Password", value=pass_default, type="password")

        if st.button("Masuk Seller Center", type="primary", use_container_width=True):
            auth = login_seller(seller_code, email, password)

            if auth:
                st.session_state.seller_auth = auth
                st.rerun()
            else:
                st.error("Login gagal. Pilih seller dan akun yang sesuai.")

        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        demo_credentials(
            "Akun demo seller",
            [
                ("Toyota", "Auto2000 Official", "sales@auto2000.co.id", "seller123"),
                ("Honda", "Honda Prospect Motor", "sales@honda.co.id", "seller123"),
                ("Mitsubishi", "Mitsubishi Motors", "sales@mitsubishi.co.id", "seller123"),
                ("Hyundai", "Hyundai Motors Indonesia", "sales@hyundai.co.id", "seller123"),
                ("Suzuki", "Suzuki Indomobil", "sales@suzuki.co.id", "seller123"),
                ("Wuling", "Wuling Motors", "sales@wuling.co.id", "seller123"),
            ],
        )

        info_card(
            "Data terpisah per perusahaan",
            "Setiap seller hanya melihat inventory, order, profit, dan pelanggan miliknya sendiri.",
            "🔐",
        )

        show = sellers.rename(
            columns={
                "seller_code": "Kode",
                "seller_name": "Company",
                "city": "Kota",
            }
        )

        df_table(show[["Kode", "Company", "Kota"]])

    st.stop()


if not st.session_state.seller_auth:
    login_screen()


auth = st.session_state.seller_auth
seller = auth["seller"]
user = auth["user"]

seller_code = seller["seller_code"]
primary, soft, label = SELLER_THEME.get(
    seller_code,
    ("#2563eb", "#dbeafe", seller["seller_name"]),
)

addr = get_seller_address(seller_code, seller.get("city", ""))

with st.sidebar:
    sidebar_brand("Seller Center", "Portal perusahaan seller", "🏢")
    sidebar_user(seller["seller_name"], "Company seller aktif")

    page = st.radio(
        "Menu",
        [
            "Dashboard",
            "Katalog Saya",
            "Order Masuk",
            "Pengiriman Seller",
            "Laporan Profit",
            "Restock Supplier",
            "Pelanggan",
            "Profil Company",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    if st.button("Logout", use_container_width=True):
        st.session_state.seller_auth = None
        st.rerun()


hero(
    seller["seller_name"],
    f"Seller portal khusus {seller['seller_name']}. Alamat pengiriman: {addr['address']}",
    f"linear-gradient(120deg,{primary},#e0f2fe,#fff)",
)

try:
    inventory = get_inventory_df(seller_code)
    orders = get_orders_df(seller_code, inventory)
    profit = get_profit_df(orders)
    customers = get_customers_df(seller_code, orders)
except Exception as exc:
    st.error("Data seller gagal dimuat. Cek schema database dan Secrets.")
    st.code(str(exc))
    st.stop()


if page == "Dashboard":
    total_stock = int(inventory.stock_available.sum()) if not inventory.empty and "stock_available" in inventory else 0
    total_profit = profit.gross_profit.sum() if not profit.empty and "gross_profit" in profit else 0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        kpi("Unit Aktif", len(inventory), "model di katalog seller")

    with c2:
        kpi("Total Stok", total_stock, "unit tersedia")

    with c3:
        kpi("Order Masuk", len(orders), "dari marketplace")

    with c4:
        kpi("Gross Profit", money(total_profit), "akumulasi profit")

    col1, col2 = st.columns([1.1, 0.9])

    with col1:
        section("Grafik profit harian")

        if not profit.empty:
            daily = profit.groupby("recap_date", as_index=False)[["revenue", "gross_profit"]].sum()
            st.line_chart(daily.set_index("recap_date"))
        else:
            st.info("Belum ada data profit.")

    with col2:
        section("Stok per model")

        if not inventory.empty and "model" in inventory.columns and "stock_available" in inventory.columns:
            st.bar_chart(inventory.set_index("model")[["stock_available"]])
        else:
            st.info("Belum ada data stok.")


elif page == "Katalog Saya":
    section("Inventory kendaraan seller")

    if not inventory.empty:
        for _, row in inventory.iterrows():
            st.markdown("<div class='card'>", unsafe_allow_html=True)

            c1, c2, c3 = st.columns([0.8, 1.4, 0.8])

            with c1:
                img_path = row.get("image_path", "")
                img = ROOT / str(img_path)

                if img.exists():
                    st.image(str(img), use_container_width=True)

            with c2:
                st.markdown(f"### {row.get('brand', '-')} {row.get('model', '-')}")
                st.markdown(
                    f"{row.get('year', '-')} • {row.get('vehicle_type', '-')} • "
                    f"{row.get('fuel_type', '-')} • {row.get('transmission', '-')}"
                )
                st.markdown(f"Gudang: **{row.get('warehouse', addr['city'])}**")

            with c3:
                kpi(
                    "Harga",
                    money(row.get("selling_price", 0)),
                    f"Stok {row.get('stock_available', 0)} unit",
                )
                st.caption("Modal/unit: " + money(row.get("unit_cost", 0)))

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Belum ada inventory.")


elif page == "Order Masuk":
    section("Order masuk setelah pembayaran terkonfirmasi")

    if orders.empty:
        st.info("Belum ada order masuk untuk seller ini.")
    else:
        required_cols = [
            "marketplace_order_global_id",
            "customer_name",
            "brand",
            "model",
            "qty",
            "revenue",
            "gross_profit",
            "order_status",
            "shipment_status",
            "created_at",
        ]

        show_cols = [c for c in required_cols if c in orders.columns]
        show = orders[show_cols].copy()

        if "revenue" in show:
            show["revenue"] = show["revenue"].apply(money)

        if "gross_profit" in show:
            show["gross_profit"] = show["gross_profit"].apply(money)

        df_table(show)

        section("Update status order")

        c1, c2, c3 = st.columns([2, 1, 1])

        with c1:
            oid = st.selectbox("Order ID", orders.marketplace_order_global_id.tolist())

        with c2:
            new = st.selectbox("Status baru", ["PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"])

        ship = {
            "PROCESSING": "PACKING",
            "SHIPPED": "ON_DELIVERY",
            "DELIVERED": "DELIVERED",
            "CANCELLED": "CANCELLED",
        }[new]

        with c3:
            st.write("")
            st.write("")

            if st.button("Update", type="primary", use_container_width=True):
                try:
                    message = update_order_status(seller_code, oid, new, ship)
                    st.success(message)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


elif page == "Pengiriman Seller":
    section("Kesiapan pengiriman dari seller")

    if orders.empty:
        st.info("Belum ada pengiriman.")
    else:
        cols = [
            c for c in [
                "marketplace_order_global_id",
                "customer_name",
                "model",
                "shipment_status",
                "order_status",
                "created_at",
            ]
            if c in orders.columns
        ]

        df_table(orders[cols].copy())

        info_card(
            "Alamat pickup seller",
            f"Setiap unit dikirim dari:<br><b>{html.escape(addr['address'])}</b>",
            "📍",
        )


elif page == "Laporan Profit":
    section("Laporan profit seller")

    if profit.empty:
        st.info("Belum ada data profit.")
    else:
        c1, c2, c3 = st.columns(3)

        with c1:
            kpi("Revenue", money(profit.revenue.sum()), "penjualan")

        with c2:
            kpi("Modal", money(profit.cost.sum()), "biaya kendaraan")

        with c3:
            kpi("Profit Kotor", money(profit.gross_profit.sum()), "gross profit")

        col1, col2 = st.columns(2)

        with col1:
            daily = profit.groupby("recap_date", as_index=False)[["revenue", "gross_profit"]].sum()
            st.line_chart(daily.set_index("recap_date"))

        with col2:
            bymodel = profit.groupby("vehicle_code", as_index=False)["gross_profit"].sum()
            st.bar_chart(bymodel.set_index("vehicle_code"))

        show = profit.copy()

        for col in ["revenue", "cost", "gross_profit"]:
            show[col] = show[col].apply(money)

        df_table(show)


elif page == "Restock Supplier":
    section("Restock supplier")

    if inventory.empty:
        st.info("Inventory kosong.")
    else:
        with st.form("restock"):
            options = [
                f"{r.vehicle_code} — {r.brand} {r.model}"
                for r in inventory.itertuples()
            ]

            selected_vehicle = st.selectbox("Mobil", options)
            qty = st.number_input("Jumlah restock", 1, 100, 5)
            supplier = st.selectbox("Supplier", ["SUP-ASTRA", "SUP-JDM", "SUP-EV"])
            ok = st.form_submit_button("Kirim request restock", type="primary")

        if ok:
            code = selected_vehicle.split(" — ")[0]

            try:
                message = restock_inventory(seller_code, supplier, code, int(qty))
                st.success(message)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


elif page == "Pelanggan":
    section("Pelanggan seller")

    if not customers.empty:
        show = customers.copy()

        if "total_spend" in show.columns:
            show["total_spend"] = show["total_spend"].apply(money)

        df_table(show)
    else:
        st.info("Belum ada pelanggan.")


elif page == "Profil Company":
    c1, c2 = st.columns(2)

    with c1:
        info_card(
            "Company",
            f"<b>{seller['seller_name']}</b><br>"
            f"Kode: {seller_code}<br>"
            f"Status: {seller.get('status', 'ACTIVE')}",
            "🏢",
        )

    with c2:
        info_card("Alamat pickup", html.escape(addr["address"]), "📍")