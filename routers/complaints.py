# ============================================================
# Complaints Router
# File: backend/routers/complaints.py
# ============================================================

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import Optional, List
import os, uuid, aiofiles, logging

from database import get_db
from models.schemas import ComplaintCreate, ComplaintUpdate, ComplaintStatus, Priority, success_response
from routers.users import get_current_user, require_admin
from services.ai_service import AIAnalysisService
from services.notification_service import NotificationService
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Department mapping
DEPT_MAP = {
    "Pothole": "PWD", "Garbage": "MCD", "Water Leakage": "DJB",
    "Street Light": "BSES", "Sewage": "DJB", "Encroachment": "MCorp",
    "Noise Pollution": "Pollution Dept", "Air Pollution": "DPCC",
    "Road Damage": "PWD", "Park Maintenance": "Horticulture", "Other": "General"
}

def generate_complaint_id() -> str:
    year = datetime.utcnow().year
    unique = str(uuid.uuid4().int)[:5]
    return f"CMP-{year}-{unique}"

# ============================================================
# CREATE COMPLAINT
# ============================================================
@router.post("/", status_code=201)
async def create_complaint(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    address: str = Form(...),
    city: str = Form("Delhi"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    contact_number: Optional[str] = Form(None),
    is_anonymous: bool = Form(False),
    files: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    # Upload media files
    media_urls = []
    for file in files:
        if file.filename:
            ext = file.filename.split(".")[-1].lower()
            if ext not in settings.ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")
            
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(settings.UPLOAD_DIR, filename)
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            
            async with aiofiles.open(filepath, "wb") as f:
                content = await file.read()
                if len(content) > settings.MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail="File too large (max 10MB)")
                await f.write(content)
            
            media_urls.append(f"/uploads/{filename}")

    # Run AI analysis
    ai_analysis = None
    priority = Priority.MEDIUM.value
    
    if settings.ENABLE_AI_ANALYSIS:
        try:
            ai_service = AIAnalysisService()
            ai_result = await ai_service.analyze_complaint(title, description, category)
            ai_analysis = ai_result
            priority = ai_result.get("priority", Priority.MEDIUM.value)
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")

    # Check for duplicates
    existing = await db.complaints.find_one({
        "title": {"$regex": title[:20], "$options": "i"},
        "location.city": city,
        "status": {"$nin": ["Resolved", "Rejected"]},
        "created_at": {"$gte": datetime(datetime.utcnow().year, datetime.utcnow().month, 1)}
    })
    
    is_duplicate = existing is not None

    # Build complaint document
    complaint_doc = {
        "complaint_id": generate_complaint_id(),
        "title": title,
        "description": description,
        "category": category,
        "status": ComplaintStatus.PENDING.value,
        "priority": priority,
        "location": {
            "address": address,
            "city": city,
            "coordinates": [longitude, latitude] if longitude and latitude else None
        },
        "user_id": str(current_user["_id"]),
        "user_name": None if is_anonymous else current_user["name"],
        "department": DEPT_MAP.get(category, "General"),
        "media_urls": media_urls,
        "votes": 0,
        "voters": [],
        "is_duplicate": is_duplicate,
        "duplicate_of": str(existing["_id"]) if existing else None,
        "contact_number": contact_number,
        "is_anonymous": is_anonymous,
        "ai_analysis": ai_analysis,
        "resolution_notes": None,
        "assigned_to": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "resolved_at": None
    }

    result = await db.complaints.insert_one(complaint_doc)
    complaint_doc["_id"] = result.inserted_id

    # Update user complaint count
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$inc": {"complaints_filed": 1}}
    )

    # Send notification (async, non-blocking)
    try:
        notif_service = NotificationService()
        await notif_service.send_complaint_received(
            current_user.get("email"),
            complaint_doc["complaint_id"],
            complaint_doc["department"]
        )
    except Exception as e:
        logger.warning(f"Notification failed: {e}")

    return success_response(
        data=_format_complaint(complaint_doc),
        message=f"Complaint filed successfully! ID: {complaint_doc['complaint_id']}"
    )

