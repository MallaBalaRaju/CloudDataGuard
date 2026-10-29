import os
import logging
import hashlib
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "cloud_data_guard")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is not configured in .env")

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
    # Quick connectivity check
    client.admin.command("ping")
except Exception as e:
    logger.warning("Failed to connect with primary MONGODB_URI (%s): %s. Falling back to localhost.", MONGODB_URI, e)
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=3000)

db = client[DATABASE_NAME]

# Main collection for verified unique records
records_collection = db["records"]

# Collection for logging detected duplicate attempts
duplicate_logs_collection = db["duplicate_logs"]


def setup_indexes():
    """
    Creates necessary MongoDB indexes for query performance and data integrity:
    1. Unique index on 'email' (prevents duplicate identity)
    2. Unique index on 'phone' (prevents duplicate phone contact)
    3. Unique index on 'content_hash' (prevents duplicate payload/file redundancy)
    4. Index on 'category' (accelerates category filtering and aggregation)
    5. Index on 'created_at' (accelerates reverse-chronological retrieval)
    """
    try:
        records_collection.create_index("email", unique=True)
        records_collection.create_index("phone", unique=True)
        records_collection.create_index("content_hash", unique=True)
        records_collection.create_index("category")
        records_collection.create_index("created_at")
        
        duplicate_logs_collection.create_index("detected_at")
        duplicate_logs_collection.create_index("content_hash")
    except Exception as e:
        logger.warning("Index creation notice: %s", e)


def setup_schema_validation():
    """
    Applies MongoDB JSON Schema validation ($jsonSchema) to the records collection
    demonstrating engine-level NoSQL validation for academic evaluation.
    """
    schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "email", "phone", "category", "data", "content_hash", "size_bytes", "status"],
            "properties": {
                "name": {
                    "bsonType": "string",
                    "description": "must be a string and is required"
                },
                "email": {
                    "bsonType": "string",
                    "pattern": "^.+@.+$",
                    "description": "must be a valid email string and is required"
                },
                "phone": {
                    "bsonType": "string",
                    "description": "must be a phone number string and is required"
                },
                "category": {
                    "bsonType": "string",
                    "description": "must be a category string and is required"
                },
                "data": {
                    "bsonType": "string",
                    "description": "must be the record content string and is required"
                },
                "content_hash": {
                    "bsonType": "string",
                    "description": "SHA-256 hash string for redundancy checking and is required"
                },
                "size_bytes": {
                    "bsonType": ["int", "long"],
                    "description": "integer size in bytes and is required"
                },
                "status": {
                    "enum": ["verified", "pending", "rejected"],
                    "description": "can only be one of the enum values"
                }
            }
        }
    }
    try:
        db.command({
            "collMod": "records",
            "validator": schema,
            "validationLevel": "moderate"
        })
    except Exception as e:
        logger.debug("Schema validator setup note: %s", e)


def migrate_legacy_records():
    """
    Ensures any legacy records without content_hash or size_bytes are backfilled
    so indexes and validations remain consistent.
    """
    try:
        cursor = records_collection.find({"$or": [
            {"content_hash": {"$exists": False}},
            {"size_bytes": {"$exists": False}}
        ]})
        for r in cursor:
            data_text = r.get("data", "")
            chash = hashlib.sha256(data_text.strip().encode("utf-8")).hexdigest()
            csize = len(data_text.encode("utf-8"))
            records_collection.update_one(
                {"_id": r["_id"]},
                {"$set": {
                    "content_hash": chash,
                    "size_bytes": csize,
                    "metadata": {"encoding": "utf-8", "content_type": "text/plain"}
                }}
            )
    except Exception as e:
        logger.warning("Legacy migration warning: %s", e)


# Run startup initializations
migrate_legacy_records()
setup_indexes()
setup_schema_validation()
