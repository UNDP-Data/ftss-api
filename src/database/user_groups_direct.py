"""
Alternative direct SQL implementation for user group functions.

This module provides direct SQL implementations of key user group functions
that bypass the normal processing logic to ensure reliable results.

These functions should only be used in case of persistent issues with 
the standard implementations in user_groups.py.
"""

import logging
from typing import List
from psycopg import AsyncCursor

from ..entities import UserGroup, User, UserGroupWithUsers

logger = logging.getLogger(__name__)

async def get_user_groups_direct(cursor: AsyncCursor, user_id: int) -> List[UserGroup]:
    """
    Get all groups that a user is a member of or an admin of using direct SQL.
    
    This implementation uses the simplest possible SQL and minimal processing
    to maximize reliability.
    
    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_id : int
        The ID of the user.
        
    Returns
    -------
    List[UserGroup]
        A list of user groups.
    """
    logger.debug("DIRECT SQL: Getting user groups for user_id: %s", user_id)
    
    # Direct SQL with minimal processing
    query = """
    WITH user_groups_for_user AS (
        SELECT
            id, 
            name,
            signal_ids,
            user_ids,
            admin_ids,
            collaborator_map,
            created_at
        FROM 
            user_groups
        WHERE 
            %s = ANY(user_ids) OR %s = ANY(admin_ids)
    )
    SELECT * FROM user_groups_for_user
    ORDER BY created_at DESC;
    """
    
    await cursor.execute(query, (user_id, user_id))
    
    result = []
    row_count = 0
    
    async for row in cursor:
        row_count += 1
        # Convert row to dictionary
        data = dict(row)
        # Convert empty arrays to empty lists
        if data['user_ids'] is None:
            data['user_ids'] = []
        if data['admin_ids'] is None:
            data['admin_ids'] = []
        if data['signal_ids'] is None:
            data['signal_ids'] = []
            
        # Create UserGroup instance
        group = UserGroup(**data)
        result.append(group)
        logger.debug("DIRECT SQL: Found group ID: %s, Name: %s", group.id, group.name)
    
    logger.debug("DIRECT SQL: Query returned %s groups", row_count)
    return result

async def get_users_by_ids(cursor: AsyncCursor, user_ids: List[int]) -> List[User]:
    """
    Get user details for a list of user IDs.
    
    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_ids : List[int]
        List of user IDs.
        
    Returns
    -------
    List[User]
        List of User objects.
    """
    if not user_ids:
        return []
        
    query = """
    SELECT 
        id, 
        email, 
        role, 
        name, 
        unit, 
        acclab,
        created_at
    FROM 
        users
    WHERE 
        id = ANY(%s)
    ORDER BY 
        name;
    """
    
    await cursor.execute(query, (user_ids,))
    users = []
    
    async for row in cursor:
        user_data = dict(row)
        users.append(User(**user_data))
        
    return users

async def get_signals_by_ids(cursor: AsyncCursor, signal_ids: List[int]) -> List[dict]:
    """
    Get signal details for a list of signal IDs.
    
    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal_ids : List[int]
        List of signal IDs.
        
    Returns
    -------
    List[dict]
        List of signal dictionaries.
    """
    if not signal_ids:
        return []
        
    query = """
    SELECT 
        s.*,
        array_agg(c.trend_id) FILTER (WHERE c.trend_id IS NOT NULL) AS connected_trends
    FROM 
        signals s
    LEFT JOIN 
        connections c ON s.id = c.signal_id
    WHERE 
        s.id = ANY(%s)
    GROUP BY 
        s.id
    ORDER BY 
        s.id;
    """
    
    await cursor.execute(query, (signal_ids,))
    signals = []
    
    async for row in cursor:
        signal_data = dict(row)
        signals.append(signal_data)
        
    return signals

async def get_user_groups_with_users_direct(cursor: AsyncCursor, user_id: int) -> List[UserGroupWithUsers]:
    """
    Get all groups that a user is a member of or an admin of, with user details, using direct SQL.
    
    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_id : int
        The ID of the user.
        
    Returns
    -------
    List[UserGroupWithUsers]
        A list of user groups with user details.
    """
    logger.debug("DIRECT SQL: Getting user groups with users for user_id: %s", user_id)
    
    # First, get the groups
    groups = await get_user_groups_direct(cursor, user_id)
    result = []
    
    # For each group, fetch the users
    for group in groups:
        group_data = group.model_dump()
        users = await get_users_by_ids(cursor, group.user_ids)
        
        # Create UserGroupWithUsers instance
        group_with_users = UserGroupWithUsers(**group_data, users=users)
        result.append(group_with_users)
        
    logger.debug("DIRECT SQL: Returning %s groups with users", len(result))
    return result

async def get_user_groups_with_signals_direct(cursor: AsyncCursor, user_id: int) -> List:
    """
    Get all groups that a user is a member of or an admin of, with signals, using direct SQL.
    
    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_id : int
        The ID of the user.
        
    Returns
    -------
    List
        A list of user groups with signals and users data.
    """
    from ..entities import Signal, UserGroupComplete
    
    logger.debug("DIRECT SQL: Getting user groups with signals for user_id: %s", user_id)
    
    # First, get the groups
    groups = await get_user_groups_direct(cursor, user_id)
    result = []
    
    # For each group, fetch the signals and users
    for group in groups:
        group_data = group.model_dump()
        signals = []
        
        # Get signals for this group if it has any
        if group.signal_ids:
            signal_data_list = await get_signals_by_ids(cursor, group.signal_ids)
            
            for signal_data in signal_data_list:
                # Check if user is a collaborator for this signal
                can_edit = False
                signal_id_str = str(signal_data["id"])
                
                if group.collaborator_map and signal_id_str in group.collaborator_map:
                    if user_id in group.collaborator_map[signal_id_str]:
                        can_edit = True
                
                # Add can_edit attribute to signal data
                signal_data["can_edit"] = can_edit
                
                # Create Signal instance
                signal = Signal(**signal_data)
                signals.append(signal)
        
        # Get users for this group
        users = await get_users_by_ids(cursor, group.user_ids)
        
        # Create UserGroupComplete instance
        group_complete = UserGroupComplete(**group_data, signals=signals, users=users)
        result.append(group_complete)
        
    logger.debug("DIRECT SQL: Returning %s groups with signals", len(result))
    return result