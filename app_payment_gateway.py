from __future__ import annotations

import os
import html
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

from ui_style import setup_page, hero, kpi, money, section, df_table, info_card, status_badge

# Fallback supaya tidak error kalau fungsi ini belum ada di ui_style.py
try:
    from ui_style import demo_credentials, sidebar_brand, sidebar_user
except Exception:
    def demo_credentials(title, rows):
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(title)
        for role, company, email, password in rows:
            st.markdown(
                f"""
                <div style="
                    padding:12px 14px;
                    border:1px solid #e5e7eb;
                    border-radius:16px;
                    margin-bottom:10px;
                    background:#f8fafc;
                ">
                    <b>{html.escape(company)}</b><br>
                    <span style="color:#64748b;font-size:.88rem">{html.escape(role)}</span><br>
                    <code>{html.escape(email)}</code><br>
                    Password: <code>{html.escape(password)}</code>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    def sidebar_brand(title, subtitle, icon=""):
        st.markdown(
            f"""
            <div style="padding:10px 0 18px 0">
                <h2 style="margin:0;font-size:1.35rem">{icon} {html.escape(title)}</h2>
                <p style="margin:6px 0 0;color:#64748b">{html.escape(subtitle)}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    def sidebar_user(name, subtitle=""):
        st.markdown(
            f"""
            <div style="
                padding:14px;
                border-radius:18px;
                background:linear-gradient(135deg,#e0f2fe,#f5f3ff);
                border:1px solid #dbeafe;
                margin-bottom:14px;
            ">
                <b>{html.escape(str(name))}</b><br>
                <span style="font-size:.86rem;color:#64748b">{html.escape(str(subtitle))}</span>
            </div>
            """,
            unsafe_allow_html=True
        )


def step_pills(items, active_index=0):
    pills = ""
    for i, item in enumerate(items):
        active = "active" if i == active_index else ""
        pills += f"<span class='step-pill {active}'>{i + 1}. {html.escape(item)}</span>"

    st.markdown(
        f"""
        <style>
        .step-wrap {{
            display:flex;
            gap:10px;
            flex-wrap:wrap;
            margin:10px 0 22px 0;
        }}
        .step-pill {{
            display:inline-flex;
            align-items:center;
            padding:9px 14px;
            border-radius:999px;
            background:#f1f5f9;
            color:#334155;
            border:1px solid #e2e8f0;
            font-size:13px;
            font-weight:700;
        }}
        .step-pill.active {{
            background:linear-gradient(135deg,#06b6d4,#6366f1);
            color:white;
            border:none;
            box-shadow:0 8px 18px rgba(99,102,241,.22);
        }}
        .qris-box {{
            background:linear-gradient(135deg,#f8fafc,#ecfeff);
            border:1px solid #dbeafe;
            border-radius:22px;
            padding:22px;
            box-shadow:0 16px 36px rgba(15,23,42,.08);
            text-align:center;
        }}
        .qris-grid {{
            margin:16px auto;
            width:150px;
            height:150px;
            border-radius:18px;
            background:white;
            border:1px solid #e5e7eb;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:2rem;
            line-height:1.3;
            color:#0f172a;
        }}
        .pay-box {{
            background:linear-gradient(135deg,#ecfeff,#f5f3ff);
            border:1px solid #bae6fd;
        }}
        </style>
        <div class="step-wrap">{pills}</div>
        """,
        unsafe_allow_html=True
    )


def safe_get(row, key, default=""):
    try:
        value = row.get(key, default)
        if pd.isna(value):
            return default
        return value
    except Exception:
        return default


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

API = os.getenv("PAYMENT_API_URL", "http://127.0.0.1:8003")

setup_page("MobilNiaga Payment Gateway", "💳")

CREDS = {
    "FIN-DANA": ("dana@mobilniaga.id", "dana123"),
    "FIN-BANK": ("bank@mobilniaga.id", "bank123"),
    "FIN-GOPAY": ("gopay@mobilniaga.id", "gopay123"),
}


def get(path):
    try:
        response = requests.get(API + path, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception:
        st.error(
            "Payment API belum aktif. Jalankan: "
            "python -m uvicorn payment_api:app --port 8003 --reload"
        )
        return []


def post(path, payload):
    response = requests.post(API + path, json=payload, timeout=20)
    if not response.ok:
        raise RuntimeError(response.text)
    return response.json()


if "payment_auth" not in st.session_state:
    st.session_state.payment_auth = None


# =========================================================
# LOGIN PAGE
# =========================================================
if not st.session_state.payment_auth:
    hero(
        "Payment Gateway Center",
        "DANA, Bank Kirana, dan GoPay login masing-masing. VA/QRIS dan transaksi difilter sesuai provider yang aktif."
    )

    step_pills(
        ["Login provider", "Lihat transaksi", "Verifikasi bayar", "Pantau VA/QRIS", "Settlement"],
        active_index=0
    )

    providers = pd.DataFrame(get("/providers"))
    if providers.empty:
        st.stop()

    c1, c2 = st.columns([0.9, 1.1])

    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Login Payment Company")

        name = st.selectbox("Provider", providers.provider_name.tolist())
        code = providers.loc[providers.provider_name == name, "provider_code"].iloc[0]

        default_email, default_password = CREDS.get(code, ("", ""))

        email = st.text_input("Email provider", value=default_email)
        password = st.text_input("Password", value=default_password, type="password")

        if st.button("Masuk Payment Center", type="primary", use_container_width=True):
            try:
                st.session_state.payment_auth = post(
                    "/auth/login",
                    {
                        "provider_code": code,
                        "email": email,
                        "password": password,
                    }
                )
                st.rerun()
            except Exception:
                st.error("Login provider gagal. Cek provider, email, dan password.")

        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        demo_credentials(
            "Akun demo payment company",
            [
                ("QRIS / Wallet", "DANA Digital Wallet", "dana@mobilniaga.id", "dana123"),
                ("Virtual Account", "Bank Kirana Digital", "bank@mobilniaga.id", "bank123"),
                ("QRIS / Wallet", "GoPay Financial Services", "gopay@mobilniaga.id", "gopay123"),
            ]
        )

        info_card(
            "Akses payment terpisah",
            "DANA hanya melihat transaksi DANA/QRIS, Bank Kirana melihat Virtual Account, dan GoPay melihat transaksi GoPay/QRIS.",
            "🔐"
        )

    st.stop()


# =========================================================
# AUTHENTICATED PAYMENT CENTER
# =========================================================
auth = st.session_state.payment_auth
provider = auth["provider"]
code = provider["provider_code"]

with st.sidebar:
    sidebar_brand("Payment Center", "Portal perusahaan payment gateway", "💳")
    sidebar_user(provider["provider_name"], "Company payment aktif")

    page = st.radio(
        "Menu",
        [
            "Dashboard",
            "Transaksi Masuk",
            "Konfirmasi Pembayaran",
            "VA / QRIS",
            "Settlement",
            "Profil Provider",
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    if st.button("Logout", use_container_width=True):
        st.session_state.payment_auth = None
        st.rerun()


hero(
    provider["provider_name"],
    "Monitor pembayaran, VA/QRIS, konfirmasi transaksi, dan settlement provider.",
    f"linear-gradient(120deg,{provider.get('brand_color', '#2563eb')},#e0f2fe,#fff)"
)

payments = pd.DataFrame(get("/payments"))
settlements = pd.DataFrame(get("/settlements"))

if not payments.empty:
    payments = payments[payments.provider_code == code]

if not settlements.empty:
    settlements = settlements[settlements.provider_code == code]


# =========================================================
# DASHBOARD
# =========================================================
if page == "Dashboard":
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        kpi("Transaksi", len(payments), "records")

    with c2:
        pending_count = int((payments.payment_status == "PENDING").sum()) if not payments.empty else 0
        kpi("Pending", pending_count, "menunggu konfirmasi")

    with c3:
        paid_count = int((payments.payment_status == "PAID").sum()) if not payments.empty else 0
        kpi("Paid", paid_count, "berhasil")

    with c4:
        volume = payments.amount.sum() if not payments.empty else 0
        kpi("Volume", money(volume), "gross payment")

    if not payments.empty:
        daily = (
            payments
            .assign(day=pd.to_datetime(payments.created_at).dt.date)
            .groupby("day", as_index=False)["amount"]
            .sum()
        )
        st.line_chart(daily.set_index("day"))


# =========================================================
# TRANSAKSI MASUK
# =========================================================
elif page == "Transaksi Masuk":
    section("Transaksi masuk")

    show = payments.copy()

    if not show.empty:
        for col in ["amount", "fee", "net_amount"]:
            if col in show.columns:
                show[col] = show[col].apply(money)

        df_table(
            show[
                [
                    "transaction_global_id",
                    "order_global_id",
                    "customer_name",
                    "payment_channel",
                    "amount",
                    "fee",
                    "payment_status",
                    "created_at",
                ]
            ]
        )
    else:
        st.info("Belum ada transaksi untuk provider ini.")


# =========================================================
# KONFIRMASI PEMBAYARAN
# =========================================================
elif page == "Konfirmasi Pembayaran":
    section("Konfirmasi pembayaran pending")

    pending = payments[payments.payment_status == "PENDING"] if not payments.empty else pd.DataFrame()

    if pending.empty:
        st.info("Tidak ada transaksi pending.")
    else:
        transaction_id = st.selectbox("Transaksi", pending.transaction_global_id.tolist())
        row = pending[pending.transaction_global_id == transaction_id].iloc[0]

        info_card(
            "Detail transaksi",
            f"""
            Order: <b>{row.order_global_id}</b><br>
            Customer: {row.customer_name}<br>
            Nominal: <b>{money(row.amount)}</b><br>
            Metode: {row.payment_channel}
            """,
            "💳"
        )

        if st.button("Konfirmasi pembayaran", type="primary"):
            try:
                result = post("/payments/confirm", {"transaction_global_id": transaction_id})
                st.success(result["message"])
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


# =========================================================
# VA / QRIS
# =========================================================
elif page == "VA / QRIS":
    section("Instruksi pembayaran terakhir")

    if payments.empty:
        st.info("Belum ada instruksi pembayaran.")
    else:
        row = payments.iloc[0]

        c1, c2 = st.columns(2)

        with c1:
            info_card(
                "Pembayaran",
                f"""
                Order: <b>{row.order_global_id}</b><br>
                Customer: {row.customer_name}<br>
                Total: <b>{money(row.amount)}</b><br>
                Status: {status_badge(row.payment_status)}
                """,
                "🧾"
            )

        with c2:
            virtual_account = safe_get(row, "virtual_account", "")
            qris_code = safe_get(row, "qris_code", "QRIS-MN")

            if virtual_account:
                info_card(
                    "Virtual Account",
                    f"""
                    Nomor VA:<br>
                    <b style='font-size:1.5rem'>{html.escape(str(virtual_account))}</b><br>
                    Bayar tepat: <b>{money(row.amount)}</b>
                    """,
                    "🏦",
                    "pay-box"
                )
            else:
                st.markdown(
                    f"""
                    <div class='qris-box'>
                        <b>QRIS {html.escape(provider["provider_name"])}</b>
                        <div class='qris-grid'>
                            ▣ ▦ ▣<br>
                            ▦ ▣ ▦<br>
                            ▣ ▦ ▣
                        </div>
                        <div>{html.escape(str(qris_code))}</div>
                        <small>Nominal {money(row.amount)}</small>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


# =========================================================
# SETTLEMENT
# =========================================================
elif page == "Settlement":
    section("Settlement provider")

    show = settlements.copy()

    if not show.empty:
        for col in ["gross_amount", "fee_amount", "net_settlement"]:
            if col in show.columns:
                show[col] = show[col].apply(money)

        df_table(show)
    else:
        st.info("Belum ada settlement untuk provider ini.")


# =========================================================
# PROFIL PROVIDER
# =========================================================
elif page == "Profil Provider":
    section("Profil provider")

    info_card(
        "Profil provider",
        f"""
        <b>{provider["provider_name"]}</b><br>
        Kode: {code}<br>
        Tipe: {provider.get("provider_type", "-")}<br>
        Status: {provider.get("status", "ACTIVE")}
        """,
        "🏦"
    )