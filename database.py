from motor.motor_asyncio import AsyncIOMotorClient
import logging
from config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_db():
    try:
        db_instance.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            maxPoolSize=10
        )
        db_instance.db = db_instance.client[settings.DB_NAME]
        await db_instance.client.admin.command('ping')
        logger.info(f"✅ Connected to MongoDB: {settings.DB_NAME}")
        await create_indexes()
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        # Don't raise - let app start anyway
        logger.warning("⚠️ Starting without database connection")

async def disconnect_db():
    if db_instance.client:
        db_instance.client.close()

async def create_indexes():
    try:
        db = db_instance.db
        await db.users.create_index("email", unique=True)
        await db.complaints.create_index("complaint_id", unique=True)
        await db.complaints.create_index("status")
        await db.complaints.create_index("category")
        await db.complaints.create_index("user_id")
        await db.complaints.create_index("created_at")
        logger.info("✅ Database indexes created")
    except Exception as e:
        logger.warning(f"Index creation failed: {e}")

def get_db():
    return db_instance.db