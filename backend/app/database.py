import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "cloud_data_guard")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is not configured in .env")

client = MongoClient(MONGODB_URI)

db = client[DATABASE_NAME]

# Main collection for verified unique records
records_collection = db["records"]

# Collection for storing detected duplicate attempts
duplicate_logs_collection = db["duplicate_logs"]

# Unique indexes to prevent duplicate records
records_collection.create_index("email", unique=True)
records_collection.create_index("phone", unique=True)