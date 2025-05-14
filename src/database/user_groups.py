"""
CRUD operations for user group entities.
"""

from psycopg import AsyncCursor
import json
import logging
from typing import List

from ..entities import UserGroup, Signal, User, UserGroupWithSignals, UserGroupWithUsers, UserGroupComplete

__all__ = [
    "create_user_group",
    "read_user_group",
    "update_user_group",
    "delete_user_group",
    "list_user_groups",
    "add_user_to_group",
    "remove_user_from_group",
    "get_user_groups",
    "get_group_users",
    "get_user_groups_with_signals",
    "get_signal_group_collaborators",
    "get_user_group_with_users",
    "list_user_groups_with_users",
    "get_user_groups_with_signals_and_users",
    "get_user_groups_with_users_by_user_id",
]

logger = logging.getLogger(__name__)

# SQL Query Constants
SQL_SELECT_USER_GROUP = """
    SELECT 
        id, 
        name,
        signal_ids,
        user_ids,
        admin_ids,
        collaborator_map
    FROM 
        user_groups
"""

SQL_SELECT_USERS = """
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
        name
"""

SQL_SELECT_SIGNALS = """
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
        s.id
"""

def handle_user_group_row(row) -> dict:
    """
    Helper function to safely extract user group data from a database row.
    
    Parameters
    ----------
    row : dict or tuple
        A database result row
        
    Returns
    -------
    dict
        A dictionary of user group data ready for creating a UserGroup
    """
    data = {}
    if isinstance(row, dict):
        data['id'] = row["id"]
        data['name'] = row["name"]
        data['signal_ids'] = row["signal_ids"] or []
        data['user_ids'] = row["user_ids"] or []
        data['admin_ids'] = row["admin_ids"] or []
        collab_map = row["collaborator_map"]
    else:
        data['id'] = row[0]
        data['name'] = row[1]
        data['signal_ids'] = row[2] or []
        data['user_ids'] = row[3] or []
        data['admin_ids'] = row[4] or []
        collab_map = row[5]
    
    # Handle collaborator_map field
    data['collaborator_map'] = {}
    if collab_map:
        if isinstance(collab_map, str):
            try:
                data['collaborator_map'] = json.loads(collab_map)
            except json.JSONDecodeError:
                data['collaborator_map'] = {}
        else:
            data['collaborator_map'] = collab_map
    
    return data

async def get_users_for_group(cursor: AsyncCursor, user_ids: List[int]) -> List[User]:
    """
    Helper function to fetch user details for a group.
    
    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_ids : List[int]
        List of user IDs to fetch.
        
    Returns
    -------
    List[User]
        List of User objects.
    """
    users = []
    if user_ids:
        await cursor.execute(SQL_SELECT_USERS, (user_ids,))
        async for row in cursor:
            user_data = dict(row)
            users.append(User(**user_data))
    return users


async def create_user_group(cursor: AsyncCursor, group: UserGroup) -> int:
    """
    Create a new user group in the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group : UserGroup
        The user group to create.

    Returns
    -------
    int
        The ID of the created user group.
    """
    # Convert model to dict and ensure collaborator_map is a JSON string
    name = group.name
    signal_ids = group.signal_ids
    user_ids = group.user_ids
    admin_ids = group.admin_ids
    collaborator_map = json.dumps(group.collaborator_map)
    
    query = """
        INSERT INTO user_groups (
            name,
            signal_ids,
            user_ids,
            admin_ids,
            collaborator_map
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s
        )
        RETURNING id
        ;
    """
    await cursor.execute(query, (name, signal_ids, user_ids, admin_ids, collaborator_map))
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Failed to create user group")
    
    # Access the ID safely
    if isinstance(row, dict):
        group_id = row["id"]
    else:
        group_id = row[0]
    
    return group_id


async def read_user_group(cursor: AsyncCursor, group_id: int, fetch_details: bool = False) -> UserGroup | UserGroupWithUsers | None:
    """
    Read a user group from the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group_id : int
        The ID of the user group to read.
    fetch_details : bool, optional
        If True, fetches detailed user information for each group member,
        by default False

    Returns
    -------
    UserGroup | UserGroupWithUsers | None
        The user group if found (with optional detailed user data), otherwise None.
    """
    query = f"{SQL_SELECT_USER_GROUP} WHERE id = %s;"
    await cursor.execute(query, (group_id,))
    if (row := await cursor.fetchone()) is None:
        return None

    data = handle_user_group_row(row)

    if fetch_details:
        # Fetch detailed user information if requested
        users = await get_users_for_group(cursor, data['user_ids'])
        return UserGroupWithUsers(**data, users=users)
    else:
        return UserGroup(**data)


