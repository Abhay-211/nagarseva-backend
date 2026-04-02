# ============================================================
# NagarSeva AI - FastAPI Backend
# File: backend/main.py
# ============================================================

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
from datetime import datetime

from routers import complaints, users, admin, departments
from database import connect_db, disconnect_db
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("🚀 Starting NagarSeva AI Backend...")
    await connect_db()
    logger.info("✅ Database connected")
    yield
    await disconnect_db()
    logger.info("🛑 Application shutdown")

app = FastAPI(
    title="NagarSeva AI - Civic Complaint Platform",
    description="AI-Powered Unified Civic Complaint Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ============================================================
# CORS MIDDLEWARE
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://nagarseva.vercel.app", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ROUTERS
# ============================================================
app.include_router(users.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(complaints.router, prefix="/api/v1/complaints", tags=["Complaints"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(departments.router, prefix="/api/v1/departments", tags=["Departments"])

# ============================================================
# ROOT ENDPOINTS
# ============================================================
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "NagarSeva AI Backend Running",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "NagarSeva AI", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
