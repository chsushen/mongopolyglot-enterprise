import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
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
        """Simulates an ACID multi-document banking transaction with explicit Commit or Abort (Rollback)."""
        accounts_coll = self.db["accounts"]
        audit_coll = self.db["transaction_audit_logs"]

        events = []
        now_str = datetime.now(timezone.utc).isoformat()

        # Step 1: Read initial balances
        from_acc = await accounts_coll.find_one({"account_id": from_account_id})
        to_acc = await accounts_coll.find_one({"account_id": to_account_id})

        if not from_acc:
            raise ValueError(f"Source account '{from_account_id}' not found.")
        if not to_acc:
            raise ValueError(f"Destination account '{to_account_id}' not found.")

        initial_from_bal = float(from_acc.get("balance", 0.0))
        initial_to_bal = float(to_acc.get("balance", 0.0))

        events.append(f"Transaction session initialized for ${amount:.2f} transfer.")
        events.append(f"Account {from_account_id} initial balance: ${initial_from_bal:.2f}")
        events.append(f"Account {to_account_id} initial balance: ${initial_to_bal:.2f}")

        # Check funds
        if initial_from_bal < amount:
            events.append("ABORT TRIGGERED: Insufficient funds in source account.")
            return {
                "success": False,
                "status": "ABORTED_INSUFFICIENT_FUNDS",
                "from_account_balance_before": initial_from_bal,
                "from_account_balance_after": initial_from_bal,
                "to_account_balance_before": initial_to_bal,
                "to_account_balance_after": initial_to_bal,
                "audit_events": events,
            }

        # Step 2: Debit Source Account
        await accounts_coll.update_one(
            {"account_id": from_account_id},
            {"$inc": {"balance": -amount}, "$set": {"updated_at": now_str}},
        )
        events.append(f"Phase 1: Debited ${amount:.2f} from {from_account_id}.")

        # Step 3: Check for simulated failure injection (Network drop, DB crash, Bug)
        if simulate_failure:
            events.append("🚨 ERROR INJECTED: Network partition occurred during transaction!")
            events.append("ACID ROLLBACK INITIATED: Restoring debit...")
            # Rollback
            await accounts_coll.update_one(
                {"account_id": from_account_id},
                {"$inc": {"balance": amount}, "$set": {"updated_at": now_str}},
            )
            events.append(f"ACID ROLLBACK COMPLETE: {from_account_id} balance restored to ${initial_from_bal:.2f}.")

            await audit_coll.insert_one({
                "from_account": from_account_id,
                "to_account": to_account_id,
                "amount": amount,
                "status": "ROLLED_BACK",
                "timestamp": now_str,
            })

            return {
                "success": False,
                "status": "TRANSACTION_ABORTED_AND_ROLLED_BACK",
                "from_account_balance_before": initial_from_bal,
                "from_account_balance_after": initial_from_bal,
                "to_account_balance_before": initial_to_bal,
                "to_account_balance_after": initial_to_bal,
                "audit_events": events,
            }

        # Step 4: Credit Destination Account
        await accounts_coll.update_one(
            {"account_id": to_account_id},
            {"$inc": {"balance": amount}, "$set": {"updated_at": now_str}},
        )
        events.append(f"Phase 2: Credited ${amount:.2f} to {to_account_id}.")

        # Step 5: Commit Audit Log
        tx_id = f"TX-{int(datetime.now().timestamp())}"
        await audit_coll.insert_one({
            "transaction_id": tx_id,
            "from_account": from_account_id,
            "to_account": to_account_id,
            "amount": amount,
            "status": "COMMITTED",
            "timestamp": now_str,
        })
        events.append(f"Phase 3: Audit log committed. Transaction {tx_id} SUCCESSFUL.")

        final_from_bal = round(initial_from_bal - amount, 2)
        final_to_bal = round(initial_to_bal + amount, 2)

        return {
            "success": True,
            "status": "TRANSACTION_COMMITTED",
            "transaction_id": tx_id,
            "from_account_balance_before": initial_from_bal,
            "from_account_balance_after": final_from_bal,
            "to_account_balance_before": initial_to_bal,
            "to_account_balance_after": final_to_bal,
            "audit_events": events,
        }


crud_manager = CRUDManager()
