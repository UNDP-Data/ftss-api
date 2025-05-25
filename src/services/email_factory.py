"""
Factory for creating email service instances.
"""

import os
import logging
from typing import Optional

from .email_service import EmailServiceBase
from .msgraph_service import MSGraphEmailService
from .sendgrid_service import SendGridEmailService
from .user_auth_service import UserAuthEmailService

logger = logging.getLogger(__name__)

# Email service types
MS_GRAPH = "ms_graph"
SENDGRID = "sendgrid"
USER_AUTH = "user_auth"

# Default to USER_AUTH with Azure CLI authentication
DEFAULT_EMAIL_SERVICE = USER_AUTH

def create_email_service(useUserAccessToken: bool = False) -> EmailServiceBase:
    """
    Factory function to create an email service instance based on configuration.
    Accepts useUserAccessToken to control delegated vs app auth.
    
    Returns:
        EmailServiceBase: An instance of the configured email service.
    """
    service_type = os.getenv("EMAIL_SERVICE_TYPE", DEFAULT_EMAIL_SERVICE).lower()
    
    logger.info(f"Creating email service of type: {service_type} (useUserAccessToken={useUserAccessToken})")
    
    if service_type == MS_GRAPH:
        return MSGraphEmailService(useUserAccessToken=useUserAccessToken)
    elif service_type == SENDGRID:
        return SendGridEmailService()
    elif service_type == USER_AUTH:
        return UserAuthEmailService()
    else:
        logger.warning(f"Unknown email service type: {service_type}. Defaulting to {DEFAULT_EMAIL_SERVICE}")
        return UserAuthEmailService() 