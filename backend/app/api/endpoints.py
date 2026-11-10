import logging
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from ..engine.crud_manager import crud_manager
from ..core.db_mongo import mongo_manager
import re
from ..engine.aggregation_runner import aggregation_runner, SYLLABUS_PRESETS
from ..engine.index_profiler import index_profiler
from ..engine.polyglot_benchmarker import polyglot_benchmarker
from .schemas import (
    CreateDocumentRequest,
    UpdateDocumentRequest,
    DeleteDocumentRequest,
    RunAggregationRequest,
    AggregationResponse,
    TransferFundsRequest,
    TransactionResponse,
    CompareIndexQueryRequest,
    CreateIndexRequest,
    AcademicReportRequest,
    AcademicReportResponse,
    StoreCheckoutRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Document CRUD Endpoints
# ---------------------------------------------------------------------------

@router.get("/crud/documents")
async def list_documents(
    collection_name: str = Query(..., description="Target MongoDB collection"),
    limit: int = Query(25, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    """Retrieves documents from target collection with pagination."""
    docs = await crud_manager.read_documents(collection_name, limit=limit, skip=skip)
    return {"collection": collection_name, "count": len(docs), "documents": docs}


@router.post("/crud/documents")
async def create_document(req: CreateDocumentRequest):
    """Inserts a new BSON document into the specified collection."""
    result = await crud_manager.create_document(req.collection_name, req.document)
    return {"success": True, "created_document": result}


@router.put("/crud/documents")
async def update_document(req: UpdateDocumentRequest):
    """Updates matching document(s) in collection."""
    res = await crud_manager.update_document(req.collection_name, req.filter_query, req.update_spec)
    return {"success": True, "result": res}


@router.delete("/crud/documents")
async def delete_document(req: DeleteDocumentRequest):
    """Deletes matching document(s) from collection."""
    res = await crud_manager.delete_documents(req.collection_name, req.filter_query)
    return {"success": True, "result": res}


# ---------------------------------------------------------------------------
# 2. Advanced Aggregation Pipelines
# ---------------------------------------------------------------------------

@router.get("/aggregations/presets")
async def get_aggregation_presets():
    """Returns syllabus-mapped standard aggregation pipeline presets (21CSE562T)."""
    return aggregation_runner.get_presets()


@router.post("/aggregations/run", response_model=AggregationResponse)
async def run_aggregation(req: RunAggregationRequest):
    """Executes multi-stage MongoDB aggregation pipeline."""
    pipeline = req.pipeline
    if req.preset_key and req.preset_key in SYLLABUS_PRESETS:
        preset = SYLLABUS_PRESETS[req.preset_key]
        pipeline = preset["pipeline"]
        req.collection_name = preset["collection"]

    res = await aggregation_runner.run_pipeline(req.collection_name, pipeline)
    return res


# ---------------------------------------------------------------------------
# 3. Multi-Document ACID Transactions
# ---------------------------------------------------------------------------

@router.get("/transactions/accounts")
async def list_transaction_accounts(limit: int = 10):
    """Retrieves active user accounts for transaction simulation."""
    accounts = await crud_manager.read_documents("accounts", limit=limit)
    return {"accounts": accounts}


@router.post("/transactions/transfer", response_model=TransactionResponse)
async def transfer_funds_transaction(req: TransferFundsRequest):
    """Executes or aborts a multi-document ACID banking transfer across accounts."""
    try:
        res = await crud_manager.transfer_funds_transaction(
            from_account_id=req.from_account_id,
            to_account_id=req.to_account_id,
            amount=req.amount,
            simulate_failure=req.simulate_failure,
        )
        return res
    except Exception as exc:
        logger.error("Transaction error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# 4. Indexing & Query Profiler
# ---------------------------------------------------------------------------

@router.get("/indexes/list")
async def list_collection_indexes(
    collection_name: str = Query(..., description="Target collection"),
):
    """Lists existing single, compound, and geospatial indexes."""
    indexes = await index_profiler.list_indexes(collection_name)
    return {"collection": collection_name, "indexes": indexes}


@router.post("/indexes/create")
async def create_index(req: CreateIndexRequest):
    """Creates a new B-Tree or geospatial index on collection."""
    idx_name = await index_profiler.create_index(
        req.collection_name, [(req.field_name, req.order)], unique=req.unique
    )
    return {"success": True, "created_index": idx_name}


@router.post("/indexes/profile")
async def profile_query_index(req: CompareIndexQueryRequest):
    """Compares execution time between unindexed COLLSCAN and indexed IXSCAN."""
    profile_data = await index_profiler.compare_query_performance(
        collection_name=req.collection_name,
        query=req.query,
        indexed_field=req.indexed_field,
    )
    return profile_data


# ---------------------------------------------------------------------------
# 5. Polyglot Latency Benchmark (SQL vs NoSQL)
# ---------------------------------------------------------------------------

@router.get("/benchmark/run")
async def run_polyglot_benchmark():
    """Conducts real-time comparative benchmark between RDBMS SQL and MongoDB NoSQL."""
    benchmark_res = await polyglot_benchmarker.run_comprehensive_benchmark()
    return benchmark_res


# ---------------------------------------------------------------------------
# 6. CLA-2 Academic Evaluation Report Generator
# ---------------------------------------------------------------------------

@router.post("/academic/generate-report", response_model=AcademicReportResponse)
async def generate_academic_report(req: AcademicReportRequest):
    """Generates an evidence-based academic report for 21CSE562T CLA-2."""
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M:%S UTC")

    # Honor the optional report sections requested by the client.
    bench_data = None
    benchmarks = []

    if req.include_benchmarks:
        bench_data = await polyglot_benchmarker.run_comprehensive_benchmark()
        benchmarks = bench_data.get("benchmarks", [])

    # Genuine MongoDB execution statistics, or an explicit unavailable result
    # when the application is operating in mock mode.
    idx_prof = await index_profiler.compare_query_performance(
        "restaurants_mcdonalds",
        {"borough": "Manhattan"},
        "borough",
    )

    collscan = idx_prof.get("collscan") or {}
    ixscan = idx_prof.get("ixscan") or {}

    report = [
        "# 📑 Academic Evaluation Report: CLA-2",
        "",
        f"**Course Code:** {req.course_code} - Advanced Database Management Systems",
        f"**Candidate Name:** {req.student_name}",
        f"**Assessment:** {req.assessment}",
        f"**Generated:** {now_str}",
        "**Architecture:** MongoDB Atlas (document database) + local SQLite (relational database)",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "This application demonstrates advanced MongoDB operations and polyglot persistence "
        "through a FastAPI backend, MongoDB document collections, a local SQLite relational "
        "database, and a browser-based dashboard.",
        "",
        "The implementation covers document CRUD, aggregation pipelines, index management, "
        "query-plan inspection, multi-document transactions, and comparative database "
        "benchmarking.",
        "",
        "The report distinguishes implemented functionality from measured experimental "
        "evidence. It does not assign a faculty grade or claim universal database superiority.",
        "",
        "## 2. Architecture and Dataset Provenance",
        "",
        "- **Document store:** MongoDB Atlas, accessed through the application's asynchronous MongoDB driver.",
        "- **Relational store:** SQLite, stored locally and accessed through aiosqlite.",
        "- **Application layer:** FastAPI endpoints and database engine modules.",
        "- **Presentation layer:** Browser dashboard for CRUD, transactions, aggregation, indexes, and benchmarks.",
        "- **Consistency validation:** Dataset identifiers and relevant field values are checked before benchmark results are accepted.",
        "",
        "**Dataset provenance:** The application uses generated synthetic demonstration data. "
        "Restaurant coordinates are generated within approximate borough bounding boxes; "
        "they are not verified real-world restaurant coordinates. E-commerce users, products, "
        "orders, and accounts are also demonstration records, not production customer data.",
        "",
    ]

    # Include actual validated record counts when the benchmark was requested.
    if bench_data:
        counts = bench_data.get("dataset_validation", {}).get("record_counts", {})
        if counts:
            report.append("**Validated dataset record counts:**")
            for name, count in counts.items():
                report.append(f"- {name.replace('_', ' ').title()}: {count}")
            report.append("")

    # Aggregation section: list the presets that are actually implemented.
    if req.include_aggregations:
        report.extend([
            "## 3. Advanced Aggregation Pipeline Formulations",
            "",
            "The application provides the following syllabus-mapped aggregation presets. "
            "These are implemented pipeline definitions exposed through the aggregation API; "
            "their availability alone should not be interpreted as a separate benchmark result.",
            "",
        ])

        presets = aggregation_runner.get_presets()
        for key, preset in presets.items():
            stage_names = []
            for stage in preset.get("pipeline", []):
                if isinstance(stage, dict):
                    stage_names.extend(f"${name}" for name in stage.keys())

            report.append(f"### {preset.get('title', key)}")
            report.append("")
            report.append(preset.get("description", ""))
            report.append("")
            report.append(
                "**Pipeline stages:** " + ", ".join(stage_names)
                if stage_names else "**Pipeline stages:** Not specified"
            )
            report.append("")

        report.extend([
            "The implemented presets cover borough-level grouping, embedded-array "
            "unwinding, cross-collection enrichment using `$lookup`, and multi-faceted "
            "analytics using `$facet`.",
            "",
        ])

    # Genuine index profiling evidence.
    report.extend([
        "## 4. COLLSCAN vs IXSCAN: Index Management and Query Execution Profiling",
        "",
        f"**Measurement status:** {idx_prof.get('status', 'unknown')}",
        f"**Measurement source:** {idx_prof.get('measurement_source', 'not reported')}",
        f"**Collection:** {idx_prof.get('collection', 'restaurants_mcdonalds')}",
        f"**Filter:** `{idx_prof.get('query', {'borough': 'Manhattan'})}`",
        f"**Indexed field:** `{idx_prof.get('indexed_field', 'borough')}`",
        "",
    ])

    if idx_prof.get("status") == "measured":
        coll_docs = collscan.get("docs_examined")
        ix_docs = ixscan.get("docs_examined")
        reduction = None

        if (
            isinstance(coll_docs, (int, float))
            and isinstance(ix_docs, (int, float))
            and coll_docs > 0
        ):
            reduction = round((1 - ix_docs / coll_docs) * 100, 1)

        report.extend([
            "| Metric | COLLSCAN | IXSCAN |",
            "|---|---:|---:|",
            f"| Execution stage | {collscan.get('stage', 'N/A')} | {ixscan.get('stage', 'N/A')} |",
            f"| Execution time (ms) | {collscan.get('execution_time_ms', 'N/A')} | {ixscan.get('execution_time_ms', 'N/A')} |",
            f"| Documents examined | {coll_docs if coll_docs is not None else 'N/A'} | {ix_docs if ix_docs is not None else 'N/A'} |",
            f"| Keys examined | {collscan.get('keys_examined', 'N/A')} | {ixscan.get('keys_examined', 'N/A')} |",
            f"| Documents returned | {collscan.get('docs_returned', 'N/A')} | {ixscan.get('docs_returned', 'N/A')} |",
            f"| Index used | {collscan.get('index_used') or 'None'} | {ixscan.get('index_used') or 'N/A'} |",
            "",
            f"**Reported speedup:** {idx_prof.get('speedup_factor', 'N/A')}",
            f"**Document examination reduction:** {str(reduction) + '%' if reduction is not None else 'N/A'}",
            "",
            "The execution stages and counters are extracted from MongoDB `explain` "
            "output with `executionStats`. MongoDB reports execution time at "
            "millisecond resolution; a speedup ratio is therefore not reported when "
            "the measurements are too small or too coarse for a reliable calculation.",
            "",
            "The document-examination comparison describes this query and dataset only. "
            "Index benefit depends on selectivity, data distribution, index maintenance, "
            "and workload characteristics.",
            "",
        ])
    else:
        report.extend([
            "Genuine execution-plan measurements were unavailable for this report run. "
            "The profiler does not manufacture COLLSCAN or IXSCAN measurements in mock mode.",
            "",
            f"**Profiler message:** {idx_prof.get('recommendation', 'No further information available.')}",
            "",
        ])

    # Transaction implementation and verification.
    if req.include_transactions:
        report.extend([
            "## 5. Multi-Document ACID Transaction Implementation",
            "",
            "**Live MongoDB path:** The application uses a MongoDB session and native "
            "multi-document transaction on the live replica-set deployment. The transfer "
            "operation reads and updates the source and destination accounts and writes "
            "its successful audit record within the transaction.",
            "",
            "The transaction uses snapshot read concern and majority write concern. "
            "An injected failure inside the transaction causes MongoDB to abort the "
            "transaction, preventing a partially applied debit or credit.",
            "",
            "**Verification evidence:** The live application transaction path was tested "
            "with disposable accounts. A successful transfer committed, and an injected "
            "failure caused an automatic abort with the account balances remaining "
            "unchanged from their pre-failure values. Temporary verification accounts "
            "and their test audit records were subsequently removed.",
            "",
            "**Mock-mode distinction:** The mock backend provides a transaction simulation "
            "for development and automated tests. It is not represented as a native "
            "MongoDB ACID transaction.",
            "",
        ])

    # Empirical polyglot benchmark.
    if req.include_benchmarks and bench_data:
        report.extend([
            "## 6. Polyglot Persistence Benchmark: SQLite vs MongoDB",
            "",
            f"**Measurement protocol:** {bench_data.get('measurement_protocol', 'Not reported')}",
            "",
            "| Scenario | SQLite median (ms) | MongoDB median (ms) | Measured winner | Equivalent results | Result count |",
            "|---|---:|---:|---|---|---:|",
        ])

        for benchmark in benchmarks:
            test_name = str(benchmark.get("test_name", "Unnamed scenario")).replace("|", r"\|")
            sql_ms = benchmark.get("sql_latency_ms", "N/A")
            mongo_ms = benchmark.get("nosql_latency_ms", "N/A")
            winner = str(benchmark.get("winner", "Not reported")).replace("|", r"\|")
            equivalent = "Yes" if benchmark.get("result_equivalence") is True else "Not confirmed"
            result_count = benchmark.get("result_count", "N/A")

            report.append(
                f"| {test_name} | {sql_ms} | {mongo_ms} | {winner} | "
                f"{equivalent} | {result_count} |"
            )

        report.append("")
        report.append("**Scenario rationale:**")
        report.append("")
        for benchmark in benchmarks:
            name = benchmark.get("test_name", "Unnamed scenario")
            rationale = benchmark.get(
                "architectural_rationale",
                "No scenario rationale was supplied.",
            )
            report.append(f"- **{name}:** {rationale}")

        report.extend([
            "",
            "**Interpretation and limitations:**",
            "",
            "The benchmark uses two warm-up runs and seven measured runs per scenario, "
            "reports median latency, alternates execution order, and validates result "
            "equivalence before accepting measurements.",
            "",
            "SQLite executes locally, whereas MongoDB Atlas is accessed over a network. "
            "Consequently, the MongoDB application-level timings include driver and "
            "network round-trip overhead, along with the configured database operation "
            "and acknowledgement behavior. These are end-to-end application measurements, "
            "not isolated database-server execution times.",
            "",
            "The batch-insertion scenario compares SQLite `executemany()` with one "
            "transaction commit against MongoDB `insert_many()` for 50 equivalent "
            "records. Temporary benchmark records are removed by their unique IDs and "
            "cleanup is verified.",
            "",
            "The results describe this workload, dataset, software configuration, and "
            "deployment topology. They do not establish that either database is "
            "universally faster. Database selection should consider consistency "
            "requirements, data model, query patterns, deployment topology, operational "
            "cost, and measured workload.",
            "",
        ])
    elif req.include_benchmarks:
        report.extend([
            "## 6. Polyglot Persistence Benchmark",
            "",
            "Benchmark data was requested but was not returned by the benchmark engine.",
            "",
        ])
    else:
        report.extend([
            "## 6. Polyglot Persistence Benchmark",
            "",
            "Benchmark measurements were excluded by the report request.",
            "",
        ])

    # Evidence-oriented close; this is not a grade or rubric guarantee.
    report.extend([
        "## 7. Implementation Evidence Summary",
        "",
        "- **Document CRUD:** Create, read, update, and delete API endpoints are implemented.",
        "- **Aggregation:** Four syllabus-mapped MongoDB aggregation presets are implemented.",
        "- **Index management:** Index listing, index creation, and index profiling endpoints are implemented.",
        "- **Query-plan evidence:** Genuine MongoDB execution statistics are used when the live backend is active.",
        "- **Transactions:** A native MongoDB transaction path and a separate mock simulation are implemented.",
        "- **Polyglot comparison:** Four SQL-versus-MongoDB benchmark scenarios are implemented with result-equivalence validation.",
        "",
        "**Evaluation note:** This report summarizes implementation and experimental evidence. "
        "Final assessment against the course rubric and any academic grade remain the "
        "responsibility of the faculty evaluator.",
        "",
    ])

    report_md = "\n".join(report)

    return AcademicReportResponse(
        course_code=req.course_code,
        assessment=req.assessment,
        generated_at=now_str,
        markdown_content=report_md,
        summary={
            "benchmarks_evaluated": len(benchmarks),
            "ixscan_speedup": idx_prof.get("speedup_factor", "N/A"),
            "index_measurement_status": idx_prof.get("status", "unknown"),
            "polyglot_winner": (
                bench_data.get("overall_summary", {}).get(
                    "recommended_store", "Not run"
                )
                if bench_data else "Not run"
            ),
            "dataset_validation": (
                bench_data.get("dataset_validation", {}).get("status", "Not run")
                if bench_data else "Not run"
            ),
        },
    )



# ---------------------------------------------------------------------------
# Customer Store API — live MongoDB product catalogue
# ---------------------------------------------------------------------------

@router.get("/store/products")
async def get_store_products(
    q: Optional[str] = Query(None, max_length=100),
    category: Optional[str] = Query(None, max_length=80),
    sort: str = Query("featured"),
    limit: int = Query(30, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """Read products from the live MongoDB catalogue for the storefront."""
    db = mongo_manager.db
    filters = {}

    if q and q.strip():
        pattern = {"$regex": re.escape(q.strip()), "$options": "i"}
        filters["$or"] = [
            {"name": pattern},
            {"category": pattern},
            {"sku": pattern},
        ]

    if category and category.strip() and category.lower() != "all":
        filters["category"] = {"$regex": "^" + re.escape(category.strip()) + "$", "$options": "i"}

    sort_options = {
        "featured": [("product_id", 1)],
        "price_asc": [("price", 1)],
        "price_desc": [("price", -1)],
        "name": [("name", 1)],
    }
    sort_order = sort_options.get(sort, sort_options["featured"])

    total = await db["products"].count_documents(filters)
    cursor = db["products"].find(
        filters,
        {"_id": 0, "product_id": 1, "name": 1, "category": 1,
         "price": 1, "stock_quantity": 1, "sku": 1}
    ).sort(sort_order).skip(skip).limit(limit)

    products = await cursor.to_list(length=limit)
    categories = await db["products"].distinct("category")

    return {
        "success": True,
        "total": total,
        "count": len(products),
        "categories": sorted([c for c in categories if c]),
        "products": products,
    }


@router.get("/store/products/{product_id}")
async def get_store_product(product_id: str):
    """Read one product by its catalogue ID."""
    product = await mongo_manager.db["products"].find_one(
        {"product_id": product_id},
        {"_id": 0, "product_id": 1, "name": 1, "category": 1,
         "price": 1, "stock_quantity": 1, "sku": 1}
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "product": product}



@router.post("/store/checkout")
async def create_store_order(req: StoreCheckoutRequest):
    """Validate a guest cart against MongoDB and persist a pending demo order."""
    db = mongo_manager.db
    aggregated = {}

    for item in req.items:
        aggregated[item.product_id] = (
            aggregated.get(item.product_id, 0) + item.quantity
        )

    order_items = []
    total_amount = 0.0

    for product_id, quantity in aggregated.items():
        product = await db["products"].find_one(
            {"product_id": product_id},
            {"_id": 0, "product_id": 1, "name": 1, "category": 1,
             "price": 1, "stock_quantity": 1}
        )

        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product {product_id} is no longer available"
            )

        if quantity > int(product.get("stock_quantity", 0)):
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.get('name', product_id)}"
            )

        unit_price = float(product["price"])
        line_total = round(unit_price * quantity, 2)
        total_amount += line_total

        order_items.append({
            "item_id": f"ITEM-{product_id}-{uuid4().hex[:8].upper()}",
            "product_id": product_id,
            "product_name": product["name"],
            "category": product.get("category", "General"),
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": line_total,
        })

    order_id = f"STORE-{uuid4().hex[:10].upper()}"
    now = datetime.now(timezone.utc)

    order = {
        "order_id": order_id,
        "user_id": "GUEST",
        "username": req.customer_name.strip(),
        "customer_name": req.customer_name.strip(),
        "customer_email": req.customer_email.strip(),
        "region": "DEMO",
        "order_date": now,
        "status": "PENDING",
        "total_amount": round(total_amount, 2),
        "items": order_items,
        "payment_method": "demo_checkout",
    }

    await db["orders"].insert_one(order)

    return {
        "success": True,
        "order_id": order_id,
        "status": "PENDING",
        "total_amount": round(total_amount, 2),
        "message": "Demo order saved successfully. No payment was collected.",
    }
