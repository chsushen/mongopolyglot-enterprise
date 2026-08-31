import logging
import time
from typing import Dict, Any, List, Optional
from ..core.db_mongo import mongo_manager
from .crud_manager import serialize_bson

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 21CSE562T Course Presets
# ---------------------------------------------------------------------------
SYLLABUS_PRESETS = {
    "borough_performance": {
        "title": "Borough Performance & Average Rating ($match, $group, $sort)",
        "description": "Calculates total restaurants, average customer rating, and seating capacity grouped by borough.",
        "collection": "restaurants_mcdonalds",
        "pipeline": [
            {"$match": {"avg_rating": {"$gte": 3.5}}},
            {
                "$group": {
                    "_id": "$borough",
                    "total_restaurants": {"$sum": 1},
                    "avg_rating": {"$avg": "$avg_rating"},
                    "avg_seating_capacity": {"$avg": "$seating_capacity"},
                }
            },
            {
                "$project": {
                    "borough": "$_id",
                    "total_restaurants": 1,
                    "avg_rating": 1,
                    "avg_seating": "$avg_seating_capacity",
                    "_id": 0,
                }
            },
            {"$sort": {"avg_rating": -1}},
        ],
    },
    "menu_unwind_analysis": {
        "title": "Menu Category Breakdown via Array Unwinding ($unwind, $group)",
        "description": "Flattens the embedded menu items array to analyze pricing distribution across categories.",
        "collection": "restaurants_mcdonalds",
        "pipeline": [
            {"$unwind": "$menu"},
            {
                "$group": {
                    "_id": "$menu.category",
                    "item_count": {"$sum": 1},
                    "avg_price": {"$avg": "$menu.price"},
                    "max_price": {"$max": "$menu.price"},
                    "min_price": {"$min": "$menu.price"},
                }
            },
            {
                "$project": {
                    "category": "$_id",
                    "item_count": 1,
                    "avg_price": 1,
                    "max_price": 1,
                    "min_price": 1,
                    "_id": 0,
                }
            },
            {"$sort": {"avg_price": -1}},
        ],
    },
    "orders_users_lookup": {
        "title": "Relational NoSQL Join ($lookup orders with accounts)",
        "description": "Performs left outer join across 'orders' and 'accounts' to enrich order telemetry with live balance status.",
        "collection": "orders",
        "pipeline": [
            {"$match": {"status": "COMPLETED"}},
            {
                "$lookup": {
                    "from": "accounts",
                    "localField": "user_id",
                    "foreignField": "user_id",
                    "as": "account_info",
                }
            },
            {"$unwind": "$account_info"},
            {
                "$project": {
                    "order_id": 1,
                    "username": 1,
                    "region": 1,
                    "total_amount": 1,
                    "account_balance": "$account_info.balance",
                    "account_status": "$account_info.status",
                    "_id": 0,
                }
            },
            {"$limit": 20},
        ],
    },
    "faceted_ecommerce_dashboard": {
        "title": "Multi-Faceted Analytical Aggregation ($facet)",
        "description": "Executes simultaneous sub-pipelines in a single pass to generate metrics across multiple dimensions.",
        "collection": "orders",
        "pipeline": [
            {
                "$facet": {
                    "regional_breakdown": [
                        {"$group": {"_id": "$region", "revenue": {"$sum": "$total_amount"}, "count": {"$sum": 1}}},
                        {"$sort": {"revenue": -1}},
                    ],
                    "payment_methods": [
                        {"$group": {"_id": "$payment_method", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ],
                    "status_distribution": [
                        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                    ],
                }
            }
        ],
    },
}


class AggregationRunner:
    """Executes multi-stage MongoDB aggregation pipelines with timing and formatting."""

    def __init__(self, db=None):
        self._db = db

    @property
    def db(self):
        return self._db if self._db is not None else mongo_manager.db

    async def run_pipeline(
        self,
        collection_name: str,
        pipeline: List[Dict[str, Any]],
        allow_disk_use: bool = False,
    ) -> Dict[str, Any]:
        coll = self.db[collection_name]
        t0 = time.perf_counter()

        try:
            cursor = coll.aggregate(pipeline, allowDiskUse=allow_disk_use)
            results = await cursor.to_list(length=1000)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

            serialized_results = [serialize_bson(r) for r in results]

            return {
                "success": True,
                "collection": collection_name,
                "pipeline": pipeline,
                "stage_count": len(pipeline),
                "execution_time_ms": elapsed_ms,
                "result_count": len(serialized_results),
                "results": serialized_results,
            }
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("Aggregation pipeline failed: %s", exc)
            return {
                "success": False,
                "collection": collection_name,
                "pipeline": pipeline,
                "stage_count": len(pipeline),
                "execution_time_ms": elapsed_ms,
                "result_count": 0,
                "error": str(exc),
                "results": [],
            }

    def get_presets(self) -> Dict[str, Any]:
        return SYLLABUS_PRESETS


aggregation_runner = AggregationRunner()
