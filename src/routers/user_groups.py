"""
A router for managing user groups.
"""

import logging
import bugsnag
from typing import Annotated, List, Optional, Union

from fastapi import APIRouter, Depends, Path, Body, Query, HTTPException, Request
from psycopg import AsyncCursor
from pydantic import BaseModel

from .. import database as db
from .. import exceptions
from ..dependencies import require_admin, require_user
from ..entities import UserGroup, User, UserGroupWithSignals
from ..authentication import authenticate_user

# Set up logger for this module
logger = logging.getLogger(__name__)

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
    try:
        if isinstance(user_identifier, int):
            # Check if user exists
            user = await db.read_user(cursor, user_identifier)
            return user.id if user else None
        else:
            # Try to find user by email
            user = await db.read_user_by_email(cursor, user_identifier)
            return user.id if user else None
    except Exception as e:
        logger.error(f"Error in get_user_id: {str(e)}")
        bugsnag.notify(
            e,
            metadata={
                "user_identifier": str(user_identifier),
                "type": type(user_identifier).__name__
            }
        )
        return None


@router.get("", response_model=List[UserGroup], dependencies=[Depends(require_admin)])
async def list_user_groups(
    request: Request,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """List all user groups."""
    try:
        groups = await db.list_user_groups(cursor)
        logger.info(f"Listed {len(groups)} user groups")
        return groups
    except Exception as e:
        logger.error(f"Error listing user groups: {str(e)}")
        bugsnag.notify(
            e,
            metadata={
                "request": {
                    "url": str(request.url),
                    "method": request.method,
                }
            }
        )
        raise


@router.get("/me", response_model=List[UserGroup])
async def get_my_user_groups(
    request: Request,
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Get all user groups that the current user is a member of.
    This endpoint is accessible to all authenticated users.
    """
    try:
        if not user.id:
            logger.warning("User ID not found in get_my_user_groups")
            raise exceptions.not_found
        
        # Get groups this user is a member of
        user_groups = await db.get_user_groups(cursor, user.id)
        logger.info(f"User {user.id} retrieved {len(user_groups)} groups")
        return user_groups
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error in get_my_user_groups: {str(e)}")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "user": {
                        "id": user.id if user else None,
                        "email": user.email if user else None
                    }
                }
            )
        raise


@router.get("/me/with-signals", response_model=List[UserGroupWithSignals])
async def get_my_user_groups_with_signals(
    request: Request,
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
    try:
        if not user.id:
            logger.warning("User ID not found in get_my_user_groups_with_signals")
            raise exceptions.not_found
        
        # Get groups with signals for this user
        user_groups_with_signals = await db.get_user_groups_with_signals(cursor, user.id)
        logger.info(f"User {user.id} retrieved {len(user_groups_with_signals)} groups with signals")
        return user_groups_with_signals
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error in get_my_user_groups_with_signals: {str(e)}")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "user": {
                        "id": user.id if user else None,
                        "email": user.email if user else None
                    }
                }
            )
        raise


@router.post("", response_model=UserGroup, dependencies=[Depends(require_admin)])
async def create_user_group(
    request: Request,
    group_data: UserGroupCreate,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Create a new user group."""
    try:
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
        logger.info(f"Created user group {group_id} with name '{group.name}'")
        return await db.read_user_group(cursor, group_id)
    except Exception as e:
        logger.error(f"Error creating user group: {str(e)}")
        bugsnag.notify(
            e,
            metadata={
                "request": {
                    "url": str(request.url),
                    "method": request.method,
                },
                "group_data": {
                    "name": group_data.name,
                    "users_count": len(group_data.users) if group_data.users else 0
                }
            }
        )
        raise


@router.get("/{group_id}", response_model=UserGroup, dependencies=[Depends(require_admin)])
async def read_user_group(
    request: Request,
    group_id: Annotated[int, Path(description="The ID of the user group to retrieve")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Get a user group by ID."""
    try:
        if (group := await db.read_user_group(cursor, group_id)) is None:
            logger.warning(f"User group {group_id} not found")
            raise exceptions.not_found
        logger.info(f"Retrieved user group {group_id}")
        return group
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error reading user group {group_id}: {str(e)}")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "group_id": group_id
                }
            )
        raise


@router.put("/{group_id}", response_model=UserGroup, dependencies=[Depends(require_admin)])
async def update_user_group(
    request: Request,
    group_id: Annotated[int, Path(description="The ID of the user group to update")],
    group: UserGroup,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Update a user group."""
    try:
        if group_id != group.id:
            logger.warning(f"ID mismatch: path ID {group_id} != body ID {group.id}")
            raise exceptions.id_mismatch
        if (updated_id := await db.update_user_group(cursor, group)) is None:
            logger.warning(f"User group {group_id} not found for update")
            raise exceptions.not_found
        logger.info(f"Updated user group {updated_id}")
        return await db.read_user_group(cursor, updated_id)
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error updating user group {group_id}: {str(e)}")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "group_id": group_id,
                    "group_data": {
                        "id": group.id,
                        "name": group.name,
                        "user_count": len(group.user_ids) if group.user_ids else 0,
                        "signal_count": len(group.signal_ids) if group.signal_ids else 0
                    }
                }
            )
        raise


@router.delete("/{group_id}", response_model=bool, dependencies=[Depends(require_admin)])
async def delete_user_group(
    request: Request,
    group_id: Annotated[int, Path(description="The ID of the user group to delete")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Delete a user group."""
    try:
        if not await db.delete_user_group(cursor, group_id):
            logger.warning(f"User group {group_id} not found for deletion")
            raise exceptions.not_found
        logger.info(f"Deleted user group {group_id}")
        return True
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error deleting user group {group_id}: {str(e)}")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "group_id": group_id
                }
            )
        raise


@router.post("/{group_id}/users", response_model=bool, dependencies=[Depends(require_admin)])
async def add_user_to_group_by_email(
    request: Request,
    group_id: Annotated[int, Path(description="The ID of the user group")],
    user_data: UserEmailIdentifier,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Add a user to a group by email address."""
    try:
        # Find user ID from email
        user = await db.read_user_by_email(cursor, user_data.email)
        if not user or not user.id:
            logger.warning(f"User with email {user_data.email} not found")
            raise HTTPException(status_code=404, detail=f"User with email {user_data.email} not found")
        
        # Add user to group
        if not await db.add_user_to_group(cursor, group_id, user.id):
            logger.warning(f"Group {group_id} not found when adding user {user.id}")
            raise exceptions.not_found
        
        logger.info(f"Added user {user.id} ({user.email}) to group {group_id}")
        return True
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error adding user to group {group_id}: {str(e)}")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "group_id": group_id,
                    "user_email": user_data.email
                }
            )
        raise


@router.post("/{group_id}/users/{user_id_or_email}", response_model=bool, dependencies=[Depends(require_admin)])
async def add_user_to_group(
    request: Request,
    group_id: Annotated[int, Path(description="The ID of the user group")],
    user_id_or_email: Annotated[str, Path(description="The ID or email of the user to add")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Add a user to a group.
    
    This endpoint accepts either a numeric user ID or an email address.
    If an email is provided, the system will look up the corresponding user ID.
    """
    try:
        # Try to parse as int for backward compatibility
        try:
            user_id = int(user_id_or_email)
        except ValueError:
            # Not an integer, treat as email
            user = await db.read_user_by_email(cursor, user_id_or_email)
            if not user or not user.id:
                logger.warning(f"User with email {user_id_or_email} not found")
                raise HTTPException(status_code=404, detail=f"User with email {user_id_or_email} not found")
            user_id = user.id
        
        # Add user to group
        if not await db.add_user_to_group(cursor, group_id, user_id):
            logger.warning(f"Group {group_id} not found when adding user {user_id}")
            raise exceptions.not_found
        
        logger.info(f"Added user {user_id} to group {group_id}")
        return True
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error adding user to group: {str(e)}")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "group_id": group_id,
                    "user_id_or_email": user_id_or_email
                }
            )
        raise


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
    request: Request,
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
    try:
        # Try to parse as int for backward compatibility
        try:
            user_id = int(user_id_or_email)
        except ValueError:
            # Not an integer, treat as email
            user = await db.read_user_by_email(cursor, user_id_or_email)
            if not user or not user.id:
                logger.warning(f"User with email {user_id_or_email} not found")
                raise HTTPException(status_code=404, detail=f"User with email {user_id_or_email} not found")
            user_id = user.id
        
        # Get the group
        group = await db.read_user_group(cursor, group_id)
        if group is None:
            logger.warning(f"Group {group_id} not found")
            raise exceptions.not_found
        
        # Check if signal is in the group
        signal_ids = group.signal_ids or []
        if signal_id not in signal_ids:
            logger.warning(f"Signal {signal_id} not in group {group_id}")
            raise exceptions.not_found
        
        # Check if user is in the group
        user_ids = group.user_ids or []
        if user_id not in user_ids:
            logger.warning(f"User {user_id} not in group {group_id}")
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
                logger.error(f"Failed to update group {group_id}")
                raise exceptions.not_found
            
            logger.info(f"Added user {user_id} as collaborator for signal {signal_id} in group {group_id}")
        else:
            logger.info(f"User {user_id} already a collaborator for signal {signal_id} in group {group_id}")
        
        return True
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error adding collaborator: {str(e)}")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "group_id": group_id,
                    "signal_id": signal_id,
                    "user_id_or_email": user_id_or_email
                }
            )
        raise


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