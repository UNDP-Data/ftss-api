"""
CRUD operations for user entities.
"""

from psycopg import AsyncCursor

from ..entities import User, UserFilters, UserPage

__all__ = [
    "search_users",
    "create_user",
    "read_user_by_email",
    "read_user",
    "update_user",
    "get_acclab_users",
]


async def search_users(cursor: AsyncCursor, filters: UserFilters) -> UserPage:
    """
    Search users in the database using filters and pagination.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    filters : UserFilters
        Query filters for search, including pagination.

    Returns
    -------
    page : UserPage
        Paginated search results for users.
    """
    where_clauses = []
    params = filters.model_dump()

    # Only add roles filter if present and non-empty
    # if getattr(filters, "roles", None):
    #     where_clauses.append("role = ANY(%(roles)s)")
    
    # Always allow searching by query
    where_clauses.append("(%(query)s IS NULL OR name ~* %(query)s)")

    where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

    query = f"""
        SELECT
            *, COUNT(*) OVER() AS total_count
        FROM
            users
        WHERE
            {where_sql}
        ORDER BY
            name
        OFFSET
            %(offset)s
        LIMIT
            %(limit)s
        ;
    """
    await cursor.execute(query, params)
    rows = await cursor.fetchall()
    page = UserPage.from_search(rows, filters)
    return page


async def create_user(cursor: AsyncCursor, user: User) -> int:
    """
    Insert a user into the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user : User
        A user object to insert.

    Returns
    -------
    int
        An ID of the user in the database.
    """
    query = """
        INSERT INTO users (
            created_at,
            email,
            role,
            name,
            unit,
            acclab
        )
        VALUES (
            %(created_at)s,
            %(email)s,
            %(role)s,
            %(name)s,
            %(unit)s,
            %(acclab)s
        )
        RETURNING
            id
        ;
    """
    await cursor.execute(query, user.model_dump())
    row = await cursor.fetchone()
    return row["id"]


async def read_user_by_email(cursor: AsyncCursor, email: str) -> User | None:
    """
    Read a user from the database using an email address.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    email : str
        An email address.

    Returns
    -------
    user : User
        A user object if found, otherwise None.
    """
    query = "SELECT * FROM users WHERE email = %s;"
    await cursor.execute(query, (email,))
    if (row := await cursor.fetchone()) is None:
        return None
    user = User(**row)
    return user


async def read_user(cursor: AsyncCursor, uid: int) -> User | None:
    """
    Read a user from the database using an ID.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    uid : int
        An ID of the user to retrieve data for.

    Returns
    -------
    User | None
        A user if it exits, otherwise None.
    """
    query = "SELECT * FROM users WHERE id = %s;"
    await cursor.execute(query, (uid,))
    if (row := await cursor.fetchone()) is None:
        return None
    return User(**row)


async def update_user(cursor: AsyncCursor, user: User) -> int | None:
    """
    Update a user in the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user : User
        A user object to update.

    Returns
    -------
    int | None
        A user ID if the update has been performed, otherwise None.
    """
    query = """
        UPDATE
            users
        SET
            role = %(role)s,
            name = %(name)s,
            unit = %(unit)s,
            acclab = %(acclab)s
        WHERE
            email = %(email)s
        RETURNING
            id
        ;
    """
    await cursor.execute(query, user.model_dump())
    if (row := await cursor.fetchone()) is None:
        return None
    return row["id"]


async def get_acclab_users(cursor: AsyncCursor) -> list[str]:
    """
    Get emails of users who are part of the Accelerator Labs.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.

    Returns
    -------
    list[str]
        A list of emails for users who are part of the Accelerator Labs.
    """
    query = "SELECT email FROM users WHERE acclab = TRUE;"
    await cursor.execute(query)
    return [row["email"] async for row in cursor]
