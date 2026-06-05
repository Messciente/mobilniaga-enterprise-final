
from __future__ import annotations
import html
import pandas as pd
import streamlit as st

SELLER_THEME = {
    "SELLER-A2000": ("#2563eb", "#dbeafe", "Auto2000 Official Toyota"),
    "SELLER-HONDA": ("#dc2626", "#fee2e2", "Honda Prospect Motor"),
    "SELLER-MITSUBISHI": ("#7c3aed", "#ede9fe", "Mitsubishi Motors"),
    "SELLER-HYUNDAI": ("#0891b2", "#cffafe", "Hyundai Motors Indonesia"),
    "SELLER-SUZUKI": ("#16a34a", "#dcfce7", "Suzuki Indomobil"),
    "SELLER-WULING": ("#ea580c", "#ffedd5", "Wuling Motors"),
}

SELLER_ADDRESS = {
    "SELLER-A2000": {"name":"Auto2000 Yogyakarta", "city":"Sleman", "address":"Jl. Magelang Km 7, Sinduadi, Mlati, Sleman, DI Yogyakarta"},
    "SELLER-HONDA": {"name":"Honda Prospect Semarang", "city":"Semarang", "address":"Jl. Setiabudi No. 88, Banyumanik, Semarang, Jawa Tengah"},
    "SELLER-MITSUBISHI": {"name":"Mitsubishi Motors Surabaya", "city":"Surabaya", "address":"Jl. Ahmad Yani No. 120, Wonokromo, Surabaya, Jawa Timur"},
    "SELLER-HYUNDAI": {"name":"Hyundai Motors Bandung", "city":"Bandung", "address":"Jl. Soekarno Hatta No. 501, Bandung, Jawa Barat"},
    "SELLER-SUZUKI": {"name":"Suzuki Indomobil Solo", "city":"Surakarta", "address":"Jl. Adi Sucipto No. 45, Laweyan, Surakarta, Jawa Tengah"},
    "SELLER-WULING": {"name":"Wuling Motors Jakarta Barat", "city":"Jakarta Barat", "address":"Jl. Daan Mogot No. 77, Jakarta Barat, DKI Jakarta"},
}

def money(v):
    try:
        return "Rp " + f"{int(float(v or 0)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"

