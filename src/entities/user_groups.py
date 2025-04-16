"""
Entity (model) definitions for user group objects.
"""

from pydantic import ConfigDict, Field

from .base import BaseEntity
from .user import User

__all__ = ["UserGroup"]


class UserGroup(BaseEntity):
    """The user group entity model used in the database and API endpoints."""

    name: str = Field(
        description="Name of the user group.",
        min_length=3,
    )
    users: list[str] = Field(
        default_factory=list,
        description="List of user emails who are members of this group.",
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "CDO",
                "users": ["john.doe@undp.org", "jane.smith@undp.org"],
            }
        }
    )
