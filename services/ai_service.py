# ============================================================
# AI Analysis Service
# File: backend/services/ai_service.py
# ============================================================

import re, hashlib, logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import numpy as np

logger = logging.getLogger(__name__)

# ============================================================
# KEYWORD-BASED NLP CLASSIFIER
# ============================================================
CATEGORY_KEYWORDS = {
    "Pothole": ["pothole", "pit", "hole", "depression", "crater", "road dug", "broken road"],
    "Garbage": ["garbage", "trash", "waste", "litter", "dump", "rubbish", "debris", "filth", "dirty"],
    "Water Leakage": ["water", "pipe", "leak", "burst", "flood", "overflow", "seepage", "waterlogging"],
    "Street Light": ["light", "lamp", "bulb", "dark", "electricity", "street light", "pole", "illumination"],
    "Sewage": ["sewer", "sewage", "drain", "drainage", "manhole", "stench", "smell", "odor", "gutter"],
    "Encroachment": ["encroachment", "illegal", "occupation", "obstruction", "blocking", "footpath"],
    "Noise Pollution": ["noise", "loud", "sound", "music", "generator", "construction noise", "horn"],
    "Air Pollution": ["smoke", "pollution", "dust", "smog", "emission", "burning", "fumes", "air quality"],
    "Road Damage": ["road damage", "crack", "broken", "uneven", "damaged road", "bump"],
    "Park Maintenance": ["park", "garden", "tree", "grass", "bench", "playground", "maintenance"],
}

URGENCY_KEYWORDS = {
    "HIGH": ["emergency", "accident", "danger", "hazard", "urgent", "serious", "severe", "critical", "immediate", "injury", "death", "health risk", "collapse"],
    "MEDIUM": ["problem", "issue", "concern", "need", "repair", "fix", "multiple", "many days", "week"],
    "LOW": ["minor", "small", "slight", "inconvenience", "sometimes", "occasional"]
}

SENTIMENT_MAP = {
    "urgent": ["immediately", "asap", "urgent", "emergency", "danger", "accident", "severe"],
    "moderate": ["problem", "days", "week", "need", "should", "fix", "repair"],
    "mild": ["minor", "small", "sometimes", "occasional", "when possible"]
}

# Priority scoring matrix
PRIORITY_MATRIX = {
    "Pothole": {"base": 6, "health_risk": True},
    "Garbage": {"base": 7, "health_risk": True},
    "Water Leakage": {"base": 8, "health_risk": True},
    "Street Light": {"base": 5, "health_risk": False},
    "Sewage": {"base": 9, "health_risk": True},
    "Encroachment": {"base": 4, "health_risk": False},
    "Noise Pollution": {"base": 4, "health_risk": False},
    "Air Pollution": {"base": 7, "health_risk": True},
    "Road Damage": {"base": 6, "health_risk": True},
    "Park Maintenance": {"base": 3, "health_risk": False},
    "Other": {"base": 5, "health_risk": False}
}

RESOLUTION_TIMES = {
    "LOW": "14-21 days",
    "MEDIUM": "7-14 days",
    "HIGH": "1-3 days",
}

