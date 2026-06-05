from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from db_common import query, one, execute
from ui_style import (
    setup_page, hero, kpi, section, df_table, info_card,
    status_badge, sidebar_brand, sidebar_user, demo_credentials, step_pills
)

ROOT = Path(__file__).resolve().parent

MASTER_DB = "mobilniaga_master"
DELIVERY_DB = "delivery_gateway_db"

setup_page("MobilNiaga Delivery Center", "🚚")

CREDS = {
    "DEL-SKY": ("skysend@mobilniaga.id", "sky123"),
    "DEL-NEO": ("neorush@mobilniaga.id", "neo123"),
    "DEL-ORI": ("orion@mobilniaga.id", "orion123"),
}


def get_delivery_companies_df() -> pd.DataFrame:
    rows = query(
        MASTER_DB,
        """
        SELECT
            partner_code AS delivery_code,
            partner_name AS delivery_name,
            partner_type,
            city,
            status,
            brand_color
        FROM partners
        WHERE partner_type = 'DELIVERY'
        ORDER BY partner_name
        """
    )

    return pd.DataFrame(rows)


def login_delivery(delivery_code: str, email: str, password: str):
    default_email, default_password = CREDS.get(delivery_code, ("", ""))

    if email != default_email or password != default_password:
        return None

    delivery = one(
        MASTER_DB,
        """
        SELECT
            partner_code AS delivery_code,
            partner_name AS delivery_name,
            partner_type,
            city,
            status,
            brand_color
        FROM partners
        WHERE partner_code = %s
          AND partner_type = 'DELIVERY'
        """,
        (delivery_code,)
    )

    if not delivery:
        return None

    return {
        "delivery": delivery,
        "user": {
            "email": email,
            "role": "DELIVERY_OPERATOR",
        }
    }


def get_shipments_df(delivery_code: str) -> pd.DataFrame:
    rows = query(
        DELIVERY_DB,
        """
        SELECT
            shipment_global_id,
            order_global_id,
            delivery_code,
            buyer_name,
            origin_city,
            destination_city,
            tracking_number,
            shipment_status,
            current_location,
            estimated_arrival,
            created_at
        FROM delivery_shipments
        WHERE delivery_code = %s
        ORDER BY created_at DESC
        """,
        (delivery_code,)
    )

    return pd.DataFrame(rows)


def get_tracking_events(tracking_number: str) -> pd.DataFrame:
    rows = query(
        DELIVERY_DB,
        """
        SELECT
            tracking_number,
            status,
            location,
            note,
            created_at
        FROM tracking_events
        WHERE tracking_number = %s
        ORDER BY created_at ASC
        """,
        (tracking_number,)
    )

    return pd.DataFrame(rows)


def update_tracking(delivery_code: str, tracking_number: str, status: str, location: str, note: str) -> str:
    shipment = one(
        DELIVERY_DB,
        """
        SELECT *
        FROM delivery_shipments
        WHERE delivery_code = %s
          AND tracking_number = %s
        """,
        (delivery_code, tracking_number)
    )

    if not shipment:
        raise RuntimeError("Shipment tidak ditemukan untuk perusahaan delivery ini.")

    order_global_id = shipment["order_global_id"]

    execute(
        DELIVERY_DB,
        """
        UPDATE delivery_shipments
        SET shipment_status = %s,
            current_location = %s
        WHERE delivery_code = %s
          AND tracking_number = %s
        """,
        (status, location, delivery_code, tracking_number)
    )

    execute(
        DELIVERY_DB,
        """
        INSERT INTO tracking_events
        (tracking_number, status, location, note, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        """,
        (tracking_number, status, location, note)
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
        (status, location, order_global_id)
    )

    new_order_status = None

    if status in ["READY_TO_SHIP", "PICKED_UP"]:
        new_order_status = "PROCESSING"
    elif status == "ON_DELIVERY":
        new_order_status = "SHIPPED"
    elif status == "DELIVERED":
        new_order_status = "DELIVERED"
    elif status == "FAILED":
        new_order_status = "DELIVERY_FAILED"

    if new_order_status:
        execute(
            MASTER_DB,
            """
            UPDATE orders
            SET order_status = %s,
                shipment_status = %s
            WHERE order_global_id = %s
            """,
            (new_order_status, status, order_global_id)
        )

    execute(
        MASTER_DB,
        """
        INSERT INTO order_status_history
        (order_global_id, status, note, created_at)
        VALUES (%s, %s, %s, NOW())
        """,
        (
            order_global_id,
            status,
            f"Delivery memperbarui tracking: {note}",
        )
    )

    return "Tracking berhasil diperbarui."


