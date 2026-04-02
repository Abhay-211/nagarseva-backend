# ============================================================
# Database Configuration - MongoDB with Motor (async)
# File: backend/database.py
# ============================================================

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import logging
from config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_db():
    """Connect to MongoDB"""
    try:
        db_instance.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=10
        )
        # Verify connection
        await db_instance.client.admin.command('ping')
        db_instance.db = db_instance.client[settings.DB_NAME]
        logger.info(f"✅ Connected to MongoDB: {settings.DB_NAME}")
        
        # Create indexes
        await create_indexes()
    except ConnectionFailure as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise

async def disconnect_db():
    """Disconnect from MongoDB"""
    if db_instance.client:
        db_instance.client.close()
        logger.info("MongoDB disconnected")

async def create_indexes():
    """Create database indexes for performance"""
    db = db_instance.db
    
    # Users collection
    await db.users.create_index("email", unique=True)
    await db.users.create_index("phone")
    
    # Complaints collection
    await db.complaints.create_index("complaint_id", unique=True)
    await db.complaints.create_index("status")
    await db.complaints.create_index("category")
    await db.complaints.create_index("priority")
    await db.complaints.create_index("user_id")
    await db.complaints.create_index([("location.coordinates", "2dsphere")])
    await db.complaints.create_index("created_at")
    
    # Departments collection
    await db.departments.create_index("name", unique=True)
    
    logger.info("✅ Database indexes created")

def get_db():
    """Get database instance"""
    return db_instance.db
