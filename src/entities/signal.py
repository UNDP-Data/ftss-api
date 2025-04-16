"""
Entity (model) definitions for signal objects.
"""

from pydantic import ConfigDict, Field

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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://undp.medium.com/the-cost-of-corruption-a827306696fb",
                "relevance": "Of the approximately US$13 trillion that governments spend on public spending, up to 25 percent is lost to corruption.",
                "keywords": ["economy", "governance"],
                "location": "Global",
                "favorite": False,
                "is_draft": True,
                "collaborators": ["john.doe@undp.org", "group:1"]
            }
        }
    )
