#!/usr/bin/env python3
"""
Seed Database with Sample Data
File: backend/seed_data.py
Run: python seed_data.py
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timedelta
import random

MONGODB_URL = "mongodb+srv://abhay:abhay5121@cluster0.f2nhca8.mongodb.net/?appName=Cluster0"
DB_NAME = "nagarseva_db"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SAMPLE_USERS = [
   
    {"name": "Admin User", "email": "admin@nagarseva.in", "password": "Admin123", "role": "admin", "phone": "9876543200"},
    {"name": "Raj Kumar", "email": "raj@example.com", "password": "User1234", "role": "user", "phone": "9876543201"},
    {"name": "Priya Singh", "email": "priya@example.com", "password": "User1234", "role": "user", "phone": "9876543202"},
    {"name": "Amit Sharma", "email": "amit@example.com", "password": "User1234", "role": "officer", "phone": "9876543203"},
]

SAMPLE_COMPLAINTS = [
    {"title": "Deep pothole on MG Road", "category": "Pothole", "description": "There is a very large pothole on MG Road near the bus stop. Multiple vehicles have been damaged. It has been here for over 2 weeks and is causing accidents.", "address": "MG Road, Sector 5", "city": "Delhi", "priority": "HIGH", "status": "In Progress", "lat": 28.6139, "lng": 77.2090, "votes": 23},
    {"title": "Garbage overflow near Karol Bagh market", "category": "Garbage", "description": "The garbage bins near Karol Bagh market have been overflowing for the past 3 days. The smell is unbearable and is a health hazard for local residents.", "address": "Karol Bagh Market", "city": "Delhi", "priority": "HIGH", "status": "Pending", "lat": 28.6519, "lng": 77.1909, "votes": 45},
    {"title": "Water pipe burst on Ring Road", "category": "Water Leakage", "description": "A major water pipe has burst on Ring Road causing significant water wastage. The road has become waterlogged and traffic is affected.", "address": "Ring Road, Lajpat Nagar", "city": "Delhi", "priority": "HIGH", "status": "Resolved", "lat": 28.5694, "lng": 77.2350, "votes": 18},
    {"title": "Street lights not working in Dwarka", "category": "Street Light", "description": "5 consecutive street lights on Dwarka Sector 10 main road are not working for the past week. This has made the area very unsafe at night.", "address": "Dwarka Sector 10", "city": "Delhi", "priority": "MEDIUM", "status": "Under Review", "lat": 28.5921, "lng": 77.0460, "votes": 12},
    {"title": "Sewage overflow causing health hazard", "category": "Sewage", "description": "Sewage water is overflowing on the main road in Rohini Sector 3. The stench is terrible and children playing nearby are at serious health risk.", "address": "Rohini Sector 3", "city": "Delhi", "priority": "HIGH", "status": "In Progress", "lat": 28.7041, "lng": 77.1025, "votes": 31},
    {"title": "Road cracks after monsoon", "category": "Road Damage", "description": "The road in Janakpuri West has developed multiple cracks after the recent monsoon. The road is uneven and vehicles are getting damaged.", "address": "Janakpuri West", "city": "Delhi", "priority": "MEDIUM", "status": "Pending", "lat": 28.6297, "lng": 77.0878, "votes": 8},
    {"title": "Illegal construction blocking footpath", "category": "Encroachment", "description": "An illegal construction has completely blocked the footpath on Connaught Place outer circle. Pedestrians are forced to walk on the road.", "address": "Connaught Place", "city": "Delhi", "priority": "MEDIUM", "status": "Under Review", "lat": 28.6330, "lng": 77.2194, "votes": 15},
    {"title": "Generator noise causing sleep disturbance", "category": "Noise Pollution", "description": "A commercial generator near residential area in Vasant Kunj runs all night causing severe sleep disturbance for residents. Noise levels are unacceptable.", "address": "Vasant Kunj Sector B", "city": "Delhi", "priority": "LOW", "status": "Pending", "lat": 28.5199, "lng": 77.1580, "votes": 6},
    {"title": "Factory emissions causing breathing issues", "category": "Air Pollution", "description": "A factory in industrial area is emitting thick black smoke without filters. Residents are experiencing respiratory issues. Children and elderly are badly affected.", "address": "Okhla Industrial Area", "city": "Delhi", "priority": "HIGH", "status": "In Progress", "lat": 28.5355, "lng": 77.2729, "votes": 52},
    {"title": "Park benches broken and grass overgrown", "category": "Park Maintenance", "description": "The park in Saket has broken benches, overgrown grass, and non-functional water fountain. The park has been neglected for months.", "address": "Saket District Park", "city": "Delhi", "priority": "LOW", "status": "Pending", "lat": 28.5244, "lng": 77.2167, "votes": 4},
]

SAMPLE_DEPARTMENTS = [
    {"name": "Public Works Department", "code": "PWD", "head_name": "Shri Ramesh Gupta", "email": "pwd@delhi.gov.in", "phone": "011-23456789", "categories": ["Pothole", "Road Damage"], "city": "Delhi"},
    {"name": "Municipal Corporation of Delhi", "code": "MCD", "head_name": "Dr. Sunita Rao", "email": "mcd@delhi.gov.in", "phone": "011-23456790", "categories": ["Garbage", "Encroachment", "Park Maintenance"], "city": "Delhi"},
    {"name": "Delhi Jal Board", "code": "DJB", "head_name": "Shri Vikram Singh", "email": "djb@delhi.gov.in", "phone": "011-23456791", "categories": ["Water Leakage", "Sewage"], "city": "Delhi"},
    {"name": "BSES Rajdhani Power Limited", "code": "BSES", "head_name": "Ms. Anita Krishnan", "email": "bses@delhi.gov.in", "phone": "011-23456792", "categories": ["Street Light"], "city": "Delhi"},
    {"name": "Delhi Pollution Control Committee", "code": "DPCC", "head_name": "Dr. Manish Kumar", "email": "dpcc@delhi.gov.in", "phone": "011-23456793", "categories": ["Air Pollution", "Noise Pollution"], "city": "Delhi"},
]

DEPT_MAP = {
    "Pothole": "PWD", "Garbage": "MCD", "Water Leakage": "DJB",
    "Street Light": "BSES", "Sewage": "DJB", "Encroachment": "MCorp",
    "Noise Pollution": "Pollution Dept", "Air Pollution": "DPCC",
    "Road Damage": "PWD", "Park Maintenance": "Horticulture"
}

async def seed():
    print("🌱 Seeding NagarSeva AI database...")
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    
    # Clear existing data
    await db.users.drop()
    await db.complaints.drop()
    await db.departments.drop()
    print("✅ Cleared existing collections")
    
    # Seed users
    user_ids = []
    for u in SAMPLE_USERS:
        doc = {
            **{k: v for k, v in u.items() if k != "password"},
            "password_hash": pwd_context.hash(u["password"]),
            "is_active": True,
            "complaints_filed": random.randint(0, 10),
            "avatar_url": f"https://ui-avatars.com/api/?name={u['name'].replace(' ', '+')}&background=2563eb&color=fff",
            "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 365)),
            "updated_at": datetime.utcnow()
        }
        result = await db.users.insert_one(doc)
        user_ids.append(str(result.inserted_id))
    print(f"✅ Seeded {len(SAMPLE_USERS)} users")
    
    # Seed departments
    for dept in SAMPLE_DEPARTMENTS:
        await db.departments.insert_one({
            **dept,
            "active_complaints": random.randint(5, 30),
            "resolved_complaints": random.randint(50, 200),
            "avg_resolution_days": round(random.uniform(2, 8), 1),
            "created_at": datetime.utcnow() - timedelta(days=365)
        })
    print(f"✅ Seeded {len(SAMPLE_DEPARTMENTS)} departments")
    
    # Seed complaints
    import uuid
    for i, c in enumerate(SAMPLE_COMPLAINTS):
        days_ago = random.randint(1, 30)
        created_at = datetime.utcnow() - timedelta(days=days_ago)
        
        doc = {
            "complaint_id": f"CMP-2024-{str(i+1).zfill(3)}",
            "title": c["title"],
            "description": c["description"],
            "category": c["category"],
            "status": c["status"],
            "priority": c["priority"],
            "location": {
                "address": c["address"],
                "city": c["city"],
                "state": "Delhi",
                "coordinates": [c["lng"], c["lat"]]
            },
            "user_id": user_ids[1] if len(user_ids) > 1 else user_ids[0],
            "user_name": "Raj Kumar",
            "department": DEPT_MAP.get(c["category"], "General"),
            "media_urls": [],
            "votes": c["votes"],
            "voters": [],
            "is_duplicate": False,
            "ai_analysis": {
                "priority": c["priority"],
                "priority_reason": "AI-assigned based on category and description analysis",
                "sentiment": "urgent" if c["priority"] == "HIGH" else "moderate",
                "keywords": [c["category"].lower(), "civic", "repair"],
                "severity_score": 8 if c["priority"] == "HIGH" else 5 if c["priority"] == "MEDIUM" else 3,
                "recommended_actions": ["Inspect the area", "Assign department", "Schedule repair"],
                "is_duplicate": False
            },
            "resolution_notes": "Issue resolved by PWD team" if c["status"] == "Resolved" else None,
            "assigned_to": "Field Officer A" if c["status"] in ["In Progress", "Resolved"] else None,
            "created_at": created_at,
            "updated_at": datetime.utcnow(),
            "resolved_at": datetime.utcnow() if c["status"] == "Resolved" else None
        }
        await db.complaints.insert_one(doc)
    
    print(f"✅ Seeded {len(SAMPLE_COMPLAINTS)} complaints")
    
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.complaints.create_index("complaint_id", unique=True)
    await db.complaints.create_index([("location.coordinates", "2dsphere")])
    print("✅ Created indexes")
    
    client.close()
    print("\n🎉 Database seeded successfully!")
    print("\n📋 Login credentials:")
    print("   Admin: admin@nagarseva.in / Admin@123")
    print("   User:  raj@example.com / User@123")

if __name__ == "__main__":
    asyncio.run(seed())
