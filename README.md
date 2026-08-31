# 🍃 MongoPolyglot Enterprise

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-5.0%2B%20%7C%206.0%2B%20%7C%207.0%2B-47A248.svg?style=flat&logo=mongodb)](https://www.mongodb.com/)
[![Motor](https://img.shields.io/badge/Motor-AsyncIO_Driver-13AA52.svg)](https://motor.readthedocs.io/)
[![SQLite/MySQL](https://img.shields.io/badge/RDBMS-SQL_Polyglot-003B57.svg?logo=sqlite)](https://sqlite.org)
[![Syllabus](https://img.shields.io/badge/Syllabus-21CSE562T%20(CLA--2)-8B5CF6.svg)](https://www.srmist.edu.in)
[![Tests](https://img.shields.io/badge/Tests-13%2F13%20PASSED-10B981.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Enterprise MongoDB & SQL Polyglot Database Platform with Aggregation Pipelines, Performance Profiling, and ACID Transactions.**  
> Purpose-built for **Units 4 & 5 of the 21CSE562T syllabus (SQL and NoSQL for Data Science — Continuous Learning Assessment CLA-2)**.

---

## 🏛️ System Architecture

```text
+---------------------------------------------------------------------------------------------------------+
|                                MONGO-POLYGLOT ENTERPRISE MISSION CONTROL                                |
|                                       http://127.0.0.1:8000/dashboard                                   |
+---------------------------------------------------------------------------------------------------------+
       |                           |                           |                           |
       v                           v                           v                           v
 [ Workspace 1 ]             [ Workspace 2 ]             [ Workspace 3 ]             [ Workspace 4 ]
 MQL Aggregations            Index Profiler              ACID Transactions           Polyglot Benchmarks
 - $match, $group, $sort     - Single/Compound/Geospatial- Session Management        - SQL JOIN vs NoSQL
 - $unwind (Arrays)          - COLLSCAN vs IXSCAN        - Two-Phase Commit          - Latency Matrix
 - $lookup (NoSQL Joins)     - Latency & Examined Docs   - Failure Rollback          - Hybrid Store Rec
 - $facet (Multi-Stage)      - Speedup Factor            - Audit Event Trail
                                                           |
                                                           v
                                                     [ Workspace 5 ]
                                              CLA-2 Academic Report Exporter
                                              - Automated Markdown Compilation
                                              - Evaluator Rubric Verification
```

---

## 🎯 Direct Academic Alignment to 21CSE562T (Units 4 & 5)

| Syllabus Topic | Practical Realization in MongoPolyglot Enterprise | Source Implementation |
| :--- | :--- | :--- |
| **Unit 4: Advanced CRUD** | Full BSON CRUD operations with typed schemas and pagination | [`backend/app/engine/crud_manager.py`](backend/app/engine/crud_manager.py) |
| **Unit 4: Document Transactions** | Multi-document ACID session transfers with atomic commit & rollback | [`backend/app/engine/crud_manager.py`](backend/app/engine/crud_manager.py) |
| **Unit 4: Aggregation Pipelines** | Multi-stage MQL: `$match`, `$group`, `$unwind`, `$lookup`, and `$facet` | [`backend/app/engine/aggregation_runner.py`](backend/app/engine/aggregation_runner.py) |
| **Unit 4: Index Profiling** | Quantitative comparison between unindexed `COLLSCAN` and indexed `IXSCAN` | [`backend/app/engine/index_profiler.py`](backend/app/engine/index_profiler.py) |
| **Unit 5: Polyglot Persistence** | Comparative execution between normalized SQL and denormalized MongoDB BSON | [`backend/app/engine/polyglot_benchmarker.py`](backend/app/engine/polyglot_benchmarker.py) |
| **Unit 5: Production Datasets** | Authentic `restaurants_mcdonalds` (NYC) and `ecommerce_events` | [`scripts/seed_mcdonalds_dataset.py`](scripts/seed_mcdonalds_dataset.py) |

---

## 🚀 Key Feature Workspaces

### 1. Interactive MQL Aggregation Builder (`Workspace 1`)
- **Borough Restaurant Analytics:** Uses `$match` and `$group` to aggregate restaurant density, average customer review ratings, and seating capacities across Manhattan, Brooklyn, Queens, Bronx, and Staten Island.
- **Menu Array Unwinding:** Uses `$unwind` on the embedded menu items array, allowing category pricing distributions and price bounds (`$min`, `$max`, `$avg`) without schema changes.
- **Relational NoSQL Join:** `$lookup` connects `orders` with `accounts` based on `user_id` to perform left outer joins.
- **Multi-Faceted Categorization:** `$facet` processes regional revenue, payment method breakdowns, and order fulfillment distributions in a single pass.

### 2. Index Profiler: COLLSCAN vs IXSCAN (`Workspace 2`)
- Measures exact execution time in milliseconds.
- Tracks `docs_examined` vs `docs_returned` ratios.
- Provides visual millisecond latency bars demonstrating $O(1)$ / $O(\log N)$ B-Tree performance vs $O(N)$ full table scans.

### 3. Multi-Document ACID Transactions (`Workspace 3`)
- Simulates real-time banking transfers between user accounts.
- **Commit Scenario:** Deducts amount from source account, credits destination account, and commits transaction audit log atomically.
- **Rollback Scenario:** Injects mid-transaction network failures to trigger deterministic rollback, restoring original account balances with zero data leakage.

### 4. Polyglot Persistence Benchmark (`Workspace 4`)
- Real-time side-by-side benchmark matrix measuring:
  1. Point query by indexed ID (`SELECT ... WHERE id = ?` vs `findOne({ _id: ... })`).
  2. Categorical multi-dimension group by (`GROUP BY` vs `$match` + `$group`).
  3. Relational multi-table join vs embedded document read (`JOIN` vs embedded BSON array).
  4. Batch document ingestion throughput (50 records).

### 5. CLA-2 Academic Evaluation Report Exporter (`Workspace 5`)
- One-click generation of publication-grade Markdown reports containing query syntax, execution stats, output screenshots, and observations formatted for university evaluation.

---

## 🛠️ Quick Start Guide

### 1. Environment Setup & Installation
```bash
git clone https://github.com/chsushen/mongopolyglot-enterprise.git
cd mongopolyglot-enterprise

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Dataset Seeding
```bash
# Seed 150+ NYC restaurants with coordinates, inspection grades, and menus
python scripts/seed_mcdonalds_dataset.py

# Seed E-Commerce datasets (users, accounts, products, orders)
python scripts/seed_ecommerce_dataset.py
```

### 3. Launch Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Comprehensive Automated Test Verification

Execute all 13 unit, integration, and API test suites:
```bash
pytest tests/ -v
```

```
============================= test session starts ==============================
tests/test_aggregations.py::test_match_group_sort_aggregation PASSED     [  7%]
tests/test_aggregations.py::test_unwind_aggregation PASSED               [ 15%]
tests/test_aggregations.py::test_facet_aggregation PASSED                [ 23%]
tests/test_api.py::test_root_status PASSED                               [ 30%]
tests/test_api.py::test_dashboard_page_rendering PASSED                  [ 38%]
tests/test_api.py::test_aggregation_endpoints PASSED                     [ 46%]
tests/test_api.py::test_transaction_api PASSED                           [ 53%]
tests/test_api.py::test_index_profiler_and_benchmark PASSED              [ 61%]
tests/test_api.py::test_cla2_academic_report_generation PASSED           [ 69%]
tests/test_crud.py::test_crud_lifecycle PASSED                           [ 76%]
tests/test_transactions.py::test_transaction_commit_success PASSED       [ 84%]
tests/test_transactions.py::test_transaction_rollback_on_failure PASSED  [ 92%]
tests/test_transactions.py::test_transaction_insufficient_funds PASSED   [100%]

======================== 13 passed, 1 warning in 0.63s =========================
```

---

## 🌐 Live Service Endpoints

| Endpoint | Method | Purpose |
| :--- | :---: | :--- |
| `/dashboard` | `GET` | Dark-Mode Mission Control Console (5 Workspaces) |
| `/docs` | `GET` | FastAPI Interactive Swagger UI Documentation |
| `/api/v1/aggregations/presets` | `GET` | Fetch 21CSE562T MQL pipeline presets |
| `/api/v1/aggregations/run` | `POST` | Execute custom MongoDB aggregation pipeline |
| `/api/v1/transactions/transfer`| `POST` | Execute or abort multi-document ACID transfer |
| `/api/v1/indexes/profile` | `POST` | Profile query: COLLSCAN vs IXSCAN executionStats |
| `/api/v1/benchmark/run` | `GET` | Run live SQL vs NoSQL latency benchmark |
| `/api/v1/academic/generate-report` | `POST` | Generate publication-grade CLA-2 Markdown report |

---

## 📄 License
MIT License. Developed for Academic Assessment and Enterprise Polyglot Systems Engineering.
