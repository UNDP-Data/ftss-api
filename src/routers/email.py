"""
Router for email-related endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from ..dependencies import require_admin
from ..entities import User
from ..services.email_factory import create_email_service
from ..authentication import authenticate_user

router = APIRouter(prefix="/email", tags=["email"])

# Request models
class EmailRequest(BaseModel):
    to_emails: List[EmailStr]
    subject: str
    content: str
    content_type: str = "text/plain"

class NotificationRequest(BaseModel):
    to_email: EmailStr
    subject: str
    template_id: str
    dynamic_data: dict

class DigestRequest(BaseModel):
    days: int | None = None
    status: List[str] | None = None
    limit: int | None = None
    test: bool = False

# Lazy email service initialization
def get_email_service():
    """Get email service instance. Created on first use to avoid startup errors."""
    return create_email_service()

@router.post("/send", dependencies=[Depends(require_admin)])
async def send_email(request: EmailRequest):
    """
    Send an email to multiple recipients.
    Only accessible by admin users.
    """
    email_service = get_email_service()
    success = await email_service.send_email(
        to_emails=request.to_emails,
        subject=request.subject,
        content=request.content,
        content_type=request.content_type
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email")
    
    return {"message": "Email sent successfully"}

@router.post("/notify", dependencies=[Depends(require_admin)])
async def send_notification(request: NotificationRequest):
    """
    Send a templated notification email.
    Only accessible by admin users.
    """
    email_service = get_email_service()
    success = await email_service.send_notification_email(
        to_email=request.to_email,
        subject=request.subject,
        template_id=request.template_id,
        dynamic_data=request.dynamic_data
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    
    return {"message": "Notification sent successfully"}

@router.post("/digest")
async def trigger_digest(request: DigestRequest, user: User = Depends(authenticate_user)):
    """
    Trigger the email digest process as the authenticated user (delegated permissions).
    Only sends to the hardcoded cdo.curators@undp.org address.
    """
    from src.services.weekly_digest import WeeklyDigestService, Status
    import logging
    import asyncio

    logger = logging.getLogger(__name__)
    curator_email = "cdo.curators@undp.org"
    logger.info(f"User {user.email} is triggering a digest email to {curator_email}")

    # Map status strings to Status enum if provided
    status_enum = None
    if request.status:
        status_enum = [Status(s) for s in request.status]

    digest_service = WeeklyDigestService()
    subject = "UNDP Futures Weekly Digest"
    if request.test:
        subject = f"[TEST] {subject}"

    # Generate signals and HTML
    signals_list = await digest_service.get_recent_signals(days=request.days, status=status_enum, limit=request.limit)
    html_content = digest_service.generate_email_html(signals_list)

    # Use user access token for this endpoint
    email_service = create_email_service(useUserAccessToken=True)
    success = await email_service.send_email(
        to_emails=[curator_email],
        subject=subject,
        content=html_content,
        content_type="text/html",
        useUserAccessToken=True
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send digest email")
    return {"message": "Digest email sent successfully"} 