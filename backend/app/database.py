import os
import logging

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "cloud_data_guard")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is not configured in .env")

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
except Exception as e:
    logger.warning("Failed to initialize MongoClient with %s: %s. Using localhost.", MONGODB_URI, e)
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=3000)

db = client[DATABASE_NAME]

# Main collection for verified unique records
records_collection = db["records"]

# Collection for storing detected duplicate attempts
duplicate_logs_collection = db["duplicate_logs"]

# Unique indexes to prevent duplicate records
try:
    records_collection.create_index("email", unique=True)
    records_collection.create_index("phone", unique=True)
except Exception as e:
    logger.warning("Could not create unique indexes on MongoDB collections: %s", e)