# ============================================================
# GET COMPLAINTS (with filters)
# ============================================================
@router.get("/")
async def get_complaints(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all complaints with optional filters"""
    query = {}
    
    if status: query["status"] = status
    if category: query["category"] = category
    if priority: query["priority"] = priority
    if city: query["location.city"] = {"$regex": city, "$options": "i"}
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"complaint_id": {"$regex": search, "$options": "i"}},
            {"location.address": {"$regex": search, "$options": "i"}}
        ]

    total = await db.complaints.count_documents(query)
    complaints = await db.complaints.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    return success_response(data={
        "complaints": [_format_complaint(c) for c in complaints],
        "total": total,
        "skip": skip,
        "limit": limit
    })

# ============================================================
# GET SINGLE COMPLAINT
# ============================================================
@router.get("/{complaint_id}")
async def get_complaint(complaint_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get a single complaint by ID or complaint_id"""
    # Try complaint_id format first
    complaint = await db.complaints.find_one({"complaint_id": complaint_id})
    
    # Try MongoDB ObjectId
    if not complaint and len(complaint_id) == 24:
        try:
            complaint = await db.complaints.find_one({"_id": ObjectId(complaint_id)})
        except Exception:
            pass
    
    if not complaint:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")
    
    return success_response(data=_format_complaint(complaint))

# ============================================================
# UPDATE COMPLAINT STATUS (Admin/Officer)
# ============================================================
@router.put("/{complaint_id}/status")
async def update_status(
    complaint_id: str,
    update_data: ComplaintUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Update complaint status (admin or officer)"""
    if current_user["role"] not in ["admin", "officer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    complaint = await db.complaints.find_one({"complaint_id": complaint_id})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    update_doc = {"updated_at": datetime.utcnow()}
    
    if update_data.status:
        update_doc["status"] = update_data.status.value
        if update_data.status == ComplaintStatus.RESOLVED:
            update_doc["resolved_at"] = datetime.utcnow()
    
    if update_data.priority: update_doc["priority"] = update_data.priority.value
    if update_data.resolution_notes: update_doc["resolution_notes"] = update_data.resolution_notes
    if update_data.assigned_to: update_doc["assigned_to"] = update_data.assigned_to
    
    await db.complaints.update_one({"complaint_id": complaint_id}, {"$set": update_doc})
    
    # Notify user about status change
    try:
        user = await db.users.find_one({"_id": ObjectId(complaint["user_id"])})
        if user and user.get("email"):
            notif_service = NotificationService()
            await notif_service.send_status_update(user["email"], complaint_id, update_data.status.value if update_data.status else complaint["status"])
    except Exception as e:
        logger.warning(f"Status notification failed: {e}")
    
    updated = await db.complaints.find_one({"complaint_id": complaint_id})
    return success_response(data=_format_complaint(updated), message="Status updated successfully")

# ============================================================
# VOTE ON COMPLAINT
# ============================================================
@router.post("/{complaint_id}/vote")
async def vote_complaint(
    complaint_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Upvote a complaint (once per user)"""
    user_id = str(current_user["_id"])
    complaint = await db.complaints.find_one({"complaint_id": complaint_id})
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    if user_id in complaint.get("voters", []):
        raise HTTPException(status_code=400, detail="Already voted on this complaint")
    
    await db.complaints.update_one(
        {"complaint_id": complaint_id},
        {"$inc": {"votes": 1}, "$push": {"voters": user_id}}
    )
    
    return success_response(message="Vote recorded", data={"votes": complaint["votes"] + 1})

# ============================================================
# MY COMPLAINTS
# ============================================================
@router.get("/user/my-complaints")
async def get_my_complaints(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get current user's complaints"""
    complaints = await db.complaints.find(
        {"user_id": str(current_user["_id"])}
    ).sort("created_at", -1).to_list(100)
    
    return success_response(data=[_format_complaint(c) for c in complaints])

def _format_complaint(c: dict) -> dict:
    """Format complaint for API response"""
    return {
        "id": str(c["_id"]),
        "complaint_id": c.get("complaint_id", ""),
        "title": c.get("title", ""),
        "description": c.get("description", ""),
        "category": c.get("category", ""),
        "status": c.get("status", "Pending"),
        "priority": c.get("priority", "MEDIUM"),
        "location": c.get("location", {}),
        "user_id": c.get("user_id", ""),
        "user_name": c.get("user_name"),
        "department": c.get("department", "General"),
        "media_urls": c.get("media_urls", []),
        "votes": c.get("votes", 0),
        "ai_analysis": c.get("ai_analysis"),
        "is_duplicate": c.get("is_duplicate", False),
        "resolution_notes": c.get("resolution_notes"),
        "assigned_to": c.get("assigned_to"),
        "created_at": c.get("created_at", datetime.utcnow()).isoformat(),
        "updated_at": c.get("updated_at", datetime.utcnow()).isoformat(),
        "resolved_at": c["resolved_at"].isoformat() if c.get("resolved_at") else None
    }
