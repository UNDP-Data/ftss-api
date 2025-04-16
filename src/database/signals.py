"""
CRUD operations for signal entities.
"""

from psycopg import AsyncCursor, sql

from .. import storage
from ..entities import Signal, SignalFilters, SignalPage, Status

__all__ = [
    "search_signals",
    "create_signal",
    "read_signal",
    "update_signal",
    "delete_signal",
    "read_user_signals",
    "is_signal_favorited",
    "add_collaborator",
    "remove_collaborator",
    "get_signal_collaborators",
    "can_user_edit_signal",
]


async def search_signals(cursor: AsyncCursor, filters: SignalFilters) -> SignalPage:
    """
    Search signals in the database using filters and pagination.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    filters : SignalFilters
        Query filters for search, including pagination.

    Returns
    -------
    page : SignalPage
        Paginated search results for signals.
    """
    query = """
        SELECT 
            *, COUNT(*) OVER() AS total_count
        FROM
            signals AS s
        LEFT OUTER JOIN (
            SELECT
                signal_id, array_agg(trend_id) AS connected_trends
            FROM
                connections
            GROUP BY
                signal_id
            ) AS c
        ON
            s.id = c.signal_id
        LEFT OUTER JOIN (
            SELECT
                name AS unit_name,
                region AS unit_region
            FROM
                units
            ) AS u
        ON
            s.created_unit = u.unit_name
        LEFT OUTER JOIN (
            SELECT
                name AS location,
                region AS location_region,
                bureau AS location_bureau
            FROM
                locations
            ) AS l
        ON
            s.location = l.location
        WHERE
             (%(ids)s IS NULL OR id = ANY(%(ids)s))
             AND status = ANY(%(statuses)s)
             AND (%(created_by)s IS NULL OR created_by = %(created_by)s)
             AND (%(created_for)s IS NULL OR created_for = %(created_for)s)
             AND (%(steep_primary)s IS NULL OR steep_primary = %(steep_primary)s)
             AND (%(steep_secondary)s IS NULL OR steep_secondary && %(steep_secondary)s)
             AND (%(signature_primary)s IS NULL OR signature_primary = %(signature_primary)s)
             AND (%(signature_secondary)s IS NULL OR signature_secondary && %(signature_secondary)s)
             AND (%(location)s IS NULL OR (s.location = %(location)s) OR location_region = %(location)s)
             AND (%(bureau)s IS NULL OR location_bureau = %(bureau)s)
             AND (%(sdgs)s IS NULL OR %(sdgs)s && sdgs)
             AND (%(score)s IS NULL OR score = %(score)s)
             AND (%(unit)s IS NULL OR unit_region = %(unit)s OR unit_name = %(unit)s)
             AND (%(query)s IS NULL OR text_search_field @@ websearch_to_tsquery('english', %(query)s))
        ORDER BY
            {} {}
        OFFSET
            %(offset)s
        LIMIT
            %(limit)s
        ;
    """
    query = sql.SQL(query).format(
        sql.Identifier(filters.order_by),
        sql.SQL(filters.direction),
    )
    await cursor.execute(query, filters.model_dump())
    rows = await cursor.fetchall()
    # extract total count of rows matching the WHERE clause
    page = SignalPage.from_search(rows, filters)
    return page


async def create_signal(cursor: AsyncCursor, signal: Signal) -> int:
    """
    Insert a signal into the database, connect it to trends and upload an attachment
    to Azure Blob Storage if applicable.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal : Signal
        A signal object to insert.

    Returns
    -------
    signal_id : int
        An ID of the signal in the database.
    """
    query = """
        INSERT INTO signals (
            status,
            created_by,
            created_for,
            modified_by,
            headline,
            description,
            steep_primary,
            steep_secondary,
            signature_primary,
            signature_secondary,
            sdgs, 
            created_unit,
            url,
            relevance,
            keywords,
            location,
            score
        )
        VALUES (
            %(status)s,
            %(created_by)s,
            %(created_for)s,
            %(modified_by)s,
            %(headline)s,
            %(description)s, 
            %(steep_primary)s,
            %(steep_secondary)s,
            %(signature_primary)s,
            %(signature_secondary)s,
            %(sdgs)s,
            %(created_unit)s,
            %(url)s,
            %(relevance)s,
            %(keywords)s,
            %(location)s,
            %(score)s
        )
        RETURNING
            id
        ;
    """
    await cursor.execute(query, signal.model_dump())
    row = await cursor.fetchone()
    signal_id = row["id"]

    # add connected trends if any are present
    for trend_id in signal.connected_trends or []:
        query = "INSERT INTO connections (signal_id, trend_id, created_by) VALUES (%s, %s, %s);"
        await cursor.execute(query, (signal_id, trend_id, signal.created_by))

    # upload an image
    if signal.attachment is not None:
        try:
            blob_url = await storage.upload_image(
                signal_id, "signals", signal.attachment
            )
        except Exception as e:
            print(e)
        else:
            query = "UPDATE signals SET attachment = %s WHERE id = %s;"
            await cursor.execute(query, (blob_url, signal_id))
    return signal_id


