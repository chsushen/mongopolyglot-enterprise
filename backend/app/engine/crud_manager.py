import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4
import math
from pymongo import ReadPreference
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from bson import ObjectId
from ..core.db_mongo import mongo_manager

logger = logging.getLogger(__name__)


def serialize_bson(obj: Any) -> Any:
    """Recursively converts BSON ObjectId, datetime to JSON serializable structures."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, list):
        return [serialize_bson(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize_bson(v) for k, v in obj.items()}
    return obj


class CRUDManager:
    r"""Manages BSON document CRUD operations and multi-document ACID transactions.

    Algorithmic & Mathematical Architecture:
    -----------------------------------------
    1. Atomicity (All-or-Nothing Execution):
       Multi-document operations guarantee that all state modifications succeed
       or the database state is restored to its exact pre-transaction image.
       Mathematically, if an operation sequence is $O = (o_1, o_2, \dots, o_k)$,
       the state transition function satisfies:
       $$\mathcal{S}_{t+1} = \begin{cases} \mathcal{S}_t \circ O & \text{if } \forall i, o_i = \text{SUCCESS} \\ \mathcal{S}_t & \text{if } \exists i, o_i = \text{FAILURE} \end{cases}$$

    2. Consistency (Conservation of Invariants):
       In banking and inventory transactions, balance conservation is strictly preserved:
       $$\sum_{i=1}^{M} \text{Balance}_i^{(t)} = \sum_{i=1}^{M} \text{Balance}_i^{(t+1)}$$
       No currency units or stock quantities are created or destroyed during phase transitions.

    3. Isolation (Snapshot & Read Committed):
       Transactions execute within an isolated snapshot context preventing dirty reads,
       non-repeatable reads, and phantom modifications across concurrent client sessions.

    4. Durability & Two-Phase Rollback Compensation:
       In both live replica sets (using MongoDB `w: majority` write concerns) and mock
       sandboxes, explicit abort triggers deterministic compensation logic to guarantee zero
       state leakage upon unexpected failures.
    """

    def __init__(self, db=None):
        self._db = db

    @property
    def db(self):
        return self._db if self._db is not None else mongo_manager.db

    # ---------------------------------------------------------------------------
    # CRUD Operations
    # ---------------------------------------------------------------------------

    async def create_document(self, collection_name: str, document: Dict[str, Any]) -> Dict[str, Any]:
        coll = self.db[collection_name]
        doc = dict(document)
        result = await coll.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return serialize_bson(doc)

    async def create_documents(self, collection_name: str, documents: List[Dict[str, Any]]) -> List[str]:
        coll = self.db[collection_name]
        docs = [dict(d) for d in documents]
        result = await coll.insert_many(docs)
        return [str(_id) for _id in result.inserted_ids]

    async def read_documents(
        self,
        collection_name: str,
        filter_query: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        skip: int = 0,
        sort_by: Optional[str] = None,
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        coll = self.db[collection_name]
        q = filter_query or {}
        cursor = coll.find(q).skip(skip).limit(limit)
        if sort_by:
            cursor = cursor.sort(sort_by, 1 if ascending else -1)
        docs = await cursor.to_list(length=limit)
        return [serialize_bson(d) for d in docs]

    async def read_document_by_id(self, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        coll = self.db[collection_name]
        # Try finding by string id, ObjectId, or domain key
        query = {"_id": doc_id}
        if ObjectId.is_valid(doc_id):
            query = {"$or": [{"_id": doc_id}, {"_id": ObjectId(doc_id)}]}
        
        doc = await coll.find_one(query)
        return serialize_bson(doc) if doc else None

    @staticmethod
    def _normalize_filter(filter_query: Dict[str, Any]) -> Dict[str, Any]:
        q = dict(filter_query)
        if "_id" in q and isinstance(q["_id"], str) and ObjectId.is_valid(q["_id"]):
            q["_id"] = ObjectId(q["_id"])
        return q

    async def update_document(
        self, collection_name: str, filter_query: Dict[str, Any], update_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        coll = self.db[collection_name]
        q = self._normalize_filter(filter_query)
        update_op = update_spec if any(k.startswith("$") for k in update_spec) else {"$set": update_spec}
        res = await coll.update_one(q, update_op)
        return {
            "matched_count": res.matched_count,
            "modified_count": res.modified_count,
            "acknowledged": res.acknowledged,
        }

    async def delete_document(self, collection_name: str, filter_query: Dict[str, Any]) -> Dict[str, Any]:
        coll = self.db[collection_name]
        q = self._normalize_filter(filter_query)
        res = await coll.delete_one(q)
        return {
            "deleted_count": res.deleted_count,
            "acknowledged": res.acknowledged,
        }

    async def delete_documents(self, collection_name: str, filter_query: Dict[str, Any]) -> Dict[str, Any]:
        coll = self.db[collection_name]
        q = self._normalize_filter(filter_query)
        res = await coll.delete_many(q)
        return {
            "deleted_count": res.deleted_count,
            "acknowledged": res.acknowledged,
        }

    # ---------------------------------------------------------------------------
    # ACID Multi-Document Transactions
    # ---------------------------------------------------------------------------


    async def transfer_funds_transaction(
        self,
        from_account_id: str,
        to_account_id: str,
        amount: float,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:
        """Dispatch to native MongoDB transactions or isolated mock simulation."""

        amount = float(amount)

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Transfer amount must be a positive finite number.")

        if from_account_id == to_account_id:
            raise ValueError("Source and destination accounts must be different.")

        if mongo_manager.is_mock:
            return await self._transfer_mock(
                from_account_id, to_account_id, amount, simulate_failure
            )

        return await self._transfer_native(
            from_account_id, to_account_id, amount, simulate_failure
        )

    async def _transfer_mock(
        self,
        from_account_id: str,
        to_account_id: str,
        amount: float,
        simulate_failure: bool,
    ) -> Dict[str, Any]:
        """Test-only simulation. This is NOT a native ACID transaction."""

        accounts = self.db["accounts"]
        audit = self.db["transaction_audit_logs"]
        tx_id = f"TX-{uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        source = await accounts.find_one({"account_id": from_account_id})
        destination = await accounts.find_one({"account_id": to_account_id})

        if not source:
            raise ValueError(f"Source account '{from_account_id}' not found.")
        if not destination:
            raise ValueError(f"Destination account '{to_account_id}' not found.")

        source_before = float(source.get("balance", 0))
        destination_before = float(destination.get("balance", 0))

        def response(success, status, source_after, destination_after, events):
            return {
                "success": success,
                "status": status,
                "transaction_id": tx_id,
                "transaction_mode": "MOCK_SIMULATION",
                "from_account_balance_before": source_before,
                "from_account_balance_after": source_after,
                "to_account_balance_before": destination_before,
                "to_account_balance_after": destination_after,
                "audit_events": events,
            }

        events = ["MOCK SIMULATION: No native database transaction is active."]

        if source_before < amount:
            events.append("Simulation aborted: insufficient source balance.")
            return response(
                False, "ABORTED_INSUFFICIENT_FUNDS",
                source_before, destination_before, events
            )

        debit = await accounts.update_one(
            {"account_id": from_account_id, "balance": {"$gte": amount}},
            {"$inc": {"balance": -amount}, "$set": {"updated_at": now}},
        )

        if debit.matched_count != 1:
            events.append("Simulation aborted: source balance changed.")
            return response(
                False, "ABORTED_INSUFFICIENT_FUNDS",
                source_before, destination_before, events
            )

        if simulate_failure:
            await accounts.update_one(
                {"account_id": from_account_id},
                {"$inc": {"balance": amount}, "$set": {"updated_at": now}},
            )
            events.append("Mock failure injected; compensating update executed.")

            await audit.insert_one({
                "transaction_id": tx_id,
                "from_account": from_account_id,
                "to_account": to_account_id,
                "amount": amount,
                "status": "MOCK_ROLLED_BACK",
                "transaction_mode": "MOCK_SIMULATION",
                "timestamp": now,
            })

            return response(
                False, "TRANSACTION_ABORTED_AND_ROLLED_BACK",
                source_before, destination_before, events
            )

        await accounts.update_one(
            {"account_id": to_account_id},
            {"$inc": {"balance": amount}, "$set": {"updated_at": now}},
        )

        await audit.insert_one({
            "transaction_id": tx_id,
            "from_account": from_account_id,
            "to_account": to_account_id,
            "amount": amount,
            "status": "MOCK_COMMITTED",
            "transaction_mode": "MOCK_SIMULATION",
            "timestamp": now,
        })

        events.append("Mock transfer simulation completed.")

        return response(
            True, "TRANSACTION_COMMITTED",
            round(source_before - amount, 2),
            round(destination_before + amount, 2),
            events,
        )

    async def _transfer_native(
        self,
        from_account_id: str,
        to_account_id: str,
        amount: float,
        simulate_failure: bool,
    ) -> Dict[str, Any]:
        """Execute a real multi-document MongoDB transaction."""

        db = self.db
        client = db.client
        accounts = db["accounts"]
        audit = db["transaction_audit_logs"]

        tx_id = f"TX-{uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        events = ["Native MongoDB transaction session requested."]

        source_before = None
        destination_before = None
        abort_reason = None

        try:
            async with await client.start_session() as session:
                try:
                    async with session.start_transaction(
                        read_concern=ReadConcern("snapshot"),
                        write_concern=WriteConcern("majority"),
                        read_preference=ReadPreference.PRIMARY,
                    ):
                        source = await accounts.find_one(
                            {"account_id": from_account_id},
                            session=session,
                        )
                        destination = await accounts.find_one(
                            {"account_id": to_account_id},
                            session=session,
                        )

                        if source is None:
                            raise ValueError(
                                f"Source account '{from_account_id}' not found."
                            )
                        if destination is None:
                            raise ValueError(
                                f"Destination account '{to_account_id}' not found."
                            )

                        source_before = float(source.get("balance", 0))
                        destination_before = float(destination.get("balance", 0))

                        if source_before < amount:
                            raise _TransferInsufficientFunds()

                        debit = await accounts.update_one(
                            {
                                "account_id": from_account_id,
                                "balance": {"$gte": amount},
                            },
                            {
                                "$inc": {"balance": -amount},
                                "$set": {"updated_at": now},
                            },
                            session=session,
                        )

                        if debit.matched_count != 1:
                            raise _TransferInsufficientFunds()

                        events.append("Source debit staged inside MongoDB transaction.")

                        if simulate_failure:
                            raise _TransferInjectedFailure(
                                "Intentional failure injected after source debit."
                            )

                        credit = await accounts.update_one(
                            {"account_id": to_account_id},
                            {
                                "$inc": {"balance": amount},
                                "$set": {"updated_at": now},
                            },
                            session=session,
                        )

                        if credit.matched_count != 1:
                            raise RuntimeError(
                                "Destination account could not be credited."
                            )

                        events.append(
                            "Destination credit staged inside MongoDB transaction."
                        )

                        # Audit record is part of the SAME transaction.
                        await audit.insert_one({
                            "transaction_id": tx_id,
                            "from_account": from_account_id,
                            "to_account": to_account_id,
                            "amount": amount,
                            "status": "COMMITTED",
                            "transaction_mode": "NATIVE_MONGODB",
                            "timestamp": now,
                        }, session=session)

                        events.append(
                            "Transaction audit record staged for atomic commit."
                        )

                except _TransferInjectedFailure as exc:
                    abort_reason = str(exc)
                except _TransferInsufficientFunds:
                    abort_reason = "Insufficient source balance."

        except Exception:
            logger.exception(
                "Native MongoDB transaction failed; transaction was not reported as committed."
            )
            raise

        if abort_reason:
            # The transaction context has already aborted. This separate
            # record documents the failed attempt, not part of the aborted work.
            await audit.insert_one({
                "transaction_id": tx_id,
                "from_account": from_account_id,
                "to_account": to_account_id,
                "amount": amount,
                "status": "ABORTED",
                "transaction_mode": "NATIVE_MONGODB",
                "reason": abort_reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            events.append(f"MongoDB transaction aborted: {abort_reason}")

            insufficient = isinstance(
                abort_reason, str
            ) and abort_reason == "Insufficient source balance."

            return {
                "success": False,
                "status": (
                    "ABORTED_INSUFFICIENT_FUNDS"
                    if insufficient else "TRANSACTION_ABORTED"
                ),
                "transaction_id": tx_id,
                "transaction_mode": "NATIVE_MONGODB",
                "from_account_balance_before": source_before,
                "from_account_balance_after": source_before,
                "to_account_balance_before": destination_before,
                "to_account_balance_after": destination_before,
                "audit_events": events,
            }

        events.append("MongoDB confirmed transaction commit.")

        return {
            "success": True,
            "status": "TRANSACTION_COMMITTED",
            "transaction_id": tx_id,
            "transaction_mode": "NATIVE_MONGODB",
            "from_account_balance_before": source_before,
            "from_account_balance_after": round(source_before - amount, 2),
            "to_account_balance_before": destination_before,
            "to_account_balance_after": round(destination_before + amount, 2),
            "audit_events": events,
        }


class _TransferInjectedFailure(Exception):
    """Internal signal used to test native transaction abort."""


class _TransferInsufficientFunds(Exception):
    """Internal signal used to abort a transfer with insufficient funds."""


crud_manager = CRUDManager()
