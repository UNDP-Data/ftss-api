"""
Base email service interface.
"""

import abc
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class EmailServiceBase(abc.ABC):
    """Abstract base class for email services"""
    
    @abc.abstractmethod
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        content: str,
        content_type: str = "text/plain"
    ) -> bool:
        """Send an email to multiple recipients"""
        pass

    @abc.abstractmethod
    async def send_notification_email(
        self,
        to_email: str,
        subject: str,
        template_id: str,
        dynamic_data: Dict[str, Any]
    ) -> bool:
        """Send a templated notification email"""
        pass 