import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import records_collection, duplicate_logs_collection

client = TestClient(app)


def test_1_database_connection():
    """Verify MongoDB connectivity and database ping."""
    response = client.get("/database-status")
    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "MongoDB"
    assert data["status"] == "connected"


def test_2_create_record_with_sha256_hash():
    """Verify CREATE operation, SHA-256 content hashing, and size calculation."""
    payload = {
        "name": "Prof. Alan Turing",
        "email": "alan.turing@enigma-lab.edu",
        "phone": "+441234567890",
        "category": "Computer Science",
        "data": "A machine can be said to think if it can fool a human into thinking so."
    }
    response = client.post("/records", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "record_id" in data
    assert "content_hash" in data
    assert len(data["content_hash"]) == 64  # Valid SHA-256 hex string
    assert data["size_bytes"] == len(payload["data"].encode("utf-8"))


def test_3_read_all_records():
    """Verify READ ALL operation with pagination and serialization."""
    response = client.get("/records?page=1&limit=20")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "records" in data
    assert data["total"] >= 1
    record = next(r for r in data["records"] if r["email"] == "alan.turing@enigma-lab.edu")
    assert record["name"] == "Prof. Alan Turing"
    assert record["status"] == "verified"
    assert record["content_hash"] is not None


def test_4_read_single_record():
    """Verify READ ONE operation using BSON ObjectId."""
    # Find record created in step 2
    doc = records_collection.find_one({"email": "alan.turing@enigma-lab.edu"})
    assert doc is not None
    record_id = str(doc["_id"])

    response = client.get(f"/records/{record_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == record_id
    assert data["email"] == "alan.turing@enigma-lab.edu"
    assert data["category"] == "Computer Science"


def test_5_update_record():
    """Verify UPDATE operation, recalculating hash and setting updated_at."""
    doc = records_collection.find_one({"email": "alan.turing@enigma-lab.edu"})
    record_id = str(doc["_id"])

    update_payload = {
        "name": "Sir Alan Turing, OBE",
        "data": "Machines take me by surprise with great frequency."
    }
    response = client.put(f"/records/{record_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify updated values in MongoDB
    updated_doc = records_collection.find_one({"_id": doc["_id"]})
    assert updated_doc["name"] == "Sir Alan Turing, OBE"
    assert updated_doc["updated_at"] is not None


def test_6_duplicate_detection_by_email():
    """Verify duplicate rejection on identity fields and audit logging."""
    duplicate_payload = {
        "name": "Imposter Turing",
        "email": "alan.turing@enigma-lab.edu",  # Same email!
        "phone": "+449999999999",
        "category": "Security",
        "data": "Different text payload."
    }
    response = client.post("/records", json=duplicate_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert "email" in data["duplicate_fields"]

    # Verify duplicate was logged into duplicate_logs collection
    log_doc = duplicate_logs_collection.find_one({"email": "alan.turing@enigma-lab.edu"})
    assert log_doc is not None


def test_7_duplicate_detection_by_content_hash():
    """Verify duplicate rejection when identical content hash is detected."""
    # Existing text of Turing's updated record:
    existing_text = "Machines take me by surprise with great frequency."
    redundant_payload = {
        "name": "Different Student",
        "email": "student.diff@university.edu",
        "phone": "+19876543210",
        "category": "Artificial Intelligence",
        "data": existing_text  # Identical content!
    }
    response = client.post("/records", json=redundant_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert any("content_hash" in field for field in data["duplicate_fields"])
    assert data["bytes_saved"] > 0


def test_8_validation_errors():
    """Verify Pydantic request validation rejects malformed input with HTTP 422."""
    bad_payload = {
        "name": "A",  # Min length 2
        "email": "not-a-valid-email",
        "phone": "123",  # Min length 10
        "category": "",
        "data": ""
    }
    response = client.post("/records", json=bad_payload)
    assert response.status_code == 422


def test_9_invalid_and_nonexistent_ids():
    """Verify BSON ObjectId validation (400) and missing record handling (404)."""
    # Invalid ObjectId hex string
    bad_id_resp = client.get("/records/invalid-id-xyz")
    assert bad_id_resp.status_code == 400

    # Nonexistent valid ObjectId hex string
    missing_resp = client.get("/records/0123456789abcdef01234567")
    assert missing_resp.status_code == 404


def test_10_aggregation_framework():
    """Verify MongoDB Aggregation pipelines for category stats and storage metrics."""
    response = client.get("/records/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_records" in data
    assert "storage_metrics" in data
    metrics = data["storage_metrics"]
    assert metrics["total_stored_bytes"] > 0
    assert metrics["total_redundant_bytes_saved"] > 0
    assert "deduplication_ratio_percent" in metrics
    assert len(data["categories"]) >= 1


def test_11_indexes_inspection():
    """Verify NoSQL Indexing demonstration endpoint."""
    response = client.get("/records/indexes")
    assert response.status_code == 200
    data = response.json()
    index_names = [idx["name"] for idx in data["records_collection_indexes"]]
    assert "email_1" in index_names
    assert "phone_1" in index_names
    assert "content_hash_1" in index_names
    assert "category_1" in index_names


def test_12_query_explain_plan():
    """Verify MongoDB explain() plan demonstrating IXSCAN vs COLLSCAN for viva."""
    # Query indexed field (email) -> must be IXSCAN
    resp_indexed = client.get("/records/explain?field=email&value=alan.turing@enigma-lab.edu")
    assert resp_indexed.status_code == 200
    indexed_data = resp_indexed.json()
    assert indexed_data["is_index_used"] is True
    assert "IXSCAN" in indexed_data["execution_stage"]

    # Query non-indexed field (name) -> must be COLLSCAN
    resp_unindexed = client.get("/records/explain?field=name&value=Sir Alan Turing, OBE")
    assert resp_unindexed.status_code == 200
    unindexed_data = resp_unindexed.json()
    assert unindexed_data["is_index_used"] is False
    assert unindexed_data["execution_stage"] == "COLLSCAN"


def test_13_delete_record():
    """Verify DELETE operation removing document from MongoDB."""
    doc = records_collection.find_one({"email": "alan.turing@enigma-lab.edu"})
    record_id = str(doc["_id"])

    response = client.delete(f"/records/{record_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify document is no longer in MongoDB
    check_deleted = client.get(f"/records/{record_id}")
    assert check_deleted.status_code == 404

    # Clean up duplicate logs created by tests for Turing
    duplicate_logs_collection.delete_many({"email": "alan.turing@enigma-lab.edu"})
