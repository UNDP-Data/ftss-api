"""
Direct authentication approach for Graph API using user credentials.
This is a simplified version for testing purposes.
"""

import os
import httpx
import logging
import asyncio
import json
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class GraphDirectAuth:
    """Direct authentication for Graph API using user credentials"""
    
    def __init__(self):
        self.token = None
        self.token_expires = 0
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Missing required environment variables for Graph authentication")
            
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.graph_url = "https://graph.microsoft.com/v1.0"
        
    async def ensure_token(self) -> str:
        """Ensure we have a valid token, refreshing if necessary"""
        current_time = asyncio.get_event_loop().time()
        
        # If token is expired or will expire in the next 5 minutes, refresh it
        if not self.token or current_time > (self.token_expires - 300):
            await self.refresh_token()
            
        return self.token
        
    async def refresh_token(self) -> None:
        """Get a new access token using client credentials flow"""
        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.token_url, data=data, headers=headers)
                
            if response.status_code != 200:
                logger.error(f"Failed to get token: {response.status_code}, {response.text}")
                raise Exception(f"Failed to get token: {response.status_code}")
                
            token_data = response.json()
            self.token = token_data['access_token']
            
            # Calculate token expiration time (convert expires_in from seconds to epoch time)
            current_time = asyncio.get_event_loop().time()
            self.token_expires = current_time + token_data['expires_in']
            
            logger.info(f"Token refreshed, expires in {token_data['expires_in']} seconds")
            
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise
            
    async def send_email(self, from_email: str, to_emails: List[str], subject: str, 
                        content: str, content_type: str = "HTML") -> bool:
        """Send an email using Graph API"""
        try:
            token = await self.ensure_token()
            
            # Prepare the email message
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": content_type,
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
                            "address": from_email
                        }
                    }
                },
                "saveToSentItems": "true"
            }
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Use /users/{from_email} instead of /me to send as that user
            endpoint = f"{self.graph_url}/users/{from_email}/sendMail"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=message, headers=headers)
                
            if response.status_code in [200, 201, 202, 204]:
                logger.info(f"Email sent successfully: {response.status_code}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False