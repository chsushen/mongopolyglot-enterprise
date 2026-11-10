import math
import statistics
import time
import uuid
from datetime import datetime, timezone

import aiosqlite

from ..core.db_mongo import mongo_manager
from ..core.db_mysql import sql_manager


class PolyglotBenchmarker:
    """Repeated SQLite/MongoDB benchmarks with result-equivalence checks."""

    WARMUPS = 2
    REPETITIONS = 7
    BATCH_SIZE = 50

    def __init__(self, mongo_db=None, sql_mgr=None):
        self._mongo_db = mongo_db
        self._sql_mgr = sql_mgr or sql_manager

    @property
    def mongo_db(self):
        return self._mongo_db if self._mongo_db is not None else mongo_manager.db

    @staticmethod
    async def _sql_rows(conn, query, params=()):
        async with conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def _validate_datasets(self, conn):
        checks = [
            ("restaurants", "restaurants_mcdonalds", "restaurant_id"),
            ("users", "users", "user_id"),
            ("accounts", "accounts", "account_id"),
            ("products", "products", "product_id"),
            ("orders", "orders", "order_id"),
        ]
        counts = {}

        for sql_table, collection, field in checks:
            sql_ids = {
                row[field]
                for row in await self._sql_rows(
                    conn, f"SELECT {field} FROM {sql_table}"
                )
            }
            mongo_ids = {
                doc[field]
                async for doc in self.mongo_db[collection].find(
                    {}, {field: 1, "_id": 0}
                )
            }
            if sql_ids != mongo_ids:
                raise RuntimeError(
                    f"Benchmark stopped: {sql_table} ID mismatch "
                    f"(SQLite={len(sql_ids)}, MongoDB={len(mongo_ids)})."
                )
            counts[sql_table] = len(sql_ids)

        sql_items = {
            row["item_id"]
            for row in await self._sql_rows(
                conn, "SELECT item_id FROM order_items"
            )
        }
        mongo_items = set()
        async for order in self.mongo_db["orders"].find(
            {}, {"items": 1, "_id": 0}
        ):
            for item in order.get("items", []):
                mongo_items.add(item["item_id"])

        if sql_items != mongo_items:
            raise RuntimeError(
                "Benchmark stopped: relational and embedded order-item IDs differ "
                f"(SQLite={len(sql_items)}, MongoDB={len(mongo_items)})."
            )

        counts["order_items"] = len(sql_items)
        return {"status": "passed", "record_counts": counts}

    async def _measure_pair(self, sql_fn, mongo_fn, validator):
        sql_samples, mongo_samples = [], []

        # Warm-up runs are validated but not included in timings.
        for _ in range(self.WARMUPS):
            validator(await sql_fn(), await mongo_fn())

        # Alternate execution order to reduce ordering bias.
        for index in range(self.REPETITIONS):
            if index % 2 == 0:
                start = time.perf_counter()
                sql_result = await sql_fn()
                sql_samples.append((time.perf_counter() - start) * 1000)

                start = time.perf_counter()
                mongo_result = await mongo_fn()
                mongo_samples.append((time.perf_counter() - start) * 1000)
            else:
                start = time.perf_counter()
                mongo_result = await mongo_fn()
                mongo_samples.append((time.perf_counter() - start) * 1000)

                start = time.perf_counter()
                sql_result = await sql_fn()
                sql_samples.append((time.perf_counter() - start) * 1000)

            result_count = validator(sql_result, mongo_result)

        return sql_samples, mongo_samples, result_count

    @staticmethod
    def _make_result(
        name, operation, sql_query, mongo_query, rationale,
        sql_samples, mongo_samples, result_count
    ):
        sql_median = statistics.median(sql_samples)
        mongo_median = statistics.median(mongo_samples)

        if math.isclose(
            sql_median, mongo_median, rel_tol=0.02, abs_tol=0.01
        ):
            winner = "No material difference"
        else:
            winner = (
                "RDBMS SQL" if sql_median < mongo_median
                else "MongoDB NoSQL"
            )

        ratio = (
            round(max(sql_median, mongo_median) /
                  min(sql_median, mongo_median), 2)
            if min(sql_median, mongo_median) > 0 else None
        )

        return {
            "test_name": name,
            "operation": operation,
            "sql_query": sql_query,
            "nosql_query": mongo_query,
            "sql_latency_ms": round(sql_median, 3),
            "nosql_latency_ms": round(mongo_median, 3),
            "sql_samples_ms": [round(v, 3) for v in sql_samples],
            "nosql_samples_ms": [round(v, 3) for v in mongo_samples],
            "warmup_runs": PolyglotBenchmarker.WARMUPS,
            "repetitions": PolyglotBenchmarker.REPETITIONS,
            "result_count": result_count,
            "result_equivalence": True,
            "measurement": "Median of repeated execution times",
            "speedup_ratio": f"{ratio}x" if ratio is not None else "N/A",
            "winner": winner,
            "architectural_rationale": rationale,
        }

    async def _benchmark_batch(self, conn):
        sql_samples, mongo_samples = [], []
        suite_token = uuid.uuid4().hex[:12].upper()

        for iteration in range(self.WARMUPS + self.REPETITIONS):
            tag = f"BENCH-{suite_token}-{iteration}"
            now = datetime.now(timezone.utc).isoformat()
            documents = [
                {
                    "order_id": f"{tag}-{i:03d}",
                    "user_id": "USR-0001",
                    "order_date": now,
                    "status": "COMPLETED",
                    "total_amount": round(100.0 + i, 2),
                }
                for i in range(self.BATCH_SIZE)
            ]
            ids = [doc["order_id"] for doc in documents]
            placeholders = ",".join("?" for _ in ids)

            try:
                def sql_values():
                    return [
                        (
                            d["order_id"], d["user_id"], d["order_date"],
                            d["status"], d["total_amount"]
                        )
                        for d in documents
                    ]

                async def insert_sql():
                    start = time.perf_counter()
                    await conn.executemany(
                        """
                        INSERT INTO orders
                        (order_id, user_id, order_date, status, total_amount)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        sql_values(),
                    )
                    await conn.commit()
                    return (time.perf_counter() - start) * 1000

                async def insert_mongo():
                    start = time.perf_counter()
                    result = await self.mongo_db["orders"].insert_many(
                        [dict(d) for d in documents],
                        ordered=True,
                    )
                    elapsed = (time.perf_counter() - start) * 1000
                    if len(result.inserted_ids) != self.BATCH_SIZE:
                        raise RuntimeError("MongoDB batch insert count mismatch.")
                    return elapsed

                if iteration % 2 == 0:
                    sql_ms = await insert_sql()
                    mongo_ms = await insert_mongo()
                else:
                    mongo_ms = await insert_mongo()
                    sql_ms = await insert_sql()

                sql_rows = await self._sql_rows(
                    conn,
                    f"""
                    SELECT order_id, user_id, order_date, status, total_amount
                    FROM orders WHERE order_id IN ({placeholders})
                    ORDER BY order_id
                    """,
                    tuple(ids),
                )
                mongo_rows = await self.mongo_db["orders"].find(
                    {"order_id": {"$in": ids}},
                    {
                        "_id": 0, "order_id": 1, "user_id": 1,
                        "order_date": 1, "status": 1, "total_amount": 1,
                    },
                ).sort("order_id", 1).to_list(length=self.BATCH_SIZE)

                def normalize(rows):
                    return [
                        (
                            r["order_id"], r["user_id"], r["order_date"],
                            r["status"], round(float(r["total_amount"]), 6)
                        )
                        for r in rows
                    ]

                if (
                    len(sql_rows) != self.BATCH_SIZE
                    or normalize(sql_rows) != normalize(mongo_rows)
                ):
                    raise RuntimeError(
                        "Batch-write results differ between SQLite and MongoDB."
                    )

                if iteration >= self.WARMUPS:
                    sql_samples.append(sql_ms)
                    mongo_samples.append(mongo_ms)

            finally:
                # Exact, unique IDs only. Never delete a broad prefix.
                await conn.execute(
                    f"DELETE FROM orders WHERE order_id IN ({placeholders})",
                    tuple(ids),
                )
                await conn.commit()
                await self.mongo_db["orders"].delete_many(
                    {"order_id": {"$in": ids}}
                )

                remaining_sql = await self._sql_rows(
                    conn,
                    f"SELECT order_id FROM orders WHERE order_id IN ({placeholders})",
                    tuple(ids),
                )
                remaining_mongo = await self.mongo_db["orders"].count_documents(
                    {"order_id": {"$in": ids}}
                )
                if remaining_sql or remaining_mongo:
                    raise RuntimeError("Benchmark batch cleanup verification failed.")

        return self._make_result(
            "Batch Order Insertion (50 records)",
            "Insert 50 equivalent order records with one commit per database",
            "SQLite executemany with one transaction commit (50 orders)",
            "MongoDB insertMany (50 orders)",
            "Both stores receive the same 50 records. Results reflect the "
            "configured drivers, storage and acknowledgement settings.",
            sql_samples, mongo_samples, self.BATCH_SIZE,
        )

    async def run_comprehensive_benchmark(self):
        if self.mongo_db is None:
            raise RuntimeError("MongoDB connection is not available.")

        benchmarks = []

        # Ensure point-lookup indexing exists in the live MongoDB collection.
        await self.mongo_db["restaurants_mcdonalds"].create_index(
            [("restaurant_id", 1)]
        )

        async with aiosqlite.connect(self._sql_mgr.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")

            dataset_validation = await self._validate_datasets(conn)

            # Scenario 1: Indexed point lookup.
            target = await self._sql_rows(
                conn,
                "SELECT restaurant_id FROM restaurants "
                "ORDER BY restaurant_id LIMIT 1",
            )
            if not target:
                raise RuntimeError("No restaurant records are available.")

            target_id = target[0]["restaurant_id"]

            async def sql_point():
                return await self._sql_rows(
                    conn,
                    """
                    SELECT restaurant_id, name, borough, cuisine, zipcode, avg_rating
                    FROM restaurants WHERE restaurant_id = ?
                    """,
                    (target_id,),
                )

            async def mongo_point():
                doc = await self.mongo_db["restaurants_mcdonalds"].find_one(
                    {"restaurant_id": target_id},
                    {
                        "_id": 0, "restaurant_id": 1, "name": 1,
                        "borough": 1, "cuisine": 1,
                        "address.zipcode": 1, "avg_rating": 1,
                    },
                )
                return [doc] if doc else []

            def validate_point(sql_rows, mongo_rows):
                if len(sql_rows) != 1 or len(mongo_rows) != 1:
                    raise RuntimeError("Point-lookup result counts differ.")
                s, m = sql_rows[0], mongo_rows[0]
                left = (
                    s["restaurant_id"], s["name"], s["borough"],
                    s["cuisine"], s["zipcode"], round(float(s["avg_rating"]), 6)
                )
                right = (
                    m["restaurant_id"], m["name"], m["borough"],
                    m["cuisine"], m["address"]["zipcode"],
                    round(float(m["avg_rating"]), 6)
                )
                if left != right:
                    raise RuntimeError("Point-lookup result values differ.")
                return 1

            sql_s, mongo_s, count = await self._measure_pair(
                sql_point, mongo_point, validate_point
            )
            benchmarks.append(self._make_result(
                "Indexed Restaurant Point Lookup",
                "Retrieve the same restaurant by identifier",
                "SELECT ... FROM restaurants WHERE restaurant_id = ?",
                "db.restaurants_mcdonalds.findOne({restaurant_id: ...})",
                "Both databases retrieve and validate the same projected record.",
                sql_s, mongo_s, count,
            ))

            # Scenario 2: Equivalent borough aggregation.
            async def sql_aggregation():
                return await self._sql_rows(
                    conn,
                    """
                    SELECT borough, COUNT(*) AS count, AVG(avg_rating) AS avg_rating
                    FROM restaurants GROUP BY borough ORDER BY borough
                    """,
                )

            async def mongo_aggregation():
                cursor = self.mongo_db["restaurants_mcdonalds"].aggregate([
                    {
                        "$group": {
                            "_id": "$borough",
                            "count": {"$sum": 1},
                            "avg_rating": {"$avg": "$avg_rating"},
                        }
                    },
                    {"$sort": {"_id": 1}},
                ])
                return await cursor.to_list(length=100)

            def validate_aggregation(sql_rows, mongo_rows):
                left = {
                    r["borough"]: (int(r["count"]), float(r["avg_rating"]))
                    for r in sql_rows
                }
                right = {
                    r["_id"]: (int(r["count"]), float(r["avg_rating"]))
                    for r in mongo_rows
                }
                if left.keys() != right.keys():
                    raise RuntimeError("Aggregation group keys differ.")
                for key in left:
                    lc, la = left[key]
                    rc, ra = right[key]
                    if lc != rc or not math.isclose(
                        la, ra, rel_tol=1e-8, abs_tol=1e-8
                    ):
                        raise RuntimeError(f"Aggregation values differ for {key}.")
                return len(left)

            sql_s, mongo_s, count = await self._measure_pair(
                sql_aggregation, mongo_aggregation, validate_aggregation
            )
            benchmarks.append(self._make_result(
                "Borough Grouping and Average Rating",
                "Group restaurants by borough and calculate count and mean rating",
                "SELECT borough, COUNT(*), AVG(avg_rating) FROM restaurants GROUP BY borough",
                "db.restaurants_mcdonalds.aggregate([$group, $sort])",
                "Both operations process the same restaurants and validate "
                "equivalent group counts and average ratings.",
                sql_s, mongo_s, count,
            ))

            # Scenario 3: SQL join versus MongoDB embedded line items.
            selected = await self._sql_rows(
                conn,
                "SELECT order_id FROM orders ORDER BY order_id LIMIT 50",
            )
            order_ids = [r["order_id"] for r in selected]
            if not order_ids:
                raise RuntimeError("No orders are available for join comparison.")

            placeholders = ",".join("?" for _ in order_ids)
            join_query = f"""
                SELECT o.order_id, o.status, o.total_amount,
                       i.item_id, i.product_id, i.quantity, i.unit_price
                FROM orders o
                JOIN order_items i ON o.order_id = i.order_id
                WHERE o.order_id IN ({placeholders})
                ORDER BY o.order_id, i.item_id
            """

            async def sql_join():
                return await self._sql_rows(conn, join_query, tuple(order_ids))

            async def mongo_embedded():
                docs = await self.mongo_db["orders"].find(
                    {"order_id": {"$in": order_ids}},
                    {
                        "_id": 0, "order_id": 1, "status": 1,
                        "total_amount": 1, "items": 1,
                    },
                ).sort("order_id", 1).to_list(length=len(order_ids))

                rows = []
                for order in docs:
                    for item in order.get("items", []):
                        rows.append({
                            "order_id": order["order_id"],
                            "status": order["status"],
                            "total_amount": order["total_amount"],
                            "item_id": item["item_id"],
                            "product_id": item["product_id"],
                            "quantity": item["quantity"],
                            "unit_price": item["unit_price"],
                        })
                return sorted(rows, key=lambda r: (r["order_id"], r["item_id"]))

            def normalize_join(rows):
                return [
                    (
                        r["order_id"], r["status"],
                        round(float(r["total_amount"]), 6),
                        r["item_id"], r["product_id"], int(r["quantity"]),
                        round(float(r["unit_price"]), 6),
                    )
                    for r in rows
                ]

            def validate_join(sql_rows, mongo_rows):
                if normalize_join(sql_rows) != normalize_join(mongo_rows):
                    raise RuntimeError("JOIN and embedded item results differ.")
                return len(sql_rows)

            sql_s, mongo_s, count = await self._measure_pair(
                sql_join, mongo_embedded, validate_join
            )
            benchmarks.append(self._make_result(
                "Relational JOIN versus Embedded Items",
                "Read line items for the same first 50 orders",
                "SELECT orders JOIN order_items for the same 50 order IDs",
                "Find 50 MongoDB orders and flatten their embedded items",
                "Both representations are normalized into identical order-item "
                "rows before latency results are accepted.",
                sql_s, mongo_s, count,
            ))

            # Scenario 4: Equivalent batch insert.
            benchmarks.append(await self._benchmark_batch(conn))

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset_validation": dataset_validation,
            "measurement_protocol": (
                f"{self.WARMUPS} warm-ups; {self.REPETITIONS} measured runs; "
                "median latency; alternating execution order; "
                "result equivalence validated"
            ),
            "benchmarks": benchmarks,
            "overall_summary": {
                "recommended_store": (
                    "No universal winner; select the database by measured workload"
                ),
                "speedup_ratio": (
                    "Scenario-specific; see individual benchmark medians"
                ),
                "measurement_protocol": (
                    f"Median of {self.REPETITIONS} measured runs after "
                    f"{self.WARMUPS} warm-ups"
                ),
                "dataset_validation": "Passed",
            },
        }


polyglot_benchmarker = PolyglotBenchmarker()