async def update_user_group(cursor: AsyncCursor, group: UserGroup) -> int | None:
    """
    Update a user group in the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group : UserGroup
        The user group to update.

    Returns
    -------
    int | None
        The ID of the updated user group if successful, otherwise None.
    """
    # Convert model to dict and ensure collaborator_map is a JSON string
    group_data = group.model_dump()
    group_data["collaborator_map"] = json.dumps(group_data["collaborator_map"])
    
    query = """
        UPDATE user_groups
        SET 
            name = %(name)s,
            signal_ids = %(signal_ids)s,
            user_ids = %(user_ids)s,
            admin_ids = %(admin_ids)s,
            collaborator_map = %(collaborator_map)s
        WHERE id = %(id)s
        RETURNING id
        ;
    """
    await cursor.execute(query, group_data)
    if (row := await cursor.fetchone()) is None:
        return None
    
    # Access the ID safely
    if isinstance(row, dict):
        return row["id"]
    else:
        return row[0]


async def delete_user_group(cursor: AsyncCursor, group_id: int) -> bool:
    """
    Delete a user group from the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group_id : int
        The ID of the user group to delete.

    Returns
    -------
    bool
        True if the group was deleted, False otherwise.
    """
    query = "DELETE FROM user_groups WHERE id = %s RETURNING id;"
    await cursor.execute(query, (group_id,))
    
    return await cursor.fetchone() is not None


async def list_user_groups(cursor: AsyncCursor) -> list[UserGroup]:
    """
    List all user groups from the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.

    Returns
    -------
    list[UserGroup]
        A list of all user groups.
    """
    query = f"{SQL_SELECT_USER_GROUP} ORDER BY name;"
    await cursor.execute(query)
    result = []
    
    async for row in cursor:
        data = handle_user_group_row(row)
        result.append(UserGroup(**data))
    
    return result


async def add_user_to_group(cursor: AsyncCursor, group_id: int, user_id: int) -> bool:
    """
    Add a user to a group.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group_id : int
        The ID of the group.
    user_id : int
        The ID of the user to add.

    Returns
    -------
    bool
        True if the user was added, False otherwise.
    """
    # Check if the user exists
    await cursor.execute("SELECT 1 FROM users WHERE id = %s;", (user_id,))
    if await cursor.fetchone() is None:
        return False
    
    # Check if the group exists
    await cursor.execute("SELECT user_ids FROM user_groups WHERE id = %s;", (group_id,))
    row = await cursor.fetchone()
    if row is None:
        return False
    
    # Add the user to the group (if not already a member)
    user_ids = row[0] if row[0] is not None else []
    if user_id not in user_ids:
        user_ids.append(user_id)
        
        query = """
            UPDATE user_groups
            SET user_ids = %s
            WHERE id = %s
            RETURNING id
            ;
        """
        await cursor.execute(query, (user_ids, group_id))
        return await cursor.fetchone() is not None
    
    return True


async def remove_user_from_group(cursor: AsyncCursor, group_id: int, user_id: int) -> bool:
    """
    Remove a user from a group.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group_id : int
        The ID of the group.
    user_id : int
        The ID of the user to remove.

    Returns
    -------
    bool
        True if the user was removed, False otherwise.
    """
    # Check if the group exists and get its current state
    await cursor.execute("SELECT user_ids, collaborator_map FROM user_groups WHERE id = %s;", (group_id,))
    row = await cursor.fetchone()
    if row is None:
        return False
    
    user_ids = row[0] if row[0] is not None else []
    
    # Parse collaborator_map from JSON if needed
    if row[1] is not None and isinstance(row[1], str):
        try:
            collaborator_map = json.loads(row[1])
        except json.JSONDecodeError:
            collaborator_map = {}
    else:
        collaborator_map = row[1] if row[1] is not None else {}
    
    if user_id not in user_ids:
        return True  # Already not in the group
    
    # Remove user from user_ids
    user_ids.remove(user_id)
    
    # Remove user from collaborator_map
    for signal_id, users in list(collaborator_map.items()):
        if user_id in users:
            users.remove(user_id)
            
        if not users:
            del collaborator_map[signal_id]
    
    # Update the group
    query = """
        UPDATE user_groups
        SET 
            user_ids = %s,
            collaborator_map = %s
        WHERE id = %s
        RETURNING id
        ;
    """
    # Convert collaborator_map to JSON string
    collaborator_map_json = json.dumps(collaborator_map)
    await cursor.execute(query, (user_ids, collaborator_map_json, group_id))
    
    return await cursor.fetchone() is not None


