# 🍃 MongoPolyglot Enterprise

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-5.0%2B%20%7C%206.0%2B%20%7C%207.0%2B-47A248.svg?style=flat&logo=mongodb)](https://www.mongodb.com/)
[![Motor](https://img.shields.io/badge/Motor-AsyncIO_Driver-13AA52.svg)](https://motor.readthedocs.io/)
[![SQLite/MySQL](https://img.shields.io/badge/RDBMS-SQL_Polyglot-003B57.svg?logo=sqlite)](https://sqlite.org)
[![Syllabus](https://img.shields.io/badge/Syllabus-21CSE562T%20(CLA--2)-8B5CF6.svg)](https://www.srmist.edu.in)
[![Tests](https://img.shields.io/badge/Tests-13%2F13%20PASSED-10B981.svg)]()

> **Enterprise MongoDB & SQL Polyglot Database Platform with Aggregation Pipelines, Performance Profiling, and ACID Transactions.**  
> Built for **Units 4 & 5 of the 21CSE562T syllabus (Continuous Learning Assessment CLA-2)**.

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

## 🚀 Key Modules & Capabilities

### 1. Advanced MQL Aggregation Pipelines (`backend/app/engine/aggregation_runner.py`)
- **`$match` & `$group`:** Borough restaurant density, average rating calculations, and capacity analytics.
- **`$unwind`:** Flattens embedded menu arrays to analyze category pricing and statistical spreads.
- **`$lookup` (NoSQL Join):** Left outer joins between `orders` and `accounts` to enrich order records with live banking status.
- **`$facet`:** Multi-faceted simultaneous pipeline execution (revenue by region, payment method frequency, and order status distributions).

### 2. Index Profiling & Optimization (`backend/app/engine/index_profiler.py`)
- Quantitative comparison between unindexed collection table scans (`COLLSCAN`) and B-Tree index scans (`IXSCAN`).
- Measures execution time in milliseconds and documents examined vs documents returned ratios.
- Visual comparative bars and automated production index recommendations.

### 3. Multi-Document ACID Transactions (`backend/app/engine/crud_manager.py`)
- Simulates banking funds transfer between accounts.
- Atomic two-phase execution: debit source account, credit destination account, and commit audit trail.
- **Deterministic Rollback:** Injects mid-transaction network partitions or crashes, validating that debits are rolled back and balances are restored with zero leakage.

### 4. Polyglot Persistence Benchmark (`backend/app/engine/polyglot_benchmarker.py`)
- Comparative latency benchmark running equivalent queries across SQLite/MySQL and MongoDB BSON stores:
  1. Point Query Lookup by Primary Key / Indexed ID.
  2. Multi-Dimension Group By & Aggregation.
  3. Relational `JOIN` vs Embedded Document Read.
  4. Batch Document Ingestion (50 records).

### 5. Standard Curricula Datasets (`scripts/`)
- `restaurants_mcdonalds`: NYC restaurants across 5 boroughs with coordinates, health inspection grades, and menus.
- `ecommerce_events`: Accounts, users, products, orders, and line items.

---

## 🧪 Comprehensive Verification Suite

Run all 13 automated tests:
```bash
PYTHONPATH=. pytest tests/ -v
```

```
======================== 13 passed, 1 warning in 0.63s =========================
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
```

---

## 🌐 Quick Start Guide

### 1. Launch Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Access Mission Control Dashboard
- **Web UI:** [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
- **FastAPI Interactive API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **CLA-2 Report Endpoint:** `POST http://127.0.0.1:8000/api/v1/academic/generate-report`
