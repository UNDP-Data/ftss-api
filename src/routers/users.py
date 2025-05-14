"""
A router for creating, reading and updating trends.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from psycopg import AsyncCursor

from .. import database as db
from .. import exceptions
from ..authentication import authenticate_user
from ..dependencies import require_admin, require_user
from ..entities import Role, User, UserFilters, UserPage

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search", response_model=UserPage, dependencies=[Depends(require_admin)])
async def search_users(
    filters: Annotated[UserFilters, Query()],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Search users in the database using pagination and filters."""
    page = await db.search_users(cursor, filters)
    return page


@router.get("/me", response_model=User)
async def read_current_user(user: User = Depends(authenticate_user)):
    """Read the current user information from a JTW token."""
    logging.debug(f"User: {user}")
    if user is None:
        raise exceptions.not_found
    return user


@router.get("/{uid}", response_model=User, dependencies=[Depends(require_admin)])
async def read_user(
    uid: Annotated[int, Path(description="The ID of the user to retrieve")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Read users form the database using IDs."""
    if (users := await db.read_user(cursor, uid)) is None:
        raise exceptions.not_found
    return users


@router.put("/{uid}", response_model=User)
async def update_user(
    uid: Annotated[int, Path(description="The ID of the user to be updated")],
    user_new: User,
    user: User = Depends(require_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Update a user in the database. Non-admin users can only update
    their own name, unit and accelerator lab flag. Only admin users can
    update other users' roles.
    """
    if uid != user_new.id:
        raise exceptions.id_mismatch
    if user.role == Role.ADMIN:
        pass
    elif user.email != user_new.email or user.id != user_new.id:
        raise exceptions.permission_denied
    elif user.role != user_new.role:
        raise exceptions.permission_denied
    if (user_id := await db.update_user(cursor, user_new)) is None:
        raise exceptions.not_found
    return await db.read_user(cursor, user_id)
