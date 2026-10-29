import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.database import client
from backend.app.routes.records import router as records_router


app = FastAPI(
    title="CloudDataGuard",
    description="Cloud-Based Data Redundancy Removal System",
    version="1.0.0"
)


# ========================================
# CORS Configuration
# ========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# Home
# ========================================

@app.get("/")
def home():
    return {
        "message": "CloudDataGuard API is running",
        "status": "success"
    }


# ========================================
# Database Status
# ========================================

@app.get("/database-status")
def database_status():

    try:
        client.admin.command("ping")

        return {
            "database": "MongoDB",
            "status": "connected"
        }

    except Exception as e:

        return {
            "database": "MongoDB",
            "status": "connection failed",
            "error": str(e)
        }


# ========================================
# Records Router
# ========================================

app.include_router(records_router)


# ========================================
# Frontend Static Files
# ========================================

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")



# ========================================
# Frontend Static Files
# ========================================

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")