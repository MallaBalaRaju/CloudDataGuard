import hashlib
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, status
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from backend.app.database import (
    records_collection,
    duplicate_logs_collection
)
from backend.app.schemas import RecordCreate, RecordUpdate

router = APIRouter(
    prefix="/records",
    tags=["Records"]
)


# ─────────────────────────────────────────────────────────
# HELPER FUNCTIONS (SHA-256 Hashing, Sizing & Serialization)
# ─────────────────────────────────────────────────────────

def compute_content_hash(text: str) -> str:
    """
    Computes SHA-256 cryptographic checksum of data content
    for data redundancy identification.
    """
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def compute_size_bytes(text: str) -> int:
    """Calculates data size in bytes."""
    return len(text.encode("utf-8"))


def _serialize(record: dict) -> dict:
    """Serializes MongoDB BSON document into JSON-serializable dictionary."""
    return {
        "id":           str(record["_id"]),
        "name":         record.get("name", ""),
        "email":        record.get("email", ""),
        "phone":        record.get("phone", ""),
        "category":     record.get("category", ""),
        "data":         record.get("data", ""),
        "content_hash": record.get("content_hash"),
        "size_bytes":   record.get("size_bytes", compute_size_bytes(record.get("data", ""))),
        "status":       record.get("status", "verified"),
        "metadata":     record.get("metadata", {"encoding": "utf-8", "content_type": "text/plain"}),
        "created_at":   record["created_at"].isoformat() if record.get("created_at") else None,
        "updated_at":   record["updated_at"].isoformat() if record.get("updated_at") else None,
    }


# ─────────────────────────────────────────────────────────
# CREATE  –  POST /records/add & POST /records/
# ─────────────────────────────────────────────────────────

@router.post("", summary="Add a new record (Create)")
@router.post("/add", summary="Add a new record (Create alias)")
def add_record(record: RecordCreate):
    """
    Creates a new unique record in MongoDB with SHA-256 redundancy detection.
    
    Duplicates are detected on:
    1. Email address
    2. Phone number
    3. Content Hash (Identical data redundancy)
    """
    email = str(record.email).lower().strip()
    phone = record.phone.strip()
    content_hash = compute_content_hash(record.data)
    size_bytes = compute_size_bytes(record.data)

    # Check for existing duplicate records
    existing = records_collection.find_one(
        {
            "$or": [
                {"email": email},
                {"phone": phone},
                {"content_hash": content_hash}
            ]
        }
    )

    if existing:
        dup_fields = []
        if existing.get("email") == email:
            dup_fields.append("email")
        if existing.get("phone") == phone:
            dup_fields.append("phone")
        if existing.get("content_hash") == content_hash:
            dup_fields.append("content_hash (identical data payload)")

        # Log redundancy removal event
        duplicate_log = {
            "email":            email,
            "phone":            phone,
            "content_hash":     content_hash,
            "category":         record.category.strip(),
            "duplicate_fields": dup_fields,
            "size_bytes":       size_bytes,
            "bytes_saved":      size_bytes,
            "detected_at":      datetime.now(timezone.utc),
        }
        duplicate_logs_collection.insert_one(duplicate_log)

        return {
            "status":           "rejected",
            "message":          "Redundant data detected. Storage of duplicate content was prevented.",
            "duplicate_fields": dup_fields,
            "bytes_saved":      size_bytes
        }

    # Prepare document for insertion
    new_record = {
        "name":         record.name.strip(),
        "email":        email,
        "phone":        phone,
        "category":     record.category.strip(),
        "data":         record.data.strip(),
        "content_hash": content_hash,
        "size_bytes":   size_bytes,
        "metadata": {
            "encoding":     "utf-8",
            "content_type": "text/plain"
        },
        "status":       "verified",
        "created_at":   datetime.now(timezone.utc),
        "updated_at":   None,
    }

    try:
        result = records_collection.insert_one(new_record)
    except DuplicateKeyError:
        return {
            "status":  "rejected",
            "message": "Redundant data detected via database unique index constraint. Record not added."
        }

    return {
        "status":       "success",
        "message":      "Unique and verified record added successfully.",
        "record_id":    str(result.inserted_id),
        "content_hash": content_hash,
        "size_bytes":   size_bytes
    }


