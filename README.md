# MobilNiaga Enterprise Multi-Company

> **Simulation of Multi-System Integration Between Independent Companies**
> Workshop Implementasi Rancangan Perangkat Lunak

---

# Project Overview

MobilNiaga Enterprise is a simulation of **multi-system integration** in the vehicle marketplace ecosystem.

The objective of this project is **not to build one large application**, but to demonstrate how several independent companies collaborate to complete a vehicle purchase transaction while maintaining their own information systems.

Every participating company owns:

* Its own User Interface (UI)
* Its own REST API
* Its own Database
* Its own Business Logic
* Its own Authentication
* Its own Business Reports

Communication between companies is performed **through REST API integration**, while every company remains independent.

This implementation follows the same business concept as:

> **ELS Computer ↔ Shopee ↔ Blibli**

where every company has its own information system but exchanges business data through integration.

---

# Team Members

| Name                          | Student ID         |
| ----------------------------- | ------------------ |
| Kukuh Agus Hermawan           | 24/533395/PA/22573 |
| Erdziah Ghodi Al Haidar       | 24/537670/PA/22787 |
| Ivan Zuhri Ramadhani Syahrial | 24/540342/PA/22939 |
| Giganus Revo                  | 24/541359/PA/22965 |
| Muhammad Dzaky Ar-Rasyid      | 24/543165/PA/23067 |
| Ifham Syafwan Fikri           | 24/545184/PA/23161 |

---

# Multi-System Business Architecture

```text
                                CUSTOMER
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │ P1 - MobilNiaga Marketplace  │
                    └──────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
  ┌────────────────┐      ┌────────────────┐      ┌────────────────┐
  │ P2 - Sellers   │      │ P3 - Payment   │      │ P4 - Delivery  │
  │   Companies    │      │   Companies    │      │   Companies    │
  └────────────────┘      └────────────────┘      └────────────────┘
           │                        │                        │
           ▼                        ▼                        ▼
 Seller Databases         Payment Database        Delivery Database
```

Each company owns its own information system.

Marketplace **never modifies another company's database directly**.

All communication is performed through REST APIs.

---

# Participating Companies

## P1 - Marketplace Company

**Application**

* MobilNiaga Marketplace

Responsibilities

* Customer registration
* Customer login
* Vehicle catalog
* Checkout
* Order management
* Payment selection
* Delivery selection
* Marketplace reports

Owns

* Marketplace UI
* Marketplace API
* Marketplace Database

---

## P2 - Seller Companies

Seller companies participating in this project

* Auto2000 Official Toyota
* Honda Prospect Motor
* Mitsubishi Motors
* Hyundai Motors Indonesia
* Suzuki Indomobil
* Wuling Motors

Responsibilities

* Vehicle inventory
* Vehicle stock
* Customer management
* Sales reports
* Profit reports
* Warehouse management
* Order fulfillment

Each seller owns

* Seller UI
* Seller API
* Seller Database

Every seller only manages its own inventory and reports.

---

## P3 - Payment Companies

Payment providers

* DANA
* Bank Kirana Digital
* GoPay Financial Services

Responsibilities

* Payment instruction
* Virtual Account
* QRIS
* Payment confirmation
* Settlement
* Payment reports

Owns

* Payment UI
* Payment API
* Payment Database

---

## P4 - Delivery Companies

Delivery providers

* SkySend Express
* NeoRush Delivery
* OrionCargo Logistics

Responsibilities

* Shipment
* Tracking
* Delivery status
* Delivery history
* Delivery reports

Owns

* Delivery UI
* Delivery API
* Delivery Database

---

# Multi-System Integration Flow

A single customer transaction involves collaboration between multiple companies.

```text
Customer

↓

Marketplace Company

↓

Marketplace API

↓

Payment Company

↓

Payment API

↓

Payment Confirmation

↓

Marketplace API

↓

Seller Company

↓

Seller API

↓

Seller Database

↓

Marketplace API

↓

Delivery Company

↓

Delivery API

↓

Tracking Number Created

↓

Customer Tracking
```

Each company updates only its own database.

---

# Purchase Workflow

## Step 1

Customer logs into Marketplace.

↓

Customer selects a vehicle.

↓

Marketplace creates a new order.

Status

```
WAITING_PAYMENT
```

---

## Step 2

Marketplace requests payment instruction.

↓

Payment Company generates

* Virtual Account

or

* QRIS

Status

```
PENDING
```

---

## Step 3

Customer completes payment.

↓

Payment Company verifies transaction.

↓

Payment status becomes

```
PAID
```

---

## Step 4

Marketplace receives payment confirmation.

↓

Marketplace forwards order to Seller Company.

Seller Company

* reduces inventory
* records customer
* creates seller order
* calculates profit

---

## Step 5

Marketplace requests shipment creation.

↓

Delivery Company creates

* Shipment
* Tracking Number

Status

```
READY_TO_SHIP
```

---

## Step 6

Delivery Company updates shipment independently.

```
READY_TO_SHIP
        ↓
PICKED_UP
        ↓
ON_DELIVERY
        ↓
DELIVERED
```

Marketplace only displays the latest tracking information.

---

# User Interfaces

| Company             | Application            | Port |
| ------------------- | ---------------------- | ---- |
| Marketplace Company | app_marketplace.py     | 8501 |
| Seller Company      | app_seller.py          | 8502 |
| Payment Company     | app_payment_gateway.py | 8503 |
| Delivery Company    | app_delivery.py        | 8504 |

---

# REST APIs

