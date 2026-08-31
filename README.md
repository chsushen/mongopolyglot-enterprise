# MongoPolyglot Enterprise

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0%2B%20%7C%207.0%2B-47A248.svg?style=flat&logo=mongodb)](https://www.mongodb.com/)
[![Motor](https://img.shields.io/badge/Motor-3.3+-13AA52.svg)](https://motor.readthedocs.io/)
[![SQLite/MySQL](https://img.shields.io/badge/RDBMS-SQL_Polyglot-003B57.svg?logo=sqlite)](https://sqlite.org)
[![Tests](https://img.shields.io/badge/Tests-13%2F13%20PASSED-10B981.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**MongoPolyglot Enterprise** is a dual-engine database engineering platform designed for exploring polyglot persistence, advanced MongoDB aggregation pipelines, index latency profiling, and multi-document ACID transactions. 

The project specifically implements and validates all practical learning outcomes for **Units 4 & 5 of the 21CSE562T syllabus (SQL and NoSQL for Data Science)** at SRM Institute of Science and Technology.

---

## 👨‍💻 Author & Academic Attribution

- **Author:** **Chunduri Sushen**
- **Program:** M.Tech in Data Science
- **Institution:** SRM Institute of Science and Technology, Kattankulathur
- **Course:** 21CSE562T — SQL and NoSQL for Data Science (Continuous Learning Assessment CLA-2)

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

The system employs an asynchronous architecture built on **FastAPI** with two parallel data engines:
1. **Document Store (BSON):** MongoDB accessed via the non-blocking `Motor` AsyncIO driver (with automated in-process mock fallback for self-contained, zero-dependency local testing).
2. **Relational Store (SQL):** Mirrored schema executed asynchronously using `aiosqlite` with normalized 3NF tables.

---

## ⚖️ Real-World Architectural Tradeoffs

### 1. Embedded Documents vs. Normalized Relational Joins
* **When to Embed (MongoDB):** Entities with a 1:1 or bounded 1:Few relationship (such as items within an order or coordinates within a restaurant) benefit significantly from embedding. Because the child entities reside inside the parent's contiguous disk block, reads require a single sequential I/O operation ($\mathcal{O}(1)$ page seek) rather than expensive multi-table joins.
* **When to Normalize (RDBMS):** Unbounded relationships (e.g., millions of logs associated with a single account) or entities requiring independent lifecycle management risk exceeding MongoDB's 16MB BSON document limit. Here, 3NF relational normalization with indexed foreign keys prevents document bloat and write amplification.

### 2. Index Overhead vs. Read Performance
* **Query Latency ($O(\log N)$ vs $O(N)$):** B-Tree indexes (`IXSCAN`) drastically reduce execution latency by limiting scans to relevant leaf pages. In our McDonald's NYC dataset (150+ locations across 5 boroughs), indexing borough fields reduced scanned documents from 150 (`COLLSCAN`) down to matching rows (e.g., 42).
* **Write Penalty:** Every secondary index must be updated synchronously on write (`insert`, `update`, `delete`). On high-throughput ingestion pipelines, unneeded indexes induce significant write latency and cache churn.

### 3. ACID Transactions in Distributed NoSQL
* **Session Overhead:** While MongoDB supports multi-document transactions using replica set WiredTiger snapshots, transactions incur locking overhead and write contention. The platform demonstrates atomic two-phase transfers with deterministic rollback compensation upon network partition or hardware failure.

---

## 🎯 21CSE562T Syllabus Coverage (Units 4 & 5)

| Syllabus Component | Practical Realization in MongoPolyglot Enterprise | Source Implementation |
| :--- | :--- | :--- |
| **Unit 4: Advanced CRUD** | Full BSON CRUD operations with typed schemas and pagination | [`backend/app/engine/crud_manager.py`](backend/app/engine/crud_manager.py) |
| **Unit 4: Document Transactions** | Multi-document ACID session transfers with atomic commit & rollback | [`backend/app/engine/crud_manager.py`](backend/app/engine/crud_manager.py) |
| **Unit 4: Aggregation Pipelines** | Multi-stage MQL: `$match`, `$group`, `$unwind`, `$lookup`, and `$facet` | [`backend/app/engine/aggregation_runner.py`](backend/app/engine/aggregation_runner.py) |
| **Unit 4: Index Profiling** | Quantitative comparison between unindexed `COLLSCAN` and indexed `IXSCAN` | [`backend/app/engine/index_profiler.py`](backend/app/engine/index_profiler.py) |
| **Unit 5: Polyglot Persistence** | Comparative execution between normalized SQL and denormalized MongoDB BSON | [`backend/app/engine/polyglot_benchmarker.py`](backend/app/engine/polyglot_benchmarker.py) |
| **Unit 5: Production Datasets** | Authentic `restaurants_mcdonalds` (NYC) and `ecommerce_events` | [`scripts/seed_mcdonalds_dataset.py`](scripts/seed_mcdonalds_dataset.py) |

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.11+
* (Optional) Docker and Docker Compose
* (Optional) Local MongoDB 6.0+ instance (system defaults to in-memory sandbox if none detected)

### 1. Clone & Setup
```bash
git clone https://github.com/chsushen/mongopolyglot-enterprise.git
cd mongopolyglot-enterprise

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies via Makefile or pip
make install
# or: pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Seed Datasets
```bash
make seed
# Seeds 150+ NYC restaurants with coordinates, inspection grades, and menus
# Seeds E-Commerce accounts, products, and multi-item orders
```

### 4. Run the Application
```bash
make run
# Starts server at http://127.0.0.1:8000
```

* **Web UI Dashboard:** [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
* **API Documentation (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🐳 Docker Deployment

To spin up the entire platform (FastAPI + MongoDB 7.0) in containers:
```bash
make docker-up
# Runs both services with persistent named volumes
```

To stop containers:
```bash
make docker-down
```

---

## 🧪 Test Suite & Quality Assurance

Run the complete test suite:
```bash
make test
```

```text
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

======================== 13 passed, 1 warning in 0.60s =========================
```

---

## 📑 Pre-compiled Academic Reports

Static evaluation reports for course evaluation:
* **Markdown Report:** [`docs/CLA2_ACADEMIC_EVALUATION_REPORT.md`](docs/CLA2_ACADEMIC_EVALUATION_REPORT.md)
* **Print-Ready HTML Report:** [`docs/CLA2_ACADEMIC_EVALUATION_REPORT.html`](docs/CLA2_ACADEMIC_EVALUATION_REPORT.html)

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
