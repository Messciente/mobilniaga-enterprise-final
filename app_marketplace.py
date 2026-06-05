from __future__ import annotations
import os, html
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from ui_style import setup_page, hero, kpi, money, section, df_table, info_card, amount_row, badge, status_badge, SELLER_ADDRESS, sidebar_brand, sidebar_user, demo_credentials, step_pills

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')
API=os.getenv('MARKETPLACE_API_URL','http://127.0.0.1:8001')
setup_page('MobilNiaga Marketplace','🚗')

def get(path):
    try:
        r=requests.get(API+path, timeout=20); r.raise_for_status(); return r.json()
    except Exception:
        st.error('Marketplace API belum aktif. Jalankan: python -m uvicorn marketplace_api:app --port 8001 --reload')
        return []

def post(path, payload):
    r=requests.post(API+path, json=payload, timeout=30)
    if not r.ok:
        raise RuntimeError(r.text)
    return r.json()

if 'customer' not in st.session_state: st.session_state.customer=None
if 'selected_listing' not in st.session_state: st.session_state.selected_listing=None
if 'pending_payment' not in st.session_state: st.session_state.pending_payment=None
if 'confirmed_order' not in st.session_state: st.session_state.confirmed_order=None

partners=pd.DataFrame(get('/partners'))
catalog=pd.DataFrame(get('/catalog'))

with st.sidebar:
    sidebar_brand('MobilNiaga', 'Marketplace kendaraan multi-company untuk pembeli', '🚘')
    if st.session_state.customer:
        sidebar_user(st.session_state.customer['full_name'], st.session_state.customer.get('email',''))
        page=st.radio('Menu', ['Dashboard','Katalog Mobil','Checkout','Pembayaran Saya','Tracking Pesanan','Profil'], label_visibility='collapsed')
        st.markdown('---')
        if st.button('Logout', use_container_width=True):
            st.session_state.customer=None; st.session_state.pending_payment=None; st.session_state.confirmed_order=None; st.rerun()
    else:
        page='Login/Register'
        st.markdown("<div class='demo-note'>Masuk sebagai pembeli untuk melihat katalog, checkout, VA/QRIS, dan tracking.</div>", unsafe_allow_html=True)

if page=='Login/Register':
    hero('MobilNiaga Marketplace', 'Demo marketplace kendaraan multi-company: pembeli memilih mobil, membuat VA/QRIS, konfirmasi pembayaran, lalu order masuk ke seller dan delivery.')
    step_pills(['1. Login/Register', '2. Pilih mobil', '3. Bayar VA/QRIS', '4. Konfirmasi bayar', '5. Tracking'])
    c1,c2=st.columns([.9,1.1])
    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader('Login Pembeli')
        email=st.text_input('Email', value='anne@mail.com')
        password=st.text_input('Password', value='anne123', type='password')
        if st.button('Masuk', type='primary', use_container_width=True):
            try:
                res=post('/auth/login', {'email':email,'password':password})
                st.session_state.customer=res['customer']; st.rerun()
            except Exception:
                st.error('Email atau password salah.')
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        demo_credentials('Akun demo buyer', [
            ('Buyer','Anne Melanika','anne@mail.com','anne123'),
            ('Buyer','Soni Mahardika','soni@mail.com','soni123'),
            ('Buyer','Raka Pratama','raka@mail.com','raka123'),
            ('Buyer','Nadia Putri','nadia@mail.com','nadia123'),
        ])
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader('Register Pembeli Baru')
        with st.form('register'):
            n=st.text_input('Nama lengkap')
            ph=st.text_input('No HP')
            em=st.text_input('Email baru')
            pw=st.text_input('Password', type='password')
            city=st.text_input('Kota', value='Yogyakarta')
            addr=st.text_area('Alamat lengkap')
            ok=st.form_submit_button('Buat akun', type='primary')
        if ok:
            try:
                res=post('/auth/register', {'full_name':n,'phone':ph,'email':em,'password':pw,'city':city,'address':addr})
                st.success('Akun dibuat. Silakan login.')
            except Exception as e:
                st.error('Register gagal. Email mungkin sudah digunakan.')
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

orders=pd.DataFrame(get('/orders/customer/'+st.session_state.customer['customer_global_id']))

