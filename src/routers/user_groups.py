"""
A router for managing user groups.
"""

import logging
import bugsnag
from typing import Annotated, List, Optional, Union, Dict, Any

from fastapi import APIRouter, Depends, Path, Body, Query, HTTPException, Request
from psycopg import AsyncCursor
from pydantic import BaseModel

from .. import database as db
from .. import exceptions
from ..dependencies import require_admin, require_user
from ..entities import UserGroup, User, UserGroupWithSignals, UserGroupWithUsers, UserGroupComplete, Signal
from ..authentication import authenticate_user
from ..database.signals import read_signal
from ..database import user_groups_direct

# Set up logger for this module
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user-groups", tags=["user groups"])

user_group_defaults: dict[str, Any] = {
    # "dependencies": [Depends(require_admin)],
}

# Add models to support user emails in requests
class UserGroupCreate(BaseModel):
    name: str
    users: Optional[List[str]] = None


class UserGroupUpdate(BaseModel):
    id: int
    name: str
    signal_ids: List[int] = []
    user_ids: List[Union[str, int]] = []  # Can be either user IDs or email addresses
    collaborator_map: Dict[str, List[int]] = {}


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


@router.get("", response_model=List[UserGroup], **user_group_defaults)
async def list_user_groups(
    request: Request,
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """List all user groups."""
    logger.info(f"Endpoint called: list_user_groups - URL: {request.url} - Method: {request.method}")
    try:
        logger.debug("Fetching all user groups from database...")
        groups = await db.list_user_groups(cursor)
        logger.info(f"Successfully listed {len(groups)} user groups")
        logger.debug(f"Returning group IDs: {[g.id for g in groups]}")
        return groups
    except Exception as e:
        logger.error(f"Error listing user groups: {str(e)}")
        logger.exception("Detailed traceback for listing user groups:")
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


@router.get("/me", response_model=List[UserGroup], **user_group_defaults)
async def get_my_user_groups(
    request: Request,
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Get all user groups that the current user is a member of or an admin of.
    This endpoint is accessible to all authenticated users.
    """
    logger.info(f"Endpoint called: get_my_user_groups - URL: {request.url} - Method: {request.method}")
    logger.debug(f"User requesting their groups: {user.id} ({user.email})")
    
    try:
        if not user.id:
            logger.warning("User ID not found in get_my_user_groups")
            raise exceptions.not_found
        
        # Run debug queries first
        logger.debug(f"Running debug queries for user {user.id}...")
        debug_info = await db.debug_user_groups(cursor, user.id)
        
        # Check if we can directly extract groups from debug info
        direct_group_ids = []
        for row in debug_info["combined_query"]:
            direct_group_ids.append(row["id"])
        
        logger.debug(f"Direct query found group IDs: {direct_group_ids}")
        
        # Now get the full groups with user details
        logger.debug(f"Fetching groups for user {user.id}...")
        user_groups = await db.get_user_groups_with_users_by_user_id(cursor, user.id)
        
        # Check if there's a mismatch
        fetched_ids = [g.id for g in user_groups]
        missing_ids = [gid for gid in direct_group_ids if gid not in fetched_ids]
        
        if missing_ids:
            logger.warning(f"MISMATCH! Direct query found groups {direct_group_ids} but function returned only {fetched_ids}")
            logger.warning(f"Missing groups: {missing_ids}")
            
            # Fall back to direct SQL implementation
            logger.warning("Falling back to direct SQL implementation")
            user_groups = await user_groups_direct.get_user_groups_with_users_direct(cursor, user.id)
            logger.info(f"Direct SQL implementation returned {len(user_groups)} groups")
        
        logger.info(f"User {user.id} ({user.email}) retrieved {len(user_groups)} groups (as member or admin)")
        if user_groups:
            logger.debug(f"Returning group IDs: {[g.id for g in user_groups]}")
            logger.debug(f"Group names: {[g.name for g in user_groups]}")
        return user_groups
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error in get_my_user_groups: {str(e)}")
            logger.exception(f"Detailed traceback for get_my_user_groups (user {user.id}):")
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


@router.get("/me/with-signals", response_model=List[Union[UserGroupWithSignals, UserGroupComplete]], **user_group_defaults)
async def get_my_user_groups_with_signals(
    request: Request,
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
    include_users: bool = Query(True, description="If true, includes detailed user information for each group member (defaults to true)")
):
    """
    Get all user groups that the current user is a member of or an admin of along with their signals data.

    This enhanced endpoint provides detailed information about each signal associated with the groups,
    including whether the current user has edit permissions for each signal. This is useful for:

    - Displaying a dashboard of all signals a user can access through their groups
    - Showing which signals the user can edit vs. view-only
    - Building collaborative workflows where users can see their assigned signals

    The response includes all signal details plus a `can_edit` flag for each signal indicating
    if the current user has edit permissions based on the group's collaborator_map.

    By default, detailed user information for each group member is included. Set the `include_users`
    parameter to false to get only basic user ID references without detailed user information.
    """
    logger.info(f"Endpoint called: get_my_user_groups_with_signals - URL: {request.url} - Method: {request.method}")
    logger.debug(f"User requesting groups with signals: {user.id} ({user.email})")
    logger.debug(f"Query parameters: include_users={include_users}")
    
    try:
        if not user.id:
            logger.warning("User ID not found in get_my_user_groups_with_signals")
            raise exceptions.not_found

        # Run debug queries first to check for discrepancies
        logger.debug(f"Running debug queries for user {user.id}...")
        debug_info = await db.debug_user_groups(cursor, user.id)
        
        # Check if we can directly extract groups from debug info
        direct_group_ids = []
        for row in debug_info["combined_query"]:
            direct_group_ids.append(row["id"])
        
        logger.debug(f"Direct query found group IDs: {direct_group_ids}")
        
        logger.debug(f"Fetching groups with signals for user {user.id}...")
        # Get groups with signals for this user, optionally including full user details
        user_groups_with_signals = await db.get_user_groups_with_signals(
            cursor,
            user.id,
            fetch_users=include_users
        )
        
        # Check if there's a mismatch and fall back to direct implementation if needed
        fetched_ids = [g.id for g in user_groups_with_signals]
        missing_ids = [gid for gid in direct_group_ids if gid not in fetched_ids]
        
        if missing_ids:
            logger.warning(f"MISMATCH in signals endpoint! Direct query found groups {direct_group_ids} but function returned only {fetched_ids}")
            logger.warning(f"Missing groups: {missing_ids}")
            
            # Fall back to direct SQL implementation
            logger.warning("Falling back to direct SQL implementation for signals")
            user_groups_with_signals = await user_groups_direct.get_user_groups_with_signals_direct(cursor, user.id)
            logger.info(f"Direct SQL implementation returned {len(user_groups_with_signals)} groups with signals")
        
        logger.info(f"User {user.id} ({user.email}) retrieved {len(user_groups_with_signals)} groups with signals")
        if user_groups_with_signals:
            logger.debug(f"Returning group IDs: {[g.id for g in user_groups_with_signals]}")
            
            # Log total signals count across all groups
            total_signals = sum(len(g.signals) for g in user_groups_with_signals)
            logger.debug(f"Total signals across all groups: {total_signals}")
            
            # Log collaborator access details
            editable_signals = 0
            for group in user_groups_with_signals:
                for signal in group.signals:
                    if signal.can_edit:
                        editable_signals += 1
            
            logger.debug(f"User can edit {editable_signals} out of {total_signals} signals")
        
        return user_groups_with_signals
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error in get_my_user_groups_with_signals: {str(e)}")
            logger.exception(f"Detailed traceback for get_my_user_groups_with_signals (user {user.id}):")
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
                    },
                    "query_params": {
                        "include_users": include_users
                    }
                }
            )
        raise


@router.post("", response_model=Union[UserGroup, UserGroupWithUsers], **user_group_defaults)
async def create_user_group(
    request: Request,
    group_data: UserGroupCreate,
    current_user: User = Depends(authenticate_user),  # Get the current user
    cursor: AsyncCursor = Depends(db.yield_cursor),
    include_users: bool = Query(False, description="If true, includes detailed user information for each group member"),
    admins: List[str] = Query(None, description="List of user emails to set as admins in the group")
):
    """
    Create a new user group.

    Optionally include detailed user information for each group member in the response
    by setting the `include_users` query parameter to true.
    
    The current authenticated user is automatically added as both a member and an admin of the group.
    Additional admin users can be specified using the `admins` query parameter.
    """
    logger.info(f"Endpoint called: create_user_group - URL: {request.url} - Method: {request.method}")
    logger.debug(f"Creating user group with name: '{group_data.name}'")
    logger.debug(f"Query parameters: include_users={include_users}, admins={admins}")
    logger.debug(f"Current user: ID={current_user.id}, email={current_user.email}")
    
    try:
        # Create the base group
        group = UserGroup(name=group_data.name)
        logger.debug(f"Created base group entity with name: '{group.name}'")

        # Initialize user_ids list with the current user's ID
        user_ids = []
        admin_ids = []
        
        if current_user.id:
            user_ids.append(current_user.id)
            admin_ids.append(current_user.id)  # Make current user an admin
            logger.debug(f"Added current user (ID: {current_user.id}) as member and admin")

        # Handle email addresses if provided
        user_emails_added = []
        if group_data.users:
            logger.debug(f"Processing {len(group_data.users)} user emails from request body")
            for email in group_data.users:
                logger.debug(f"Looking up user with email: {email}")
                user = await db.read_user_by_email(cursor, email)
                if user and user.id and user.id not in user_ids:  # Avoid duplicates
                    user_ids.append(user.id)
                    user_emails_added.append(email)
                    logger.debug(f"Added user {user.id} ({email}) as member")
                else:
                    if not user:
                        logger.warning(f"User with email {email} not found")
                    elif user.id in user_ids:
                        logger.debug(f"User {user.id} ({email}) already added to members list")
            
            logger.debug(f"Added {len(user_emails_added)} users as members from request body: {user_emails_added}")

        # Handle admin emails if provided
        admin_emails_added = []
        if admins:
            logger.debug(f"Processing {len(admins)} admin emails from query parameters")
            for email in admins:
                logger.debug(f"Looking up admin with email: {email}")
                user = await db.read_user_by_email(cursor, email)
                if user and user.id:
                    if user.id not in user_ids:  # If not already in user_ids, add them
                        user_ids.append(user.id)
                        logger.debug(f"Added user {user.id} ({email}) as member")
                    
                    if user.id not in admin_ids:  # Avoid duplicates in admin_ids
                        admin_ids.append(user.id)
                        admin_emails_added.append(email)
                        logger.debug(f"Added user {user.id} ({email}) as admin")
                    else:
                        logger.debug(f"User {user.id} ({email}) already added to admins list")
                else:
                    logger.warning(f"Admin with email {email} not found")
            
            logger.debug(f"Added {len(admin_emails_added)} users as admins from query params: {admin_emails_added}")

        if user_ids:
            group.user_ids = user_ids
            logger.debug(f"Group has {len(user_ids)} members: {user_ids}")
            
        if admin_ids:
            group.admin_ids = admin_ids
            logger.debug(f"Group has {len(admin_ids)} admins: {admin_ids}")

        # Create the group
        logger.debug("Creating group in database...")
        group_id = await db.create_user_group(cursor, group)
        logger.info(f"Created user group {group_id} with name '{group.name}', {len(user_ids)} users, and {len(admin_ids)} admins")

        # Retrieve and return the created group
        logger.debug(f"Retrieving created group {group_id} from database...")
        created_group = await db.read_user_group(cursor, group_id, fetch_details=include_users)
        if not created_group:
            logger.error(f"Failed to retrieve newly created group with ID {group_id}")
            raise exceptions.not_found

        logger.debug(f"Successfully retrieved created group {group_id}")
        return created_group
    except Exception as e:
        logger.error(f"Error creating user group: {str(e)}")
        logger.exception("Detailed traceback for creating user group:")
        bugsnag.notify(
            e,
            metadata={
                "request": {
                    "url": str(request.url),
                    "method": request.method,
                },
                "group_data": {
                    "name": group_data.name,
                    "users_count": len(group_data.users) if group_data.users else 0,
                    "users": group_data.users if group_data.users else [],
                    "admins_count": len(admins) if admins else 0,
                    "admins": admins if admins else [],
                    "current_user_id": current_user.id if current_user else None,
                    "current_user_email": current_user.email if current_user else None
                }
            }
        )
        raise


@router.get("/{group_id}", response_model=Union[UserGroup, UserGroupWithUsers, UserGroupComplete], **user_group_defaults)
async def read_user_group(
    request: Request,
    group_id: Annotated[int, Path(description="The ID of the user group to retrieve")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
    include_users: bool = Query(True, description="If true, includes detailed user and signal information (defaults to true)")
):
    """
    Get a user group by ID with detailed information.

    By default, includes detailed user and signal information. Set the `include_users`
    parameter to false to get only the basic group data without user and signal details.
    """
    logger.info(f"Endpoint called: read_user_group - URL: {request.url} - Method: {request.method}")
    logger.debug(f"Reading user group ID: {group_id}")
    logger.debug(f"Query parameters: include_users={include_users}")
    
    try:
        logger.debug(f"Fetching group {group_id} from database...")
        # First, get the basic group
        if (group := await db.read_user_group(cursor, group_id, fetch_details=include_users)) is None:
            logger.warning(f"User group {group_id} not found")
            raise exceptions.not_found

        # Log basic info to avoid huge logs
        logger.info(f"Retrieved user group {group_id} with name '{group.name}'")
        
        # Log detailed information about the group
        logger.debug(f"Group details - ID: {group.id}, Name: '{group.name}'")
        logger.debug(f"Group members: {len(group.user_ids) if group.user_ids else 0} users")
        logger.debug(f"Group admins: {len(group.admin_ids) if group.admin_ids else 0} users")
        logger.debug(f"Group signals: {len(group.signal_ids) if group.signal_ids else 0} signals")
        
        # Log collaborator map details
        if group.collaborator_map:
            logger.debug(f"Group has {len(group.collaborator_map)} signals with collaborators")
            total_collaborators = sum(len(collaborators) for collaborators in group.collaborator_map.values())
            logger.debug(f"Total collaborator assignments: {total_collaborators}")

        # If include_users is true and the group has signals, fetch those signals too
        if include_users and hasattr(group, 'user_ids') and group.user_ids and hasattr(group, 'signal_ids') and group.signal_ids:
            logger.debug(f"Fetching detailed signals data for group {group_id}")
            # Get signals for this group and prepare a complete response
            signals = []

            # Import the signals database function directly
            from ..database.signals import read_signal

            # Fetch each signal individually
            signal_count = 0
            for signal_id in group.signal_ids:
                logger.debug(f"Fetching signal {signal_id}")
                signal = await read_signal(cursor, signal_id)
                if signal:
                    signals.append(signal)
                    signal_count += 1
                else:
                    logger.warning(f"Signal {signal_id} referenced by group {group_id} not found")

            logger.debug(f"Successfully fetched {signal_count} signals for group {group_id}")

            # Convert to a UserGroupComplete if we have both users and signals
            if hasattr(group, 'users') and group.users:
                logger.debug(f"Creating UserGroupComplete with {len(signals)} signals and {len(group.users)} users")
                return UserGroupComplete(
                    **group.model_dump(),
                    signals=signals
                )
            else:
                logger.debug("Group lacks user details, returning without creating UserGroupComplete")

        return group
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error reading user group {group_id}: {str(e)}")
            logger.exception(f"Detailed traceback for reading user group {group_id}:")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "group_id": group_id,
                    "query_params": {
                        "include_users": include_users
                    }
                }
            )
        raise


@router.put("/{group_id}", response_model=Union[UserGroup, UserGroupWithUsers, UserGroupComplete], **user_group_defaults)
async def update_user_group(
    request: Request,
    group_id: Annotated[int, Path(description="The ID of the user group to update")],
    group_data: UserGroupUpdate,
    cursor: AsyncCursor = Depends(db.yield_cursor),
    include_users: bool = Query(False, description="If true, includes detailed user information for each group member after update")
):
    """
    Update a user group.

    Optionally include detailed user information for each group member in the response
    by setting the `include_users` query parameter to true.

    This endpoint accepts both user IDs (integers) and email addresses (strings) in
    the user_ids field. Email addresses will be automatically converted to user IDs.
    """
    logger.info(f"Endpoint called: update_user_group - URL: {request.url} - Method: {request.method}")
    logger.debug(f"Updating user group ID: {group_id}")
    logger.debug(f"Update data: name='{group_data.name}', {len(group_data.user_ids)} users, {len(group_data.signal_ids)} signals")
    logger.debug(f"Query parameters: include_users={include_users}")
    
    try:
        # Validate ID consistency
        if group_id != group_data.id:
            logger.warning(f"ID mismatch: path ID {group_id} != body ID {group_data.id}")
            raise exceptions.id_mismatch

        # Process user_ids field in case it contains emails instead of integer IDs
        processed_user_ids = []
        email_conversions = []
        
        logger.debug(f"Processing {len(group_data.user_ids)} user identifiers...")
        for user_id in group_data.user_ids:
            if isinstance(user_id, str):
                # Check if it's an email (contains @ sign)
                if '@' in user_id:
                    # This looks like an email address, try to find the user ID
                    logger.debug(f"Looking up user by email: {user_id}")
                    user = await db.read_user_by_email(cursor, user_id)
                    if user and user.id:
                        processed_user_ids.append(user.id)
                        email_conversions.append((user_id, user.id))
                        logger.debug(f"Converted email {user_id} to user ID {user.id}")
                    else:
                        logger.warning(f"User with email {user_id} not found")
                        raise HTTPException(status_code=404, detail=f"User with email {user_id} not found")
                else:
                    # String but not an email, try to convert to int if it's a digit string
                    try:
                        numeric_id = int(user_id)
                        processed_user_ids.append(numeric_id)
                        logger.debug(f"Converted string '{user_id}' to integer {numeric_id}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid user ID format: {user_id}")
                        raise HTTPException(status_code=400, detail=f"Invalid user ID format: {user_id}")
            else:
                # Already an int
                processed_user_ids.append(user_id)
                logger.debug(f"Using integer user ID {user_id} as is")

        logger.debug(f"Processed {len(processed_user_ids)} user IDs: {processed_user_ids}")
        if email_conversions:
            logger.debug(f"Converted {len(email_conversions)} emails to user IDs: {email_conversions}")

        # Log collaborator map details if present
        if group_data.collaborator_map:
            logger.debug(f"Group has {len(group_data.collaborator_map)} signals with collaborators")
            total_collaborators = sum(len(collaborators) for collaborators in group_data.collaborator_map.values())
            logger.debug(f"Total collaborator assignments: {total_collaborators}")
            
            # Log detailed collaborator info
            for signal_id, collaborators in group_data.collaborator_map.items():
                logger.debug(f"Signal {signal_id} has {len(collaborators)} collaborators: {collaborators}")

        # Convert UserGroupUpdate to UserGroup
        logger.debug("Creating UserGroup entity from update data...")
        group = UserGroup(
            id=group_data.id,
            name=group_data.name,
            signal_ids=group_data.signal_ids,
            user_ids=processed_user_ids,  # Use the processed user IDs
            collaborator_map=group_data.collaborator_map
        )
        logger.debug("UserGroup entity created successfully")

        # Update the group in the database
        logger.debug(f"Updating group {group_id} in database...")
        if (updated_id := await db.update_user_group(cursor, group)) is None:
            logger.warning(f"User group {group_id} not found for update")
            raise exceptions.not_found
            
        logger.info(f"Successfully updated user group {updated_id}")
        
        # Fetch the updated group
        logger.debug(f"Fetching updated group {updated_id} from database...")
        updated_group = await db.read_user_group(cursor, updated_id, fetch_details=include_users)
        logger.debug(f"Successfully retrieved updated group {updated_id}")
        
        return updated_group
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error updating user group {group_id}: {str(e)}")
            logger.exception(f"Detailed traceback for updating user group {group_id}:")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "group_id": group_id,
                    "group_data": {
                        "id": group_data.id,
                        "name": group_data.name,
                        "user_count": len(group_data.user_ids) if group_data.user_ids else 0,
                        "signal_count": len(group_data.signal_ids) if group_data.signal_ids else 0,
                        "collaborator_map_size": len(group_data.collaborator_map) if group_data.collaborator_map else 0
                    },
                    "query_params": {
                        "include_users": include_users
                    }
                }
            )
        raise


@router.delete("/{group_id}", response_model=bool, **user_group_defaults)
async def delete_user_group(
    request: Request,
    group_id: Annotated[int, Path(description="The ID of the user group to delete")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Delete a user group."""
    logger.info(f"Endpoint called: delete_user_group - URL: {request.url} - Method: {request.method}")
    logger.debug(f"Deleting user group ID: {group_id}")
    
    try:
        # First get the group to log what's being deleted
        group = await db.read_user_group(cursor, group_id)
        if group:
            logger.debug(f"Found group to delete: {group.id} - '{group.name}'")
            logger.debug(f"Group contains: {len(group.user_ids) if group.user_ids else 0} members, " +
                       f"{len(group.signal_ids) if group.signal_ids else 0} signals, " +
                       f"{len(group.collaborator_map) if group.collaborator_map else 0} signal collaborator maps")
        
        logger.debug(f"Deleting group {group_id} from database...")
        if not await db.delete_user_group(cursor, group_id):
            logger.warning(f"User group {group_id} not found for deletion")
            raise exceptions.not_found
            
        logger.info(f"Successfully deleted user group {group_id}")
        return True
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error deleting user group {group_id}: {str(e)}")
            logger.exception(f"Detailed traceback for deleting user group {group_id}:")
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


@router.post("/{group_id}/users", response_model=bool, **user_group_defaults)
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


@router.post("/{group_id}/users/{user_id_or_email}", response_model=bool, **user_group_defaults)
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


@router.delete("/{group_id}/users/{user_id_or_email}", response_model=bool, **user_group_defaults)
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


@router.post("/{group_id}/signals/{signal_id}", response_model=bool, **user_group_defaults)
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


@router.delete("/{group_id}/signals/{signal_id}", response_model=bool, **user_group_defaults)
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


@router.post("/{group_id}/signals/{signal_id}/collaborators", response_model=bool, **user_group_defaults)
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


@router.post("/{group_id}/signals/{signal_id}/collaborators/{user_id_or_email}", response_model=bool, **user_group_defaults)
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
    logger.info(f"Endpoint called: add_collaborator_to_signal_in_group - URL: {request.url} - Method: {request.method}")
    logger.debug(f"Adding collaborator to group {group_id} for signal {signal_id}")
    logger.debug(f"User identifier provided: {user_id_or_email}")
    
    try:
        # Try to parse as int for backward compatibility
        user_id = None
        user_email = None
        
        try:
            user_id = int(user_id_or_email)
            logger.debug(f"User identifier is numeric: {user_id}")
        except ValueError:
            # Not an integer, treat as email
            user_email = user_id_or_email
            logger.debug(f"User identifier is an email: {user_email}")
            
            user = await db.read_user_by_email(cursor, user_email)
            if not user or not user.id:
                logger.warning(f"User with email {user_email} not found")
                raise HTTPException(status_code=404, detail=f"User with email {user_email} not found")
            
            user_id = user.id
            logger.debug(f"Resolved email {user_email} to user ID {user_id}")
        
        # Get the group
        logger.debug(f"Fetching group {group_id}...")
        group = await db.read_user_group(cursor, group_id)
        if group is None:
            logger.warning(f"Group {group_id} not found")
            raise exceptions.not_found
        
        logger.debug(f"Successfully retrieved group '{group.name}' (ID: {group.id})")
        
        # Check if signal is in the group
        signal_ids = group.signal_ids or []
        logger.debug(f"Group has {len(signal_ids)} signals: {signal_ids}")
        
        if signal_id not in signal_ids:
            logger.warning(f"Signal {signal_id} not in group {group_id}")
            raise exceptions.not_found
        
        # Check if user is in the group
        user_ids = group.user_ids or []
        logger.debug(f"Group has {len(user_ids)} members: {user_ids}")
        
        if user_id not in user_ids:
            logger.warning(f"User {user_id} not in group {group_id}")
            raise exceptions.not_found
        
        # Add collaborator
        collaborator_map = group.collaborator_map or {}
        signal_key = str(signal_id)
        
        logger.debug(f"Current collaborator map: {collaborator_map}")
        
        if signal_key not in collaborator_map:
            logger.debug(f"Creating new collaborator entry for signal {signal_id}")
            collaborator_map[signal_key] = []
        
        if user_id not in collaborator_map[signal_key]:
            logger.debug(f"Adding user {user_id} as collaborator for signal {signal_id}")
            collaborator_map[signal_key].append(user_id)
            group.collaborator_map = collaborator_map
            
            logger.debug(f"Updating group {group_id} with new collaborator map")
            if await db.update_user_group(cursor, group) is None:
                logger.error(f"Failed to update group {group_id}")
                raise exceptions.not_found
            
            logger.info(f"Successfully added user {user_id} as collaborator for signal {signal_id} in group {group_id}")
        else:
            logger.info(f"User {user_id} is already a collaborator for signal {signal_id} in group {group_id}")
        
        return True
    except Exception as e:
        if not isinstance(e, HTTPException):  # Don't log HTTPExceptions
            logger.error(f"Error adding collaborator: {str(e)}")
            logger.exception(f"Detailed traceback for adding collaborator to group {group_id}, signal {signal_id}:")
            bugsnag.notify(
                e,
                metadata={
                    "request": {
                        "url": str(request.url),
                        "method": request.method,
                    },
                    "group_id": group_id,
                    "signal_id": signal_id,
                    "user_id_or_email": user_id_or_email,
                    "resolved_user_id": user_id if 'user_id' in locals() else None
                }
            )
        raise


@router.delete("/{group_id}/signals/{signal_id}/collaborators/{user_id_or_email}", response_model=bool, **user_group_defaults)
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