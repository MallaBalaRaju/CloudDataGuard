# CloudDataGuard — MongoDB-Based Data Redundancy Removal System

**Project Category:** Intelligent NoSQL Databases Mini-Project  
**Tech Stack:** Python 3 (FastAPI, PyMongo, Pydantic) &bull; MongoDB (BSON, `$jsonSchema`, Indexes, Aggregation, `explain()`) &bull; Cryptographic Hashing (SHA-256) &bull; Modern Responsive Web Dashboard  

---

## 📌 Executive Summary

**CloudDataGuard** is an intelligent cloud-connected data redundancy removal and storage optimization system built using **MongoDB** and **FastAPI**. 

In cloud databases, redundant records and duplicate file contents lead to unnecessary storage inflation, slow query response times, and increased cloud hosting costs. CloudDataGuard solves this by combining **NoSQL Document Modeling**, **B-Tree Unique Index Constraints**, and **SHA-256 Cryptographic Checksums** to intercept and prevent duplicate data ingestion before it reaches permanent storage.

---

## 🎯 Syllabus Alignment (Intelligent NoSQL Databases)

| Syllabus Requirement | Implementation in CloudDataGuard | Verification Method |
|---|---|---|
| **1. NoSQL Concepts** | Document-oriented architecture with decoupled collections (`records`, `duplicate_logs`). | Reviewed collections & BSON models in MongoDB |
| **2. CRUD Operations** | Complete Create, Read (All & By ID), Update, and Delete operations connected to real MongoDB actions. | Automated test suite (`pytest`) & live UI operations |
| **3. BSON Data Types** | Uses `ObjectId`, `String`, `Int64` (`size_bytes`), `ISODate` (`created_at`, `updated_at`), and Embedded Subdocuments (`metadata`). | Inspected via `/records/{id}` and View Details modal |
| **4. Schema Validation** | Dual-layer validation: Pydantic schemas in FastAPI + MongoDB engine-level `$jsonSchema` collection validator. | Validated against invalid payloads (HTTP 422 & MongoDB validator) |
| **5. Redundancy Removal** | Cryptographic SHA-256 content hashing to detect identical payloads regardless of identity; logs intercepted duplicates and tracks storage bytes saved. | Tested via identical data payload submission |
| **6. Database Indexing** | Unique indexes on `email`, `phone`, `content_hash`; search indexes on `category`, `created_at`. | Inspected via `/records/indexes` |
| **7. Query Execution Plan** | Demonstrates `explain("executionStats")` to prove index optimization (`IXSCAN` vs `COLLSCAN`). | Interactive explain runner on UI & `/records/explain` |
| **8. Aggregation Framework** | Multi-stage aggregation pipelines using `$group`, `$sum`, `$avg`, `$max`, `$sort` for analytics and storage savings. | Displayed on dashboard cards & `/records/stats` |
| **9. Python Integration** | FastAPI integrated with official PyMongo driver, environment variable management, and error handling. | Backend API execution & automated test suite |

---

## 🗄️ Database Architecture & Document Design

### Collections
1. **`records`**: Stores verified, unique, deduplicated documents.
2. **`duplicate_logs`**: Audit trail of intercepted redundant submissions, tracking saved storage bytes.

### Document Schema Example (`records` collection)
```json
{
  "_id": ObjectId("6ae376e9005ddbd5199f80dd"),
  "name": "Alice Smith",
  "email": "alice@example.com",
  "phone": "9876543210",
  "category": "Student",
  "data": "Sample academic payload text...",
  "content_hash": "ca455d6f99a39a68d68c08b17a2db495f219cb7159cb16a04d6347d8da2539f9",
  "size_bytes": 33,
  "status": "verified",
  "metadata": {
    "encoding": "utf-8",
    "content_type": "text/plain"
  },
  "created_at": ISODate("2026-10-29T16:40:09.975Z"),
  "updated_at": null
}
```

---

## ⚡ MongoDB Indexing & Query Explain