if "delivery_auth" not in st.session_state:
    st.session_state.delivery_auth = None


# =========================================================
# LOGIN PAGE
# =========================================================
if not st.session_state.delivery_auth:
    hero(
        "Delivery Company Portal",
        "SkySend, NeoRush, dan OrionCargo login terpisah. Setiap kurir hanya melihat shipment milik perusahaannya."
    )

    step_pills(
        ["Login kurir", "Lihat shipment", "Update lokasi", "Timeline tracking", "Riwayat selesai"]
    )

    try:
        partners = get_delivery_companies_df()
    except Exception as exc:
        st.error("Database belum siap. Pastikan Streamlit Secrets dan schema database sudah benar.")
        st.code(str(exc))
        st.stop()

    if partners.empty:
        st.info("Belum ada data perusahaan delivery di database.")
        st.stop()

    c1, c2 = st.columns([0.9, 1.1])

    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Login Delivery Company")

        name = st.selectbox("Perusahaan delivery", partners.delivery_name.tolist())
        code = partners.loc[partners.delivery_name == name, "delivery_code"].iloc[0]

        default_email, default_password = CREDS.get(code, ("", ""))

        email = st.text_input("Email company", value=default_email)
        password = st.text_input("Password", value=default_password, type="password")

        if st.button("Masuk Delivery Center", type="primary", use_container_width=True):
            auth = login_delivery(code, email, password)

            if auth:
                st.session_state.delivery_auth = auth
                st.rerun()
            else:
                st.error("Login delivery gagal. Pilih company dan akun yang sesuai.")

        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        demo_credentials(
            "Akun demo delivery company",
            [
                ("Reguler", "SkySend Express", "skysend@mobilniaga.id", "sky123"),
                ("Same-Day", "NeoRush Delivery", "neorush@mobilniaga.id", "neo123"),
                ("Cargo", "OrionCargo Logistics", "orion@mobilniaga.id", "orion123"),
            ],
        )

        info_card(
            "Tracking bersih untuk operator",
            "Tidak ada raw JSON. Operator cukup melihat shipment aktif, update lokasi, dan timeline pengiriman.",
            "🚚",
        )

    st.stop()


# =========================================================
# AUTHENTICATED DELIVERY CENTER
# =========================================================
auth = st.session_state.delivery_auth
delivery = auth["delivery"]
code = delivery["delivery_code"]