# ─────────────────────────────────────────────────────────
# READ ALL  –  GET /records/
# ─────────────────────────────────────────────────────────

@router.get("", summary="Get all records with search, filter, and pagination")
@router.get("/", summary="Get all records with search, filter, and pagination (slash)")
def get_records(
    search:   Optional[str] = Query(None, description="Search name, email, phone, or category"),
    category: Optional[str] = Query(None, description="Filter by exact category"),
    page:     int            = Query(1, ge=1, description="Page number"),
    limit:    int            = Query(20, ge=1, le=100, description="Records per page"),
):
    """
    Returns stored records from MongoDB with optional search query,
    category filtering, and pagination support.
    """
    query: dict = {}

    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": search_regex},
            {"email": search_regex},
            {"phone": search_regex},
            {"category": search_regex},
            {"content_hash": search_regex}
        ]

    if category:
        query["category"] = {"$regex": f"^{category}$", "$options": "i"}

    total = records_collection.count_documents(query)
    skip = (page - 1) * limit

    cursor = records_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    records = [_serialize(r) for r in cursor]

    return {
        "total":   total,
        "page":    page,
        "limit":   limit,
        "pages":   (total + limit - 1) // limit if total > 0 else 1,
        "records": records
    }


# ─────────────────────────────────────────────────────────
# AGGREGATION STATISTICS  –  GET /records/stats
# ─────────────────────────────────────────────────────────