CloudDataGuard configures 6 strategic indexes:
1. `_id_`: Default MongoDB primary key clustered index.
2. `email_1` (`unique: true`): Prevents duplicate user identity records.
3. `phone_1` (`unique: true`): Enforces unique phone constraints.
4. `content_hash_1` (`unique: true`): Enforces cryptographic data redundancy removal at the database engine level.
5. `category_1`: Accelerates category filtering and aggregation pipelines.
6. `created_at_1`: Optimizes reverse-chronological sorting and pagination.

### Query Performance Comparison (`explain("executionStats")`)
- **Indexed Field (`email` / `content_hash`)**: Stage = `IXSCAN` or `EXPRESS_IXSCAN`, `totalKeysExamined = 1`, `totalDocsExamined = 1`, execution time $\approx 0\text{ ms}$.
- **Non-Indexed Field (`name`)**: Stage = `COLLSCAN` (Full Collection Scan), scans all documents in collection.

---

## 📊 Aggregation Framework Pipelines

CloudDataGuard demonstrates two production aggregation pipelines:

### Pipeline 1: Categorical Breakdown & Storage Volumes
```python
[
    {
        "$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "total_bytes": {"$sum": "$size_bytes"},
            "avg_bytes": {"$avg": "$size_bytes"},
            "latest_record": {"$max": "$created_at"}
        }
    },
    {"$sort": {"count": -1}}
]
```

### Pipeline 2: Cloud Storage Savings & Deduplication Ratio
- **Total Stored Bytes**: Calculated via `$sum` of `size_bytes` on `records`.
- **Total Bytes Saved**: Calculated via `$sum` of `bytes_saved` on `duplicate_logs`.
- **Deduplication Ratio**:
$$\text{Deduplication Ratio (\%)} = \frac{\text{Duplicates Blocked}}{\text{Total Ingestion Attempts}} \times 100$$

---

## 🚀 API Endpoints Reference

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/` | API Healthcheck & root information | 200 |
| `GET` | `/database-status` | Checks real-time MongoDB ping | 200, 500 |
| `POST` | `/records` (or `/records/add`) | **Create**: Adds unique record with SHA-256 hash | 200 (Success/Rejected), 422 |
| `GET` | `/records` | **Read All**: Retrieves records with search & pagination | 200 |
| `GET` | `/records/{id}` | **Read One**: Retrieves single document by ObjectId | 200, 400, 404 |
| `PUT` | `/records/{id}` | **Update**: Updates document fields & recalculates hash | 200, 400, 404 |
| `DELETE` | `/records/{id}` | **Delete**: Permanently removes document from MongoDB | 200, 400, 404 |
| `GET` | `/records/stats` (or `/stats`) | **Aggregation**: Returns category stats & storage savings | 200 |
| `GET` | `/records/indexes` | **Indexing**: Lists all active indexes on collections | 200 |
| `GET` | `/records/explain` | **Explain**: Demonstrates query execution plan | 200, 500 |
| `GET` | `/records/logs/duplicates` | **Audit**: Retrieves duplicate rejection logs | 200 |

---

## 🛠️ Installation & Setup Instructions

### 1. Prerequisites
- Python 3.10+ installed
- MongoDB installed and running locally (`mongodb://127.0.0.1:27017`) or a MongoDB Atlas connection string.

### 2. Verify MongoDB Service is Running (Windows PowerShell)
```powershell
Get-Service -Name "MongoDB"
```
*If stopped, start it via `Start-Service -Name "MongoDB"`.*

