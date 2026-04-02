# ============================================================
# Authentication Router
# File: backend/routers/users.py
# ============================================================

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from bson import ObjectId
import logging

from database import get_db
from models.schemas import (
    UserCreate, UserLogin, UserResponse, UserUpdate,
    Token, TokenData, success_response, error_response
)
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================
# AUTH UTILITIES
# ============================================================
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Verify JWT token and return current user"""
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role"""
    if current_user.get("role") not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ============================================================
# AUTH ENDPOINTS
# ============================================================
@router.post("/register", response_model=dict, status_code=201)
async def register(user_data: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Register a new user"""
    # Check existing email
    if await db.users.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user document
    user_doc = {
        "name": user_data.name,
        "email": user_data.email,
        "phone": user_data.phone,
        "address": user_data.address,
        "city": user_data.city,
        "state": user_data.state,
        "password_hash": hash_password(user_data.password),
        "role": user_data.role.value,
        "is_active": True,
        "complaints_filed": 0,
        "avatar_url": f"https://ui-avatars.com/api/?name={user_data.name.replace(' ', '+')}&background=2563eb&color=fff",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    
    # Generate token
    token = create_access_token({"sub": str(result.inserted_id), "email": user_data.email, "role": user_data.role.value})
    
    return success_response(
        data={"access_token": token, "token_type": "bearer", "user": _format_user(user_doc)},
        message="Account created successfully"
    )

@router.post("/login", response_model=dict)
async def login(credentials: UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Login user"""
    user = await db.users.find_one({"email": credentials.email})
    
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    token = create_access_token({
        "sub": str(user["_id"]),
        "email": user["email"],
        "role": user["role"]
    })
    
    return success_response(
        data={"access_token": token, "token_type": "bearer", "user": _format_user(user)},
        message=f"Welcome back, {user['name'].split()[0]}!"
    )

@router.get("/me", response_model=dict)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return success_response(data=_format_user(current_user))

@router.put("/me", response_model=dict)
async def update_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Update user profile"""
    update_doc = {k: v for k, v in update_data.dict().items() if v is not None}
    update_doc["updated_at"] = datetime.utcnow()
    
    await db.users.update_one({"_id": current_user["_id"]}, {"$set": update_doc})
    updated_user = await db.users.find_one({"_id": current_user["_id"]})
    
    return success_response(data=_format_user(updated_user), message="Profile updated")

@router.get("/users", response_model=dict)  # Admin only
async def get_all_users(
    skip: int = 0, limit: int = 50,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all users (admin only)"""
    users = await db.users.find({}, {"password_hash": 0}).skip(skip).limit(limit).to_list(limit)
    total = await db.users.count_documents({})
    return success_response(data={"users": [_format_user(u) for u in users], "total": total})

def _format_user(user: dict) -> dict:
    """Format user for API response"""
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "phone": user.get("phone"),
        "address": user.get("address"),
        "city": user.get("city"),
        "role": user["role"],
        "is_active": user.get("is_active", True),
        "complaints_filed": user.get("complaints_filed", 0),
        "avatar_url": user.get("avatar_url"),
        "created_at": user.get("created_at", datetime.utcnow()).isoformat()
    }
