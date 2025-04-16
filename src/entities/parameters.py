"""
Dataclasses used to define query parameters in API endpoints.
"""

from typing import Literal

from pydantic import BaseModel, Field, computed_field

from .utils import Goal, Horizon, Rating, Role, Score, Signature, Status, Steep

__all__ = [
    "Pagination",
    "SignalFilters",
    "TrendFilters",
    "UserFilters",
]


class Pagination(BaseModel):
    """A container class for pagination parameters."""

    page: int = Field(default=1, gt=0)
    per_page: int = Field(default=10, gt=0, le=10_000)
    order_by: str = Field(default="created_at")
    direction: Literal["desc", "asc"] = Field(
        default="desc",
        description="Ascending or descending order.",
    )

    @computed_field
    def limit(self) -> int:
        """
        An alias for `per_page` can be dropped in favour of
        limit: int = Field(default=10, gt=0, le=10_000, alias="per_page")
        once https://github.com/fastapi/fastapi/discussions/12401 is resolved.

        Returns
        -------
        int
            A value of `per_page`.
        """
        return self.per_page

    @computed_field
    def offset(self) -> int:
        """An offset value that can be used in a database query."""
        return self.limit * (self.page - 1)


class BaseFilters(Pagination):
    """Base filtering parameters shared by signal and trend filters."""

    ids: list[int] | None = Field(default=None)
    statuses: list[Status] = Field(default=(Status.APPROVED,))
    created_by: str | None = Field(default=None)
    created_for: str | None = Field(default=None)
    steep_primary: Steep | None = Field(default=None)
    steep_secondary: list[Steep] | None = Field(default=None)
    signature_primary: Signature | None = Field(default=None)
    signature_secondary: list[Signature] | None = Field(default=None)
    sdgs: list[Goal] | None = Field(default=None)
    query: str | None = Field(default=None)


class SignalFilters(BaseFilters):
    """Filter parameters for searching signals."""

    location: str | None = Field(default=None)
    bureau: str | None = Field(default=None)
    score: Score | None = Field(default=None)
    unit: str | None = Field(default=None)


class TrendFilters(BaseFilters):
    """Filter parameters for searching trends."""

    assigned_to: str | None = Field(default=None)
    time_horizon: Horizon | None = Field(default=None)
    impact_rating: Rating | None = Field(default=None)


class UserFilters(Pagination):
    """Filter parameters for searching users."""

    roles: list[Role] = Field(default=(Role.VISITOR, Role.CURATOR, Role.ADMIN))
    query: str | None = Field(default=None)

class UserGroupFilters(Pagination):
    """Filter parameters for searching user groups."""

    query: str | None = Field(default=None)
    