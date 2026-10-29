from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
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


# -----------------------------
# ADD RECORD  (Create)
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
# GET ALL RECORDS  (Read All)
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
# GET SINGLE RECORD  (Read One)
# -----------------------------
@router.get("/{record_id}")
def get_record(record_id: str):

    try:
        object_id = ObjectId(record_id)

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid record ID"
        )

    record = records_collection.find_one({"_id": object_id})

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Record not found"
        )

    return {
        "id": str(record["_id"]),
        "name": record["name"],
        "email": record["email"],
        "phone": record["phone"],
        "category": record["category"],
        "data": record["data"],
        "status": record["status"],
        "created_at": record["created_at"].isoformat()
    }


# -----------------------------
# UPDATE RECORD  (Update)
# -----------------------------
@router.put("/{record_id}")
def update_record(record_id: str, updates: RecordUpdate):

    try:
        object_id = ObjectId(record_id)

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid record ID"
        )

    # Build update dict from only the provided fields
    update_data = {}

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

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided to update"
        )

    update_data["updated_at"] = datetime.now(timezone.utc)

    # Check for conflicts on email / phone (excluding current record)
    conflict_filters = []

    if "email" in update_data:
        conflict_filters.append({"email": update_data["email"]})

    if "phone" in update_data:
        conflict_filters.append({"phone": update_data["phone"]})

    if conflict_filters:
        conflict = records_collection.find_one(
            {
                "_id": {"$ne": object_id},
                "$or": conflict_filters
            }
        )

        if conflict:
            duplicate_fields = []

            if conflict.get("email") == update_data.get("email"):
                duplicate_fields.append("email")

            if conflict.get("phone") == update_data.get("phone"):
                duplicate_fields.append("phone")

            return {
                "status": "rejected",
                "message": "Update rejected — duplicate data detected.",
                "duplicate_fields": duplicate_fields
            }

    try:
        result = records_collection.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )

    except DuplicateKeyError:
        return {
            "status": "rejected",
            "message": "Update rejected — duplicate data detected."
        }

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Record not found"
        )

    return {
        "status": "success",
        "message": "Record updated successfully."
    }


# -----------------------------
# DELETE RECORD  (Delete)
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