@router.get("/stats", summary="Get MongoDB aggregation statistics")
def get_statistics():
    """
    Demonstrates MongoDB Aggregation Framework:
    Pipeline 1: Group by category to compute count, total bytes, and average size.
    Pipeline 2: Storage savings & deduplication efficiency calculations.
    """
    total_records = records_collection.count_documents({})
    verified_records = records_collection.count_documents({"status": "verified"})
    duplicates_detected = duplicate_logs_collection.count_documents({})

    # 1. Aggregation Pipeline: Category breakdown & storage metrics
    category_pipeline = [
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

    categories = []
    for doc in records_collection.aggregate(category_pipeline):
        latest = doc.get("latest_record")
        categories.append({
            "category":      doc["_id"] or "Uncategorized",
            "count":         doc["count"],
            "total_bytes":   int(doc.get("total_bytes") or 0),
            "avg_bytes":     round(float(doc.get("avg_bytes") or 0), 2),
            "latest_record": latest.isoformat() if isinstance(latest, datetime) else None
        })

    # 2. Aggregation Pipeline: Calculate actual storage consumed
    storage_pipeline = [
        {
            "$group": {
                "_id": None,
                "total_stored_bytes": {"$sum": "$size_bytes"}
            }
        }
    ]
    storage_res = list(records_collection.aggregate(storage_pipeline))
    total_stored_bytes = int(storage_res[0]["total_stored_bytes"]) if storage_res else 0

    # 3. Aggregation Pipeline: Calculate redundant bytes prevented from cloud storage
    savings_pipeline = [
        {
            "$group": {
                "_id": None,
                "total_saved_bytes": {"$sum": "$bytes_saved"}
            }
        }
    ]
    savings_res = list(duplicate_logs_collection.aggregate(savings_pipeline))
    total_saved_bytes = int(savings_res[0]["total_saved_bytes"]) if savings_res else 0

    # Deduplication efficiency percentage
    total_attempts = total_records + duplicates_detected
    dedup_ratio = round((duplicates_detected / total_attempts) * 100, 2) if total_attempts > 0 else 0.0

    return {
        "total_records":       total_records,
        "verified_records":    verified_records,
        "duplicates_detected": duplicates_detected,
        "storage_metrics": {
            "total_records":               total_records,
            "verified_records":            verified_records,
            "duplicates_detected":         duplicates_detected,
            "total_stored_bytes":          total_stored_bytes,
            "total_redundant_bytes_saved": total_saved_bytes,
            "deduplication_ratio_percent": dedup_ratio
        },
        "categories": categories
    }


# ─────────────────────────────────────────────────────────
# INDEX INSPECTOR  –  GET /records/indexes
# ─────────────────────────────────────────────────────────

@router.get("/indexes", summary="Inspect all MongoDB indexes for viva demonstration")
def get_indexes():
    """
    Returns information on all existing indexes across collections.
    Used for academic viva to demonstrate NoSQL indexing concepts.
    """
    records_indexes = []
    for idx in records_collection.list_indexes():
        records_indexes.append({
            "name":      idx.get("name"),
            "key":       dict(idx.get("key")),
            "unique":    idx.get("unique", False),
            "version":   idx.get("v")
        })

    duplicate_indexes = []
    for idx in duplicate_logs_collection.list_indexes():
        duplicate_indexes.append({
            "name":      idx.get("name"),
            "key":       dict(idx.get("key")),
            "unique":    idx.get("unique", False),
            "version":   idx.get("v")
        })

    return {
        "records_collection_indexes": records_indexes,
        "duplicate_logs_indexes":    duplicate_indexes
    }


# ─────────────────────────────────────────────────────────
# QUERY EXPLAIN  –  GET /records/explain
# ─────────────────────────────────────────────────────────

@router.get("/explain", summary="Demonstrate MongoDB query execution plan via explain()")
def explain_query(
    field: str = Query("email", description="Field to query: email, phone, content_hash, category, or name"),
    value: str = Query("alice@example.com", description="Value to match")
):
    """
    Runs MongoDB `.explain('executionStats')` on a query to demonstrate
    Index Scan (IXSCAN) vs Collection Scan (COLLSCAN) performance for academic evaluation.
    """
    query = {field: value}

    try:
        # Run explain on the query
        explanation = records_collection.find(query).explain()
        exec_stats = explanation.get("executionStats", {})
        
        # Navigate winning plan stages
        query_planner = explanation.get("queryPlanner", {})
        winning_plan = query_planner.get("winningPlan", {})
        
        # Check if IXSCAN or COLLSCAN
        def find_stage_and_index(plan):
            stage = plan.get("stage", "UNKNOWN")
            index_name = plan.get("indexName")
            if "IXSCAN" in stage and index_name:
                return stage, index_name
            if "inputStage" in plan:
                sub_stage, sub_index = find_stage_and_index(plan["inputStage"])
                if "IXSCAN" in sub_stage:
                    return sub_stage, sub_index
            if "inputStages" in plan:
                for sub_p in plan["inputStages"]:
                    sub_stage, sub_index = find_stage_and_index(sub_p)
                    if "IXSCAN" in sub_stage:
                        return sub_stage, sub_index
            return stage, index_name

        stage, index_name = find_stage_and_index(winning_plan)
        is_index = ("IXSCAN" in stage) or (bool(index_name))

        return {
            "query":                 query,
            "execution_stage":       stage,
            "index_used":            index_name or "None (Full Collection Scan)",
            "is_index_used":         is_index,
            "execution_time_millis": exec_stats.get("executionTimeMillis", 0),
            "total_keys_examined":   exec_stats.get("totalKeysExamined", 0),
            "total_docs_examined":   exec_stats.get("totalDocsExamined", 0),
            "n_returned":            exec_stats.get("nReturned", 0),
            "summary": (
                f"Query on '{field}' used Index '{index_name}' ({stage}) in {exec_stats.get('executionTimeMillis', 0)}ms."
                if is_index else
                f"Query on '{field}' performed a COLLSCAN (Full Collection Scan) across {exec_stats.get('totalDocsExamined', 0)} documents."
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explain execution failed: {str(e)}")


# ─────────────────────────────────────────────────────────
# READ ONE  –  GET /records/{record_id}
# ─────────────────────────────────────────────────────────

@router.get("/{record_id}", summary="Get a single record by ID (Read One)")
def get_record(record_id: str):
    """
    Retrieves a single record by its 24-character BSON ObjectId.
    """
    try:
        object_id = ObjectId(record_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format. Must be a 24-character hex string."
        )

    record = records_collection.find_one({"_id": object_id})
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )

    return _serialize(record)


# ─────────────────────────────────────────────────────────
# UPDATE  –  PUT /records/{record_id}
# ─────────────────────────────────────────────────────────

@router.put("/{record_id}", summary="Update an existing record (Update)")
def update_record(record_id: str, updates: RecordUpdate):
    """
    Updates an existing record in MongoDB.
    Validates field updates and checks for conflicts against other records.
    """
    try:
        object_id = ObjectId(record_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format."
        )

    existing = records_collection.find_one({"_id": object_id})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )

    update_data: dict = {}
    if updates.name is not None:
        update_data["name"] = updates.name.strip()
    if updates.email is not None:
        update_data["email"] = str(updates.email).lower().strip()
    if updates.phone is not None:
        update_data["phone"] = updates.phone.strip()
    if updates.category is not None:
        update_data["category"] = updates.category.strip()
    if updates.data is not None:
        update_data["data"] = updates.data.strip()
        update_data["content_hash"] = compute_content_hash(updates.data)
        update_data["size_bytes"] = compute_size_bytes(updates.data)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update."
        )

    update_data["updated_at"] = datetime.now(timezone.utc)

    # Conflict check against other records
    conflict_or = []
    if "email" in update_data:
        conflict_or.append({"email": update_data["email"]})
    if "phone" in update_data:
        conflict_or.append({"phone": update_data["phone"]})
    if "content_hash" in update_data:
        conflict_or.append({"content_hash": update_data["content_hash"]})

    if conflict_or:
        conflict = records_collection.find_one({
            "_id": {"$ne": object_id},
            "$or": conflict_or
        })
        if conflict:
            dup_fields = []
            if conflict.get("email") == update_data.get("email"):
                dup_fields.append("email")
            if conflict.get("phone") == update_data.get("phone"):
                dup_fields.append("phone")
            if conflict.get("content_hash") == update_data.get("content_hash"):
                dup_fields.append("content_hash")

            return {
                "status":           "rejected",
                "message":          "Update rejected — duplicate data detected in existing record.",
                "duplicate_fields": dup_fields
            }

    try:
        records_collection.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )
    except DuplicateKeyError:
        return {
            "status":  "rejected",
            "message": "Update rejected — duplicate key constraint violation."
        }

    return {
        "status":  "success",
        "message": "Record updated successfully."
    }


