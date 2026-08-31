import pytest
import asyncio
from backend.app.core.db_mongo import mongo_manager
from backend.app.engine.crud_manager import CRUDManager


@pytest.fixture(scope="module")
async def tx_test_db():
    db = await mongo_manager.connect(force_mock=True)
    accounts = db["accounts"]
    await accounts.delete_many({})

    # Insert two test accounts
    await accounts.insert_many([
        {"account_id": "ACC-TEST-1", "user_id": "U1", "balance": 1000.0, "currency": "USD"},
        {"account_id": "ACC-TEST-2", "user_id": "U2", "balance": 500.0, "currency": "USD"},
    ])
    yield db
    await mongo_manager.disconnect()


@pytest.mark.asyncio
async def test_transaction_commit_success(tx_test_db):
    mgr = CRUDManager(db=tx_test_db)

    res = await mgr.transfer_funds_transaction(
        from_account_id="ACC-TEST-1",
        to_account_id="ACC-TEST-2",
        amount=200.0,
        simulate_failure=False,
    )

    assert res["success"] is True
    assert res["status"] == "TRANSACTION_COMMITTED"
    assert res["from_account_balance_after"] == 800.0
    assert res["to_account_balance_after"] == 700.0

    # Verify directly in collection
    acc1 = await tx_test_db["accounts"].find_one({"account_id": "ACC-TEST-1"})
    acc2 = await tx_test_db["accounts"].find_one({"account_id": "ACC-TEST-2"})
    assert acc1["balance"] == 800.0
    assert acc2["balance"] == 700.0


@pytest.mark.asyncio
async def test_transaction_rollback_on_failure(tx_test_db):
    mgr = CRUDManager(db=tx_test_db)

    # ACC-TEST-1 currently has 800.0
    res = await mgr.transfer_funds_transaction(
        from_account_id="ACC-TEST-1",
        to_account_id="ACC-TEST-2",
        amount=300.0,
        simulate_failure=True,  # Injects failure
    )

    assert res["success"] is False
    assert res["status"] == "TRANSACTION_ABORTED_AND_ROLLED_BACK"
    assert res["from_account_balance_after"] == 800.0
    assert res["to_account_balance_after"] == 700.0

    # Verify balances were completely rolled back in database
    acc1 = await tx_test_db["accounts"].find_one({"account_id": "ACC-TEST-1"})
    acc2 = await tx_test_db["accounts"].find_one({"account_id": "ACC-TEST-2"})
    assert acc1["balance"] == 800.0
    assert acc2["balance"] == 700.0


@pytest.mark.asyncio
async def test_transaction_insufficient_funds(tx_test_db):
    mgr = CRUDManager(db=tx_test_db)

    res = await mgr.transfer_funds_transaction(
        from_account_id="ACC-TEST-1",
        to_account_id="ACC-TEST-2",
        amount=5000.0,  # Exceeds 800.0
        simulate_failure=False,
    )

    assert res["success"] is False
    assert res["status"] == "ABORTED_INSUFFICIENT_FUNDS"
    assert res["from_account_balance_after"] == 800.0
