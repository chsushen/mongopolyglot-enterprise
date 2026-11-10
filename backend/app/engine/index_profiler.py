import logging
from typing import Dict, Any, List, Optional

from ..core.db_mongo import mongo_manager

logger = logging.getLogger(__name__)


class IndexProfiler:
    """Manage indexes and inspect genuine MongoDB execution statistics."""

    def __init__(self, db=None):
        self._db = db

    @property
    def db(self):
        return self._db if self._db is not None else mongo_manager.db

    async def list_indexes(self, collection_name: str) -> List[Dict[str, Any]]:
        coll = self.db[collection_name]
        raw_indexes = await coll.index_information()

        formatted = []
        for name, spec in raw_indexes.items():
            keys = spec.get("key", [])
            formatted.append({
                "name": name,
                "key": keys,
                "unique": spec.get("unique", False),
                "is_geospatial": any(
                    "2dsphere" in str(value) or "2d" in str(value)
                    for _, value in keys
                ),
            })

        return formatted

    async def create_index(
        self,
        collection_name: str,
        keys: List[tuple],
        unique: bool = False,
        name: Optional[str] = None,
    ) -> str:
        coll = self.db[collection_name]
        kwargs = {"unique": unique}

        if name:
            kwargs["name"] = name

        return await coll.create_index(keys, **kwargs)

    async def drop_index(self, collection_name: str, index_name: str) -> bool:
        coll = self.db[collection_name]

        try:
            await coll.drop_index(index_name)
            return True
        except Exception as exc:
            logger.warning(
                "Failed to drop index %s. Error type: %s",
                index_name,
                type(exc).__name__,
            )
            return False

    @staticmethod
    def _walk_plan(node):
        """Collect execution-plan stages recursively."""
        stages = []
        index_names = []

        if isinstance(node, dict):
            stage = node.get("stage")
            if isinstance(stage, str):
                stages.append(stage)

            index_name = node.get("indexName")
            if isinstance(index_name, str):
                index_names.append(index_name)

            for value in node.values():
                child_stages, child_indexes = IndexProfiler._walk_plan(value)
                stages.extend(child_stages)
                index_names.extend(child_indexes)

        elif isinstance(node, list):
            for value in node:
                child_stages, child_indexes = IndexProfiler._walk_plan(value)
                stages.extend(child_stages)
                index_names.extend(child_indexes)

        return stages, index_names

    @staticmethod
    def _unavailable_result(collection_name, query, indexed_field, reason):
        """Never manufacture execution statistics for a mock database."""
        unavailable = {
            "stage": "UNAVAILABLE",
            "execution_time_ms": None,
            "docs_examined": None,
            "keys_examined": None,
            "docs_returned": None,
            "index_used": None,
            "scan_type": "Not available in mock mode",
        }

        return {
            "status": "unavailable",
            "measurement_source": "none",
            "collection": collection_name,
            "query": query,
            "indexed_field": indexed_field,
            "docs_returned": None,
            "collscan": dict(unavailable),
            "ixscan": dict(unavailable),
            "speedup_factor": "N/A",
            "efficiency_gain_pct": None,
            "recommendation": reason,
        }

    @staticmethod
    def _format_execution(explain_result, expected_stage, scan_type, index_used=None):
        """Extract executionStats and actual plan stage from explain output."""
        stats = explain_result.get("executionStats")

        if not isinstance(stats, dict):
            raise RuntimeError(
                "MongoDB explain response did not contain executionStats."
            )

        stages, discovered_indexes = IndexProfiler._walk_plan(
            stats.get("executionStages", {})
        )

        if expected_stage not in stages:
            raise RuntimeError(
                f"Expected {expected_stage} plan stage, "
                f"but MongoDB reported: {stages or 'unknown'}"
            )

        if expected_stage == "IXSCAN" and discovered_indexes:
            index_used = discovered_indexes[0]

        return {
            "stage": expected_stage,
            "execution_time_ms": stats.get("executionTimeMillis"),
            "docs_examined": stats.get("totalDocsExamined"),
            "keys_examined": stats.get("totalKeysExamined"),
            "docs_returned": stats.get("nReturned"),
            "index_used": index_used,
            "scan_type": scan_type,
        }

    async def compare_query_performance(
        self,
        collection_name: str,
        query: Dict[str, Any],
        indexed_field: str,
    ) -> Dict[str, Any]:
        """
        Compare forced COLLSCAN and hinted IXSCAN using real MongoDB
        executionStats. No timing values or document counts are fabricated.
        """

        # Mock implementations do not expose genuine MongoDB execution plans.
        if self._db is None and mongo_manager.is_mock:
            return self._unavailable_result(
                collection_name,
                query,
                indexed_field,
                "Genuine executionStats require a real MongoDB server. "
                "This request used the mock backend.",
            )

        coll = self.db[collection_name]

        # Reuse an existing index whose leading key matches the requested field.
        raw_indexes = await coll.index_information()
        index_name = None

        for name, spec in raw_indexes.items():
            keys = spec.get("key", [])
            if keys and keys[0][0] == indexed_field:
                index_name = name
                break

        # Create an index only when no suitable existing index is available.
        if index_name is None:
            safe_field = indexed_field.replace(".", "_")
            index_name = await coll.create_index(
                [(indexed_field, 1)],
                name=f"profiler_idx_{safe_field}",
            )

        database = coll.database

        # Force a collection scan without dropping or modifying indexes.
        collscan_explain = await database.command(
            "explain",
            {
                "find": collection_name,
                "filter": query,
                "hint": {"$natural": 1},
            },
            verbosity="executionStats",
        )

        # Force the selected existing index.
        ixscan_explain = await database.command(
            "explain",
            {
                "find": collection_name,
                "filter": query,
                "hint": index_name,
            },
            verbosity="executionStats",
        )

        collscan = self._format_execution(
            collscan_explain,
            "COLLSCAN",
            "Full collection scan",
        )

        ixscan = self._format_execution(
            ixscan_explain,
            "IXSCAN",
            "Index scan",
            index_name,
        )

        coll_time = collscan["execution_time_ms"]
        ix_time = ixscan["execution_time_ms"]

        # MongoDB reports executionTimeMillis as an integer. Small queries
        # may legitimately report 0 ms, so no artificial speedup is produced.
        if (
            isinstance(coll_time, (int, float))
            and isinstance(ix_time, (int, float))
            and coll_time > 0
            and ix_time > 0
        ):
            speedup = round(coll_time / ix_time, 2)
            speedup_factor = f"{speedup}x"
            efficiency = round((1 - ix_time / coll_time) * 100, 1)
        else:
            speedup_factor = "N/A"
            efficiency = None

        docs_returned = ixscan["docs_returned"]

        recommendation = (
            f"MongoDB executionStats confirmed COLLSCAN and IXSCAN "
            f"for the query on '{indexed_field}'. "
            f"Index used: {index_name}. "
        )

        if speedup_factor == "N/A":
            recommendation += (
                "Execution times were too small for a reliable "
                "millisecond-level speedup calculation."
            )
        else:
            recommendation += f"Measured explain-time ratio: {speedup_factor}."

        return {
            "status": "measured",
            "measurement_source": "MongoDB explain executionStats",
            "collection": collection_name,
            "query": query,
            "indexed_field": indexed_field,
            "docs_returned": docs_returned,
            "collscan": collscan,
            "ixscan": ixscan,
            "speedup_factor": speedup_factor,
            "efficiency_gain_pct": efficiency,
            "recommendation": recommendation,
        }


index_profiler = IndexProfiler()
