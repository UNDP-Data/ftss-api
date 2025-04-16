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
            name
        )
        VALUES (
            %(name)s
        )
        RETURNING id
        ;
    """
    await cursor.execute(query, group.model_dump(exclude={"users", "id"}))
    row = await cursor.fetchone()
    group_id = row[0]
    
    # Add users to the group
    if group.users:
        for user_email in group.users:
            await add_user_to_group(cursor, group_id, user_email)
    
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
            g.id, 
            g.name,
            ARRAY_AGG(u.email) AS users
        FROM 
            user_groups g
        LEFT JOIN 
            user_group_members m ON g.id = m.group_id
        LEFT JOIN 
            users u ON m.user_email = u.email
        WHERE 
            g.id = %s
        GROUP BY 
            g.id, g.name
        ;
    """
    await cursor.execute(query, (group_id,))
    if (row := await cursor.fetchone()) is None:
        return None
    
    # Convert row to dict and handle null values for users
    data = dict(zip(["id", "name", "users"], row))
    if data["users"] == [None]:
        data["users"] = []
    
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
        SET name = %(name)s
        WHERE id = %(id)s
        RETURNING id
        ;
    """
    await cursor.execute(query, group.model_dump(exclude={"users"}))
    if (row := await cursor.fetchone()) is None:
        return None
    
    group_id = row[0]
    
    # First remove all existing members
    await cursor.execute("DELETE FROM user_group_members WHERE group_id = %s;", (group_id,))
    
    # Then add the new members
    if group.users:
        for user_email in group.users:
            await add_user_to_group(cursor, group_id, user_email)
    
    return group_id


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
    # First delete all members
    await cursor.execute("DELETE FROM user_group_members WHERE group_id = %s;", (group_id,))
    
    # Then delete the group
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
            g.id, 
            g.name,
            ARRAY_AGG(u.email) AS users
        FROM 
            user_groups g
        LEFT JOIN 
            user_group_members m ON g.id = m.group_id
        LEFT JOIN 
            users u ON m.user_email = u.email
        GROUP BY 
            g.id, g.name
        ORDER BY 
            g.name
        ;
    """
    await cursor.execute(query)
    result = []
    
    async for row in cursor:
        # Convert row to dict and handle null values for users
        data = dict(zip(["id", "name", "users"], row))
        if data["users"] == [None]:
            data["users"] = []
        
        result.append(UserGroup(**data))
    
    return result


async def add_user_to_group(cursor: AsyncCursor, group_id: int, user_email: str) -> bool:
    """
    Add a user to a group.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group_id : int
        The ID of the group.
    user_email : str
        The email of the user to add.

    Returns
    -------
    bool
        True if the user was added, False otherwise.
    """
    # Check if the user exists
    await cursor.execute("SELECT 1 FROM users WHERE email = %s;", (user_email,))
    if await cursor.fetchone() is None:
        return False
    
    # Check if the group exists
    await cursor.execute("SELECT 1 FROM user_groups WHERE id = %s;", (group_id,))
    if await cursor.fetchone() is None:
        return False
    
    # Add the user to the group (if not already a member)
    query = """
        INSERT INTO user_group_members (group_id, user_email)
        VALUES (%s, %s)
        ON CONFLICT (group_id, user_email) DO NOTHING
        RETURNING group_id
        ;
    """
    await cursor.execute(query, (group_id, user_email))
    
    return await cursor.fetchone() is not None


async def remove_user_from_group(cursor: AsyncCursor, group_id: int, user_email: str) -> bool:
    """
    Remove a user from a group.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    group_id : int
        The ID of the group.
    user_email : str
        The email of the user to remove.

    Returns
    -------
    bool
        True if the user was removed, False otherwise.
    """
    query = """
        DELETE FROM user_group_members
        WHERE group_id = %s AND user_email = %s
        RETURNING group_id
        ;
    """
    await cursor.execute(query, (group_id, user_email))
    
    return await cursor.fetchone() is not None


async def get_user_groups(cursor: AsyncCursor, user_email: str) -> list[UserGroup]:
    """
    Get all groups that a user is a member of.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_email : str
        The email of the user.

    Returns
    -------
    list[UserGroup]
        A list of user groups.
    """
    query = """
        SELECT 
            g.id, 
            g.name,
            ARRAY_AGG(u.email) AS users
        FROM 
            user_groups g
        JOIN 
            user_group_members m ON g.id = m.group_id
        LEFT JOIN 
            user_group_members m2 ON g.id = m2.group_id
        LEFT JOIN 
            users u ON m2.user_email = u.email
        WHERE 
            m.user_email = %s
        GROUP BY 
            g.id, g.name
        ORDER BY 
            g.name
        ;
    """
    await cursor.execute(query, (user_email,))
    result = []
    
    async for row in cursor:
        # Convert row to dict and handle null values for users
        data = dict(zip(["id", "name", "users"], row))
        if data["users"] == [None]:
            data["users"] = []
        
        result.append(UserGroup(**data))
    
    return result


async def get_group_users(cursor: AsyncCursor, group_id: int) -> list[str]:
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
    list[str]
        A list of user emails.
    """
    query = """
        SELECT u.email
        FROM user_group_members m
        JOIN users u ON m.user_email = u.email
        WHERE m.group_id = %s
        ORDER BY u.email
        ;
    """
    await cursor.execute(query, (group_id,))
    
    return [row[0] async for row in cursor]
