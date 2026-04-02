from fastapi import APIRouter
router = APIRouter()

@router.get("/")
async def get_departments():
    return {"departments": [
        {"name": "PWD", "categories": ["Pothole", "Road Damage"]},
        {"name": "MCD", "categories": ["Garbage", "Encroachment"]},
        {"name": "DJB", "categories": ["Water Leakage", "Sewage"]},
        {"name": "BSES", "categories": ["Street Light"]},
        {"name": "DPCC", "categories": ["Air Pollution", "Noise Pollution"]},
    ]}