async def get_user_groups(cursor: AsyncCursor, user_id: int) -> list[UserGroup]:
    """
    Get all groups that a user is a member of or an admin of.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_id : int
        The ID of the user.

    Returns
    -------
    list[UserGroup]
        A list of user groups.
    """
    query = f"{SQL_SELECT_USER_GROUP} WHERE %s = ANY(user_ids) OR %s = ANY(admin_ids) ORDER BY name;"
    await cursor.execute(query, (user_id, user_id))
    result = []
    
    async for row in cursor:
        data = handle_user_group_row(row)
        result.append(UserGroup(**data))
    
    return result


async def get_group_users(cursor: AsyncCursor, group_id: int) -> list[int]:
    """
    Get all users in a group.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group_id : int
        The ID of the group.

    Returns
    -------
    list[int]
        A list of user IDs.
    """
    query = """
        SELECT user_ids
        FROM user_groups
        WHERE id = %s
        ;
    """
    await cursor.execute(query, (group_id,))
    row = await cursor.fetchone()
    
    return row[0] if row and row[0] else []


async def get_user_groups_with_signals(cursor: AsyncCursor, user_id: int, fetch_users: bool = False) -> list[UserGroupWithSignals]:
    """
    Get all groups that a user is a member of, along with the associated signals data.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_id : int
        The ID of the user.
    fetch_users : bool, optional
        If True, also fetches detailed user information for each group member,
        by default False

    Returns
    -------
    list[UserGroupWithSignals]
        A list of user groups with associated signals and optional user details.
    """
    logger.debug("Getting user groups with signals for user_id: %s", user_id)

    # First get the groups the user belongs to
    user_groups = await get_user_groups(cursor, user_id)
    result = []

    # For each group, fetch the signals data
    for group in user_groups:
        group_data = group.model_dump()
        signals = []

        # Get signals for this group
        if group.signal_ids:
            logger.debug("Fetching signals for group_id: %s, signal_ids: %s", group.id, group.signal_ids)

            # Import read_signal function directly
            from .signals import read_signal

            # Get each signal individually
            for signal_id in group.signal_ids:
                signal = await read_signal(cursor, signal_id)
                if signal:
                    # Check if user is a collaborator for this signal
                    can_edit = False
                    signal_id_str = str(signal_id)

                    if group.collaborator_map and signal_id_str in group.collaborator_map:
                        if user_id in group.collaborator_map[signal_id_str]:
                            can_edit = True

                    # Create a copy of the signal with can_edit flag
                    signal_dict = signal.model_dump()
                    signal_dict["can_edit"] = can_edit
                    signals.append(Signal(**signal_dict))

        # Fetch full user details if requested
        users = []
        if fetch_users and group.user_ids:
            users = await get_users_for_group(cursor, group.user_ids)

        # Create a UserGroupWithSignals instance
        if fetch_users:
            # If we fetched user details, create a UserGroupComplete
            group_with_signals = UserGroupComplete(
                **group_data,
                signals=signals,
                users=users
            )
        else:
            # Otherwise create a UserGroupWithSignals
            group_with_signals = UserGroupWithSignals(
                **group_data,
                signals=signals
            )

        result.append(group_with_signals)

    logger.debug("Found %s user groups with signals for user_id: %s", len(result), user_id)
    return result


async def get_signal_group_collaborators(cursor: AsyncCursor, signal_id: int) -> list[int]:
    """
    Get all user IDs that can collaborate on a signal through group membership.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal_id : int
        The ID of the signal.

    Returns
    -------
    list[int]
        A list of user IDs that can collaborate on the signal.
    """
    signal_id_str = str(signal_id)
    query = """
        SELECT 
            collaborator_map->%s as collaborators
        FROM 
            user_groups
        WHERE 
            %s = ANY(signal_ids)
            AND collaborator_map ? %s
        ;
    """
    await cursor.execute(query, (signal_id_str, signal_id, signal_id_str))
    
    collaborators = set()
    async for row in cursor:
        # Safely access collaborators
        if isinstance(row, dict):
            collab_data = row['collaborators']
        else:
            collab_data = row[0]
            
        if collab_data:
            for user_id in collab_data:
                collaborators.add(user_id)
    
    return list(collaborators)


