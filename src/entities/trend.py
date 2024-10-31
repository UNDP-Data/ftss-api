"""
Entity (model) definitions for trend objects.
"""

from pydantic import ConfigDict, Field, field_validator

from . import utils
from .base import BaseEntity

__all__ = ["Trend"]


class Trend(BaseEntity):
    """The trend entity model used in the database and API endpoints."""

    assigned_to: str | None = Field(default=None)
    time_horizon: utils.Horizon | None = Field(default=None)
    impact_rating: utils.Rating | None = Field(default=None)
    impact_description: str | None = Field(default=None)
    connected_signals: list[int] | None = Field(
        default=None,
        description="IDs of signals connected to this trend.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": BaseEntity.model_config["json_schema_extra"]["example"]
            | {
                "time_horizon": utils.Horizon.MEDIUM,
                "impact_rating": utils.Rating.HIGH,
                "impact_description": "Anywhere between 1.4 and 35 percent of climate action funds may be lost due to corruption.",
            }
        }
    )

    @field_validator("impact_rating", mode="before")
    @classmethod
    def from_string(cls, value):
        """
        Coerce an integer string for `impact_rating` to a string
        """
        if value is None or isinstance(value, str):
            return value
        return str(value)
