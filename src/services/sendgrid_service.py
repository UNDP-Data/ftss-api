"""
SendGrid implementation of the email service.
"""

import logging
import os
from typing import Any, Dict, List

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail, Subject, To

from .email_service import EmailServiceBase

logger = logging.getLogger(__name__)

class SendGridEmailService(EmailServiceBase):
    """Service class for handling email operations using SendGrid"""
    
    def __init__(self):
        try:
            api_key = os.getenv('SENDGRID_API_KEY')
            if not api_key:
                logger.error("SENDGRID_API_KEY environment variable is not set")
                raise ValueError("SendGrid API key is required")
                
            from_email = os.getenv('SENDGRID_FROM_EMAIL')
            if not from_email:
                logger.error("SENDGRID_FROM_EMAIL environment variable is not set")
                raise ValueError("SendGrid from email is required")
                
            self.sg_client = SendGridAPIClient(api_key=api_key)
            self.from_email = Email(from_email)
            logger.info("SendGridEmailService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SendGridEmailService: {str(e)}")
            raise

    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        content: str,
        content_type: str = "text/plain"
    ) -> bool:
        """Send an email using SendGrid"""
        try:
            logger.info(f"Preparing to send email to {len(to_emails)} recipients")
            
            message = Mail(
                from_email=self.from_email,
                to_emails=[To(email) for email in to_emails],
                subject=Subject(subject),
            )
            
            message.content = [Content(content_type, content)]
            
            logger.debug(f"Email content prepared: subject='{subject}', type='{content_type}'")
            
            response = self.sg_client.send(message)
            status_code = response.status_code
            
            if status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully: status_code={status_code}")
                return True
            else:
                logger.error(f"Failed to send email: status_code={status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}", exc_info=True)
            return False

    async def send_notification_email(
        self,
        to_email: str,
        subject: str,
        template_id: str,
        dynamic_data: Dict[str, Any]
    ) -> bool:
        """Send a templated notification email"""
        try:
            logger.info(f"Preparing to send notification email to {to_email}")
            logger.debug(f"Using template_id: {template_id}")
            logger.debug(f"Dynamic data: {dynamic_data}")
            
            message = Mail(
                from_email=self.from_email,
                to_emails=[To(to_email)]
            )
            
            message.template_id = template_id
            message.dynamic_template_data = dynamic_data
            
            response = self.sg_client.send(message)
            status_code = response.status_code
            
            if status_code in [200, 201, 202]:
                logger.info(f"Notification email sent successfully: status_code={status_code}")
                return True
            else:
                logger.error(f"Failed to send notification email: status_code={status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}", exc_info=True)
            return False 