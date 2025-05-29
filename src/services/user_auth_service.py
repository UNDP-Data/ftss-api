"""
Microsoft Graph implementation using user authentication.
This leverages the existing Azure CLI authentication.
"""

import logging
import os
import json
import asyncio
import subprocess
from typing import Any, Dict, List

import httpx

from .email_service import EmailServiceBase

logger = logging.getLogger(__name__)

class UserAuthEmailService(EmailServiceBase):
    """Service class for handling email operations using Microsoft Graph API with user auth"""
    
    def __init__(self):
        try:
            self.from_email = os.getenv('MS_FROM_EMAIL')
            if not self.from_email:
                logger.error("MS_FROM_EMAIL environment variable is not set")
                raise ValueError("Microsoft sender email is required")
            
            self.user_email = os.getenv('USER_EMAIL')
            if not self.user_email:
                logger.error("USER_EMAIL environment variable is not set")
                raise ValueError("User email is required")
                
            # Token cache
            self.token = None
            self.token_expires = 0
                
            logger.info("UserAuthEmailService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize UserAuthEmailService: {str(e)}")
            raise

    async def _get_token(self) -> str:
        """Get an access token using az cli"""
        current_time = asyncio.get_event_loop().time()
        
        # If we have a valid token that won't expire in the next 5 minutes, use it
        if self.token and current_time < (self.token_expires - 300):
            return self.token
            
        try:
            # Get token using az cli command
            cmd = [
                "az", "account", "get-access-token", 
                "--resource", "https://graph.microsoft.com"
            ]
            
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            token_info = json.loads(result.stdout)
            
            # Extract token and expiration
            self.token = token_info["accessToken"]
            
            # Calculate token expiration time (timestamp from Azure CLI is already in seconds)
            self.token_expires = token_info["expiresOn"]
            
            logger.info(f"Successfully got access token using Azure CLI. Expires: {self.token_expires}")
            return self.token
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing Azure CLI command: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Error getting token: {str(e)}")
            raise

    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        content: str,
        content_type: str = "text/plain",
        useUserAccessToken: bool = False
    ) -> bool:
        # useUserAccessToken is ignored here, always uses user token
        try:
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
            
            # Get token
            token = await self._get_token()
            
            # Send the email using Microsoft Graph API
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Use the /me/sendMail endpoint to send from the authenticated user
            url = "https://graph.microsoft.com/v1.0/me/sendMail"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=message, headers=headers)
            
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
        # useUserAccessToken is ignored here, always uses user token
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
            return await self.send_email(
                to_emails=[to_email],
                subject=subject,
                content=template_content,
                content_type="text/html"
            )
            
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