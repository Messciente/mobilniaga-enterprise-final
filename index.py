from fastapi import FastAPI

from marketplace_api import app as marketplace_app
from seller_api import app as seller_app
from payment_api import app as payment_app
from delivery_api import app as delivery_app

app = FastAPI(title="MobilNiaga Enterprise API")

app.mount("/marketplace", marketplace_app)
app.mount("/seller", seller_app)
app.mount("/payment", payment_app)
app.mount("/delivery", delivery_app)

@app.get("/")
def root():
    return {
        "message": "MobilNiaga Enterprise API aktif",
        "services": {
            "marketplace": "/marketplace/docs",
            "seller": "/seller/docs",
            "payment": "/payment/docs",
            "delivery": "/delivery/docs"
        }
    }