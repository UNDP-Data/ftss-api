"""
Microsoft Graph implementation of the email service using Enterprise Application credentials.
"""

import logging
import os
import json
from typing import Any, Dict, List

from azure.identity import ClientSecretCredential
import httpx

from .email_service import EmailServiceBase
from .user_auth_service import UserAuthEmailService

logger = logging.getLogger(__name__)

# Define the Microsoft Graph scopes
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"

class MSGraphEmailService(EmailServiceBase):
    """Service class for handling email operations using Microsoft Graph API"""
    
    def __init__(self, useUserAccessToken: bool = False):
        self.useUserAccessToken = useUserAccessToken
        if useUserAccessToken:
            self.user_auth_service = UserAuthEmailService()
            return
        try:
            # Get credentials from environment variables
            tenant_id = os.getenv('TENANT_ID')
            client_id = os.getenv('CLIENT_ID')
            client_secret = os.getenv('CLIENT_SECRET')
            service_type = os.getenv('EMAIL_SERVICE_TYPE')
            self.from_email = os.getenv('MS_FROM_EMAIL')
            logger.info(f"MSGraphEmailService config: TENANT_ID={tenant_id}, CLIENT_ID={client_id}, FROM_EMAIL={self.from_email}, EMAIL_SERVICE_TYPE={service_type}")
            if not all([tenant_id, client_id, client_secret]):
                logger.error("Missing required environment variables for authentication")
                raise ValueError("TENANT_ID, CLIENT_ID, and CLIENT_SECRET must be set")
            
            # Use ClientSecretCredential for app authentication
            self.credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            
            if not self.from_email:
                logger.error("MS_FROM_EMAIL environment variable is not set")
                raise ValueError("Microsoft sender email is required")
                
            logger.info("MSGraphEmailService initialized successfully with enterprise application credentials")
            
        except Exception as e:
            logger.error(f"Failed to initialize MSGraphEmailService: {str(e)}")
            raise

    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        content: str,
        content_type: str = "text/plain",
        useUserAccessToken: bool = False
    ) -> bool:
        if getattr(self, 'useUserAccessToken', False):
            return await self.user_auth_service.send_email(
                to_emails=to_emails,
                subject=subject,
                content=content,
                content_type=content_type,
                useUserAccessToken=True
            )
        """Send an email using Microsoft Graph API with Mail.Send permission"""
        try:
            logger.info(f"send_email config: TENANT_ID={os.getenv('TENANT_ID')}, CLIENT_ID={os.getenv('CLIENT_ID')}, FROM_EMAIL={self.from_email}, EMAIL_SERVICE_TYPE={os.getenv('EMAIL_SERVICE_TYPE')}, to_emails={to_emails}, subject={subject}")
            logger.info(f"Preparing to send email to {len(to_emails)} recipients")
            
            # Prepare the email message
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML" if content_type.lower() == "text/html" else "Text",
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
            
            logger.debug(f"Email content prepared: subject='{subject}', type='{content_type}'")
            
            # For enterprise applications with app permissions, we send on behalf of a user
            # using /users/{user_id}/sendMail instead of /me/sendMail
            user_email = self.from_email
            
            logger.info("Acquiring Microsoft Graph token...")
            try:
                token = self.credential.get_token(GRAPH_SCOPE)
                logger.info("Token acquired successfully.")
            except Exception as token_exc:
                logger.error(f"Failed to acquire token: {token_exc}", exc_info=True)
                return False
            
            logger.info(f"Sending email via Graph API to /users/{user_email}/sendMail ...")
            try:
                response = await self._post(f"/users/{user_email}/sendMail", message, token=token)
            except Exception as post_exc:
                logger.error(f"Exception during HTTP POST to Graph API: {post_exc}", exc_info=True)
                return False
            
            if response.status_code in [200, 201, 202, 204]:
                logger.info(f"Email sent successfully: status_code={response.status_code}")
                return True
            else:
                logger.error(f"Failed to send email: status_code={response.status_code}, response={response.text}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}", exc_info=True)
            return False

    async def send_notification_email(
        self,
        to_email: str,
        subject: str,
        template_id: str,
        dynamic_data: Dict[str, Any],
        useUserAccessToken: bool = False
    ) -> bool:
        if getattr(self, 'useUserAccessToken', False):
            return await self.user_auth_service.send_notification_email(
                to_email=to_email,
                subject=subject,
                template_id=template_id,
                dynamic_data=dynamic_data,
                useUserAccessToken=True
            )
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
            
            # For enterprise applications with app permissions, we send on behalf of a user
            user_email = self.from_email
            
            # Send the email
            response = await self._post(f"/users/{user_email}/sendMail", message)
            
            if response.status_code in [200, 201, 202, 204]:
                logger.info(f"Notification email sent successfully: status_code={response.status_code}")
                return True
            else:
                logger.error(f"Failed to send notification email: status_code={response.status_code}, response={response.text}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}", exc_info=True)
            return False
    
    async def _post(self, endpoint: str, data: dict, token=None) -> httpx.Response:
        """Helper method to make a POST request to the Graph API"""
        try:
            if token is None:
                logger.info("Acquiring token inside _post (should be passed from send_email)...")
                token = self.credential.get_token(GRAPH_SCOPE)
            headers = {
                "Authorization": f"Bearer {token.token}",
                "Content-Type": "application/json"
            }
            url = f"{GRAPH_ENDPOINT}{endpoint}"
            logger.info(f"Making HTTP POST to {url}")
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
            logger.info(f"HTTP POST completed with status {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Error in _post method: {str(e)}", exc_info=True)
            raise
            
    async def _get_template_content(self, template_id: str) -> str:
        """
        Get the template content from Azure storage or other source.
        This is a placeholder - implement based on where templates are stored.
        """
        # TODO: Implement template retrieval from Azure storage or other source
        logger.warning("Template retrieval not implemented - using placeholder")
        return f"<html><body><h1>Template {template_id}</h1><p>This is a placeholder template.</p></body></html>"