if page=='Dashboard':
    hero(f"Selamat datang, {st.session_state.customer['full_name'].split()[0]}", 'Dashboard pembeli dibuat simpel: lihat katalog, pembayaran pending, dan tracking pesanan aktif.')
    pending=int((orders.payment_status=='PENDING').sum()) if not orders.empty else 0
    active=int((orders.shipment_status!='DELIVERED').sum()) if not orders.empty else 0
    c1,c2,c3,c4=st.columns(4)
    with c1: kpi('Katalog Aktif', len(catalog), 'unit multi-seller')
    with c2: kpi('Pesanan Saya', len(orders), 'riwayat order')
    with c3: kpi('Menunggu Bayar', pending, 'perlu konfirmasi')
    with c4: kpi('Pengiriman Aktif', active, 'belum delivered')
    col1,col2=st.columns([1.2,.8])
    with col1:
        section('Mobil rekomendasi')
        cards=st.columns(3)
        for i,row in catalog.head(3).iterrows():
            with cards[i%3]:
                img=ROOT/row['image_path']
                st.markdown("<div class='product'>", unsafe_allow_html=True)
                if img.exists(): st.image(str(img), use_container_width=True)
                st.markdown(f"<div class='body'>{badge(row['seller_name'],'#e0f2fe','#075985')}<div class='product-title'>{row['brand']} {row['model']}</div><div class='product-meta'>{row['year']} • {row['fuel_type']} • {row['transmission']}</div><div class='price'>{money(row['price'])}</div></div></div>", unsafe_allow_html=True)
    with col2:
        section('Langkah pemesanan')
        info_card('Alur singkat', '1. Pilih mobil dari katalog<br>2. Lengkapi alamat pengiriman<br>3. Pilih VA atau QRIS<br>4. Klik <b>Saya Sudah Bayar</b><br>5. Seller memproses unit<br>6. Kurir membuat tracking', '✅')

elif page=='Katalog Mobil':
    hero('Katalog Mobil Multi-Seller', 'Produk dikelompokkan dari banyak seller resmi. Setiap mobil punya seller, alamat asal, ongkir estimasi, dan stok sendiri.')
    sellers=partners[partners.partner_type=='SELLER'] if not partners.empty else pd.DataFrame()
    f1,f2,f3=st.columns([1.4,1,1])
    with f1: keyword=st.text_input('Cari mobil', placeholder='Contoh: Avanza, Brio, Ioniq')
    with f2: seller_name=st.selectbox('Seller', ['Semua'] + (sellers.partner_name.tolist() if not sellers.empty else []))
    with f3: fuel=st.selectbox('Bahan bakar', ['Semua'] + (sorted(catalog.fuel_type.dropna().unique().tolist()) if not catalog.empty else []))
    data=catalog.copy()
    if keyword: data=data[data[['brand','model','vehicle_type']].astype(str).agg(' '.join, axis=1).str.contains(keyword, case=False, na=False)]
    if seller_name!='Semua':
        sc=sellers.loc[sellers.partner_name==seller_name,'partner_code'].iloc[0]; data=data[data.seller_code==sc]
    if fuel!='Semua': data=data[data.fuel_type==fuel]
    cols=st.columns(3)
    for idx,row in data.reset_index(drop=True).iterrows():
        with cols[idx%3]:
            addr=SELLER_ADDRESS.get(row.seller_code, {'address':row.seller_city,'city':row.seller_city})
            st.markdown("<div class='product'>", unsafe_allow_html=True)
            img=ROOT/row.image_path
            if img.exists(): st.image(str(img), use_container_width=True)
            st.markdown(f"""<div class='body'>
            {badge(row.seller_name,'#eef2ff','#3730a3')} {badge(row.vehicle_type,'#ecfeff','#155e75')} {badge(row.fuel_type,'#f0fdf4','#166534')}
            <div class='product-title'>{html.escape(row.brand)} {html.escape(row.model)}</div>
            <div class='product-meta'>{row.year} • {row.transmission} • stok {row.stock_snapshot} unit</div>
            <div class='price'>{money(row.price)}</div>
            <div class='product-meta'><b>Asal pengiriman:</b><br>{html.escape(addr['address'])}</div>
            </div>""", unsafe_allow_html=True)
            if st.button('Beli mobil ini', key='buy_'+row.listing_id, type='primary', use_container_width=True):
                st.session_state.selected_listing=row.listing_id; st.success('Mobil dipilih. Buka menu Checkout.')
            st.markdown('</div>', unsafe_allow_html=True)

