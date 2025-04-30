"""
A router for managing user groups.
"""

import logging
from typing import Annotated, List, Optional, Union

from fastapi import APIRouter, Depends, Path, Body, Query, HTTPException
from psycopg import AsyncCursor
from pydantic import BaseModel

from .. import database as db
from .. import exceptions
from ..dependencies import require_admin, require_user
from ..entities import UserGroup, User, UserGroupWithSignals
from ..authentication import authenticate_user

router = APIRouter(prefix="/user-groups", tags=["user groups"])


# Add models to support user emails in requests
class UserGroupCreate(BaseModel):
    name: str
    users: Optional[List[str]] = None


class UserEmailIdentifier(BaseModel):
    email: str


# Helper function to get user ID from email or ID
async def get_user_id(cursor: AsyncCursor, user_identifier: Union[str, int]) -> Optional[int]:
    """
    Get a user ID from either an email address or ID.
    
    Parameters
    ----------
    cursor : AsyncCursor
        Database cursor
    user_identifier : Union[str, int]
        Either a user email (string) or user ID (int)
        
    Returns
    -------
    Optional[int]
        User ID if found, None otherwise
    """
    if isinstance(user_identifier, int):
        # Check if user exists
        user = await db.read_user(cursor, user_identifier)
        return user.id if user else None
    else:
        # Try to find user by email
        user = await db.read_user_by_email(cursor, user_identifier)
        return user.id if user else None


