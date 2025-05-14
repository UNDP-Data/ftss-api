"""
Entity (model) definitions for signal objects.
"""

from typing import List, Dict, TYPE_CHECKING, Any, Optional
from pydantic import ConfigDict, Field, field_validator, model_validator

from . import utils
from .base import BaseEntity

# Import only for type checking to avoid circular imports
if TYPE_CHECKING:
    from .user_groups import UserGroup

__all__ = ["Signal", "SignalWithUserGroups", "SignalCreate", "SignalUpdate"]


class Signal(BaseEntity):
    """The signal entity model used in the database and API endpoints."""

    created_unit: str | None = Field(default=None)
    url: str | None = Field(default=None)
    relevance: str | None = Field(default=None)
    keywords: list[str] | None = Field(
        default=None,
        description="Use up to 3 clear, simple keywords for ease of searchability.",
    )
    location: str | None = Field(
        default=None,
        description="Region and/or country for which this signal has greatest relevance.",
    )
    secondary_location: list[str] | None = Field(
        default=None,
        description="Additional regions and/or countries for which this signal has relevance.",
    )
    score: utils.Score | None = Field(default=None)
    connected_trends: list[int] | None = Field(
        default=None,
        description="IDs of trends connected to this signal.",
    )
    favorite: bool = Field(
        default=False,
        description="Whether the current user has favorited this signal.",
    )
    is_draft: bool = Field(
        default=True,
        description="Whether the signal is in draft state or published.",
    )
    group_ids: List[int] | None = Field(
        default=None,
        description="List of user group IDs associated with this signal.",
    )
    collaborators: List[int] | None = Field(
        default=None,
        description="List of user IDs who can collaborate on this signal.",
    )

    @model_validator(mode='before')
    @classmethod
    def convert_secondary_location(cls, data):
        """Convert string secondary_location to a list before validation."""
        if isinstance(data, dict) and 'secondary_location' in data:
            if isinstance(data['secondary_location'], str):
                data['secondary_location'] = [data['secondary_location']]
        return data

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "created_unit": "HQ",
                "url": "https://undp.medium.com/the-cost-of-corruption-a827306696fb",
                "relevance": "Of the approximately US$13 trillion that governments spend on public spending, up to 25 percent is lost to corruption.",
                "keywords": ["economy", "governance"],
                "location": "Global",
                "favorite": False,
                "is_draft": True,
                "group_ids": [1, 2],
                "collaborators": [1, 2, 3],
                "secondary_location": ["Africa", "Asia"],
                "score": None,
                "connected_trends": [101, 102],
            }
        }
    )


class SignalWithUserGroups(Signal):
    """
    Extended signal entity that includes the user groups it belongs to.
    This model is used in API responses to provide a signal with its associated user groups.
    """
    
    user_groups: List[Any] = Field(
        default_factory=list,
        description="List of user groups this signal belongs to."
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "created_unit": "HQ",
                "url": "https://undp.medium.com/the-cost-of-corruption-a827306696fb",
                "relevance": "Of the approximately US$13 trillion that governments spend on public spending, up to 25 percent is lost to corruption.",
                "keywords": ["economy", "governance"],
                "location": "Global",
                "favorite": False,
                "is_draft": True,
                "group_ids": [1, 2],
                "collaborators": [1, 2, 3],
                "secondary_location": ["Africa", "Asia"],
                "score": None,
                "connected_trends": [101, 102],
                "user_groups": [
                    {
                        "id": 1,
                        "name": "Research Team",
                        "signal_ids": [1, 2, 3],
                        "user_ids": [101, 102],
                        "admin_ids": [101],
                        "collaborator_map": {"1": [101, 102]}
                    },
                    {
                        "id": 2,
                        "name": "Policy Team",
                        "signal_ids": [1, 4, 5],
                        "user_ids": [103, 104],
                        "admin_ids": [103],
                        "collaborator_map": {"1": [103]}
                    }
                ]
            }
        }
    )


class SignalCreate(Signal):
    """
    Model for signal creation request that includes user_group_ids.
    This is used for the request body in the POST endpoint.
    """
    
    user_group_ids: Optional[List[int]] = Field(
        default=None,
        description="IDs of user groups to add the signal to after creation"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "headline": "New Signal Example",
                "description": "This is a new signal with user groups.",
                "steep_primary": "T",
                "steep_secondary": ["S", "P"],
                "signature_primary": "Shift",
                "signature_secondary": ["Risk"],
                "keywords": ["example", "test"],
                "location": "Global",
                "user_group_ids": [1, 2]
            }
        }
    )


class SignalUpdate(Signal):
    """
    Model for signal update request that includes user_group_ids.
    This is used for the request body in the PUT endpoint.
    """
    
    user_group_ids: Optional[List[int]] = Field(
        default=None,
        description="IDs of user groups to replace the signal's current group associations"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "headline": "Updated Signal Example",
                "description": "This is an updated signal with new user groups.",
                "steep_primary": "T",
                "steep_secondary": ["S", "P"],
                "signature_primary": "Shift",
                "signature_secondary": ["Risk"],
                "keywords": ["updated", "test"],
                "location": "Global",
                "user_group_ids": [2, 3]
            }
        }
    )
