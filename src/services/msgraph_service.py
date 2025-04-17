"""
Microsoft Graph implementation of the email service.
"""

import logging
import os
from typing import Any, Dict, List

from azure.identity import DefaultAzureCredential
from msgraph.core import GraphClient

from .email_service import EmailServiceBase

logger = logging.getLogger(__name__)

# Define the Microsoft Graph scopes
GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]

class MSGraphEmailService(EmailServiceBase):
    """Service class for handling email operations using Microsoft Graph API"""
    
    def __init__(self):
        try:
            # Use DefaultAzureCredential which supports multiple authentication methods
            credential = DefaultAzureCredential()
            # Initialize GraphClient with the correct scopes
            self.client = GraphClient(credential=credential, scopes=GRAPH_SCOPES)
            self.from_email = os.getenv('MS_FROM_EMAIL')
            if not self.from_email:
                logger.error("MS_FROM_EMAIL environment variable is not set")
                raise ValueError("Microsoft sender email is required")
                
            logger.info("MSGraphEmailService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MSGraphEmailService: {str(e)}")
            raise

    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        content: str,
        content_type: str = "text/plain"
    ) -> bool:
        """Send an email using Microsoft Graph API with Mail.Send permission"""
        try:
            logger.info(f"Preparing to send email to {len(to_emails)} recipients")
            
            # Prepare the email message
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": content
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": email
                            }
                        } for email in to_emails
                    ],
                    "from": {
                        "emailAddress": {
                            "address": self.from_email
                        }
                    }
                },
                "saveToSentItems": "true"
            }
            
            logger.debug(f"Email content prepared: subject='{subject}', type='HTML'")
            
            # Send the email using Microsoft Graph API with Mail.Send permission
            # Note: GraphClient.post is not an async method
            response = self.client.post(
                "/me/sendMail",  # Using the standard endpoint without v1.0 prefix
                json=message,  # Use json instead of data
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully: status_code={response.status_code}")
                return True
            else:
                logger.error(f"Failed to send email: status_code={response.status_code}, response={response.json() if hasattr(response, 'json') else 'No JSON response'}")
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
        """Send a templated notification email using Microsoft Graph API"""
        try:
            logger.info(f"Preparing to send notification email to {to_email}")
            logger.debug(f"Using template_id: {template_id}")
            logger.debug(f"Dynamic data: {dynamic_data}")
            
            # For Microsoft Graph, we'll need to handle templates differently
            # This is a simplified version that just replaces variables in the template
            template_content = await self._get_template_content(template_id)
            if not template_content:
                return False
                
            # Replace template variables with dynamic data
            for key, value in dynamic_data.items():
                template_content = template_content.replace(f"{{{key}}}", str(value))
            
            # Send the email using the processed template
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": template_content
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to_email
                            }
                        }
                    ],
                    "from": {
                        "emailAddress": {
                            "address": self.from_email
                        }
                    }
                },
                "saveToSentItems": "true"
            }
            
            # Note: GraphClient.post is not an async method
            response = self.client.post(
                "/me/sendMail",  # Using the standard endpoint without v1.0 prefix
                json=message,  # Use json instead of data
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Notification email sent successfully: status_code={response.status_code}")
                return True
            else:
                logger.error(f"Failed to send notification email: status_code={response.status_code}, response={response.json() if hasattr(response, 'json') else 'No JSON response'}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}", exc_info=True)
            return False
            
    async def _get_template_content(self, template_id: str) -> str:
        """
        Get the template content from Azure storage or other source.
        This is a placeholder - implement based on where templates are stored.
        """
        # TODO: Implement template retrieval from Azure storage or other source
        logger.warning("Template retrieval not implemented - using placeholder")
        return f"<html><body><h1>Template {template_id}</h1><p>This is a placeholder template.</p></body></html>" 