@router.get("", response_model=List[UserGroup], dependencies=[Depends(require_admin)])
async def list_user_groups(
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """List all user groups."""
    groups = await db.list_user_groups(cursor)
    return groups


@router.get("/me", response_model=List[UserGroup])
async def get_my_user_groups(
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Get all user groups that the current user is a member of.
    This endpoint is accessible to all authenticated users.
    """
    if not user.id:
        raise exceptions.not_found
    
    # Get groups this user is a member of
    user_groups = await db.get_user_groups(cursor, user.id)
    return user_groups


@router.get("/me/with-signals", response_model=List[UserGroupWithSignals])
async def get_my_user_groups_with_signals(
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Get all user groups that the current user is a member of along with their signals data.
    
    This enhanced endpoint provides detailed information about each signal associated with the groups,
    including whether the current user has edit permissions for each signal. This is useful for:
    
    - Displaying a dashboard of all signals a user can access through their groups
    - Showing which signals the user can edit vs. view-only
    - Building collaborative workflows where users can see their assigned signals
    
    The response includes all signal details plus a `can_edit` flag for each signal indicating
    if the current user has edit permissions based on the group's collaborator_map.
    """
    if not user.id:
        raise exceptions.not_found
    
    # Get groups with signals for this user
    user_groups_with_signals = await db.get_user_groups_with_signals(cursor, user.id)
    return user_groups_with_signals


@router.post("", response_model=UserGroup, dependencies=[Depends(require_admin)])
async def create_user_group(
    group_data: UserGroupCreate,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Create a new user group."""
    # Create the base group
    group = UserGroup(name=group_data.name)
    
    # Handle email addresses if provided
    if group_data.users:
        user_ids = []
        for email in group_data.users:
            user = await db.read_user_by_email(cursor, email)
            if user and user.id:
                user_ids.append(user.id)
        
        if user_ids:
            group.user_ids = user_ids
    
    # Create the group
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


@router.post("/{group_id}/users", response_model=bool, dependencies=[Depends(require_admin)])
async def add_user_to_group_by_email(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    user_data: UserEmailIdentifier,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Add a user to a group by email address."""
    # Find user ID from email
    user = await db.read_user_by_email(cursor, user_data.email)
    if not user or not user.id:
        raise HTTPException(status_code=404, detail=f"User with email {user_data.email} not found")
    
    # Add user to group
    if not await db.add_user_to_group(cursor, group_id, user.id):
        raise exceptions.not_found
    
    return True


@router.post("/{group_id}/users/{user_id_or_email}", response_model=bool, dependencies=[Depends(require_admin)])
async def add_user_to_group(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    user_id_or_email: Annotated[str, Path(description="The ID or email of the user to add")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Add a user to a group.
    
    This endpoint accepts either a numeric user ID or an email address.
    If an email is provided, the system will look up the corresponding user ID.
    """
    # Try to parse as int for backward compatibility
    try:
        user_id = int(user_id_or_email)
    except ValueError:
        # Not an integer, treat as email
        user = await db.read_user_by_email(cursor, user_id_or_email)
        if not user or not user.id:
            raise HTTPException(status_code=404, detail=f"User with email {user_id_or_email} not found")
        user_id = user.id
    
    # Add user to group
    if not await db.add_user_to_group(cursor, group_id, user_id):
        raise exceptions.not_found
    
    return True


@router.delete("/{group_id}/users/{user_id_or_email}", response_model=bool, dependencies=[Depends(require_admin)])
async def remove_user_from_group(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    user_id_or_email: Annotated[str, Path(description="The ID or email of the user to remove")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Remove a user from a group.
    
    This endpoint accepts either a numeric user ID or an email address.
    If an email is provided, the system will look up the corresponding user ID.
    """
    # Try to parse as int for backward compatibility
    try:
        user_id = int(user_id_or_email)
    except ValueError:
        # Not an integer, treat as email
        user = await db.read_user_by_email(cursor, user_id_or_email)
        if not user or not user.id:
            raise HTTPException(status_code=404, detail=f"User with email {user_id_or_email} not found")
        user_id = user.id
    
    # Remove user from group
    if not await db.remove_user_from_group(cursor, group_id, user_id):
        raise exceptions.not_found
    
    return True


@router.post("/{group_id}/signals/{signal_id}", response_model=bool, dependencies=[Depends(require_admin)])
async def add_signal_to_group(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    signal_id: Annotated[int, Path(description="The ID of the signal to add")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Add a signal to a group."""
    # Get the group
    group = await db.read_user_group(cursor, group_id)
    if group is None:
        raise exceptions.not_found
    
    # Check if signal exists
    if await db.read_signal(cursor, signal_id) is None:
        raise exceptions.not_found
    
    # Add signal to group
    signal_ids = group.signal_ids or []
    if signal_id not in signal_ids:
        signal_ids.append(signal_id)
        group.signal_ids = signal_ids
        
        if await db.update_user_group(cursor, group) is None:
            raise exceptions.not_found
    
    return True


@router.delete("/{group_id}/signals/{signal_id}", response_model=bool, dependencies=[Depends(require_admin)])
async def remove_signal_from_group(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    signal_id: Annotated[int, Path(description="The ID of the signal to remove")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Remove a signal from a group."""
    # Get the group
    group = await db.read_user_group(cursor, group_id)
    if group is None:
        raise exceptions.not_found
    
    # Remove signal from group
    signal_ids = group.signal_ids or []
    if signal_id in signal_ids:
        signal_ids.remove(signal_id)
        group.signal_ids = signal_ids
        
        # Also remove collaborators for this signal
        collaborator_map = group.collaborator_map or {}
        signal_key = str(signal_id)
        if signal_key in collaborator_map:
            del collaborator_map[signal_key]
            group.collaborator_map = collaborator_map
        
        if await db.update_user_group(cursor, group) is None:
            raise exceptions.not_found
    
    return True


@router.post("/{group_id}/signals/{signal_id}/collaborators", response_model=bool, dependencies=[Depends(require_admin)])
async def add_collaborator_to_signal_by_email(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    signal_id: Annotated[int, Path(description="The ID of the signal")],
    user_data: UserEmailIdentifier,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Add a user as a collaborator for a specific signal in a group by email address."""
    # Find user ID from email
    user = await db.read_user_by_email(cursor, user_data.email)
    if not user or not user.id:
        raise HTTPException(status_code=404, detail=f"User with email {user_data.email} not found")
    
    # Get the group
    group = await db.read_user_group(cursor, group_id)
    if group is None:
        raise exceptions.not_found
    
    # Check if signal is in the group
    signal_ids = group.signal_ids or []
    if signal_id not in signal_ids:
        raise exceptions.not_found
    
    # Check if user is in the group
    user_ids = group.user_ids or []
    if user.id not in user_ids:
        raise exceptions.not_found
    
    # Add collaborator
    collaborator_map = group.collaborator_map or {}
    signal_key = str(signal_id)
    if signal_key not in collaborator_map:
        collaborator_map[signal_key] = []
    
    if user.id not in collaborator_map[signal_key]:
        collaborator_map[signal_key].append(user.id)
        group.collaborator_map = collaborator_map
        
        if await db.update_user_group(cursor, group) is None:
            raise exceptions.not_found
    
    return True


@router.post("/{group_id}/signals/{signal_id}/collaborators/{user_id_or_email}", response_model=bool, dependencies=[Depends(require_admin)])
async def add_collaborator_to_signal_in_group(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    signal_id: Annotated[int, Path(description="The ID of the signal")],
    user_id_or_email: Annotated[str, Path(description="The ID or email of the user to add as collaborator")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Add a user as a collaborator for a specific signal in a group.
    
    This endpoint accepts either a numeric user ID or an email address.
    If an email is provided, the system will look up the corresponding user ID.
    """
    # Try to parse as int for backward compatibility
    try:
        user_id = int(user_id_or_email)
    except ValueError:
        # Not an integer, treat as email
        user = await db.read_user_by_email(cursor, user_id_or_email)
        if not user or not user.id:
            raise HTTPException(status_code=404, detail=f"User with email {user_id_or_email} not found")
        user_id = user.id
    
    # Get the group
    group = await db.read_user_group(cursor, group_id)
    if group is None:
        raise exceptions.not_found
    
    # Check if signal is in the group
    signal_ids = group.signal_ids or []
    if signal_id not in signal_ids:
        raise exceptions.not_found
    
    # Check if user is in the group
    user_ids = group.user_ids or []
    if user_id not in user_ids:
        raise exceptions.not_found
    
    # Add collaborator
    collaborator_map = group.collaborator_map or {}
    signal_key = str(signal_id)
    if signal_key not in collaborator_map:
        collaborator_map[signal_key] = []
    
    if user_id not in collaborator_map[signal_key]:
        collaborator_map[signal_key].append(user_id)
        group.collaborator_map = collaborator_map
        
        if await db.update_user_group(cursor, group) is None:
            raise exceptions.not_found
    
    return True


@router.delete("/{group_id}/signals/{signal_id}/collaborators/{user_id_or_email}", response_model=bool, dependencies=[Depends(require_admin)])
async def remove_collaborator_from_signal_in_group(
    group_id: Annotated[int, Path(description="The ID of the user group")],
    signal_id: Annotated[int, Path(description="The ID of the signal")],
    user_id_or_email: Annotated[str, Path(description="The ID or email of the user to remove as collaborator")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Remove a user as a collaborator for a specific signal in a group.
    
    This endpoint accepts either a numeric user ID or an email address.
    If an email is provided, the system will look up the corresponding user ID.
    """
    # Try to parse as int for backward compatibility
    try:
        user_id = int(user_id_or_email)
    except ValueError:
        # Not an integer, treat as email
        user = await db.read_user_by_email(cursor, user_id_or_email)
        if not user or not user.id:
            raise HTTPException(status_code=404, detail=f"User with email {user_id_or_email} not found")
        user_id = user.id
    
    # Get the group
    group = await db.read_user_group(cursor, group_id)
    if group is None:
        raise exceptions.not_found
    
    # Check if this collaborator assignment exists
    collaborator_map = group.collaborator_map or {}
    signal_key = str(signal_id)
    if signal_key in collaborator_map and user_id in collaborator_map[signal_key]:
        collaborator_map[signal_key].remove(user_id)
        
        # If no collaborators left for this signal, remove the entry
        if not collaborator_map[signal_key]:
            del collaborator_map[signal_key]
        
        group.collaborator_map = collaborator_map
        
        if await db.update_user_group(cursor, group) is None:
            raise exceptions.not_found
    
    return True 