with st.sidebar:
    sidebar_brand("Delivery Center", "Portal perusahaan logistik", "🚚")
    sidebar_user(delivery["delivery_name"], "Company delivery aktif")

    page = st.radio(
        "Menu",
        [
            "Dashboard",
            "Shipment Aktif",
            "Update Tracking",
            "Riwayat Pengiriman",
            "Profil Kurir",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    if st.button("Logout", use_container_width=True):
        st.session_state.delivery_auth = None
        st.rerun()


hero(
    delivery["delivery_name"],
    "Kelola shipment kendaraan, update status, dan tampilkan tracking timeline untuk pembeli.",
    f"linear-gradient(120deg,{delivery.get('brand_color', '#0ea5e9')},#e0f2fe,#fff)",
)

try:
    ships = get_shipments_df(code)
except Exception as exc:
    st.error("Data delivery gagal dimuat. Cek schema database dan Secrets.")
    st.code(str(exc))
    st.stop()


# =========================================================
# DASHBOARD
# =========================================================
if page == "Dashboard":
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        kpi("Total Shipment", len(ships), "semua status")

    with c2:
        ready = int((ships.shipment_status == "READY_TO_SHIP").sum()) if not ships.empty else 0
        kpi("Ready", ready, "siap pickup")

    with c3:
        on_delivery = int((ships.shipment_status == "ON_DELIVERY").sum()) if not ships.empty else 0
        kpi("On Delivery", on_delivery, "dalam perjalanan")

    with c4:
        delivered = int((ships.shipment_status == "DELIVERED").sum()) if not ships.empty else 0
        kpi("Delivered", delivered, "selesai")

    section("Ringkasan status pengiriman")

    if not ships.empty:
        chart_data = ships.groupby("shipment_status", as_index=False)["tracking_number"].count()
        chart_data = chart_data.rename(columns={"tracking_number": "total"})
        st.bar_chart(chart_data.set_index("shipment_status"))
    else:
        st.info("Belum ada shipment untuk perusahaan ini.")


# =========================================================
# SHIPMENT AKTIF
# =========================================================
elif page == "Shipment Aktif":
    section("Daftar shipment perusahaan")

    if ships.empty:
        st.info("Belum ada shipment.")
    else:
        show_cols = [
            "tracking_number",
            "order_global_id",
            "buyer_name",
            "origin_city",
            "destination_city",
            "shipment_status",
            "current_location",
            "estimated_arrival",
            "created_at",
        ]

        df_table(ships[[c for c in show_cols if c in ships.columns]])


# =========================================================
# UPDATE TRACKING
# =========================================================
elif page == "Update Tracking":
    section("Update tracking pengiriman")

    if ships.empty:
        st.info("Belum ada shipment untuk kurir ini.")
    else:
        c1, c2 = st.columns([0.9, 1.1])

        with c1:
            tracking_options = ships.tracking_number.dropna().astype(str).tolist()
            tracking_options = [x for x in tracking_options if x and x != "-"]

            if not tracking_options:
                st.info("Belum ada tracking number aktif.")
                st.stop()

            trk = st.selectbox("Tracking number", tracking_options)

            status = st.selectbox(
                "Status baru",
                [
                    "READY_TO_SHIP",
                    "PICKED_UP",
                    "ON_DELIVERY",
                    "DELIVERED",
                    "FAILED",
                ],
            )

            loc = st.text_input("Lokasi sekarang", "Distribution Hub")
            note = st.text_area("Catatan untuk pembeli", "Unit kendaraan sedang diproses oleh kurir")

            if st.button("Simpan update tracking", type="primary", use_container_width=True):
                try:
                    message = update_tracking(code, trk, status, loc, note)
                    st.success(message)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        with c2:
            row = ships[ships.tracking_number == trk].iloc[0]

            info_card(
                "Detail shipment",
                f"""
                Order: <b>{row.order_global_id}</b><br>
                Pembeli: {html.escape(str(row.buyer_name))}<br>
                Asal: {html.escape(str(row.origin_city))}<br>
                Tujuan: {html.escape(str(row.destination_city))}<br>
                Estimasi tiba: <b>{row.estimated_arrival}</b><br>
                Status: {status_badge(row.shipment_status)}
                """,
                "📦",
            )

            section("Timeline pengiriman")

            timeline = get_tracking_events(trk)

            if timeline.empty:
                st.info("Belum ada timeline untuk tracking ini.")
            else:
                st.markdown("<div class='timeline'>", unsafe_allow_html=True)

                for _, ev in timeline.iterrows():
                    st.markdown(
                        f"""
                        <div class='timeline-item'>
                            <b>{status_badge(ev['status'])}</b><br>
                            {html.escape(str(ev['note']))}<br>
                            <small>{html.escape(str(ev['location']))} • {ev['created_at']}</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# RIWAYAT PENGIRIMAN
# =========================================================
elif page == "Riwayat Pengiriman":
    section("Riwayat pengiriman")

    done = ships[ships.shipment_status.isin(["DELIVERED", "FAILED"])] if not ships.empty else pd.DataFrame()

    if done.empty:
        st.info("Belum ada shipment selesai/gagal.")
    else:
        show_cols = [
            "tracking_number",
            "order_global_id",
            "buyer_name",
            "destination_city",
            "shipment_status",
            "estimated_arrival",
            "created_at",
        ]

        df_table(done[[c for c in show_cols if c in done.columns]])


# =========================================================
# PROFIL KURIR
# =========================================================
elif page == "Profil Kurir":
    info_card(
        "Profil delivery company",
        f"""
        <b>{delivery['delivery_name']}</b><br>
        Kode: {code}<br>
        Layanan: {delivery.get('partner_type', 'DELIVERY')}<br>
        Status: {delivery.get('status', 'ACTIVE')}
        """,
        "🚚",
    )