async def read_signal(cursor: AsyncCursor, uid: int) -> Signal | None:
    """
    Read a signal from the database using an ID.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    uid : int
        An ID of the signal to retrieve data for.

    Returns
    -------
    Signal | None
        A signal if it exits, otherwise None.
    """
    query = """
        SELECT 
            *
        FROM
            signals AS s
        LEFT OUTER JOIN (
            SELECT
                signal_id, array_agg(trend_id) AS connected_trends
            FROM
                connections
            GROUP BY
                signal_id
            ) AS c
        ON
            s.id = c.signal_id
        WHERE
            id = %s
        ;
        """
    await cursor.execute(query, (uid,))
    if (row := await cursor.fetchone()) is None:
        return None
    return Signal(**row)


async def update_signal(cursor: AsyncCursor, signal: Signal) -> int | None:
    """
    Update a signal in the database, update its connected trends and update an attachment
    in the Azure Blob Storage if applicable.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal : Signal
        A signal object to update.

    Returns
    -------
    int | None
        A signal ID if the update has been performed, otherwise None.
    """
    query = """
        UPDATE
            signals
        SET
             status = COALESCE(%(status)s, status),
             created_for = COALESCE(%(created_for)s, created_for),
             modified_at = NOW(),
             modified_by = %(modified_by)s,
             headline = COALESCE(%(headline)s, headline),
             description = COALESCE(%(description)s, description),
             steep_primary = COALESCE(%(steep_primary)s, steep_primary),
             steep_secondary = COALESCE(%(steep_secondary)s, steep_secondary),
             signature_primary = COALESCE(%(signature_primary)s, signature_primary),
             signature_secondary = COALESCE(%(signature_secondary)s, signature_secondary),
             sdgs = COALESCE(%(sdgs)s, sdgs),
             created_unit = COALESCE(%(created_unit)s, created_unit),
             url = COALESCE(%(url)s, url),
             relevance = COALESCE(%(relevance)s, relevance),
             keywords = COALESCE(%(keywords)s, keywords),
             location = COALESCE(%(location)s, location),
             score = COALESCE(%(score)s, score)
        WHERE
            id = %(id)s
        RETURNING
            id
        ;
    """
    await cursor.execute(query, signal.model_dump())
    if (row := await cursor.fetchone()) is None:
        return None
    signal_id = row["id"]

    # update connected trends if any are present
    await cursor.execute("DELETE FROM connections WHERE signal_id = %s;", (signal_id,))
    for trend_id in signal.connected_trends or []:
        query = "INSERT INTO connections (signal_id, trend_id, created_by) VALUES (%s, %s, %s);"
        await cursor.execute(query, (signal_id, trend_id, signal.created_by))

    # upload an image if it is not a URL to an existing image
    blob_url = await storage.update_image(signal_id, "signals", signal.attachment)
    query = "UPDATE signals SET attachment = %s WHERE id = %s;"
    await cursor.execute(query, (blob_url, signal_id))

    return signal_id


async def delete_signal(cursor: AsyncCursor, uid: int) -> Signal | None:
    """
    Delete a signal from the database and, if applicable, an image from
    Azure Blob Storage, using an ID.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    uid : int
        An ID of the signal to delete.

    Returns
    -------
    Signal | None
        A deleted signal object if the operation has been successful, otherwise None.
    """
    query = "DELETE FROM signals WHERE id = %s RETURNING *;"
    await cursor.execute(query, (uid,))
    if (row := await cursor.fetchone()) is None:
        return None
    signal = Signal(**row)
    if signal.attachment is not None:
        await storage.delete_image(entity_id=signal.id, folder_name="signals")
    return signal


async def read_user_signals(
    cursor: AsyncCursor,
    user_email: str,
    status: Status,
) -> list[Signal]:
    """
    Read signals from the database using a user email and status filter.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_email : str
        An email of the user whose signals to read.
    status : Status
        A status of signals to filter by.

    Returns
    -------
    list[Signal]
        A list of matching signals.
    """
    query = """
        SELECT 
            *
        FROM
            signals AS s
        LEFT OUTER JOIN (
            SELECT
                signal_id, array_agg(trend_id) AS connected_trends
            FROM
                connections
            GROUP BY
                signal_id
            ) AS c
        ON
            s.id = c.signal_id
        WHERE
            created_by = %s AND status = %s
        ;
        """
    await cursor.execute(query, (user_email, status))
    return [Signal(**row) async for row in cursor]


async def is_signal_favorited(cursor: AsyncCursor, user_email: str, signal_id: int) -> bool:
    """
    Check if a signal is favorited by a user.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    user_email : str
        The email of the user to check.
    signal_id : int
        The ID of the signal to check.

    Returns
    -------
    bool
        True if the signal is favorited by the user, False otherwise.
    """
    query = """
        SELECT 1
        FROM favourites f
        JOIN users u ON f.user_id = u.id
        WHERE u.email = %s AND f.signal_id = %s;
    """
    await cursor.execute(query, (user_email, signal_id))
    return await cursor.fetchone() is not None