def setup_page(title: str, icon: str = "🚗"):
    st.set_page_config(page_title=title, page_icon=icon, layout="wide", initial_sidebar_state="expanded")
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
html, body, [class*="css"]{font-family:'Inter',system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}
.stApp{background:linear-gradient(135deg,#f8fbff 0%,#f2fbff 35%,#fff7fb 100%);} 
.block-container{padding-top:1.1rem; padding-bottom:2rem; max-width:1280px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#ffffff 0%,#f0f9ff 100%); border-right:1px solid #e2e8f0;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#334155;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#0f172a;}
button[kind="primary"]{border-radius:999px!important; font-weight:800!important; box-shadow:0 12px 24px rgba(14,165,233,.18)!important;}
.stButton>button{border-radius:999px!important; font-weight:750!important; border:1px solid #cbd5e1!important;}
input, textarea, select{border-radius:14px!important;}
.hero{position:relative; overflow:hidden; padding:34px 36px; border-radius:28px; color:#07111f; margin-bottom:22px; background:linear-gradient(120deg,#dbeafe 0%,#e0f2fe 45%,#fae8ff 100%); border:1px solid rgba(255,255,255,.8); box-shadow:0 24px 60px rgba(30,64,175,.14);} 
.hero:after{content:""; position:absolute; right:-80px; top:-120px; width:320px; height:320px; background:rgba(255,255,255,.55); border-radius:999px;}
.hero h1{margin:0; font-size:2.15rem; letter-spacing:-.04em; font-weight:900; color:#0f172a;}
.hero p{margin:.65rem 0 0; color:#475569; font-size:1.02rem; max-width:780px; line-height:1.65;}
.card{background:rgba(255,255,255,.86); border:1px solid #e2e8f0; border-radius:24px; padding:22px; box-shadow:0 18px 44px rgba(15,23,42,.07); backdrop-filter:blur(12px);}
.soft-card{background:linear-gradient(180deg,#ffffff,#f8fafc); border:1px solid #e2e8f0; border-radius:22px; padding:20px; box-shadow:0 12px 32px rgba(15,23,42,.05);}
.kpi{background:rgba(255,255,255,.92); border:1px solid #e2e8f0; border-radius:22px; padding:20px; box-shadow:0 18px 42px rgba(15,23,42,.07); min-height:124px;}
.kpi .label{font-size:.82rem; color:#64748b; font-weight:700; text-transform:uppercase; letter-spacing:.05em;}
.kpi .value{font-size:1.55rem; color:#0f172a; font-weight:900; margin-top:8px; letter-spacing:-.03em;}
.kpi .desc{font-size:.86rem; color:#64748b; margin-top:4px;}
.product{background:#fff; border:1px solid #e2e8f0; border-radius:26px; overflow:hidden; box-shadow:0 20px 48px rgba(15,23,42,.08); margin-bottom:22px; transition:.2s ease;}
.product:hover{transform:translateY(-3px); box-shadow:0 28px 70px rgba(15,23,42,.12);} 
.product .body{padding:18px 20px 20px;}
.product-title{font-size:1.12rem; font-weight:900; color:#0f172a; margin:.6rem 0 .2rem; letter-spacing:-.02em;}
.product-meta{color:#64748b; font-size:.88rem; line-height:1.55;}
.price{color:#0f766e; font-size:1.18rem; font-weight:900; margin:.55rem 0;}
.badge{display:inline-flex; align-items:center; gap:6px; padding:6px 11px; border-radius:999px; font-size:.75rem; font-weight:850; margin:2px 4px 2px 0; white-space:nowrap;}
.section-title{font-size:1.22rem; font-weight:900; color:#0f172a; margin:14px 0 12px; letter-spacing:-.02em;}
.pay-box{border-radius:26px; padding:22px; background:linear-gradient(135deg,#ecfeff,#f5f3ff); border:1px solid #c4b5fd; box-shadow:0 20px 44px rgba(124,58,237,.10);} 
.qris-box{border-radius:26px; padding:24px; text-align:center; background:#fff; border:1px solid #cbd5e1; box-shadow:0 20px 44px rgba(15,23,42,.08);}
.qris-grid{display:inline-block; font-size:2rem; line-height:1.0; letter-spacing:.18rem; margin:15px 0; padding:22px; border:12px solid #0f172a; border-radius:16px; color:#0f172a; background:#fff;}
.timeline{border-left:3px solid #bae6fd; margin-left:12px; padding-left:18px;}
.timeline-item{background:#fff; border:1px solid #e2e8f0; border-radius:18px; padding:14px 16px; margin:12px 0; box-shadow:0 10px 28px rgba(15,23,42,.05); position:relative;}
.timeline-item:before{content:""; position:absolute; left:-29px; top:18px; width:14px; height:14px; border-radius:99px; background:#06b6d4; border:3px solid #e0f2fe;}
.mn-table{width:100%; border-collapse:separate; border-spacing:0 10px; font-size:.88rem;}
.mn-table thead th{background:#eff6ff; color:#1e3a8a; text-align:left; padding:12px 14px; font-size:.78rem; text-transform:uppercase; letter-spacing:.04em;}
.mn-table tbody tr{background:#fff; box-shadow:0 8px 22px rgba(15,23,42,.05);}
.mn-table tbody td{padding:13px 14px; color:#334155; border-top:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0;}
.mn-table tbody td:first-child{border-left:1px solid #e2e8f0; border-radius:14px 0 0 14px; font-weight:700; color:#0f172a;}
.mn-table tbody td:last-child{border-right:1px solid #e2e8f0; border-radius:0 14px 14px 0;}
.amount-row{display:flex; justify-content:space-between; gap:12px; padding:10px 0; border-bottom:1px dashed #cbd5e1; color:#334155;}
.amount-row b{color:#0f172a;}
.footer-note{color:#94a3b8; font-size:.82rem; margin-top:18px;}
hr{border:none; border-top:1px solid #e2e8f0; margin:14px 0;}

/* Polished sidebar navigation */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#ffffff 0%,#f0fbff 55%,#fff7fb 100%); border-right:1px solid #dbeafe; box-shadow: 8px 0 32px rgba(15,23,42,.04);} 
[data-testid="stSidebar"] .stRadio > label{display:none;}
[data-testid="stSidebar"] div[role="radiogroup"]{gap:6px; display:flex; flex-direction:column;}
[data-testid="stSidebar"] div[role="radiogroup"] label{padding:11px 14px!important; border-radius:18px!important; background:rgba(255,255,255,.78)!important; border:1px solid #e2e8f0!important; box-shadow:0 8px 22px rgba(15,23,42,.04); margin:2px 0!important; transition:.18s ease;}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover{transform:translateX(3px); background:#f8fafc!important; border-color:#bae6fd!important;}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:linear-gradient(135deg,#06b6d4,#6366f1)!important; color:#fff!important; border-color:transparent!important; box-shadow:0 14px 30px rgba(99,102,241,.22)!important;}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p{color:#fff!important; font-weight:800!important;}
[data-testid="stSidebar"] .stButton>button{background:rgba(255,255,255,.82)!important; border:1px solid #cbd5e1!important; color:#0f172a!important;}
.sidebar-brand{background:linear-gradient(135deg,#ffffff,#eff6ff); border:1px solid #dbeafe; border-radius:24px; padding:17px 16px; box-shadow:0 16px 38px rgba(15,23,42,.06); margin-bottom:14px;}
.sidebar-brand .title{font-size:1.15rem; font-weight:900; color:#0f172a; letter-spacing:-.03em;}
.sidebar-brand .sub{color:#64748b; font-size:.82rem; margin-top:4px; line-height:1.45;}
.sidebar-user{background:#fff; border:1px solid #e2e8f0; border-radius:20px; padding:14px; margin:10px 0 14px; box-shadow:0 10px 28px rgba(15,23,42,.05);}
.sidebar-user b{color:#0f172a;}
.sidebar-user small{color:#64748b;}
.demo-grid{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-top:10px;}
.demo-card{background:linear-gradient(180deg,#fff,#f8fbff); border:1px solid #dbeafe; border-radius:20px; padding:14px 16px; box-shadow:0 12px 30px rgba(15,23,42,.06);}
.demo-card .role{font-size:.76rem; color:#2563eb; font-weight:900; text-transform:uppercase; letter-spacing:.05em;}
.demo-card .name{font-size:1rem; font-weight:900; color:#0f172a; margin:5px 0 8px;}
.demo-card code{background:#eff6ff; color:#1e3a8a; border-radius:9px; padding:3px 7px; font-size:.82rem;}
.demo-note{background:linear-gradient(135deg,#ecfeff,#f5f3ff); border:1px solid #bae6fd; border-radius:22px; padding:16px; color:#334155; line-height:1.6; margin:12px 0;}
.step-strip{display:flex; gap:10px; flex-wrap:wrap; margin:10px 0 18px;}
.step-pill{background:#fff; border:1px solid #dbeafe; color:#334155; border-radius:999px; padding:8px 12px; font-size:.82rem; font-weight:800; box-shadow:0 8px 22px rgba(15,23,42,.04);}

footer{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

def hero(title: str, subtitle: str, gradient: str | None = None):
    style = f"style='background:{gradient}'" if gradient else ""
    st.markdown(f"<div class='hero' {style}><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>", unsafe_allow_html=True)

def section(title: str):
    st.markdown(f"<div class='section-title'>{html.escape(title)}</div>", unsafe_allow_html=True)

def kpi(label: str, value, desc: str = ""):
    st.markdown(f"<div class='kpi'><div class='label'>{html.escape(str(label))}</div><div class='value'>{html.escape(str(value))}</div><div class='desc'>{html.escape(str(desc))}</div></div>", unsafe_allow_html=True)

def badge(text, bg="#e0f2fe", fg="#075985"):
    return f"<span class='badge' style='background:{bg}; color:{fg}'>{html.escape(str(text))}</span>"

def info_card(title: str, body: str, icon: str = "ℹ️", class_name: str = "soft-card"):
    st.markdown(f"<div class='{class_name}'><div style='font-size:1.6rem'>{icon}</div><h3 style='margin:.2rem 0 .5rem;color:#0f172a'>{html.escape(title)}</h3><div style='color:#475569;line-height:1.65'>{body}</div></div>", unsafe_allow_html=True)

def amount_row(label: str, value: str, strong: bool=False):
    tag1, tag2 = ("<b>", "</b>") if strong else ("", "")
    return f"<div class='amount-row'><span>{html.escape(label)}</span><span>{tag1}{html.escape(str(value))}{tag2}</span></div>"

def status_badge(value: str):
    value = str(value or "-")
    colors = {
        "PENDING_PAYMENT":("#fef3c7","#92400e"), "WAITING_PAYMENT":("#fef3c7","#92400e"), "PENDING":("#fef3c7","#92400e"),
        "PAID":("#dcfce7","#166534"), "PROCESSING":("#dbeafe","#1d4ed8"), "SELLER_PROCESSING":("#dbeafe","#1d4ed8"),
        "READY_TO_SHIP":("#f5f3ff","#6d28d9"), "ON_DELIVERY":("#cffafe","#155e75"), "SHIPPED":("#cffafe","#155e75"),
        "DELIVERED":("#bbf7d0","#14532d"), "CANCELLED":("#fee2e2","#991b1b"), "FAILED":("#fee2e2","#991b1b"),
    }
    bg, fg = colors.get(value, ("#f1f5f9", "#334155"))
    return badge(value, bg, fg)


def sidebar_brand(title: str, subtitle: str, icon: str = "🚗"):
    st.markdown(f"""
<div class='sidebar-brand'>
  <div class='title'>{icon} {html.escape(title)}</div>
  <div class='sub'>{html.escape(subtitle)}</div>
</div>
""", unsafe_allow_html=True)

def sidebar_user(name: str, subtitle: str = ""):
    st.markdown(f"<div class='sidebar-user'><b>{html.escape(str(name))}</b><br><small>{html.escape(str(subtitle))}</small></div>", unsafe_allow_html=True)

def demo_credentials(title: str, items: list[tuple[str,str,str,str]]):
    cards=[]
    for role,name,email,pw in items:
        cards.append(f"""
<div class='demo-card'>
  <div class='role'>{html.escape(role)}</div>
  <div class='name'>{html.escape(name)}</div>
  <div>Email<br><code>{html.escape(email)}</code></div>
  <div style='margin-top:6px'>Password<br><code>{html.escape(pw)}</code></div>
</div>
""")
    st.markdown(f"<div class='section-title'>{html.escape(title)}</div><div class='demo-note'>Gunakan akun demo berikut saat presentasi. Akun sudah otomatis tersedia setelah menjalankan <b>python setup_mysql.py</b>.</div><div class='demo-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)

def step_pills(items: list[str]):
    content=''.join(f"<span class='step-pill'>{html.escape(str(x))}</span>" for x in items)
    st.markdown(f"<div class='step-strip'>{content}</div>", unsafe_allow_html=True)

def df_table(df: pd.DataFrame, height: int | None = None):
    if df is None or df.empty:
        st.info("Belum ada data yang tersedia.")
        return
    show = df.copy().fillna("-")
    # Limit very long text.
    for col in show.columns:
        show[col] = show[col].astype(str).map(lambda x: x if len(x) <= 80 else x[:77] + "...")
    header = "".join(f"<th>{html.escape(str(c).replace('_',' ').title())}</th>" for c in show.columns)
    rows = []
    for _, r in show.iterrows():
        cells = "".join(f"<td>{html.escape(str(v))}</td>" for v in r.tolist())
        rows.append(f"<tr>{cells}</tr>")
    body = "".join(rows)
    st.markdown(f"<div style='overflow-x:auto'><table class='mn-table'><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>", unsafe_allow_html=True)
