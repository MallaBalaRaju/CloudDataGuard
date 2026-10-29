from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class RecordCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name of person or document owner")
    email: EmailStr = Field(..., description="Unique email address")
    phone: str = Field(..., min_length=10, max_length=15, description="Unique phone number")
    category: str = Field(..., min_length=2, max_length=50, description="Category classification, e.g., Student, Finance")
    data: str = Field(..., min_length=1, description="Raw data or file content text to be stored")


class RecordUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    category: Optional[str] = Field(None, min_length=2, max_length=50)
    data: Optional[str] = Field(None, min_length=1)


class RecordMetadata(BaseModel):
    encoding: str = "utf-8"
    content_type: str = "text/plain"


class RecordResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    category: str
    data: str
    content_hash: Optional[str] = None
    size_bytes: Optional[int] = None
    status: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CategoryStat(BaseModel):
    category: str
    count: int
    total_bytes: int
    avg_bytes: float
    latest_record: Optional[str] = None


class StorageMetrics(BaseModel):
    total_records: int
    verified_records: int
    duplicates_detected: int
    total_stored_bytes: int
    total_redundant_bytes_saved: int
    deduplication_ratio_percent: float


class StatsResponse(BaseModel):
    total_records: int
    verified_records: int
    duplicates_detected: int
    storage_metrics: StorageMetrics
    categories: List[CategoryStat]


class DuplicateLogResponse(BaseModel):
    id: str
    email: str
    phone: str
    content_hash: Optional[str] = None
    size_bytes: Optional[int] = None
    bytes_saved: Optional[int] = None
    duplicate_fields: List[str]
    detected_at: Optional[str] = None
