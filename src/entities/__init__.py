"""
Entities (models) for receiving, managing and sending data.
"""

from math import ceil
from typing import Self

from pydantic import BaseModel, Field

from .parameters import *
from .signal import *
from .trend import *
from .user import *
from .user_groups import *
from .utils import *


class Page(BaseModel):
    """
    A paginated results model, holding pagination metadata and search results.
    """

    per_page: int = Field(description="Number of entities per page to retrieve.")
    current_page: int = Field(
        description="Current page for which entities should be retrieved."
    )
    total_pages: int = Field(description="Total number of pages for pagination.")
    total_count: int = Field(description="Total number of entities in the database.")
    data: list[Signal] | list[Trend] | list[User]

    @classmethod
    def from_search(cls, rows: list[dict], pagination: Pagination) -> Self:
        """
        Create paginated results model from search results.

        Parameters
        ----------
        rows : list[dict]
            A list of results returned from the database.
        pagination : Pagination
            The pagination object used to retrieve the results.

        Returns
        -------
        page : Page
            The paginated results model.
        """
        total = rows[0]["total_count"] if rows else 0
        page = cls(
            per_page=pagination.limit,
            current_page=pagination.page,
            total_pages=ceil(total / pagination.limit),
            total_count=total,
            data=rows,
        )
        return page

    def sanitise(self, user: User) -> Self:
        """
        Remove items from the list the user has no permissions to access.

        Parameters
        ----------
        user : User
            A user making the request.

        Returns
        -------
        self : Self
            The paginated results model with sanitised data.
        """
        if user.role == Role.ADMIN:
            # all signals/trends are shown
            pass
        elif user.role == Role.CURATOR:
            # all signals/trends are shown except other users' drafts
            self.data = [
                entity
                for entity in self.data
                if not (
                    entity.status == Status.DRAFT and entity.created_by != user.email
                )
            ]
            return self
        elif user.role == Role.USER:
            # only approved signals/trends are shown or signals/trends authored by the user
            self.data = [
                entity
                for entity in self.data
                if entity.status == Status.APPROVED or entity.created_by == user.email
            ]
        else:
            # only approved signals/trends after anonymisation are shown
            self.data = [
                entity.anonymise()
                for entity in self.data
                if entity.status == Status.APPROVED
            ]
            return self
        return self


class UserPage(Page):
    """A specialised paginated results model for users."""

    data: list[User]


class SignalPage(Page):
    """A specialised paginated results model for signals."""

    data: list[Signal]


class TrendPage(Page):
    """A specialised paginated results model for trends."""

    data: list[Trend]
