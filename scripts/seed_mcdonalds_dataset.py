#!/usr/bin/env python3
"""
Seed script for the standard 'restaurants_mcdonalds' dataset (21CSE562T syllabus compliant).
Generates NYC restaurants across 5 boroughs with geospatial coordinates, grades, and menu items.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
CUISINES = ["Hamburgers", "Fast Food", "American", "Cafe/Coffee/Tea"]
STREETS = [
    "Broadway", "5th Ave", "Canal St", "Fulton St", "Atlantic Ave",
    "Bedford Ave", "Flushing Ave", "Grand Concourse", "Fordham Rd", "Hylan Blvd"
]
MENU_ITEMS = [
    {"item": "Big Mac", "price": 5.99, "category": "Burgers"},
    {"item": "Quarter Pounder with Cheese", "price": 6.29, "category": "Burgers"},
    {"item": "10 pc Chicken McNuggets", "price": 5.49, "category": "Chicken"},
    {"item": "World Famous Fries (Large)", "price": 3.99, "category": "Sides"},
    {"item": "Egg McMuffin", "price": 4.49, "category": "Breakfast"},
    {"item": "Oreo McFlurry", "price": 3.79, "category": "Desserts"},
    {"item": "Iced Caramel Macchiato", "price": 3.29, "category": "Beverages"},
]

# Approximate NYC bounding boxes per borough [min_lon, min_lat, max_lon, max_lat]
BOROUGH_BOUNDS = {
    "Manhattan": [-74.01, 40.70, -73.93, 40.82],
    "Brooklyn": [-74.04, 40.57, -73.86, 40.73],
    "Queens": [-73.96, 40.54, -73.70, 40.80],
    "Bronx": [-73.93, 40.79, -73.77, 40.91],
    "Staten Island": [-74.25, 40.50, -74.05, 40.65],
}


def generate_restaurants(count: int = 150) -> List[Dict[str, Any]]:
    restaurants = []
    base_date = datetime(2025, 1, 1)

    for i in range(1, count + 1):
        borough = random.choice(BOROUGHS)
        bounds = BOROUGH_BOUNDS[borough]
        lon = round(random.uniform(bounds[0], bounds[2]), 6)
        lat = round(random.uniform(bounds[1], bounds[3]), 6)
        street = random.choice(STREETS)
        building = str(random.randint(10, 9999))
        zipcode = f"100{random.randint(10, 99)}" if borough == "Manhattan" else f"112{random.randint(10, 99)}"

        # Generate 2 to 4 health inspection grades
        num_grades = random.randint(2, 4)
        grades = []
        for g_idx in range(num_grades):
            inspect_date = base_date + timedelta(days=g_idx * 90 + random.randint(0, 30))
            score = random.randint(5, 28)
            grade = "A" if score < 14 else ("B" if score < 28 else "C")
            grades.append({
                "date": inspect_date.isoformat() + "Z",
                "grade": grade,
                "score": score,
            })

        # Selected sample menu for this location
        menu = random.sample(MENU_ITEMS, k=random.randint(4, len(MENU_ITEMS)))
        avg_rating = round(random.uniform(3.4, 4.9), 1)

        doc = {
            "restaurant_id": f"MCD-NYC-{i:04d}",
            "name": "McDonald's" if random.random() < 0.85 else f"McDonald's #{i}",
            "borough": borough,
            "cuisine": random.choice(CUISINES),
            "address": {
                "building": building,
                "coord": [lon, lat],  # GeoJSON compliant [longitude, latitude]
                "street": street,
                "zipcode": zipcode,
            },
            "grades": grades,
            "menu": menu,
            "avg_rating": avg_rating,
            "delivery_available": random.random() < 0.80,
            "seating_capacity": random.randint(30, 120),
        }
        restaurants.append(doc)

    return restaurants


async def seed_restaurants_data(mongo_db, sql_mgr, count: int = 150):
    restaurants = generate_restaurants(count)

    # 1. Seed MongoDB
    coll = mongo_db["restaurants_mcdonalds"]
    await coll.delete_many({})
    await coll.insert_many(restaurants)
    
    # Create indexes: Single, Compound, Geospatial
    await coll.create_index([("borough", 1)])
    await coll.create_index([("cuisine", 1), ("borough", 1)])
    await coll.create_index([("address.coord", "2dsphere")])

    # 2. Seed Relational SQL
    await sql_mgr.init_schema()
    for r in restaurants:
        await sql_mgr.execute_write(
            """
            INSERT OR REPLACE INTO restaurants (
                restaurant_id, name, borough, cuisine, street, zipcode, latitude, longitude, avg_rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["restaurant_id"],
                r["name"],
                r["borough"],
                r["cuisine"],
                f"{r['address']['building']} {r['address']['street']}",
                r["address"]["zipcode"],
                r["address"]["coord"][1],  # lat
                r["address"]["coord"][0],  # lon
                r["avg_rating"],
            )
        )

    logger.info("Successfully seeded %d restaurants into MongoDB 'restaurants_mcdonalds' and SQL 'restaurants'.", len(restaurants))


if __name__ == "__main__":
    from backend.app.core.db_mongo import mongo_manager
    from backend.app.core.db_mysql import sql_manager

    async def main():
        db = await mongo_manager.connect()
        await seed_restaurants_data(db, sql_manager, 150)
        await mongo_manager.disconnect()

    asyncio.run(main())