### 3. Install Dependencies
```powershell
cd d:\codealpa\CloudDataGuard
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Configuration (`.env`)
The `.env` file at the root contains the database configuration:
```env
MONGODB_URI=mongodb://127.0.0.1:27017
DATABASE_NAME=cloud_data_guard
```

### 5. Start the Application
Run the FastAPI development server:
```powershell
cd d:\codealpa\CloudDataGuard
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Frontend Dashboard:** [http://127.0.0.1:8000/frontend/index.html](http://127.0.0.1:8000/frontend/index.html)
- **Interactive Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 Running Automated Tests

A comprehensive test suite of 13 automated tests is included in `tests/test_crud_and_nosql.py`.

Run the test suite using `pytest`:
```powershell
cd d:\codealpa\CloudDataGuard
.\venv\Scripts\pytest.exe -v tests/test_crud_and_nosql.py
```

### Verified Test Suite Results:
```text
tests/test_crud_and_nosql.py::test_1_database_connection PASSED          [  7%]
tests/test_crud_and_nosql.py::test_2_create_record_with_sha256_hash PASSED [ 15%]
tests/test_crud_and_nosql.py::test_3_read_all_records PASSED             [ 23%]
tests/test_crud_and_nosql.py::test_4_read_single_record PASSED           [ 30%]
tests/test_crud_and_nosql.py::test_5_update_record PASSED                [ 38%]
tests/test_crud_and_nosql.py::test_6_duplicate_detection_by_email PASSED [ 46%]
tests/test_crud_and_nosql.py::test_7_duplicate_detection_by_content_hash PASSED [ 53%]
tests/test_crud_and_nosql.py::test_8_validation_errors PASSED            [ 61%]
tests/test_crud_and_nosql.py::test_9_invalid_and_nonexistent_ids PASSED  [ 69%]
tests/test_crud_and_nosql.py::test_10_aggregation_framework PASSED       [ 76%]
tests/test_crud_and_nosql.py::test_11_indexes_inspection PASSED          [ 84%]
tests/test_crud_and_nosql.py::test_12_query_explain_plan PASSED          [ 92%]
tests/test_crud_and_nosql.py::test_13_delete_record PASSED               [100%]
============================== 13 passed in 1.72s ==============================
```

---

## 🎓 Step-by-Step Viva Demonstration Script

When presenting CloudDataGuard to the examiner for **Intelligent NoSQL Databases**:

1. **Demonstrate System Architecture & MongoDB Connection:**
   - Open [http://127.0.0.1:8000/frontend/index.html](http://127.0.0.1:8000/frontend/index.html).
   - Point out the **"● MongoDB Connected"** status badge in the header.
   - Explain the 6 metric cards computed directly via MongoDB's aggregation engine.

2. **Demonstrate CREATE Operation:**
   - Click **"📝 Fill Sample Demo Data"** and click **"✔ Submit & Verify Record"**.
   - Show the success toast displaying the generated **SHA-256 cryptographic hash** and document size in bytes.
   - Show the newly created row appearing dynamically in the stored records table.

3. **Demonstrate Cryptographic Redundancy Removal (Duplicate Prevention):**
   - Attempt to submit a new record with the exact same data text payload (or same email).
   - Show the rejection toast: *"Redundant data detected: Identical content hash already stored"*.
   - Point to the **Duplicates Blocked** and **Cloud Storage Saved** metric counters updating.
   - Open the **"Redundancy Audit Logs"** tab to show the audit trail recorded in the `duplicate_logs` collection.

4. **Demonstrate READ (All & By ID):**
   - Click the **"View"** button on any record row.
   - In the modal, explain the BSON types: `_id` (`ObjectId`), `content_hash` (`String`), `size_bytes` (`Int64`), `created_at` (`ISODate`), and embedded `metadata` subdocument.

5. **Demonstrate UPDATE Operation:**
   - Click the **"Edit"** button on any row.
   - Change the category or content text and save changes.
   - Explain that the backend recalculates the SHA-256 checksum and sets `updated_at`.

6. **Demonstrate DELETE Operation:**
   - Click the **"Delete"** button on a row.
   - Confirm in the modal; show the document being permanently deleted from MongoDB and the table refreshing.

7. **Demonstrate MongoDB Indexing & `explain()` Plan:**
   - Scroll to the **"🎓 NoSQL Demonstration & Evaluation Tools"** section.
   - Click **"⚡ MongoDB Indexes"**: show the unique constraints on `email`, `phone`, and `content_hash`.
   - Click **"🔍 Query explain() Plan"**:
     - Select `email` and click **"Run explain()"** $\rightarrow$ Show **`STAGE: IXSCAN`** (Index Scan in 0 ms).
     - Select `name` and click **"Run explain()"** $\rightarrow$ Show **`STAGE: COLLSCAN`** (Full Collection Scan).
     - Explain why indexing is crucial for NoSQL performance.

8. **Demonstrate Aggregation Pipelines:**
   - Click **"📊 Aggregation Analytics"**:
   - Show the `$group` by category pipeline computing document count, total bytes, and average document size.
