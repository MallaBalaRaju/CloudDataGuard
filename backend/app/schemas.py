from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RecordCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    category: str = Field(..., min_length=2, max_length=50)
    data: str = Field(..., min_length=1)


class RecordUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    category: Optional[str] = Field(None, min_length=2, max_length=50)
    data: Optional[str] = Field(None, min_length=1)


class RecordResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    category: str
    data: str
    status: str
