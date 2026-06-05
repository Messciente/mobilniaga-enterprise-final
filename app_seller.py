from __future__ import annotations
import os, html
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from ui_style import setup_page, hero, kpi, money, section, df_table, info_card, SELLER_THEME, SELLER_ADDRESS, status_badge, sidebar_brand, sidebar_user, demo_credentials, step_pills

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')
API=os.getenv('SELLER_API_URL','http://127.0.0.1:8002')
setup_page('MobilNiaga Seller Center','🏢')
SELLER_CREDENTIALS={
 'SELLER-A2000':('sales@auto2000.co.id','seller123'),
 'SELLER-HONDA':('sales@honda.co.id','seller123'),
 'SELLER-MITSUBISHI':('sales@mitsubishi.co.id','seller123'),
 'SELLER-HYUNDAI':('sales@hyundai.co.id','seller123'),
 'SELLER-SUZUKI':('sales@suzuki.co.id','seller123'),
 'SELLER-WULING':('sales@wuling.co.id','seller123'),
}

def get(p):
    try:
        r=requests.get(API+p, timeout=20); r.raise_for_status(); return r.json()
    except Exception:
        st.error('Seller API belum aktif. Jalankan: python -m uvicorn seller_api:app --port 8002 --reload')
        return []

def send(method,p,payload):
    r=requests.request(method, API+p, json=payload, timeout=20)
    if not r.ok: raise RuntimeError(r.text)
    return r.json()

if 'seller_auth' not in st.session_state: st.session_state.seller_auth=None

def login_screen():
    hero('Seller Center Multi-Company', 'Setiap perusahaan seller login sendiri. Data inventory, order masuk, profit, dan pelanggan otomatis difilter sesuai company yang aktif.')
    step_pills(['Login company', 'Kelola katalog', 'Proses order paid', 'Update pengiriman', 'Pantau profit'])
    sellers=pd.DataFrame(get('/sellers'))
    if sellers.empty: st.stop()
    c1,c2=st.columns([.9,1.1])
    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader('Login Seller')
        seller_name=st.selectbox('Pilih company seller', sellers.partner_name.tolist())
        seller_code=sellers.loc[sellers.partner_name==seller_name,'seller_code'].iloc[0]
        email_default,pass_default=SELLER_CREDENTIALS.get(seller_code,('',''))
        email=st.text_input('Email company', value=email_default)
        password=st.text_input('Password', value=pass_default, type='password')
        if st.button('Masuk Seller Center', type='primary', use_container_width=True):
            try:
                st.session_state.seller_auth=send('POST','/auth/login', {'seller_code':seller_code,'email':email,'password':password})
                st.rerun()
            except Exception:
                st.error('Login gagal. Pilih seller dan akun yang sesuai.')
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        info_card('Data terpisah per perusahaan', 'Setiap seller memiliki database dan inventory sendiri. Order baru muncul setelah pembeli mengonfirmasi pembayaran.', '🔐')
        df_table(sellers.rename(columns={'seller_code':'Kode','partner_name':'Company','city':'Kota'})[['Kode','Company','Kota']])
    st.stop()

if not st.session_state.seller_auth:
    login_screen()

auth=st.session_state.seller_auth
seller=auth['seller']; user=auth['user']
seller_code=seller['seller_code']
primary, soft, label = SELLER_THEME.get(seller_code,('#2563eb','#dbeafe',seller['seller_name']))
addr=SELLER_ADDRESS.get(seller_code, {'address':seller.get('city',''), 'city':seller.get('city','')})
with st.sidebar:
    st.markdown('## 🏢 Seller Center')
    st.markdown(f"**{seller['seller_name']}**")
    st.caption('Akun company aktif')
    st.markdown('---')
    page=st.radio('Menu', ['Dashboard','Katalog Saya','Order Masuk','Pengiriman Seller','Laporan Profit','Restock Supplier','Pelanggan','Profil Company'], label_visibility='collapsed')
    st.markdown('---')
    if st.button('Logout', use_container_width=True):
        st.session_state.seller_auth=None; st.rerun()

hero(f"{seller['seller_name']}", f"Seller portal khusus {seller['seller_name']}. Alamat pengiriman: {addr['address']}", f"linear-gradient(120deg,{primary},#e0f2fe,#fff)")
inventory=pd.DataFrame(get(f'/seller/{seller_code}/inventory'))
orders=pd.DataFrame(get(f'/seller/{seller_code}/orders'))
profit=pd.DataFrame(get(f'/seller/{seller_code}/profit'))
customers=pd.DataFrame(get(f'/seller/{seller_code}/customers'))

if page=='Dashboard':
    c1,c2,c3,c4=st.columns(4)
    with c1: kpi('Unit Aktif', len(inventory), 'model di katalog seller')
    with c2: kpi('Total Stok', int(inventory.stock_available.sum()) if not inventory.empty else 0, 'unit tersedia')
    with c3: kpi('Order Masuk', len(orders), 'dari marketplace')
    with c4: kpi('Gross Profit', money(profit.gross_profit.sum() if not profit.empty else 0), 'akumulasi profit')
    col1,col2=st.columns([1.1,.9])
    with col1:
        section('Grafik profit harian')
        if not profit.empty:
            daily=profit.groupby('recap_date', as_index=False)[['revenue','gross_profit']].sum()
            st.line_chart(daily.set_index('recap_date'))
        else: st.info('Belum ada data profit.')
    with col2:
        section('Stok per model')
        if not inventory.empty: st.bar_chart(inventory.set_index('model')[['stock_available']])