| Company     | API                | Port |
| ----------- | ------------------ | ---- |
| Marketplace | marketplace_api.py | 8001 |
| Seller      | seller_api.py      | 8002 |
| Payment     | payment_api.py     | 8003 |
| Delivery    | delivery_api.py    | 8004 |

---

# Databases

This project implements a **database-per-company** architecture.

Marketplace Company

```
mobilniaga_master
```

Seller Companies

```
seller_auto2000_db
seller_honda_db
seller_mitsubishi_db
seller_hyundai_db
seller_suzuki_db
seller_wuling_db
```

Payment Company

```
payment_gateway_db
```

Delivery Company

```
delivery_gateway_db
```

Each database belongs exclusively to its company.

---

# Company Reports

## Marketplace

Reports

* Orders
* Customers
* Marketplace Revenue
* Marketplace Fee
* Settlement

---

## Seller

Reports

* Inventory
* Sales
* Customers
* Profit
* Warehouse Stock

---

## Payment

Reports

* Transactions
* Pending Payments
* Paid Payments
* Settlement
* Payment Logs

---

## Delivery

Reports

* Active Shipments
* Tracking
* Delivered Orders
* Delivery Logs

---

# Demo Accounts

## Buyer

| Name           | Email                                   | Password |
| -------------- | --------------------------------------- | -------- |
| Anne Melanika  | [anne@mail.com](mailto:anne@mail.com)   | anne123  |
| Soni Mahardika | [soni@mail.com](mailto:soni@mail.com)   | soni123  |
| Raka Pratama   | [raka@mail.com](mailto:raka@mail.com)   | raka123  |
| Nadia Putri    | [nadia@mail.com](mailto:nadia@mail.com) | nadia123 |

---

## Seller

| Company    | Email                                                   | Password  |
| ---------- | ------------------------------------------------------- | --------- |
| Auto2000   | [sales@auto2000.co.id](mailto:sales@auto2000.co.id)     | seller123 |
| Honda      | [sales@honda.co.id](mailto:sales@honda.co.id)           | seller123 |
| Mitsubishi | [sales@mitsubishi.co.id](mailto:sales@mitsubishi.co.id) | seller123 |
| Hyundai    | [sales@hyundai.co.id](mailto:sales@hyundai.co.id)       | seller123 |
| Suzuki     | [sales@suzuki.co.id](mailto:sales@suzuki.co.id)         | seller123 |
| Wuling     | [sales@wuling.co.id](mailto:sales@wuling.co.id)         | seller123 |

---

## Payment

| Provider    | Email                                             | Password |
| ----------- | ------------------------------------------------- | -------- |
| DANA        | [dana@mobilniaga.id](mailto:dana@mobilniaga.id)   | dana123  |
| Bank Kirana | [bank@mobilniaga.id](mailto:bank@mobilniaga.id)   | bank123  |
| GoPay       | [gopay@mobilniaga.id](mailto:gopay@mobilniaga.id) | gopay123 |

---

## Delivery

| Provider   | Email                                                 | Password |
| ---------- | ----------------------------------------------------- | -------- |
| SkySend    | [skysend@mobilniaga.id](mailto:skysend@mobilniaga.id) | sky123   |
| NeoRush    | [neorush@mobilniaga.id](mailto:neorush@mobilniaga.id) | neo123   |
| OrionCargo | [orion@mobilniaga.id](mailto:orion@mobilniaga.id)     | orion123 |

---

# Installation

```bash
python -m venv venv
```

```bash
source venv/bin/activate
```

Windows

```cmd
venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Initialize database

```bash
python setup_mysql.py
```

---

# Run APIs

Marketplace

```bash
python -m uvicorn marketplace_api:app --reload --port 8001
```

Seller

```bash
python -m uvicorn seller_api:app --reload --port 8002
```

Payment

```bash
python -m uvicorn payment_api:app --reload --port 8003
```

Delivery

```bash
python -m uvicorn delivery_api:app --reload --port 8004
```

---

# Run Streamlit Applications

Marketplace

```bash
streamlit run app_marketplace.py --server.port 8501
```

Seller

```bash
streamlit run app_seller.py --server.port 8502
```

Payment

```bash
streamlit run app_payment_gateway.py --server.port 8503
```

Delivery

```bash
streamlit run app_delivery.py --server.port 8504
```

---

# Deployment Architecture

```text
Customer Browser

        │

        ▼

Streamlit UI

        │

        ▼

FastAPI Gateway

        │

        ▼

Marketplace API

Seller API

Payment API

Delivery API

        │

        ▼

MySQL Databases
```

---

# Presentation Scenario

The complete business transaction is demonstrated as follows:

1. Buyer logs into Marketplace.
2. Buyer purchases a vehicle.
3. Payment Company generates Virtual Account or QRIS.
4. Buyer confirms payment.
5. Payment Company marks transaction as PAID.
6. Marketplace forwards order to Seller Company.
7. Seller Company updates inventory and creates seller order.
8. Marketplace requests shipment.
9. Delivery Company creates tracking number.
10. Customer tracks shipment through Marketplace.

This scenario demonstrates collaboration between multiple independent companies instead of a single centralized system.

---

# Conclusion

MobilNiaga Enterprise demonstrates a **realistic multi-system integration** between independent companies.

Every company maintains its own:

* Information System
* User Interface
* REST API
* Database
* Users
* Business Reports

The Marketplace acts as an orchestrator that coordinates communication between companies without directly accessing their internal databases.

This implementation fulfills the concept of **enterprise multi-system integration**, where business processes are completed through collaboration among multiple autonomous information systems rather than a single monolithic application.
