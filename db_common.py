from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pymysql
from dotenv import load_dotenv

# Load .env untuk lokal
load_dotenv(Path(__file__).resolve().parent / ".env")


def get_secret(key: str, default=None):
    """
    Ambil konfigurasi dari Streamlit Secrets jika ada.
    Kalau tidak ada, fallback ke .env / environment variable lokal.
    """
    try:
        import streamlit as st

        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    return os.getenv(key, default)


def to_bool(value, default=False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


# =========================================================
# Database config
# =========================================================

DB_HOST = get_secret("DB_HOST", "127.0.0.1")
DB_PORT = int(get_secret("DB_PORT", "3307"))
DB_USER = get_secret("DB_USER", "root")
DB_PASSWORD = get_secret("DB_PASSWORD", "")

# Untuk Streamlit Cloud + 1 database online
DB_NAME = get_secret("DB_NAME", get_secret("MYSQLDATABASE", "mobilniaga_master"))

# Jika true, semua query akan diarahkan ke 1 database utama.
# Ini yang dipakai untuk deploy Streamlit Cloud.
USE_SINGLE_DB = to_bool(get_secret("USE_SINGLE_DB", "false"))


# Mapping lama untuk mode multi-database lokal
SELLER_DBS = {
    "SELLER-A2000": "seller_auto2000_db",
    "SELLER-HONDA": "seller_honda_db",
    "SELLER-MITSUBISHI": "seller_mitsubishi_db",
    "SELLER-HYUNDAI": "seller_hyundai_db",
    "SELLER-SUZUKI": "seller_suzuki_db",
    "SELLER-WULING": "seller_wuling_db",
}


def resolve_db(db: str | None = None) -> str:
    """
    Jika USE_SINGLE_DB=true, semua query diarahkan ke DB_NAME.
    Jika false, tetap pakai nama database yang dikirim.
    """
    if USE_SINGLE_DB:
        return DB_NAME

    return db or DB_NAME


def conn(db: str | None = None):
    """
    Membuat koneksi MySQL.
    """
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=resolve_db(db),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def query(db: str | None, sql: str, params=None):
    """
    Mengambil banyak data dalam bentuk list of dict.
    Tetap compatible dengan kode lama:
    query("mobilniaga_master", "SELECT ...")
    """
    with conn(db) as c:
        with c.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def query_df(db: str | None, sql: str, params=None) -> pd.DataFrame:
    """
    Mengambil data langsung sebagai DataFrame.
    Cocok untuk Streamlit table/chart.
    """
    rows = query(db, sql, params)
    return pd.DataFrame(rows)


def one(db: str | None, sql: str, params=None):
    """
    Mengambil satu baris data.
    """
    rows = query(db, sql, params)
    return rows[0] if rows else None


def execute(db: str | None, sql: str, params=None):
    """
    Menjalankan INSERT, UPDATE, DELETE.
    Return jumlah row yang berubah.
    """
    with conn(db) as c:
        with c.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount


def execute_return_id(db: str | None, sql: str, params=None):
    """
    Menjalankan INSERT dan mengembalikan last inserted id.
    """
    with conn(db) as c:
        with c.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.lastrowid


def money(v):
    """
    Format rupiah.
    """
    try:
        return "Rp " + f"{int(v or 0):,}".replace(",", ".")
    except Exception:
        return "Rp 0"