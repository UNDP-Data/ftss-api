"""
Entity (model) definitions for user group objects.
"""

from typing import Dict, List, TYPE_CHECKING, Any
from pydantic import ConfigDict, Field

from .base import BaseEntity
from .user import User

# Import only for type checking to avoid circular imports
if TYPE_CHECKING:
    from .signal import Signal

__all__ = ["UserGroup", "UserGroupWithSignals", "UserGroupWithUsers", "UserGroupComplete"]


class UserGroup(BaseEntity):
    """The user group entity model used in the database and API endpoints."""

    name: str = Field(
        description="Name of the user group.",
        min_length=3,
    )
    signal_ids: List[int] = Field(
        default_factory=list,
        description="List of signal IDs associated with this group."
    )
    user_ids: List[str | int] = Field(
        default_factory=list,
        description="List of user IDs (integers) or emails (strings) who are members of this group."
    )
    admin_ids: List[int] = Field(
        default_factory=list,
        description="List of user IDs who have admin privileges for this group."
    )
    collaborator_map: Dict[str, List[int]] = Field(
        default_factory=dict,
        description="Map of signal IDs to lists of user IDs that can collaborate on that signal."
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "CDO",
                "signal_ids": [1, 2, 3],
                "user_ids": [1, 2, 3],
                "admin_ids": [1],
                "collaborator_map": {
                    "1": [1, 2],
                    "2": [1, 3],
                    "3": [2, 3]
                }
            }
        }
    )


class UserGroupWithSignals(UserGroup):
    """User group with associated signals data."""
    
    signals: List[Any] = Field(
        default_factory=list,
        description="List of signals associated with this group."
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "CDO",
                "signal_ids": [1, 2, 3],
                "user_ids": [1, 2, 3],
                "collaborator_map": {
                    "1": [1, 2],
                    "2": [1, 3],
                    "3": [2, 3]
                },
                "signals": [
                    {
                        "id": 1,
                        "headline": "Signal 1",
                        "can_edit": True
                    }
                ]
            }
        }
    )


class UserGroupWithUsers(UserGroup):
    """User group with associated users data."""
    
    users: List[User] = Field(
        default_factory=list,
        description="List of users who are members of this group."
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "CDO",
                "signal_ids": [1, 2, 3],
                "user_ids": [1, 2, 3],
                "collaborator_map": {
                    "1": [1, 2],
                    "2": [1, 3],
                    "3": [2, 3]
                },
                "users": [
                    {
                        "id": 1,
                        "email": "john.doe@undp.org",
                        "role": "Curator",
                        "name": "John Doe"
                    }
                ]
            }
        }
    )


class UserGroupComplete(UserGroup):
    """User group with both associated signals and users data."""
    
    signals: List[Any] = Field(
        default_factory=list,
        description="List of signals associated with this group."
    )
    
    users: List[User] = Field(
        default_factory=list,
        description="List of users who are members of this group."
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "CDO",
                "signal_ids": [1, 2, 3],
                "user_ids": [1, 2, 3],
                "collaborator_map": {
                    "1": [1, 2],
                    "2": [1, 3],
                    "3": [2, 3]
                },
                "signals": [
                    {
                        "id": 1,
                        "headline": "Signal 1",
                        "can_edit": True
                    }
                ],
                "users": [
                    {
                        "id": 1,
                        "email": "john.doe@undp.org",
                        "role": "Curator",
                        "name": "John Doe"
                    }
                ]
            }
        }
    )
