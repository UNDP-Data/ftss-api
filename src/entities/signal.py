"""
Entity (model) definitions for signal objects.
"""

from pydantic import ConfigDict, Field, field_validator, model_validator

from . import utils
from .base import BaseEntity

__all__ = ["Signal"]


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
    collaborators: list[str] | None = Field(
        default=None,
        description="List of user emails or group IDs that have editing access to this signal.",
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
                "collaborators": ["john.doe@undp.org", "group:1"]
                "secondary_location": ["Africa", "Asia"],
                "score": None,
                "connected_trends": [101, 102],
            }
        }
    )
