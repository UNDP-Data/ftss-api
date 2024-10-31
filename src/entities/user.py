"""
Entity (model) definitions for user objects.
"""

from pydantic import ConfigDict, EmailStr, Field

from .base import BaseMetadata
from .utils import Role

__all__ = ["User"]


class User(BaseMetadata):
    """The user entity model used in the database and API endpoints."""

    email: EmailStr = Field(description="Work email ending with @undp.org.")
    role: Role = Field(default=Role.VISITOR)
    name: str | None = Field(default=None, min_length=5, description="Full name.")
    unit: str | None = Field(
        default=None,
        min_length=2,
        description="UNDP unit name from a predefined list.",
    )
    acclab: bool | None = Field(
        default=None,
        description="Whether or not a user is part of the Accelerator Labs.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "john.doe@undp.org",
                "role": "Curator",
                "name": "John Doe",
                "unit": "BPPS",
                "acclab": True,
            }
        }
    )

    @property
    def is_admin(self):
        """Check if the user is an admin."""
        return self.role == Role.ADMIN

    @property
    def is_staff(self):
        """Check if the user is a curator or admin."""
        return self.role in {Role.ADMIN, Role.CURATOR}

    @property
    def is_regular(self):
        """Check if the user is a regular user, not a visitor using API key."""
        return self.role in {Role.ADMIN, Role.CURATOR, Role.USER}