class AIAnalysisService:
    """Core AI analysis service for complaint processing"""

    def __init__(self):
        self.recent_hashes = set()  # In production: use Redis

    # --------------------------------------------------------
    # MAIN ANALYSIS PIPELINE
    # --------------------------------------------------------
    async def analyze_complaint(self, title: str, description: str, category: str) -> Dict[str, Any]:
        """Full AI analysis pipeline"""
        try:
            full_text = f"{title} {description}".lower()
            
            # 1. NLP Category Suggestion
            suggested_category = self._classify_category(full_text) or category
            
            # 2. Sentiment Analysis
            sentiment = self._analyze_sentiment(full_text)
            
            # 3. Keyword Extraction
            keywords = self._extract_keywords(full_text, category)
            
            # 4. Priority Scoring
            priority, score = self._calculate_priority(title, description, category)
            
            # 5. Duplicate Detection
            is_duplicate = self._check_duplicate(full_text)
            
            # 6. Recommended Actions
            actions = self._get_recommended_actions(category, priority)
            
            # 7. Priority Reason
            priority_reason = self._get_priority_reason(priority, category, score)
            
            return {
                "priority": priority,
                "priority_reason": priority_reason,
                "sentiment": sentiment,
                "keywords": keywords,
                "suggested_category": suggested_category,
                "estimated_resolution": RESOLUTION_TIMES.get(priority, "7-14 days"),
                "is_duplicate": is_duplicate,
                "severity_score": score,
                "recommended_actions": actions,
                "analyzed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return self._fallback_analysis(category)

    # --------------------------------------------------------
    # NLP CATEGORY CLASSIFIER
    # --------------------------------------------------------
    def _classify_category(self, text: str) -> Optional[str]:
        """Classify complaint category using keyword matching"""
        scores = {}
        for cat, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[cat] = score
        
        return max(scores, key=scores.get) if scores else None

    # --------------------------------------------------------
    # SENTIMENT ANALYZER
    # --------------------------------------------------------
    def _analyze_sentiment(self, text: str) -> str:
        """Simple rule-based sentiment analysis"""
        for sentiment, keywords in SENTIMENT_MAP.items():
            if any(kw in text for kw in keywords):
                return sentiment
        return "moderate"

    # --------------------------------------------------------
    # KEYWORD EXTRACTOR
    # --------------------------------------------------------
    def _extract_keywords(self, text: str, category: str) -> List[str]:
        """Extract relevant keywords from text"""
        keywords = []
        
        # Category-specific keywords
        cat_kws = CATEGORY_KEYWORDS.get(category, [])
        keywords.extend([kw for kw in cat_kws if kw in text])
        
        # Urgency keywords
        for level, kws in URGENCY_KEYWORDS.items():
            keywords.extend([kw for kw in kws if kw in text])
        
        # Common civic terms
        civic_terms = ["road", "street", "water", "drainage", "municipality", "sector", "block"]
        keywords.extend([t for t in civic_terms if t in text])
        
        # Deduplicate and limit
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:6]

    # --------------------------------------------------------
    # PRIORITY SCORING SYSTEM
    # --------------------------------------------------------
    def _calculate_priority(self, title: str, description: str, category: str) -> tuple:
        """Multi-factor priority scoring"""
        text = f"{title} {description}".lower()
        
        # Base score from category
        cat_data = PRIORITY_MATRIX.get(category, {"base": 5, "health_risk": False})
        score = cat_data["base"]
        
        # Urgency boost
        urgency_words = URGENCY_KEYWORDS["HIGH"]
        urgency_count = sum(1 for w in urgency_words if w in text)
        score += min(urgency_count * 1.5, 3)
        
        # Health risk boost
        if cat_data["health_risk"]:
            health_terms = ["children", "elderly", "hospital", "school", "pregnant", "sick"]
            if any(t in text for t in health_terms):
                score += 1.5
        
        # Multiple occurrences
        if any(w in text for w in ["many", "multiple", "several", "all", "entire"]):
            score += 1
        
        # Duration
        if any(w in text for w in ["months", "years", "long time", "weeks"]):
            score += 0.5
        
        # Normalize to 1-10
        score = min(10, max(1, round(score)))
        
        # Map score to priority
        if score >= 7:
            priority = "HIGH"
        elif score >= 4:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        
        return priority, score

    # --------------------------------------------------------
    # DUPLICATE DETECTION (Hash-based)
    # --------------------------------------------------------
    def _check_duplicate(self, text: str) -> bool:
        """Simple content hash for duplicate detection"""
        # Normalize text
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Hash the normalized text
        content_hash = hashlib.md5(normalized.encode()).hexdigest()
        
        if content_hash in self.recent_hashes:
            return True
        
        self.recent_hashes.add(content_hash)
        
        # Keep set manageable (in prod: use Redis TTL)
        if len(self.recent_hashes) > 1000:
            self.recent_hashes = set(list(self.recent_hashes)[-500:])
        
        return False

    # --------------------------------------------------------
    # RECOMMENDED ACTIONS
    # --------------------------------------------------------
    def _get_recommended_actions(self, category: str, priority: str) -> List[str]:
        """Get recommended actions based on category and priority"""
        base_actions = {
            "Pothole": ["Conduct road inspection", "Block area if dangerous", "Schedule PWD team", "Fill and repair pothole"],
            "Garbage": ["Deploy garbage truck", "Clean area within 24hrs", "Place dustbins", "Issue notice to area"],
            "Water Leakage": ["Shut off affected valve", "Dispatch repair team", "Restore water supply"],
            "Street Light": ["Inspect electrical fault", "Replace bulb/ballast", "Check transformer"],
            "Sewage": ["Inspect sewage line", "Deploy tanker", "Clean manhole", "Check for blockage"],
            "Encroachment": ["Record evidence", "Issue notice", "Contact local authority"],
            "Noise Pollution": ["Issue warning notice", "Measure noise levels", "Take legal action if needed"],
            "Air Pollution": ["Identify pollution source", "Issue compliance notice", "Monitor air quality"],
            "Road Damage": ["Mark area with signs", "Assess damage extent", "Schedule repair team"],
            "Park Maintenance": ["Assign horticulture team", "Inspect equipment", "Schedule maintenance"]
        }
        
        actions = base_actions.get(category, ["Inspect the area", "Assign department", "Schedule repair"])
        
        if priority == "HIGH":
            return [f"⚡ URGENT: {actions[0]}"] + actions[1:3]
        
        return actions[:3]

    # --------------------------------------------------------
    # PRIORITY REASON
    # --------------------------------------------------------
    def _get_priority_reason(self, priority: str, category: str, score: int) -> str:
        reasons = {
            "HIGH": f"{category} issue with severity score {score}/10 — immediate attention needed for public safety.",
            "MEDIUM": f"{category} issue with severity score {score}/10 — needs attention within standard SLA.",
            "LOW": f"{category} issue with severity score {score}/10 — can be scheduled for routine maintenance."
        }
        return reasons.get(priority, "Standard civic issue requiring departmental attention.")

    def _fallback_analysis(self, category: str) -> Dict:
        return {
            "priority": "MEDIUM",
            "priority_reason": "Standard civic issue requiring attention",
            "sentiment": "moderate",
            "keywords": [category.lower(), "civic", "repair"],
            "suggested_category": category,
            "estimated_resolution": "7-14 days",
            "is_duplicate": False,
            "severity_score": 5,
            "recommended_actions": ["Inspect the area", "Assign to department", "Schedule repair"],
            "analyzed_at": datetime.utcnow().isoformat()
        }


