"""
Factory for creating email service instances.
"""

import os
import logging
from typing import Optional

from .email_service import EmailServiceBase
from .msgraph_service import MSGraphEmailService
from .sendgrid_service import SendGridEmailService

logger = logging.getLogger(__name__)

# Email service types
MS_GRAPH = "ms_graph"
SENDGRID = "sendgrid"

# Default to MS Graph with Mail.Send permission
DEFAULT_EMAIL_SERVICE = MS_GRAPH

def create_email_service() -> EmailServiceBase:
    """
    Factory function to create an email service instance based on configuration.
    
    Returns:
        EmailServiceBase: An instance of the configured email service.
    """
    service_type = os.getenv("EMAIL_SERVICE_TYPE", DEFAULT_EMAIL_SERVICE).lower()
    
    logger.info(f"Creating email service of type: {service_type}")
    
    if service_type == MS_GRAPH:
        return MSGraphEmailService()
    elif service_type == SENDGRID:
        return SendGridEmailService()
    else:
        logger.warning(f"Unknown email service type: {service_type}. Defaulting to {DEFAULT_EMAIL_SERVICE}")
        return MSGraphEmailService() 