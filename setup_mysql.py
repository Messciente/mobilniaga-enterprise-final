
from pathlib import Path
import pymysql
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
host = os.getenv("DB_HOST", "127.0.0.1")
port = int(os.getenv("DB_PORT", "3307"))
user = os.getenv("DB_USER", "root")
password = os.getenv("DB_PASSWORD", "")

sql_path = ROOT / "schema.sql"
raw = sql_path.read_text(encoding="utf-8")
statements = []
buf = []
for line in raw.splitlines():
    line_strip = line.strip()
    if not line_strip or line_strip.startswith("--"):
        continue
    buf.append(line)
    if line_strip.endswith(";"):
        statements.append("\n".join(buf).strip())
        buf=[]
if buf:
    statements.append("\n".join(buf).strip())

conn = pymysql.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    charset="utf8mb4",
    autocommit=True,
    ssl={"ssl": {}}
)
try:
    with conn.cursor() as cur:
        for st in statements:
            if st:
                cur.execute(st)
    print("Database berhasil dibuat ulang:")
    print("- mobilniaga_master")
    print("- seller_auto2000_db, seller_honda_db, seller_mitsubishi_db, seller_hyundai_db, seller_suzuki_db, seller_wuling_db")
    print("- payment_gateway_db")
    print("- delivery_gateway_db")
finally:
    conn.close()