# ─────────────────────────────────────────────────────────
# DELETE  –  DELETE /records/{record_id}
# ─────────────────────────────────────────────────────────

@router.delete("/{record_id}", summary="Delete a record (Delete)")
def delete_record(record_id: str):
    """
    Deletes an existing record document from MongoDB.
    """
    try:
        object_id = ObjectId(record_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format."
        )

    result = records_collection.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )

    return {
        "status":  "success",
        "message": "Record deleted successfully."
    }


# ─────────────────────────────────────────────────────────
# DUPLICATE LOGS  –  GET /records/logs/duplicates
# ─────────────────────────────────────────────────────────

@router.get("/logs/duplicates", summary="Get redundancy removal detection audit logs")
def get_duplicate_logs(
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Retrieves history of blocked duplicate attempts from MongoDB duplicate_logs collection.
    """
    total = duplicate_logs_collection.count_documents({})
    skip = (page - 1) * limit
    cursor = duplicate_logs_collection.find().sort("detected_at", -1).skip(skip).limit(limit)

    logs = []
    for log in cursor:
        logs.append({
            "id":               str(log["_id"]),
            "email":            log.get("email", ""),
            "phone":            log.get("phone", ""),
            "content_hash":     log.get("content_hash", ""),
            "category":         log.get("category", ""),
            "duplicate_fields": log.get("duplicate_fields", []),
            "size_bytes":       log.get("size_bytes", 0),
            "bytes_saved":      log.get("bytes_saved", 0),
            "detected_at":      log["detected_at"].isoformat() if log.get("detected_at") else None,
        })

    return {
        "total": total,
        "page":  page,
        "limit": limit,
        "logs":  logs
    }