elif page=='Checkout':
    hero('Checkout Aman', 'Lengkapi alamat, pilih kurir, pilih metode bayar. Setelah VA/QRIS muncul, klik konfirmasi bayar agar seller mulai memproses unit.')
    if catalog.empty:
        st.info('Katalog kosong. Pastikan API berjalan.')
    else:
        fintech=partners[partners.partner_type=='FINTECH']; delivery=partners[partners.partner_type=='DELIVERY']
        labels={f"{r.brand} {r.model} — {r.seller_name} — {money(r.price)}": r.listing_id for r in catalog.itertuples()}
        default=0
        if st.session_state.selected_listing:
            for i,(k,v) in enumerate(labels.items()):
                if v==st.session_state.selected_listing: default=i
        left,right=st.columns([1.05,.95])
        with left:
            section('1. Data mobil dan alamat')
            pick=st.selectbox('Pilih mobil', list(labels.keys()), index=default)
            selected=catalog[catalog.listing_id==labels[pick]].iloc[0]
            seller_addr=SELLER_ADDRESS.get(selected.seller_code, {'address':selected.seller_city,'city':selected.seller_city})
            qty=st.number_input('Jumlah unit', 1, 3, 1)
            st.markdown(f"<div class='soft-card'><b>{selected.brand} {selected.model}</b><br>{selected.seller_name}<br><span style='color:#64748b'>{seller_addr['address']}</span></div>", unsafe_allow_html=True)
            name=st.text_input('Nama penerima', st.session_state.customer['full_name'])
            phone=st.text_input('Nomor HP', st.session_state.customer['phone'])
            city=st.text_input('Kota tujuan', st.session_state.customer['city'])
            address=st.text_area('Alamat lengkap pengiriman', st.session_state.customer['address'])
        with right:
            section('2. Pembayaran dan kurir')
            pay_map={r.partner_name:r.partner_code for r in fintech.itertuples()}
            del_map={r.partner_name:r.partner_code for r in delivery.itertuples()}
            pay=st.selectbox('Payment gateway', list(pay_map.keys()))
            channel='Virtual Account' if 'Bank' in pay else st.selectbox('Metode pembayaran', ['QRIS','Wallet Payment'])
            dele=st.selectbox('Kurir kendaraan', list(del_map.keys()))
            # visual estimate; backend calculates final.
            subtotal=int(selected.price)*int(qty)
            visual_shipping = 650000 if city.lower() in str(seller_addr['city']).lower() else 1250000
            if del_map[dele]=='DEL-NEO': visual_shipping += 550000
            if del_map[dele]=='DEL-ORI': visual_shipping += 1600000
            admin=150000
            total=subtotal+visual_shipping+admin
            st.markdown('<div class="card">'+ amount_row('Harga kendaraan', money(subtotal)) + amount_row('Estimasi ongkir / handling unit', money(visual_shipping)) + amount_row('Biaya admin', money(admin)) + '<hr>' + amount_row('Estimasi total', money(total), True) + '</div>', unsafe_allow_html=True)
            if st.button('Buat pembayaran', type='primary', use_container_width=True):
                try:
                    res=post('/orders/buy', {'customer_global_id':st.session_state.customer['customer_global_id'],'listing_id':labels[pick],'qty':qty,'payment_provider':pay_map[pay],'payment_channel':channel,'delivery_partner':del_map[dele],'destination_city':city,'destination_address':address})
                    st.session_state.pending_payment=res; st.session_state.confirmed_order=None; st.rerun()
                except Exception as e:
                    st.error('Checkout gagal. Pastikan semua API aktif dan stok tersedia.')
        if st.session_state.pending_payment:
            res=st.session_state.pending_payment
            st.success('Instruksi pembayaran berhasil dibuat. Order ID: '+res['order_global_id'])
            payinfo=res['payment_instruction']; price=res['price_summary']; plan=res['delivery_plan']; seller=res['seller']
            c1,c2,c3=st.columns([1,1,1])
            with c1:
                info_card('Tagihan', amount_row('Harga kendaraan', money(price['subtotal'])) + amount_row('Ongkir', money(price['shipping_fee'])) + amount_row('Admin', money(price['admin_fee'])) + '<hr>' + amount_row('Total bayar', money(price['grand_total']), True), '🧾')
            with c2:
                if payinfo.get('virtual_account'):
                    body=f"Provider: <b>{payinfo['provider_name']}</b><br>Nomor VA:<br><b style='font-size:1.35rem'>{payinfo['virtual_account']}</b><br>Nominal: <b>{money(payinfo['amount'])}</b><br>Batas bayar: {payinfo['expires_at']}"
                    info_card('Virtual Account', body, '🏦', 'pay-box')
                else:
                    st.markdown(f"<div class='qris-box'><b>QRIS {html.escape(payinfo['provider_name'])}</b><div class='qris-grid'>▣ ▦ ▣<br>▦ ▣ ▦<br>▣ ▦ ▣</div><div><b>{html.escape(str(payinfo.get('qris_code','QRIS-MN')))}</b></div><small>Bayar tepat {money(payinfo['amount'])}</small></div>", unsafe_allow_html=True)
            with c3:
                body=f"Seller asal:<br><b>{seller['origin_city']}</b><br>{html.escape(seller['seller_address'])}<br><br>Kurir: <b>{plan['delivery_name']}</b><br>Estimasi tiba: <b>{plan['eta_days']} hari</b><br>Tujuan: {html.escape(plan['destination_address'])}"
                info_card('Pengiriman', body, '🚚')
            st.write('')
            if st.button('Saya sudah bayar, proses pesanan', type='primary', use_container_width=True):
                try:
                    conf=post('/orders/confirm-payment', {'order_global_id':res['order_global_id']})
                    st.session_state.confirmed_order=conf
                    st.success('Pembayaran berhasil dikonfirmasi. Seller mulai memproses pesanan.')
                    st.rerun()
                except Exception as e:
                    st.error('Konfirmasi gagal. Cek payment, seller, dan delivery API.')
        if st.session_state.confirmed_order:
            conf=st.session_state.confirmed_order
            info_card('Pesanan diproses', f"Order <b>{conf['order_global_id']}</b> sudah PAID dan diproses seller.<br>Tracking number: <b>{conf.get('tracking_number','-')}</b><br>Delivery: {conf.get('delivery_name','-')}", '✅', 'card')

