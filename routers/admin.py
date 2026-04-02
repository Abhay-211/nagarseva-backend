# ============================================================
# Admin Router with Analytics
# File: backend/routers/admin.py
# ============================================================

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from collections import defaultdict

from database import get_db
from routers.users import require_admin
from models.schemas import success_response

router = APIRouter()

@router.get("/analytics/overview")
async def get_analytics(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get complete analytics overview"""
    total = await db.complaints.count_documents({})
    resolved = await db.complaints.count_documents({"status": "Resolved"})
    pending = await db.complaints.count_documents({"status": "Pending"})
    high_priority = await db.complaints.count_documents({"priority": "HIGH"})
    
    # By category
    pipeline_cat = [{"$group": {"_id": "$category", "count": {"$sum": 1}}}]
    cat_results = await db.complaints.aggregate(pipeline_cat).to_list(None)
    by_category = {r["_id"]: r["count"] for r in cat_results if r["_id"]}
    
    # By status
    pipeline_status = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_results = await db.complaints.aggregate(pipeline_status).to_list(None)
    by_status = {r["_id"]: r["count"] for r in status_results if r["_id"]}
    
    # Top locations
    pipeline_loc = [
        {"$group": {"_id": "$location.city", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 5}
    ]
    loc_results = await db.complaints.aggregate(pipeline_loc).to_list(5)
    
    # Monthly trends (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    pipeline_monthly = [
        {"$match": {"created_at": {"$gte": six_months_ago}}},
        {"$group": {
            "_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}},
            "count": {"$sum": 1},
            "resolved": {"$sum": {"$cond": [{"$eq": ["$status", "Resolved"]}, 1, 0]}}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]
    monthly_results = await db.complaints.aggregate(pipeline_monthly).to_list(6)
    
    return success_response(data={
        "total_complaints": total,
        "resolved_complaints": resolved,
        "pending_complaints": pending,
        "high_priority": high_priority,
        "resolution_rate": round((resolved / total * 100) if total > 0 else 0, 1),
        "avg_resolution_days": 4.2,  # Calculate from resolved_at - created_at in prod
        "by_category": by_category,
        "by_status": by_status,
        "top_locations": [{"location": r["_id"], "count": r["count"]} for r in loc_results],
        "monthly_trends": [
            {"month": f"{r['_id']['year']}-{r['_id']['month']:02d}", "total": r["count"], "resolved": r["resolved"]}
            for r in monthly_results
        ]
    })

@router.get("/departments/stats")
async def department_stats(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get per-department statistics"""
    pipeline = [
        {"$group": {
            "_id": "$department",
            "total": {"$sum": 1},
            "resolved": {"$sum": {"$cond": [{"$eq": ["$status", "Resolved"]}, 1, 0]}},
            "pending": {"$sum": {"$cond": [{"$eq": ["$status", "Pending"]}, 1, 0]}},
            "high_priority": {"$sum": {"$cond": [{"$eq": ["$priority", "HIGH"]}, 1, 0]}}
        }},
        {"$sort": {"total": -1}}
    ]
    results = await db.complaints.aggregate(pipeline).to_list(None)
    return success_response(data=results)

@router.get("/heatmap")
async def get_heatmap_data(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get geo-coordinates for heatmap"""
    complaints = await db.complaints.find(
        {"location.coordinates": {"$ne": None}},
        {"location.coordinates": 1, "priority": 1, "category": 1}
    ).to_list(500)
    
    points = []
    for c in complaints:
        coords = c.get("location", {}).get("coordinates")
        if coords and len(coords) == 2:
            points.append({
                "lat": coords[1],
                "lng": coords[0],
                "weight": 3 if c.get("priority") == "HIGH" else 2 if c.get("priority") == "MEDIUM" else 1
            })
    
    return success_response(data={"points": points})
