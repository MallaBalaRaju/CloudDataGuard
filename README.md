# CloudDataGuard

## Cloud-Based Data Redundancy Removal System

CloudDataGuard is a cloud-connected data validation and redundancy removal system developed as part of the **CodeAlpha Cloud Computing Internship**.

The system validates incoming records, checks them against existing records stored in **MongoDB Atlas**, prevents duplicate entries, and maintains a log of detected duplicate attempts.

---

## Project Objective

The main objective of CloudDataGuard is to reduce redundant data in a cloud database by:

- Validating incoming records
- Checking new records against existing data
- Detecting duplicate records
- Preventing redundant records from being stored
- Logging duplicate attempts
- Storing only unique and verified records
- Providing statistics about stored and duplicate records
- Providing a simple web dashboard for users

---

## Features

### 1. Data Validation

Incoming records are validated using **Pydantic** before they are processed.

The system validates:

- Name
- Email
- Phone number
- Category
- Data

Invalid input is rejected before database insertion.

### 2. Duplicate Detection

CloudDataGuard checks incoming records against existing records using:

- Email
- Phone number

If an existing record contains the same email or phone number, the new record is classified as redundant.

### 3. Duplicate Prevention

Duplicate records are not inserted into the main records collection.

The system returns a rejection response instead.

Example:

```json
{
    "status": "rejected",
    "message": "Redundant data detected. Record was not added.",
    "duplicate_fields": [
        "email",
        "phone"
    ]
}
```

### 4. Duplicate Logging

Detected duplicate attempts are stored separately in the MongoDB `duplicate_logs` collection.

This allows the system to maintain a record of redundancy detection events.

### 5. Verified Record Storage

Unique records are stored in MongoDB Atlas with:

```text
status: verified
```

### 6. Statistics

The application provides statistics including:

- Total records
- Verified records
- Duplicate attempts detected

### 7. Web Dashboard

The frontend provides:

- Database connection status
- Statistics dashboard
- Add & Verify Record form
- Stored records table
- Delete functionality
- Refresh functionality
- Duplicate detection messages

---

## System Architecture

```text
                    ┌─────────────────────┐
                    │     Web Browser     │
                    │   HTML / CSS / JS   │
                    └──────────┬──────────┘
                               │
                               │ HTTP Requests
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Data Validation   │
                    │ & Duplicate Check   │
                    └──────────┬──────────┘
                               │
                         Duplicate?
                         /        \
                       Yes         No
                       /            \
                      ▼              ▼
             ┌──────────────┐ ┌──────────────┐
             │ Duplicate    │ │ Verified     │
             │ Log          │ │ Record       │
             └──────┬───────┘ └──────┬───────┘
                    │                │
                    └───────┬────────┘
                            ▼
                    ┌─────────────────────┐
                    │    MongoDB Atlas    │
                    │    Cloud Database   │
                    └─────────────────────┘
```

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| FastAPI | REST API framework |
| Pydantic | Data validation |
| PyMongo | MongoDB database connectivity |
| MongoDB Atlas | Cloud database |
| HTML | Frontend structure |
| CSS | Frontend styling |
| JavaScript | Frontend functionality |
| Swagger UI | API testing |
| Git | Version control |
| GitHub | Source code repository |

---

## Project Structure

```text
CloudDataGuard/
│
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── database.py
│       ├── main.py
│       ├── schemas.py
│       │
│       └── routes/
│           ├── __init__.py
│           └── records.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

> **Note:** The `.env` file contains private database credentials and must not be uploaded to GitHub.

---

# API Documentation

The project provides REST API endpoints using FastAPI.

## 1. Home

```text
GET /
```

Checks whether the CloudDataGuard API is running.

Example response:

```json
{
    "message": "CloudDataGuard API is running",
    "status": "success"
}
```

---

## 2. Database Status

```text
GET /database-status
```

Checks the connection between FastAPI and MongoDB Atlas.

Example response:

```json
{
    "database": "MongoDB",
    "status": "connected"
}
```

---

## 3. Add Record

```text
POST /records/add
```

Validates the submitted record and checks it for redundancy.

A unique record is stored in MongoDB Atlas.

A duplicate record is rejected and logged.

Example request:

```json
{
    "name": "Aman Sharma",
    "email": "aman@example.com",
    "phone": "9876543210",
    "category": "Student",
    "data": "CloudDataGuard test record"
}
```

Example successful response:

```json
{
    "status": "success",
    "message": "Unique and verified record added successfully.",
    "record_id": "..."
}
```

Example duplicate response:

```json
{
    "status": "rejected",
    "message": "Redundant data detected. Record was not added.",
    "duplicate_fields": [
        "email",
        "phone"
    ]
}
```

---

## 4. Get Records

```text
GET /records/
```

Returns the verified records currently stored in MongoDB Atlas.

Example response:

```json
{
    "total": 1,
    "records": [
        {
            "id": "...",
            "name": "Aman Sharma",
            "email": "aman@example.com",
            "phone": "9876543210",
            "category": "Student",
            "data": "CloudDataGuard test record",
            "status": "verified",
            "created_at": "..."
        }
    ]
}
```

---

## 5. Statistics

```text
GET /records/stats
```

Returns database statistics.

Example:

```json
{
    "total_records": 1,
    "verified_records": 1,
    "duplicates_detected": 1
}
```

---

## 6. Delete Record

```text
DELETE /records/{record_id}
```

Deletes a selected record using its MongoDB record ID.

Example response:

```json
{
    "status": "success",
    "message": "Record deleted successfully."
}
```

---

# Data Redundancy Detection Workflow

## Unique Record

When a new record is submitted:

```text
Input Record
     ↓
Pydantic Validation
     ↓
Database Check
     ↓
No Duplicate Found
     ↓