elif page=='Katalog Saya':
    section('Inventory kendaraan seller')
    if not inventory.empty:
        for _, row in inventory.iterrows():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            c1,c2,c3=st.columns([.8,1.4,.8])
            with c1:
                img=ROOT/row.image_path
                if img.exists(): st.image(str(img), use_container_width=True)
            with c2:
                st.markdown(f"### {row.brand} {row.model}")
                st.markdown(f"{row.year} • {row.vehicle_type} • {row.fuel_type} • {row.transmission}")
                st.markdown(f"Gudang: **{row.warehouse}**")
            with c3:
                kpi('Harga', money(row.selling_price), f"Stok {row.stock_available} unit")
                st.caption('Modal/unit: '+money(row.unit_cost))
            st.markdown('</div>', unsafe_allow_html=True)
    else: st.info('Belum ada inventory.')

elif page=='Order Masuk':
    section('Order masuk setelah pembayaran terkonfirmasi')
    if orders.empty:
        st.info('Belum ada order masuk untuk seller ini.')
    else:
        show=orders[['marketplace_order_global_id','customer_name','brand','model','qty','revenue','gross_profit','order_status','shipment_status','created_at']].copy()
        show['revenue']=show['revenue'].apply(money); show['gross_profit']=show['gross_profit'].apply(money)
        df_table(show)
        section('Update status order')
        c1,c2,c3=st.columns([2,1,1])
        with c1: oid=st.selectbox('Order ID', orders.marketplace_order_global_id.tolist())
        with c2: new=st.selectbox('Status baru', ['PROCESSING','SHIPPED','DELIVERED','CANCELLED'])
        ship={'PROCESSING':'PACKING','SHIPPED':'ON_DELIVERY','DELIVERED':'DELIVERED','CANCELLED':'CANCELLED'}[new]
        with c3:
            st.write(''); st.write('')
            if st.button('Update', type='primary', use_container_width=True):
                try:
                    st.success(send('PUT','/orders/status', {'seller_code':seller_code,'order_global_id':oid,'new_status':new,'shipment_status':ship})['message'])
                except Exception as e: st.error(str(e))

elif page=='Pengiriman Seller':
    section('Kesiapan pengiriman dari seller')
    if orders.empty: st.info('Belum ada pengiriman.')
    else:
        show=orders[['marketplace_order_global_id','customer_name','model','shipment_status','order_status','created_at']].copy()
        df_table(show)
        info_card('Alamat pickup seller', f"Setiap unit dikirim dari:<br><b>{html.escape(addr['address'])}</b>", '📍')

elif page=='Laporan Profit':
    section('Laporan profit seller')
    if profit.empty:
        st.info('Belum ada data profit.')
    else:
        c1,c2,c3=st.columns(3)
        with c1: kpi('Revenue', money(profit.revenue.sum()), 'penjualan')
        with c2: kpi('Modal', money(profit.cost.sum()), 'biaya kendaraan')
        with c3: kpi('Profit Kotor', money(profit.gross_profit.sum()), 'gross profit')
        col1,col2=st.columns(2)
        with col1:
            daily=profit.groupby('recap_date', as_index=False)[['revenue','gross_profit']].sum()
            st.line_chart(daily.set_index('recap_date'))
        with col2:
            bymodel=profit.groupby('vehicle_code', as_index=False)['gross_profit'].sum()
            st.bar_chart(bymodel.set_index('vehicle_code'))
        show=profit.copy()
        for c in ['revenue','cost','gross_profit']: show[c]=show[c].apply(money)
        df_table(show)

elif page=='Restock Supplier':
    section('Restock supplier')
    if inventory.empty: st.info('Inventory kosong.')
    else:
        with st.form('restock'):
            v=st.selectbox('Mobil', [f"{r.vehicle_code} — {r.brand} {r.model}" for r in inventory.itertuples()])
            qty=st.number_input('Jumlah restock', 1, 100, 5)
            supplier=st.selectbox('Supplier', ['SUP-ASTRA','SUP-JDM','SUP-EV'])
            ok=st.form_submit_button('Kirim request restock', type='primary')
        if ok:
            code=v.split(' — ')[0]
            try: st.success(send('POST','/restock/request', {'seller_code':seller_code,'supplier_code':supplier,'vehicle_code':code,'qty':qty})['message'])
            except Exception as e: st.error(str(e))

elif page=='Pelanggan':
    section('Pelanggan seller')
    if not customers.empty:
        show=customers.copy(); show['total_spend']=show['total_spend'].apply(money); df_table(show)
    else: st.info('Belum ada pelanggan.')

elif page=='Profil Company':
    c1,c2=st.columns(2)
    with c1: info_card('Company', f"<b>{seller['seller_name']}</b><br>Kode: {seller_code}<br>Status: {seller.get('status','ACTIVE')}", '🏢')
    with c2: info_card('Alamat pickup', html.escape(addr['address']), '📍')
