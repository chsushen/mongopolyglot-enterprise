#!/usr/bin/env python3
"""
Seed script for the standard 'ecommerce_events' dataset (21CSE562T syllabus compliant).
Generates users, accounts, products, orders, and inventory for ACID transactions and polyglot benchmarks.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

CATEGORIES = ["Electronics", "Apparel", "Home & Kitchen", "Books", "Beauty"]
REGIONS = ["US-EAST", "US-WEST", "APAC", "EMEA"]


def generate_ecommerce_data():
    now = datetime(2026, 1, 1)

    # 1. Users (50 users)
    users = []
    accounts = []
    for i in range(1, 51):
        user_id = f"USR-{i:04d}"
        username = f"user_{i}"
        email = f"user_{i}@enterprise.com"
        created_at = (now - timedelta(days=random.randint(30, 365))).isoformat() + "Z"

        users.append({
            "user_id": user_id,
            "username": username,
            "email": email,
            "created_at": created_at,
            "region": random.choice(REGIONS),
        })

        # Account for ACID transactions
        accounts.append({
            "account_id": f"ACC-{i:04d}",
            "user_id": user_id,
            "balance": round(random.uniform(500.0, 5000.0), 2),
            "currency": "USD",
            "updated_at": now.isoformat() + "Z",
            "status": "ACTIVE",
        })

    # 2. Products (30 products)
    products = []
    for i in range(1, 31):
        product_id = f"PROD-{i:04d}"
        category = random.choice(CATEGORIES)
        price = round(random.uniform(15.0, 650.0), 2)
        stock = random.randint(20, 200)

        products.append({
            "product_id": product_id,
            "name": f"Enterprise {category} Item #{i}",
            "category": category,
            "price": price,
            "stock_quantity": stock,
            "sku": f"SKU-{category[:3].upper()}-{i:03d}",
        })

    # 3. Orders & Order Items (150 orders)
    orders = []
    order_items_sql = []
    for i in range(1, 151):
        order_id = f"ORD-{i:05d}"
        user = random.choice(users)
        order_date = (now + timedelta(hours=i * 4)).isoformat() + "Z"
        status = random.choice(["COMPLETED", "COMPLETED", "COMPLETED", "PENDING", "CANCELLED"])

        num_items = random.randint(1, 3)
        chosen_prods = random.sample(products, k=num_items)
        items_bson = []
        total_amount = 0.0

        for p in chosen_prods:
            qty = random.randint(1, 3)
            item_total = round(qty * p["price"], 2)
            total_amount += item_total
            item_id = f"ITEM-{order_id}-{p['product_id']}"

            items_bson.append({
                "item_id": item_id,
                "product_id": p["product_id"],
                "product_name": p["name"],
                "category": p["category"],
                "quantity": qty,
                "unit_price": p["price"],
                "total_price": item_total,
            })

            order_items_sql.append({
                "item_id": item_id,
                "order_id": order_id,
                "product_id": p["product_id"],
                "quantity": qty,
                "unit_price": p["price"],
            })

        orders.append({
            "order_id": order_id,
            "user_id": user["user_id"],
            "username": user["username"],
            "region": user["region"],
            "order_date": order_date,
            "status": status,
            "total_amount": round(total_amount, 2),
            "items": items_bson,
            "payment_method": random.choice(["credit_card", "paypal", "wire_transfer"]),
        })

    return users, accounts, products, orders, order_items_sql


async def seed_ecommerce_data(mongo_db, sql_mgr):
    users, accounts, products, orders, order_items_sql = generate_ecommerce_data()

    # 1. MongoDB Collections
    for name, data in [
        ("users", users),
        ("accounts", accounts),
        ("products", products),
        ("orders", orders),
    ]:
        coll = mongo_db[name]
        await coll.delete_many({})
        await coll.insert_many(data)

    # MongoDB Indexes
    await mongo_db["accounts"].create_index([("account_id", 1)], unique=True)
    await mongo_db["accounts"].create_index([("user_id", 1)])
    await mongo_db["orders"].create_index([("user_id", 1)])
    await mongo_db["orders"].create_index([("status", 1)])
    await mongo_db["orders"].create_index([("order_date", -1)])
    await mongo_db["products"].create_index([("category", 1)])

    # 2. Relational SQL
    await sql_mgr.init_schema()
    for u in users:
        await sql_mgr.execute_write(
            "INSERT OR REPLACE INTO users (user_id, username, email, created_at) VALUES (?, ?, ?, ?)",
            (u["user_id"], u["username"], u["email"], u["created_at"])
        )
    for a in accounts:
        await sql_mgr.execute_write(
            "INSERT OR REPLACE INTO accounts (account_id, user_id, balance, currency, updated_at) VALUES (?, ?, ?, ?, ?)",
            (a["account_id"], a["user_id"], a["balance"], a["currency"], a["updated_at"])
        )
    for p in products:
        await sql_mgr.execute_write(
            "INSERT OR REPLACE INTO products (product_id, name, category, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
            (p["product_id"], p["name"], p["category"], p["price"], p["stock_quantity"])
        )
    for o in orders:
        await sql_mgr.execute_write(
            "INSERT OR REPLACE INTO orders (order_id, user_id, order_date, status, total_amount) VALUES (?, ?, ?, ?, ?)",
            (o["order_id"], o["user_id"], o["order_date"], o["status"], o["total_amount"])
        )
    for it in order_items_sql:
        await sql_mgr.execute_write(
            "INSERT OR REPLACE INTO order_items (item_id, order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
            (it["item_id"], it["order_id"], it["product_id"], it["quantity"], it["unit_price"])
        )

    print(f"✅ Successfully seeded E-Commerce datasets ({len(users)} users, {len(accounts)} accounts, {len(products)} products, {len(orders)} orders) into MongoDB & SQL.")


if __name__ == "__main__":
    from backend.app.core.db_mongo import mongo_manager
    from backend.app.core.db_mysql import sql_manager

    async def main():
        db = await mongo_manager.connect()
        await seed_ecommerce_data(db, sql_manager)
        await mongo_manager.disconnect()

    asyncio.run(main())
