import py_compile
for f in ['marketplace_api.py','seller_api.py','payment_api.py','delivery_api.py','app_marketplace.py','app_seller.py','app_payment_gateway.py','app_delivery.py','setup_mysql.py','db_common.py','ui_style.py']:
    py_compile.compile(f, doraise=True)
print('compile ok')
