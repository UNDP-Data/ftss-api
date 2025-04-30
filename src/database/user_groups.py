"""
CRUD operations for user group entities.
"""

from psycopg import AsyncCursor

from ..entities import UserGroup

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