Record Verified
     ↓
Stored in MongoDB Atlas
```

## Duplicate Record

When an existing record is submitted again:

```text
Input Record
     ↓
Pydantic Validation
     ↓
Database Check
     ↓
Duplicate Found
     ↓
Record Rejected
     ↓
Duplicate Attempt Logged
```

---

# Database Design

CloudDataGuard uses MongoDB Atlas as its cloud database.

## Database

```text
cloud_data_guard
```

## Collection 1: records

Stores unique and verified records.

Important fields include:

```text
_id
name
email
phone
category
data
status
created_at
```

## Collection 2: duplicate_logs

Stores detected duplicate attempts.

Important fields include:

```text
_id
email
phone
duplicate_fields
detected_at
```

## Database Indexing

Unique indexes are created for:

```text
email
phone
```

These indexes provide an additional database-level mechanism for preventing duplicate records.

---

# Installation

## Prerequisites

Make sure the following are installed:

- Python 3.x
- MongoDB Atlas account
- Git
- Web browser
- Visual Studio Code (recommended)

---

## 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd CloudDataGuard
```

---

## 2. Create a Virtual Environment

On Windows:

```powershell
python -m venv venv
```

---

## 3. Activate the Virtual Environment

```powershell
venv\Scripts\activate
```

---

## 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

---

## 5. Configure MongoDB Atlas

Create a MongoDB Atlas cluster and database user.

Create a `.env` file in the project root:

```env
MONGODB_URI=your_mongodb_atlas_connection_string
DATABASE_NAME=cloud_data_guard
```

Replace the placeholder with your own MongoDB Atlas connection string.

**Never upload the actual `.env` file to GitHub.**

---

# Running the Backend

From the project root:

```powershell
python -m uvicorn backend.app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Running the Frontend

The frontend files are located in:

```text
frontend/
```

The frontend can be served using a local web server such as **VS Code Live Server**.

Example:

```text
http://127.0.0.1:5500/CloudDataGuard/frontend/index.html
```

The frontend communicates with the FastAPI backend running on:

```text
http://127.0.0.1:8000
```

---

# Testing

CloudDataGuard was tested using the following workflow.

## Test 1 — MongoDB Connection

The database status endpoint successfully returned:

```json
{
    "database": "MongoDB",
    "status": "connected"
}
```

This confirms successful communication between the FastAPI application and MongoDB Atlas.

---

## Test 2 — Unique Record

A new record was submitted through the API.

The system validated the input and successfully stored the unique record.

Result:

```text
Status: success
```

---

## Test 3 — Duplicate Record

The same record was submitted again.

The system detected matching email and phone values.

Result:

```text
Status: rejected
```

The duplicate attempt was also logged.

---

## Test 4 — Statistics

The statistics endpoint successfully reported:

```text
Total records
Verified records
Duplicate attempts
```

---

## Test 5 — Record Retrieval

The stored records were successfully retrieved through:

```text
GET /records/
```

The records were also displayed in the frontend dashboard.

---

## Test 6 — Record Deletion

A stored record was successfully deleted using:

```text
DELETE /records/{record_id}
```

---

## Test 7 — Frontend Integration

The web dashboard successfully communicated with the FastAPI backend.

The frontend displayed:

- MongoDB connection status
- Total records
- Verified records
- Duplicate count
- Stored records
- Add record functionality
- Duplicate detection messages
- Delete functionality

---

# Security Considerations

The application follows basic security practices:

- MongoDB credentials are stored in environment variables.
- `.env` is excluded using `.gitignore`.
- User input is validated before database insertion.
- Email and phone fields use unique MongoDB indexes.
- Frontend values are escaped before being displayed in the records table.
- Database credentials are not hard-coded in the application source code.

---

# Error Handling

The application handles several common errors, including:

- Invalid input data
- Invalid email addresses
- Invalid phone numbers
- Duplicate records
- Invalid MongoDB record IDs
- Missing records
- Database connection failures
- API connection failures

---

# Future Enhancements

Possible future improvements include:

- User authentication
- Role-based access control
- Advanced duplicate detection
- Fuzzy matching for similar records
- CSV/Excel bulk upload
- Data quality scoring
- Advanced analytics
- Audit reports
- Automated data-cleaning workflows
- Cloud deployment

---

# Internship Task

This project was developed for the:

**CodeAlpha Cloud Computing Internship**

## Completed Task

**Task 1 — Data Redundancy Removal System**

The implementation demonstrates:

- Redundant data identification
- Data validation
- Duplicate detection
- Duplicate prevention
- Duplicate logging
- Unique record storage
- Cloud database integration
- Data retrieval
- Record deletion
- Statistics
- Web-based dashboard

---

# Project Demonstration

The project demonstration covers:

1. Starting the FastAPI backend
2. Connecting to MongoDB Atlas
3. Opening Swagger API documentation
4. Checking database connectivity
5. Adding a unique record
6. Submitting the same record again
7. Demonstrating duplicate detection
8. Viewing statistics
9. Viewing stored records
10. Deleting a record
11. Using the frontend dashboard

---

# Screenshots

Add project screenshots here after taking them.

Recommended screenshots:

```text
1. MongoDB Atlas Cluster
2. FastAPI Swagger Documentation
3. Database Connected Response
4. Unique Record Successfully Added
5. Duplicate Record Rejected
6. Statistics Response
7. Stored Records
8. CloudDataGuard Frontend Dashboard
9. Frontend Duplicate Detection
10. GitHub Repository
```

Example:

```markdown
![CloudDataGuard Dashboard](screenshots/dashboard.png)
```

---

# Author

**Malla Balaraju**

CloudDataGuard  
CodeAlpha Cloud Computing Internship

---

# License

This project was developed for educational and internship purposes.