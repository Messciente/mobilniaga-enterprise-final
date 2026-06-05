from __future__ import annotations
import os, html
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from ui_style import setup_page, hero, kpi, section, df_table, info_card, status_badge, sidebar_brand, sidebar_user, demo_credentials, step_pills

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')
API=os.getenv('DELIVERY_API_URL','http://127.0.0.1:8004')
setup_page('MobilNiaga Delivery Center','🚚')
CREDS={'DEL-SKY':('skysend@mobilniaga.id','sky123'),'DEL-NEO':('neorush@mobilniaga.id','neo123'),'DEL-ORI':('orion@mobilniaga.id','orion123')}

def get(p):
    try:
        r=requests.get(API+p, timeout=20); r.raise_for_status(); return r.json()
    except Exception:
        st.error('Delivery API belum aktif. Jalankan: python -m uvicorn delivery_api:app --port 8004 --reload')
        return []

def post_login(payload):
    r=requests.post(API+'/auth/login', json=payload, timeout=20)
    if not r.ok: raise RuntimeError(r.text)
    return r.json()

def put(p,payload):
    r=requests.put(API+p, json=payload, timeout=20)
    if not r.ok: raise RuntimeError(r.text)
    return r.json()

if 'delivery_auth' not in st.session_state: st.session_state.delivery_auth=None
if not st.session_state.delivery_auth:
    hero('Delivery Company Portal', 'SkySend, NeoRush, dan OrionCargo login terpisah. Setiap kurir hanya melihat shipment milik perusahaannya.')
    step_pills(['Login kurir', 'Lihat shipment', 'Update lokasi', 'Timeline tracking', 'Riwayat selesai'])
    partners=pd.DataFrame(get('/partners'))
    if partners.empty: st.stop()
    c1,c2=st.columns([.9,1.1])
    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader('Login Delivery Company')
        name=st.selectbox('Perusahaan delivery', partners.delivery_name.tolist())
        code=partners.loc[partners.delivery_name==name,'delivery_code'].iloc[0]
        e,p=CREDS.get(code,('',''))
        email=st.text_input('Email company', value=e)
        password=st.text_input('Password', value=p, type='password')
        if st.button('Masuk Delivery Center', type='primary', use_container_width=True):
            try: st.session_state.delivery_auth=post_login({'delivery_code':code,'email':email,'password':password}); st.rerun()
            except Exception: st.error('Login delivery gagal.')
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        demo_credentials('Akun demo delivery company', [
            ('Reguler','SkySend Express','skysend@mobilniaga.id','sky123'),
            ('Same-Day','NeoRush Delivery','neorush@mobilniaga.id','neo123'),
            ('Cargo','OrionCargo Logistics','orion@mobilniaga.id','orion123'),
        ])
        info_card('Tracking bersih untuk operator', 'Tidak ada raw JSON. Operator cukup melihat shipment aktif, update lokasi, dan timeline pengiriman.', '🚚')
    st.stop()

auth=st.session_state.delivery_auth; delivery=auth['delivery']; code=delivery['delivery_code']
with st.sidebar:
    sidebar_brand('Delivery Center', 'Portal perusahaan logistik', '🚚')
    sidebar_user(delivery['delivery_name'], 'Company delivery aktif')
    page=st.radio('Menu', ['Dashboard','Shipment Aktif','Update Tracking','Riwayat Pengiriman','Profil Kurir'], label_visibility='collapsed')
    st.markdown('---')
    if st.button('Logout', use_container_width=True): st.session_state.delivery_auth=None; st.rerun()

hero(delivery['delivery_name'], 'Kelola shipment kendaraan, update status, dan tampilkan tracking timeline untuk pembeli.', f"linear-gradient(120deg,{delivery.get('brand_color','#0ea5e9')},#e0f2fe,#fff)")
ships=pd.DataFrame(get('/shipments'))
if not ships.empty: ships=ships[ships.delivery_code==code]

if page=='Dashboard':
    c1,c2,c3,c4=st.columns(4)
    with c1: kpi('Total Shipment', len(ships), 'semua status')
    with c2: kpi('Ready', int((ships.shipment_status=='READY_TO_SHIP').sum()) if not ships.empty else 0, 'siap pickup')
    with c3: kpi('On Delivery', int((ships.shipment_status=='ON_DELIVERY').sum()) if not ships.empty else 0, 'dalam perjalanan')
    with c4: kpi('Delivered', int((ships.shipment_status=='DELIVERED').sum()) if not ships.empty else 0, 'selesai')
    if not ships.empty:
        st.bar_chart(ships.groupby('shipment_status')['shipment_id'].count())

elif page=='Shipment Aktif':
    section('Daftar shipment perusahaan')
    if ships.empty: st.info('Belum ada shipment.')
    else:
        show=ships[['tracking_number','order_global_id','buyer_name','origin_city','destination_city','shipment_status','current_location','estimated_arrival','created_at']]
        df_table(show)

elif page=='Update Tracking':
    section('Update tracking pengiriman')
    if ships.empty:
        st.info('Belum ada shipment untuk kurir ini.')
    else:
        c1,c2=st.columns([.9,1.1])
        with c1:
            trk=st.selectbox('Tracking number', ships.tracking_number.tolist())
            status=st.selectbox('Status baru', ['READY_TO_SHIP','PICKED_UP','ON_DELIVERY','DELIVERED','FAILED'])
            loc=st.text_input('Lokasi sekarang', 'Distribution Hub')
            note=st.text_area('Catatan untuk pembeli', 'Unit kendaraan sedang diproses oleh kurir')
            if st.button('Simpan update tracking', type='primary', use_container_width=True):
                try: st.success(put('/shipments/status', {'tracking_number':trk,'status':status,'location':loc,'note':note})['message']); st.rerun()
                except Exception as e: st.error(str(e))
        with c2:
            row=ships[ships.tracking_number==trk].iloc[0]
            info_card('Detail shipment', f"Order: <b>{row.order_global_id}</b><br>Pembeli: {html.escape(row.buyer_name)}<br>Asal: {html.escape(row.origin_city)}<br>Tujuan: {html.escape(row.destination_city)}<br>Estimasi tiba: <b>{row.estimated_arrival}</b><br>Status: {status_badge(row.shipment_status)}", '📦')
            tr=get('/tracking/'+row.order_global_id)
            section('Timeline pengiriman')
            if tr and tr.get('events'):
                st.markdown('<div class="timeline">', unsafe_allow_html=True)
                for ev in tr['events']:
                    st.markdown(f"<div class='timeline-item'><b>{status_badge(ev['status'])}</b><br>{html.escape(str(ev['note']))}<br><small>{html.escape(str(ev['location']))} • {ev['created_at']}</small></div>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

elif page=='Riwayat Pengiriman':
    done=ships[ships.shipment_status.isin(['DELIVERED','FAILED'])] if not ships.empty else pd.DataFrame()
    section('Riwayat pengiriman')
    if done.empty: st.info('Belum ada shipment selesai/gagal.')
    else: df_table(done[['tracking_number','order_global_id','buyer_name','destination_city','shipment_status','estimated_arrival','created_at']])

elif page=='Profil Kurir':
    info_card('Profil delivery company', f"<b>{delivery['delivery_name']}</b><br>Kode: {code}<br>Layanan: {delivery.get('service_type','-')}<br>Status: {delivery.get('status','ACTIVE')}", '🚚')
