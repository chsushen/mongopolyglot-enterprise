import pytest
import asyncio
from backend.app.core.db_mongo import mongo_manager
from backend.app.engine.crud_manager import CRUDManager


@pytest.fixture(scope="module")
async def crud_test_db():
    db = await mongo_manager.connect(force_mock=True)
    yield db
    await mongo_manager.disconnect()


@pytest.mark.asyncio
async def test_crud_lifecycle(crud_test_db):
    mgr = CRUDManager(db=crud_test_db)
    coll_name = "test_crud_coll"

    # 1. Create Document
    doc_payload = {
        "title": "Enterprise Database Systems",
        "code": "21CSE562T",
        "credits": 4,
        "active": True,
    }
    created = await mgr.create_document(coll_name, doc_payload)
    assert "_id" in created
    assert created["title"] == "Enterprise Database Systems"
    doc_id = created["_id"]

    # 2. Read Document by ID
    fetched = await mgr.read_document_by_id(coll_name, doc_id)
    assert fetched is not None
    assert fetched["code"] == "21CSE562T"

    # 3. Update Document
    update_res = await mgr.update_document(coll_name, {"_id": doc_id}, {"credits": 5})
    assert update_res["matched_count"] == 1
    assert update_res["modified_count"] == 1

    # Verify updated value
    updated_doc = await mgr.read_document_by_id(coll_name, doc_id)
    assert updated_doc["credits"] == 5

    # 4. List Documents
    all_docs = await mgr.read_documents(coll_name, limit=10)
    assert len(all_docs) >= 1

    # 5. Delete Document
    del_res = await mgr.delete_document(coll_name, {"_id": doc_id})
    assert del_res["deleted_count"] == 1

    # Verify deleted
    none_doc = await mgr.read_document_by_id(coll_name, doc_id)
    assert none_doc is None
