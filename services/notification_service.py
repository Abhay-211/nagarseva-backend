# ============================================================
# Notification Service (Email + Firebase)
# File: backend/services/notification_service.py
# ============================================================

import logging, asyncio
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Handles email and push notifications"""

    async def send_complaint_received(self, email: str, complaint_id: str, department: str):
        """Send confirmation when complaint is filed"""
        subject = f"✅ Complaint Filed: {complaint_id}"
        body = f"""
Dear Citizen,

Your complaint has been successfully registered.

Complaint ID: {complaint_id}
Assigned To: {department}

You can track your complaint status at: https://nagarseva.in/track/{complaint_id}

Our team will update you as the complaint progresses.

Regards,
NagarSeva AI Team
Helpline: 1800-XXX-XXXX
        """
        await self._send_email(email, subject, body)
        logger.info(f"✅ Confirmation sent to {email} for {complaint_id}")

    async def send_status_update(self, email: str, complaint_id: str, new_status: str):
        """Send status update notification"""
        status_messages = {
            "Under Review": "is now being reviewed by the concerned department.",
            "In Progress": "has been assigned and repair work has begun.",
            "Resolved": "has been RESOLVED! Thank you for helping improve our city.",
            "Rejected": "could not be processed. Please contact us for more information."
        }
        
        msg = status_messages.get(new_status, f"status has been updated to {new_status}")
        subject = f"🔔 Complaint Update: {complaint_id} — {new_status}"
        body = f"""
Dear Citizen,

Your complaint {complaint_id} {msg}

Track status: https://nagarseva.in/track/{complaint_id}

Regards,
NagarSeva AI Team
        """
        await self._send_email(email, subject, body)

    async def _send_email(self, to: str, subject: str, body: str):
        """Send email via SMTP"""
        if not settings.SMTP_HOST or not to:
            logger.info(f"[Mock Email] To: {to} | Subject: {subject}")
            return
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._smtp_send, msg, to)
        except Exception as e:
            logger.error(f"Email send failed: {e}")

    def _smtp_send(self, msg, to: str):
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)

    async def send_push_notification(self, user_id: str, title: str, body: str):
        """Send Firebase push notification"""
        if not settings.FIREBASE_PROJECT_ID:
            logger.info(f"[Mock Push] User: {user_id} | {title}: {body}")
            return
        
        try:
            import firebase_admin
            from firebase_admin import messaging, credentials
            
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                topic=f"user_{user_id}"
            )
            messaging.send(message)
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