async def add_collaborator(cursor: AsyncCursor, signal_id: int, collaborator: str) -> bool:
    """
    Add a collaborator to a signal.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal_id : int
        The ID of the signal.
    collaborator : str
        The email of the user or "group:{id}" to add as a collaborator.

    Returns
    -------
    bool
        True if the collaborator was added, False otherwise.
    """
    # Check if the signal exists
    await cursor.execute("SELECT 1 FROM signals WHERE id = %s;", (signal_id,))
    if await cursor.fetchone() is None:
        return False
    
    # Determine if this is a group or user
    if collaborator.startswith("group:"):
        group_id = int(collaborator.split(":")[1])
        query = """
            INSERT INTO signal_collaborator_groups (signal_id, group_id)
            VALUES (%s, %s)
            ON CONFLICT (signal_id, group_id) DO NOTHING
            RETURNING signal_id
            ;
        """
        await cursor.execute(query, (signal_id, group_id))
    else:
        # Check if the user exists
        await cursor.execute("SELECT 1 FROM users WHERE email = %s;", (collaborator,))
        if await cursor.fetchone() is None:
            return False
        
        query = """
            INSERT INTO signal_collaborators (signal_id, user_email)
            VALUES (%s, %s)
            ON CONFLICT (signal_id, user_email) DO NOTHING
            RETURNING signal_id
            ;
        """
        await cursor.execute(query, (signal_id, collaborator))
    
    return await cursor.fetchone() is not None


async def remove_collaborator(cursor: AsyncCursor, signal_id: int, collaborator: str) -> bool:
    """
    Remove a collaborator from a signal.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal_id : int
        The ID of the signal.
    collaborator : str
        The email of the user or "group:{id}" to remove as a collaborator.

    Returns
    -------
    bool
        True if the collaborator was removed, False otherwise.
    """
    # Determine if this is a group or user
    if collaborator.startswith("group:"):
        group_id = int(collaborator.split(":")[1])
        query = """
            DELETE FROM signal_collaborator_groups
            WHERE signal_id = %s AND group_id = %s
            RETURNING signal_id
            ;
        """
        await cursor.execute(query, (signal_id, group_id))
    else:
        query = """
            DELETE FROM signal_collaborators
            WHERE signal_id = %s AND user_email = %s
            RETURNING signal_id
            ;
        """
        await cursor.execute(query, (signal_id, collaborator))
    
    return await cursor.fetchone() is not None


async def get_signal_collaborators(cursor: AsyncCursor, signal_id: int) -> list[str]:
    """
    Get all collaborators for a signal.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal_id : int
        The ID of the signal.

    Returns
    -------
    list[str]
        A list of user emails and group IDs (as "group:{id}").
    """
    # Get individual collaborators
    query1 = """
        SELECT user_email
        FROM signal_collaborators
        WHERE signal_id = %s
        ;
    """
    await cursor.execute(query1, (signal_id,))
    user_emails = [row[0] async for row in cursor]
    
    # Get group collaborators
    query2 = """
        SELECT group_id
        FROM signal_collaborator_groups
        WHERE signal_id = %s
        ;
    """
    await cursor.execute(query2, (signal_id,))
    group_ids = [f"group:{row[0]}" async for row in cursor]
    
    return user_emails + group_ids


async def can_user_edit_signal(cursor: AsyncCursor, signal_id: int, user_email: str) -> bool:
    """
    Check if a user can edit a signal.

    A user can edit a signal if:
    1. They created the signal
    2. They are in the collaborators list
    3. They are part of a group in the collaborators list

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal_id : int
        The ID of the signal.
    user_email : str
        The email of the user.

    Returns
    -------
    bool
        True if the user can edit the signal, False otherwise.
    """
    # Check if the user created the signal
    query1 = """
        SELECT 1
        FROM signals
        WHERE id = %s AND created_by = %s
        ;
    """
    await cursor.execute(query1, (signal_id, user_email))
    if await cursor.fetchone() is not None:
        return True
    
    # Check if the user is in the collaborators list
    query2 = """
        SELECT 1
        FROM signal_collaborators
        WHERE signal_id = %s AND user_email = %s
        ;
    """
    await cursor.execute(query2, (signal_id, user_email))
    if await cursor.fetchone() is not None:
        return True
    
    # Check if the user is part of a group in the collaborators list
    query3 = """
        SELECT 1
        FROM signal_collaborator_groups scg
        JOIN user_group_members ugm ON scg.group_id = ugm.group_id
        WHERE scg.signal_id = %s AND ugm.user_email = %s
        ;
    """
    await cursor.execute(query3, (signal_id, user_email))
    if await cursor.fetchone() is not None:
        return True
    
    return False