elif page=='Pembayaran Saya':
    hero('Pembayaran Saya', 'Pantau status pembayaran dan lanjutkan konfirmasi jika masih pending.')
    my=pd.DataFrame(get('/orders/customer/'+st.session_state.customer['customer_global_id']))
    if my.empty: st.info('Belum ada pesanan.')
    else:
        show=my[['order_global_id','seller_name','brand','model','grand_total','payment_method','payment_status','order_status','created_at']].copy()
        show['grand_total']=show['grand_total'].apply(money)
        df_table(show)
        pending=my[my.payment_status=='PENDING']
        if not pending.empty:
            section('Konfirmasi pembayaran pending')
            oid=st.selectbox('Pilih order pending', pending.order_global_id.tolist())
            if st.button('Saya sudah bayar untuk order ini', type='primary'):
                try:
                    conf=post('/orders/confirm-payment', {'order_global_id':oid})
                    st.success('Pembayaran dikonfirmasi. Order diproses seller.')
                    st.session_state.confirmed_order=conf
                    st.rerun()
                except Exception:
                    st.error('Konfirmasi gagal. Pastikan service berjalan.')

elif page=='Tracking Pesanan':
    hero('Tracking Pesanan', 'Tracking dibuat seperti timeline, bukan log teknis. Masukkan Order ID untuk melihat progres.')
    default=orders.order_global_id.iloc[0] if not orders.empty else ''
    oid=st.text_input('Order ID', value=default)
    if st.button('Lacak pesanan', type='primary') and oid:
        res=get('/orders/track/'+oid)
        if not res or not res.get('order'):
            st.warning('Order tidak ditemukan.')
        else:
            order=res['order']; ship=res.get('shipment') or {}
            c1,c2,c3=st.columns(3)
            with c1: kpi('Status order', order['order_status'], order['order_global_id'])
            with c2: kpi('Pembayaran', order['payment_status'], money(order['grand_total']))
            with c3: kpi('Pengiriman', ship.get('shipment_status','-'), ship.get('tracking_number','-'))
            section('Timeline order')
            st.markdown('<div class="timeline">', unsafe_allow_html=True)
            for ev in res.get('history',[]):
                st.markdown(f"<div class='timeline-item'><b>{status_badge(ev['status'])}</b><br><span>{html.escape(str(ev['note']))}</span><br><small>{ev['created_at']}</small></div>", unsafe_allow_html=True)
            for ev in res.get('delivery_events',[]):
                st.markdown(f"<div class='timeline-item'><b>{status_badge(ev['status'])}</b><br><span>{html.escape(str(ev['note']))}</span><br><small>{ev['location']} • {ev['created_at']}</small></div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

elif page=='Profil':
    hero('Profil Pembeli', 'Data akun dan alamat utama pembeli.')
    c1,c2=st.columns(2)
    with c1: info_card('Akun', f"Nama: <b>{st.session_state.customer['full_name']}</b><br>Email: {st.session_state.customer['email']}<br>No HP: {st.session_state.customer['phone']}", '👤')
    with c2: info_card('Alamat', f"Kota: <b>{st.session_state.customer['city']}</b><br>{html.escape(st.session_state.customer['address'])}", '📍')
