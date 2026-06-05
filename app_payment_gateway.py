from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from db_common import query, one, execute
from ui_style import setup_page, hero, kpi, money, section, df_table, info_card, status_badge

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
                unsafe_allow_html=True,
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
            unsafe_allow_html=True,
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
            unsafe_allow_html=True,
        )


ROOT = Path(__file__).resolve().parent

MASTER_DB = "mobilniaga_master"
PAYMENT_DB = "payment_gateway_db"

setup_page("MobilNiaga Payment Gateway", "💳")

CREDS = {
    "FIN-DANA": ("dana@mobilniaga.id", "dana123"),
    "FIN-BANK": ("bank@mobilniaga.id", "bank123"),
    "FIN-GOPAY": ("gopay@mobilniaga.id", "gopay123"),
}


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
        unsafe_allow_html=True,
    )


def safe_get(row, key, default=""):
    try:
        value = row.get(key, default)

        if pd.isna(value):
            return default

        return value
    except Exception:
        return default


def get_providers_df() -> pd.DataFrame:
    rows = query(
        MASTER_DB,
        """
        SELECT
            partner_code AS provider_code,
            partner_name AS provider_name,
            partner_type,
            city,
            status,
            brand_color
        FROM partners
        WHERE partner_type = 'FINTECH'
        ORDER BY partner_name
        """,
    )

    return pd.DataFrame(rows)


def login_provider(provider_code: str, email: str, password: str):
    default_email, default_password = CREDS.get(provider_code, ("", ""))

    if email != default_email or password != default_password:
        return None

    provider = one(
        MASTER_DB,
        """
        SELECT
            partner_code AS provider_code,
            partner_name AS provider_name,
            partner_type AS provider_type,
            city,
            status,
            brand_color
        FROM partners
        WHERE partner_code = %s
          AND partner_type = 'FINTECH'
        """,
        (provider_code,),
    )

    if not provider:
        return None

    return {
        "provider": provider,
        "user": {
            "email": email,
            "role": "PAYMENT_ADMIN",
        },
    }


def get_payments_df(provider_code: str) -> pd.DataFrame:
    rows = query(
        PAYMENT_DB,
        """
        SELECT
            transaction_global_id,
            order_global_id,
            provider_code,
            customer_name,
            amount,
            fee,
            net_amount,
            payment_status,
            risk_score,
            payment_channel,
            virtual_account,
            qris_code,
            customer_instruction,
            expires_at,
            created_at
        FROM payment_transactions
        WHERE provider_code = %s
        ORDER BY created_at DESC
        """,
        (provider_code,),
    )

    return pd.DataFrame(rows)


def get_settlements_df(provider_code: str) -> pd.DataFrame:
    rows = query(
        MASTER_DB,
        """
        SELECT
            settlement_id,
            order_global_id,
            seller_code,
            provider_code,
            gross_amount,
            marketplace_fee,
            seller_net_amount,
            settlement_status,
            created_at
        FROM settlements
        WHERE provider_code = %s
        ORDER BY created_at DESC
        """,
        (provider_code,),
    )

    return pd.DataFrame(rows)


def confirm_payment_transaction(transaction_global_id: str, provider_code: str) -> str:
    trx = one(
        PAYMENT_DB,
        """
        SELECT *
        FROM payment_transactions
        WHERE transaction_global_id = %s
          AND provider_code = %s
        """,
        (transaction_global_id, provider_code),
    )

    if not trx:
        raise RuntimeError("Transaksi tidak ditemukan untuk provider ini.")

    if trx.get("payment_status") == "PAID":
        return "Transaksi ini sudah berstatus PAID."

    execute(
        PAYMENT_DB,
        """
        UPDATE payment_transactions
        SET payment_status = 'PAID'
        WHERE transaction_global_id = %s
          AND provider_code = %s
        """,
        (transaction_global_id, provider_code),
    )

    execute(
        MASTER_DB,
        """
        UPDATE payments_summary
        SET payment_status = 'PAID',
            paid_at = NOW()
        WHERE payment_reference = %s
          AND provider_code = %s
        """,
        (transaction_global_id, provider_code),
    )

    execute(
        MASTER_DB,
        """
        UPDATE orders
        SET payment_status = 'PAID',
            order_status = CASE
                WHEN order_status = 'WAITING_PAYMENT' THEN 'PAYMENT_CONFIRMED'
                ELSE order_status
            END
        WHERE order_global_id = %s
        """,
        (trx["order_global_id"],),
    )

    execute(
        MASTER_DB,
        """
        INSERT INTO order_status_history(order_global_id, status, note, created_at)
        VALUES (%s, 'PAYMENT_CONFIRMED', 'Payment gateway mengonfirmasi pembayaran menjadi PAID.', NOW())
        """,
        (trx["order_global_id"],),
    )

    return "Pembayaran berhasil dikonfirmasi oleh payment gateway."


