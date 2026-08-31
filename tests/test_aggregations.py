import pytest
import asyncio
from backend.app.core.db_mongo import mongo_manager
from backend.app.engine.aggregation_runner import AggregationRunner
from scripts.seed_mcdonalds_dataset import generate_restaurants


@pytest.fixture(scope="module")
async def agg_test_db():
    db = await mongo_manager.connect(force_mock=True)
    coll = db["restaurants_mcdonalds"]
    await coll.delete_many({})
    # Seed 20 test restaurants
    await coll.insert_many(generate_restaurants(20))
    yield db
    await mongo_manager.disconnect()


@pytest.mark.asyncio
async def test_match_group_sort_aggregation(agg_test_db):
    runner = AggregationRunner(db=agg_test_db)

    pipeline = [
        {"$match": {"avg_rating": {"$gte": 2.0}}},
        {
            "$group": {
                "_id": "$borough",
                "total_restaurants": {"$sum": 1},
                "avg_rating": {"$avg": "$avg_rating"},
            }
        },
        {"$sort": {"total_restaurants": -1}},
    ]

    res = await runner.run_pipeline("restaurants_mcdonalds", pipeline)
    assert res["success"] is True
    assert res["result_count"] > 0
    assert "total_restaurants" in res["results"][0]


@pytest.mark.asyncio
async def test_unwind_aggregation(agg_test_db):
    runner = AggregationRunner(db=agg_test_db)

    pipeline = [
        {"$unwind": "$menu"},
        {
            "$group": {
                "_id": "$menu.category",
                "count": {"$sum": 1},
                "avg_price": {"$avg": "$menu.price"},
            }
        },
    ]

    res = await runner.run_pipeline("restaurants_mcdonalds", pipeline)
    assert res["success"] is True
    assert res["result_count"] > 0
    assert "avg_price" in res["results"][0]


@pytest.mark.asyncio
async def test_facet_aggregation(agg_test_db):
    runner = AggregationRunner(db=agg_test_db)

    pipeline = [
        {
            "$facet": {
                "borough_summary": [
                    {"$group": {"_id": "$borough", "count": {"$sum": 1}}}
                ],
                "rating_summary": [
                    {"$group": {"_id": "$avg_rating", "count": {"$sum": 1}}}
                ],
            }
        }
    ]

    res = await runner.run_pipeline("restaurants_mcdonalds", pipeline)
    assert res["success"] is True
    assert res["result_count"] == 1
    assert "borough_summary" in res["results"][0]
    assert "rating_summary" in res["results"][0]
