from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from backend.app.database import (
    records_collection,
    duplicate_logs_collection
)
from backend.app.schemas import RecordCreate

router = APIRouter(
    prefix="/records",
    tags=["Records"]
)


# -----------------------------
# ADD RECORD
# -----------------------------
@router.post("/add")
def add_record(record: RecordCreate):
    email = str(record.email).lower().strip()
    phone = record.phone.strip()

    existing_record = records_collection.find_one(
        {
            "$or": [
                {"email": email},
                {"phone": phone}
            ]
        }
    )

    if existing_record:
        duplicate_fields = []

        if existing_record.get("email") == email:
            duplicate_fields.append("email")

        if existing_record.get("phone") == phone:
            duplicate_fields.append("phone")

        duplicate_log = {
            "email": email,
            "phone": phone,
            "duplicate_fields": duplicate_fields,
            "detected_at": datetime.now(timezone.utc)
        }

        duplicate_logs_collection.insert_one(duplicate_log)

        return {
            "status": "rejected",
            "message": "Redundant data detected. Record was not added.",
            "duplicate_fields": duplicate_fields
        }

    new_record = {
        "name": record.name.strip(),
        "email": email,
        "phone": phone,
        "category": record.category.strip(),
        "data": record.data.strip(),
        "status": "verified",
        "created_at": datetime.now(timezone.utc)
    }

    try:
        result = records_collection.insert_one(new_record)

    except DuplicateKeyError:
        return {
            "status": "rejected",
            "message": "Redundant data detected. Record was not added."
        }

    return {
        "status": "success",
        "message": "Unique and verified record added successfully.",
        "record_id": str(result.inserted_id)
    }


# -----------------------------
# GET ALL RECORDS
# -----------------------------
@router.get("/")
def get_records():
    records = []

    for record in records_collection.find().sort("created_at", -1):
        records.append({
            "id": str(record["_id"]),
            "name": record["name"],
            "email": record["email"],
            "phone": record["phone"],
            "category": record["category"],
            "data": record["data"],
            "status": record["status"],
            "created_at": record["created_at"].isoformat()
        })

    return {
        "total": len(records),
        "records": records
    }


# -----------------------------
# STATISTICS
# -----------------------------
@router.get("/stats")
def get_statistics():
    total_records = records_collection.count_documents({})
    verified_records = records_collection.count_documents(
        {"status": "verified"}
    )
    duplicate_records = duplicate_logs_collection.count_documents({})

    return {
        "total_records": total_records,
        "verified_records": verified_records,
        "duplicates_detected": duplicate_records
    }


# -----------------------------
# DELETE RECORD
# -----------------------------
@router.delete("/{record_id}")
def delete_record(record_id: str):

    try:
        object_id = ObjectId(record_id)

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid record ID"
        )

    result = records_collection.delete_one(
        {"_id": object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Record not found"
        )

    return {
        "status": "success",
        "message": "Record deleted successfully."
    }