async def get_user_group_with_users(cursor: AsyncCursor, group_id: int) -> UserGroupWithUsers | None:
    """
    Get a user group with detailed user information for each member.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group_id : int
        The ID of the user group.

    Returns
    -------
    UserGroupWithUsers | None
        A user group with detailed user information, or None if the group doesn't exist.
    """
    logger.debug("Getting user group with users for group_id: %s", group_id)
    
    # First, get the user group
    group = await read_user_group(cursor, group_id)
    if group is None:
        logger.warning("User group not found with id: %s", group_id)
        return None
    
    # Convert to dict for modification
    group_data = group.model_dump()
    users = await get_users_for_group(cursor, group.user_ids)
    
    # Create a UserGroupWithUsers instance
    return UserGroupWithUsers(**group_data, users=users)


async def list_user_groups_with_users(cursor: AsyncCursor) -> list[UserGroupWithUsers]:
    """
    List all user groups with detailed user information.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.

    Returns
    -------
    list[UserGroupWithUsers]
        A list of user groups with detailed user information.
    """
    logger.debug("Listing all user groups with users")
    
    # Get all user groups
    groups = await list_user_groups(cursor)
    result = []
    
    # For each group, get user details
    for group in groups:
        group_data = group.model_dump()
        users = await get_users_for_group(cursor, group.user_ids)
        
        # Create a UserGroupWithUsers instance
        group_with_users = UserGroupWithUsers(**group_data, users=users)
        result.append(group_with_users)
    
    logger.debug("Listed %s user groups with users", len(result))
    return result


async def get_user_groups_with_signals_and_users(cursor: AsyncCursor, user_id: int) -> list[UserGroupComplete]:
    """
    Get all groups that a user is a member of, along with the associated signals and users data.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_id : int
        The ID of the user.

    Returns
    -------
    list[UserGroupComplete]
        A list of user groups with signals and users data.
    """
    logger.debug("Getting user groups with signals and users for user_id: %s", user_id)
    
    # First get the groups the user belongs to
    user_groups = await get_user_groups(cursor, user_id)
    result = []
    
    # For each group, fetch the signals data and user data
    for group in user_groups:
        group_data = group.model_dump()
        signals = []
        
        # Get signals for this group
        if group.signal_ids:
            logger.debug("Fetching signals for group_id: %s, signal_ids: %s", group.id, group.signal_ids)
            await cursor.execute(SQL_SELECT_SIGNALS, (group.signal_ids,))
            
            signal_count = 0
            async for row in cursor:
                signal_dict = dict(row)
                # Check if user is a collaborator for this signal
                can_edit = False
                signal_id_str = str(signal_dict["id"])
                
                if group.collaborator_map and signal_id_str in group.collaborator_map:
                    if user_id in group.collaborator_map[signal_id_str]:
                        can_edit = True
                
                signal_dict["can_edit"] = can_edit
                
                # Create Signal instance
                signal = Signal(**signal_dict)
                signals.append(signal)
                signal_count += 1
            
            logger.debug("Found %s signals for group_id: %s", signal_count, group.id)
        
        # Get users for this group
        users = await get_users_for_group(cursor, group.user_ids)
        
        # Create a UserGroupComplete instance
        group_complete = UserGroupComplete(**group_data, signals=signals, users=users)
        result.append(group_complete)
    
    logger.debug("Found %s user groups with signals and users for user_id: %s", len(result), user_id)
    return result


async def get_user_groups_with_users_by_user_id(cursor: AsyncCursor, user_id: int) -> list[UserGroupWithUsers]:
    """
    Get all groups that a user is a member of or an admin of, along with detailed user information 
    for each group member.
    This is a more focused version that only fetches user data, not signals.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_id : int
        The ID of the user.

    Returns
    -------
    list[UserGroupWithUsers]
        A list of user groups with detailed user information.
    """
    logger.debug("Getting user groups with users for user_id: %s", user_id)
    
    # Get groups where the user is a member or an admin
    query = f"{SQL_SELECT_USER_GROUP} WHERE %s = ANY(user_ids) OR %s = ANY(admin_ids) ORDER BY name;"
    await cursor.execute(query, (user_id, user_id))
    result = []
    
    async for row in cursor:
        group_data = handle_user_group_row(row)
        users = await get_users_for_group(cursor, group_data['user_ids'])
        
        # Create a UserGroupWithUsers instance
        group_with_users = UserGroupWithUsers(**group_data, users=users)
        result.append(group_with_users)
    
    logger.debug("Found %s user groups with users for user_id: %s", len(result), user_id)
    return result
