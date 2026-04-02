# ============================================================
# Database Models (Pydantic Schemas)
# File: backend/models/schemas.py
# ============================================================

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re

# ============================================================
# ENUMS
# ============================================================
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    DEPARTMENT_OFFICER = "officer"

class ComplaintStatus(str, Enum):
    PENDING = "Pending"
    UNDER_REVIEW = "Under Review"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    REJECTED = "Rejected"

class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ComplaintCategory(str, Enum):
    POTHOLE = "Pothole"
    GARBAGE = "Garbage"
    WATER_LEAKAGE = "Water Leakage"
    STREET_LIGHT = "Street Light"
    SEWAGE = "Sewage"
    ENCROACHMENT = "Encroachment"
    NOISE_POLLUTION = "Noise Pollution"
    AIR_POLLUTION = "Air Pollution"
    ROAD_DAMAGE = "Road Damage"
    PARK_MAINTENANCE = "Park Maintenance"
    OTHER = "Other"

# ============================================================
# USER MODELS
# ============================================================
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^[6-9]\d{9}$")
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=50)
    role: UserRole = UserRole.USER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    role: UserRole
    is_active: bool = True
    complaints_filed: int = 0
    created_at: datetime
    avatar_url: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None

# ============================================================
# AUTH MODELS
# ============================================================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    user_id: str
    email: str
    role: str

# ============================================================
# COMPLAINT MODELS
# ============================================================
class LocationData(BaseModel):
    address: str
    city: str = "Delhi"
    state: str = "Delhi"
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    landmark: Optional[str] = None

class AIAnalysis(BaseModel):
    priority: Priority
    priority_reason: str
    sentiment: str
    keywords: List[str]
    suggested_category: str
    estimated_resolution: str
    is_duplicate: bool = False
    severity_score: int = Field(..., ge=1, le=10)
    recommended_actions: List[str]
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    image_detection: Optional[Dict[str, Any]] = None

class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=20, max_length=2000)
    category: ComplaintCategory
    location: LocationData
    contact_number: Optional[str] = None
    is_anonymous: bool = False

class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    priority: Optional[Priority] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    estimated_completion: Optional[datetime] = None

class ComplaintResponse(BaseModel):
    id: str
    complaint_id: str  # CMP-2024-XXX
    title: str
    description: str
    category: str
    status: ComplaintStatus
    priority: Priority
    location: LocationData
    user_id: str
    user_name: Optional[str] = None
    department: str
    media_urls: List[str] = []
    votes: int = 0
    ai_analysis: Optional[AIAnalysis] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

# ============================================================
# DEPARTMENT MODELS
# ============================================================
class DepartmentCreate(BaseModel):
    name: str
    code: str
    head_name: str
    email: EmailStr
    phone: str
    categories: List[ComplaintCategory]
    city: str = "Delhi"

class DepartmentResponse(DepartmentCreate):
    id: str
    active_complaints: int = 0
    resolved_complaints: int = 0
    avg_resolution_days: float = 0.0
    created_at: datetime

# ============================================================
# ANALYTICS MODELS
# ============================================================
class AnalyticsResponse(BaseModel):
    total_complaints: int
    resolved_complaints: int
    pending_complaints: int
    high_priority: int
    resolution_rate: float
    avg_resolution_days: float
    complaints_by_category: Dict[str, int]
    complaints_by_status: Dict[str, int]
    complaints_by_priority: Dict[str, int]
    top_locations: List[Dict[str, Any]]
    monthly_trends: List[Dict[str, Any]]

# ============================================================
# RESPONSE WRAPPER
# ============================================================
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

def success_response(data: Any = None, message: str = "Success") -> dict:
    return {"success": True, "message": message, "data": data}

def error_response(message: str, errors: list = None) -> dict:
    return {"success": False, "message": message, "errors": errors or []}
