"""
CRUD operations for user group entities.
"""

from psycopg import AsyncCursor

from ..entities import UserGroup, Signal

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
]


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
    query = """
        INSERT INTO user_groups (
            name,
            signal_ids,
            user_ids,
            collaborator_map
        )
        VALUES (
            %(name)s,
            %(signal_ids)s,
            %(user_ids)s,
            %(collaborator_map)s
        )
        RETURNING id
        ;
    """
    await cursor.execute(query, group.model_dump(exclude={"id"}))
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Failed to create user group")
    group_id = row[0]
    
    return group_id


async def read_user_group(cursor: AsyncCursor, group_id: int) -> UserGroup | None:
    """
    Read a user group from the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group_id : int
        The ID of the user group to read.

    Returns
    -------
    UserGroup | None
        The user group if found, otherwise None.
    """
    query = """
        SELECT 
            id, 
            name,
            signal_ids,
            user_ids,
            collaborator_map
        FROM 
            user_groups
        WHERE 
            id = %s
        ;
    """
    await cursor.execute(query, (group_id,))
    if (row := await cursor.fetchone()) is None:
        return None
    
    # Convert row to dict
    data = dict(zip(["id", "name", "signal_ids", "user_ids", "collaborator_map"], row))
    
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
    query = """
        UPDATE user_groups
        SET 
            name = %(name)s,
            signal_ids = %(signal_ids)s,
            user_ids = %(user_ids)s,
            collaborator_map = %(collaborator_map)s
        WHERE id = %(id)s
        RETURNING id
        ;
    """
    await cursor.execute(query, group.model_dump())
    if (row := await cursor.fetchone()) is None:
        return None
    
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
    query = """
        SELECT 
            id, 
            name,
            signal_ids,
            user_ids,
            collaborator_map
        FROM 
            user_groups
        ORDER BY 
            name
        ;
    """
    await cursor.execute(query)
    result = []
    
    async for row in cursor:
        # Convert row to dict
        data = dict(zip(["id", "name", "signal_ids", "user_ids", "collaborator_map"], row))
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
    # Get current user_ids
    await cursor.execute("SELECT user_ids, collaborator_map FROM user_groups WHERE id = %s;", (group_id,))
    row = await cursor.fetchone()
    if row is None:
        return False
    
    user_ids = row[0] if row[0] is not None else []
    collaborator_map = row[1] if row[1] is not None else {}
    
    # Remove user from user_ids
    if user_id in user_ids:
        user_ids.remove(user_id)
        
        # Remove user from collaborator_map
        for signal_id, users in list(collaborator_map.items()):
            if user_id in users:
                users.remove(user_id)
                if not users:  # If empty, remove signal from map
                    del collaborator_map[signal_id]
        
        query = """
            UPDATE user_groups
            SET 
                user_ids = %s,
                collaborator_map = %s
            WHERE id = %s
            RETURNING id
            ;
        """
        await cursor.execute(query, (user_ids, collaborator_map, group_id))
        return await cursor.fetchone() is not None
    
    return False


async def get_user_groups(cursor: AsyncCursor, user_id: int) -> list[UserGroup]:
    """
    Get all groups that a user is a member of.

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
    query = """
        SELECT 
            id, 
            name,
            signal_ids,
            user_ids,
            collaborator_map
        FROM 
            user_groups
        WHERE 
            %s = ANY(user_ids)
        ORDER BY 
            name
        ;
    """
    await cursor.execute(query, (user_id,))
    result = []
    
    async for row in cursor:
        # Convert row to dict
        data = dict(zip(["id", "name", "signal_ids", "user_ids", "collaborator_map"], row))
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


async def get_user_groups_with_signals(cursor: AsyncCursor, user_id: int) -> list[dict]:
    """
    Get all groups that a user is a member of, along with the associated signals data.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_id : int
        The ID of the user.

    Returns
    -------
    list[dict]
        A list of dictionaries containing user group and signal data.
    """
    # First get the groups the user belongs to
    user_groups = await get_user_groups(cursor, user_id)
    result = []
    
    # For each group, fetch the signals data
    for group in user_groups:
        group_data = group.model_dump()
        signals = []
        
        # Get signals for this group
        if group.signal_ids:
            signals_query = """
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
                ;
            """
            await cursor.execute(signals_query, (group.signal_ids,))
            
            async for row in cursor:
                signal_dict = dict(row)
                # Check if user is a collaborator for this signal
                can_edit = False
                signal_id_str = str(signal_dict["id"])
                
                if group.collaborator_map and signal_id_str in group.collaborator_map:
                    if user_id in group.collaborator_map[signal_id_str]:
                        can_edit = True
                
                signal_dict["can_edit"] = can_edit
                signals.append(Signal(**signal_dict))
        
        group_data["signals"] = signals
        result.append(group_data)
    
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
        if row[0]:  # Access first column using integer index
            for user_id in row[0]:
                collaborators.add(user_id)
    
    return list(collaborators)