if "payment_auth" not in st.session_state:
    st.session_state.payment_auth = None


# =========================================================
# LOGIN PAGE
# =========================================================
if not st.session_state.payment_auth:
    hero(
        "Payment Gateway Center",
        "DANA, Bank Kirana, dan GoPay login masing-masing. VA/QRIS dan transaksi difilter sesuai provider yang aktif.",
    )

    step_pills(
        ["Login provider", "Lihat transaksi", "Verifikasi bayar", "Pantau VA/QRIS", "Settlement"],
        active_index=0,
    )

    try:
        providers = get_providers_df()
    except Exception as exc:
        st.error("Database belum siap. Pastikan Streamlit Secrets dan schema database sudah benar.")
        st.code(str(exc))
        st.stop()

    if providers.empty:
        st.info("Belum ada data payment provider di database.")
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
            auth = login_provider(code, email, password)

            if auth:
                st.session_state.payment_auth = auth
                st.rerun()
            else:
                st.error("Login provider gagal. Cek provider, email, dan password.")

        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        demo_credentials(
            "Akun demo payment company",
            [
                ("QRIS / Wallet", "DANA Digital Wallet", "dana@mobilniaga.id", "dana123"),
                ("Virtual Account", "Bank Kirana Digital", "bank@mobilniaga.id", "bank123"),
                ("QRIS / Wallet", "GoPay Financial Services", "gopay@mobilniaga.id", "gopay123"),
            ],
        )

        info_card(
            "Akses payment terpisah",
            "DANA hanya melihat transaksi DANA/QRIS, Bank Kirana melihat Virtual Account, dan GoPay melihat transaksi GoPay/QRIS.",
            "🔐",
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
        label_visibility="collapsed",
    )

    st.markdown("---")

    if st.button("Logout", use_container_width=True):
        st.session_state.payment_auth = None
        st.rerun()


hero(
    provider["provider_name"],
    "Monitor pembayaran, VA/QRIS, konfirmasi transaksi, dan settlement provider.",
    f"linear-gradient(120deg,{provider.get('brand_color', '#2563eb')},#e0f2fe,#fff)",
)

try:
    payments = get_payments_df(code)
    settlements = get_settlements_df(code)
except Exception as exc:
    st.error("Data payment gagal dimuat. Cek schema database dan Secrets.")
    st.code(str(exc))
    st.stop()


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
        volume = payments.amount.sum() if not payments.empty and "amount" in payments else 0
        kpi("Volume", money(volume), "gross payment")

    if not payments.empty and "created_at" in payments.columns:
        daily = (
            payments.assign(day=pd.to_datetime(payments.created_at).dt.date)
            .groupby("day", as_index=False)["amount"]
            .sum()
        )
        st.line_chart(daily.set_index("day"))
    else:
        st.info("Belum ada transaksi untuk divisualisasikan.")


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

        cols = [
            "transaction_global_id",
            "order_global_id",
            "customer_name",
            "payment_channel",
            "amount",
            "fee",
            "payment_status",
            "created_at",
        ]

        df_table(show[[c for c in cols if c in show.columns]])
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
            Customer: {html.escape(str(row.customer_name))}<br>
            Nominal: <b>{money(row.amount)}</b><br>
            Metode: {html.escape(str(row.payment_channel))}
            """,
            "💳",
        )

        if st.button("Konfirmasi pembayaran", type="primary"):
            try:
                message = confirm_payment_transaction(transaction_id, code)
                st.success(message)
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
                Customer: {html.escape(str(row.customer_name))}<br>
                Total: <b>{money(row.amount)}</b><br>
                Status: {status_badge(row.payment_status)}
                """,
                "🧾",
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
                    "pay-box",
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
                    unsafe_allow_html=True,
                )


# =========================================================
# SETTLEMENT
# =========================================================
elif page == "Settlement":
    section("Settlement provider")

    show = settlements.copy()

    if not show.empty:
        for col in ["gross_amount", "marketplace_fee", "seller_net_amount"]:
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
        "🏦",
    )