# ============================================================
# IMAGE CLASSIFICATION SERVICE (YOLO/TF wrapper)
# ============================================================
class ImageClassificationService:
    """
    Image classification for civic complaints.
    In production: integrate YOLO v8 or TensorFlow model.
    """
    
    # Class labels the model can detect
    CLASSES = ["pothole", "garbage_pile", "water_leakage", "damaged_road", "broken_light", "encroachment"]
    
    CATEGORY_MAP = {
        "pothole": "Pothole",
        "garbage_pile": "Garbage",
        "water_leakage": "Water Leakage",
        "damaged_road": "Road Damage",
        "broken_light": "Street Light",
        "encroachment": "Encroachment"
    }

    def __init__(self, model_path: str = None):
        self.model = None
        self.model_path = model_path
        # self._load_model()  # Uncomment when model is available

    def _load_model(self):
        """Load YOLO or TF model"""
        try:
            # For YOLO:
            # from ultralytics import YOLO
            # self.model = YOLO(self.model_path)
            
            # For TensorFlow:
            # import tensorflow as tf
            # self.model = tf.saved_model.load(self.model_path)
            
            logger.info(f"✅ Image model loaded from {self.model_path}")
        except Exception as e:
            logger.warning(f"Model load failed: {e}. Using mock classifier.")

    async def classify(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Classify image and return detected category.
        
        In production with YOLO:
            results = self.model(image_bytes)
            boxes = results[0].boxes
            ...
        
        Returns mock result for demo.
        """
        if self.model:
            return await self._run_model(image_bytes)
        else:
            return self._mock_classify()

    async def _run_model(self, image_bytes: bytes) -> Dict:
        """Run actual model inference"""
        import io
        from PIL import Image
        
        image = Image.open(io.BytesIO(image_bytes))
        # Process with YOLO or TF model
        # ...
        return self._mock_classify()

    def _mock_classify(self) -> Dict:
        """Mock classification for development"""
        import random
        detected = random.choice(self.CLASSES)
        confidence = round(random.uniform(0.75, 0.97), 3)
        severity = "HIGH" if confidence > 0.88 else "MEDIUM"
        
        return {
            "detected_class": self.CATEGORY_MAP.get(detected, detected),
            "raw_class": detected,
            "confidence": confidence,
            "severity": severity,
            "bounding_box": {"x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.7},
            "model_version": "yolov8n-civic-v1.0"
        }
