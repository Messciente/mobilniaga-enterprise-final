
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
import pymysql

load_dotenv(Path(__file__).resolve().parent / ".env")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3307"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

SELLER_DBS = {
    "SELLER-A2000":"seller_auto2000_db",
    "SELLER-HONDA":"seller_honda_db",
    "SELLER-MITSUBISHI":"seller_mitsubishi_db",
    "SELLER-HYUNDAI":"seller_hyundai_db",
    "SELLER-SUZUKI":"seller_suzuki_db",
    "SELLER-WULING":"seller_wuling_db",
}

def conn(db: str):
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=db, charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=True)

def query(db: str, sql: str, params=None):
    with conn(db) as c:
        with c.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

def one(db: str, sql: str, params=None):
    rows = query(db, sql, params)
    return rows[0] if rows else None

def execute(db: str, sql: str, params=None):
    with conn(db) as c:
        with c.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount

def money(v):
    return "Rp " + f"{int(v or 0):,}".replace(",", ".")
