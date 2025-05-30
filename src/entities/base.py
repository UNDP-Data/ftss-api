"""
Entity (model) definitions for base objects that others inherit from.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from . import utils

__all__ = ["BaseMetadata", "BaseEntity", "timestamp"]


def timestamp() -> str:
    """
    Get the current timestamp in the ISO format.

    Returns
    -------
    str
        A timestamp in the ISO format.
    """
    return datetime.now(UTC).isoformat()


class BaseMetadata(BaseModel):
    """Base metadata for database objects."""

    id: int = Field(default=1)
    created_at: str = Field(default_factory=timestamp)

    @field_validator("created_at", mode="before")
    @classmethod
    def format_created_at(cls, value):
        """(De)serialisation function for `created_at` timestamp."""
        if value is None:
            return timestamp()  # Use default timestamp if None
        if isinstance(value, str):
            return value
        return value.isoformat()


class BaseEntity(BaseMetadata):
    """Base entity for signals and trends."""

    status: utils.Status = Field(
        default=utils.Status.NEW,
        description="Current signal review status.",
    )
    created_by: EmailStr | None = Field(default=None)
    created_for: str | None = Field(default=None)
    modified_at: str = Field(default_factory=timestamp)
    modified_by: EmailStr | None = Field(default=None)
    headline: str | None = Field(
        default=None,
        description="A clear and concise title headline.",
    )
    description: str | None = Field(
        default=None,
        description="A clear and concise description.",
    )
    attachment: str | None = Field(
        default=None,
        description="An optional base64-encoded image/URL for illustration.",
    )
    steep_primary: utils.Steep | None = Field(
        default=None,
        description="Primary category in terms of STEEP+V analysis methodology.",
    )
    steep_secondary: list[utils.Steep] | None = Field(
        default=None,
        description="Secondary categories in terms of STEEP+V analysis methodology.",
    )
    signature_primary: utils.Signature | None = Field(
        default=None,
        description="Primary category in terms of UNDP Signature Solutions methodology.",
    )
    signature_secondary: list[utils.Signature] | None = Field(
        default=None,
        description="Secondary categories in terms of UNDP Signature Solutions methodology.",
    )
    sdgs: list[utils.Goal] | None = Field(
        default=None,
        description="Relevant Sustainable Development Goals.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "headline": "The cost of corruption",
                "description": "Corruption is one of the scourges of modern life. Its costs are staggering.",
                "steep_primary": utils.Steep.ECONOMIC,
                "steep_secondary": [utils.Steep.SOCIAL],
                "signature_primary": utils.Signature.GOVERNANCE,
                "signature_secondary": [
                    utils.Signature.POVERTY,
                    utils.Signature.RESILIENCE,
                ],
                "sdgs": [utils.Goal.G16, utils.Goal.G17],
            }
        }
    )

    @field_validator("modified_at", mode="before")
    @classmethod
    def format_modified_at(cls, value):
        """(De)serialisation function for `modified_at` timestamp."""
        if value is None:
            return timestamp()  # Use default timestamp if None
        if isinstance(value, str):
            return value
        return value.isoformat()

    def anonymise(self) -> "BaseEntity":
        """
        Anonymise an entity by removing personal information, such as user emails.

        This function is to be used to retrieve information for visitors, i.e.,
        not authenticated users, to preserve privacy of other users.
        """
        email_mask = "email.hidden@undp.org"
        self.created_by = email_mask
        self.modified_by = email_mask
        return self
