"""
A router for managing user groups.
"""

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, Path, Body
from psycopg import AsyncCursor

from .. import database as db
from .. import exceptions
from ..dependencies import require_admin
from ..entities import UserGroup

router = APIRouter(prefix="/user-groups", tags=["user groups"])


@router.get("", response_model=List[UserGroup], dependencies=[Depends(require_admin)])
async def list_user_groups(
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """List all user groups."""
    groups = await db.list_user_groups(cursor)
    return groups


@router.post("", response_model=UserGroup, dependencies=[Depends(require_admin)])
async def create_user_group(
    group: UserGroup,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Create a new user group."""
    group_id = await db.create_user_group(cursor, group)
    return await db.read_user_group(cursor, group_id)


@router.get("/{group_id}", response_model=UserGroup, dependencies=[Depends(require_admin)])
async def read_user_group(
    group_id: Annotated[int, Path(description="The ID of the user group to retrieve")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Get a user group by ID."""
    if (group := await db.read_user_group(cursor, group_id)) is None:
        raise exceptions.not_found
    return group


@router.put("/{group_id}", response_model=UserGroup, dependencies=[Depends(require_admin)])
async def update_user_group(
    group_id: Annotated[int, Path(description="The ID of the user group to update")],
    group: UserGroup,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Update a user group."""
    if group_id != group.id:
        raise exceptions.id_mismatch
    if (updated_id := await db.update_user_group(cursor, group)) is None:
        raise exceptions.not_found
    return await db.read_user_group(cursor, updated_id)


@router.delete("/{group_id}", response_model=bool, dependencies=[Depends(require_admin)])
async def delete_user_group(
    group_id: Annotated[int, Path(description="The ID of the user group to delete")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Delete a user group."""
    if not await db.delete_user_group(cursor, group_id):
        raise exceptions.not_found
    return True


@router.post("/{group_id}/users/{email}", response_model=bool, dependencies=[Depends(require_admin)])
async def add_user_to_group(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    email: Annotated[str, Path(description="The email of the user to add")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Add a user to a group."""
    if not await db.add_user_to_group(cursor, group_id, email):
        raise exceptions.not_found
    return True


@router.delete("/{group_id}/users/{email}", response_model=bool, dependencies=[Depends(require_admin)])
async def remove_user_from_group(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    email: Annotated[str, Path(description="The email of the user to remove")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Remove a user from a group."""
    if not await db.remove_user_from_group(cursor, group_id, email):
        raise exceptions.not_found
    return True 