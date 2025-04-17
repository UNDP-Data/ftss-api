"""
Router for email-related endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from ..dependencies import require_admin
from ..entities import User
from ..services.email_factory import create_email_service

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

# Initialize email service
email_service = create_email_service()

@router.post("/send", dependencies=[Depends(require_admin)])
async def send_email(request: EmailRequest):
    """
    Send an email to multiple recipients.
    Only accessible by admin users.
    """
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
    success = await email_service.send_notification_email(
        to_email=request.to_email,
        subject=request.subject,
        template_id=request.template_id,
        dynamic_data=request.dynamic_data
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    
    return {"message": "Notification sent successfully"} 