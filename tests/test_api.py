import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.db_mongo import mongo_manager


@pytest.fixture(scope="module", autouse=True)
def init_lifespan():
    original_mock_mode = settings.USE_MOCK_SANDBOX
    settings.USE_MOCK_SANDBOX = True

    try:
        with TestClient(app) as client:
            assert mongo_manager.is_mock, (
                "API tests must never connect to the real Atlas database."
            )
            yield client
    finally:
        settings.USE_MOCK_SANDBOX = original_mock_mode


def test_root_status(init_lifespan):
    client = init_lifespan
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "MongoPolyglot" in resp.text
    assert "Discover Products" in resp.text


def test_dashboard_page_rendering(init_lifespan):
    client = init_lifespan
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html = resp.text

    # Verify syllabus branding
    assert "MongoPolyglot Enterprise" in html
    assert "21CSE562T" in html
    assert "CLA-2 Compliant" in html

    # Verify all 5 Workspaces
    assert 'id="ws-aggregations"' in html
    assert 'id="ws-profiler"' in html
    assert 'id="ws-transactions"' in html
    assert 'id="ws-benchmark"' in html
    assert 'id="ws-report"' in html


def test_aggregation_endpoints(init_lifespan):
    client = init_lifespan
    # 1. Fetch Presets
    presets_resp = client.get("/api/v1/aggregations/presets")
    assert presets_resp.status_code == 200
    presets = presets_resp.json()
    assert "borough_performance" in presets
    assert "menu_unwind_analysis" in presets

    # 2. Run Preset Pipeline
    run_resp = client.post(
        "/api/v1/aggregations/run",
        json={"collection_name": "restaurants_mcdonalds", "pipeline": [], "preset_key": "borough_performance"}
    )
    assert run_resp.status_code == 200
    res_data = run_resp.json()
    assert res_data["success"] is True
    assert res_data["result_count"] > 0


def test_transaction_api(init_lifespan):
    client = init_lifespan
    # Fetch accounts
    acc_resp = client.get("/api/v1/transactions/accounts?limit=5")
    assert acc_resp.status_code == 200
    accounts = acc_resp.json()["accounts"]
    assert len(accounts) >= 2

    acc1 = accounts[0]["account_id"]
    acc2 = accounts[1]["account_id"]

    # Execute transfer
    tx_resp = client.post(
        "/api/v1/transactions/transfer",
        json={"from_account_id": acc1, "to_account_id": acc2, "amount": 50.0, "simulate_failure": False}
    )
    assert tx_resp.status_code == 200
    tx_data = tx_resp.json()
    assert tx_data["success"] is True
    assert tx_data["status"] == "TRANSACTION_COMMITTED"


def test_index_profiler_and_benchmark(init_lifespan):
    client = init_lifespan
    # Profile index
    idx_resp = client.post(
        "/api/v1/indexes/profile",
        json={"collection_name": "restaurants_mcdonalds", "query": {"borough": "Manhattan"}, "indexed_field": "borough"}
    )
    assert idx_resp.status_code == 200
    idx_data = idx_resp.json()
    assert "collscan" in idx_data
    assert "ixscan" in idx_data
    assert "speedup_factor" in idx_data

    # Polyglot benchmark
    bench_resp = client.get("/api/v1/benchmark/run")
    assert bench_resp.status_code == 200
    bench_data = bench_resp.json()
    assert len(bench_data["benchmarks"]) >= 3
    assert "overall_summary" in bench_data


def test_cla2_academic_report_generation(init_lifespan):
    client = init_lifespan
    rep_resp = client.post(
        "/api/v1/academic/generate-report",
        json={"student_name": "Candidate Principal Engineer", "course_code": "21CSE562T", "assessment": "CLA-2"}
    )
    assert rep_resp.status_code == 200
    rep_data = rep_resp.json()
    assert rep_data["course_code"] == "21CSE562T"
    assert "# 📑 Academic Evaluation Report" in rep_data["markdown_content"]
    assert "COLLSCAN vs IXSCAN" in rep_data["markdown_content"]
