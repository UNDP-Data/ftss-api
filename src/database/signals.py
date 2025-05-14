"""
CRUD operations for signal entities.
"""

import logging
from typing import List
from psycopg import AsyncCursor, sql

from .. import storage
from ..entities import Signal, SignalFilters, SignalPage, Status, SignalWithUserGroups, UserGroup

logger = logging.getLogger(__name__)

__all__ = [
    "search_signals",
    "create_signal",
    "read_signal",
    "read_signal_with_user_groups",
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
    query = f"""
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
            {filters.order_by} {filters.direction}
        OFFSET
            %(offset)s
        LIMIT
            %(limit)s
        ;
    """
    await cursor.execute(query, filters.model_dump())
    rows = await cursor.fetchall()
    # extract total count of rows matching the WHERE clause
    page = SignalPage.from_search(rows, filters)
    return page


async def create_signal(cursor: AsyncCursor, signal: Signal, user_group_ids: List[int] = None) -> int:
    """
    Insert a signal into the database, connect it to trends, upload an attachment
    to Azure Blob Storage if applicable, and add it to user groups if specified.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal : Signal
        A signal object to insert. The following fields are supported:
        - secondary_location: list[str] | None
    user_group_ids : List[int], optional
        List of user group IDs to add the signal to.

    Returns
    -------
    signal_id : int
        An ID of the signal in the database.
    """
    logger.info(f"Creating new signal with headline: '{signal.headline}', created by: {signal.created_by}")
    if user_group_ids:
        logger.info(f"Will add signal to user groups: {user_group_ids}")
    
    # Insert signal into database
    try:
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
                secondary_location,
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
                %(secondary_location)s,
                %(score)s
            )
            RETURNING
                id
            ;
        """
        await cursor.execute(query, signal.model_dump())
        row = await cursor.fetchone()
        signal_id = row["id"]
        logger.info(f"Signal created successfully with ID: {signal_id}")
    except Exception as e:
        logger.error(f"Failed to create signal: {e}")
        raise

    # Add connected trends if any are present
    try:
        if signal.connected_trends:
            logger.info(f"Adding connected trends for signal {signal_id}: {signal.connected_trends}")
            for trend_id in signal.connected_trends:
                query = "INSERT INTO connections (signal_id, trend_id, created_by) VALUES (%s, %s, %s);"
                await cursor.execute(query, (signal_id, trend_id, signal.created_by))
            logger.info(f"Successfully added {len(signal.connected_trends)} trends to signal {signal_id}")
    except Exception as e:
        logger.error(f"Error adding connected trends to signal {signal_id}: {e}")
        # Continue execution despite error with trends

    # Upload an image if provided
    if signal.attachment is not None:
        logger.info(f"Uploading image attachment for signal {signal_id}")
        try:
            blob_url = await storage.upload_image(
                signal_id, "signals", signal.attachment
            )
            query = "UPDATE signals SET attachment = %s WHERE id = %s;"
            await cursor.execute(query, (blob_url, signal_id))
            logger.info(f"Image attachment uploaded successfully for signal {signal_id}")
        except Exception as e:
            logger.error(f"Failed to upload image for signal {signal_id}: {e}")
            # Continue execution despite attachment error
    
    # Add signal to user groups if specified
    if user_group_ids:
        logger.info(f"Processing user group assignments for signal {signal_id}")
        from . import user_groups
        groups_added = 0
        groups_failed = 0
        
        for group_id in user_group_ids:
            try:
                logger.debug(f"Attempting to add signal {signal_id} to group {group_id}")
                # Get the group
                group = await user_groups.read_user_group(cursor, group_id)
                if group is not None:
                    # Add signal to group's signal_ids
                    signal_ids = group.signal_ids or []
                    if signal_id not in signal_ids:
                        signal_ids.append(signal_id)
                        group.signal_ids = signal_ids
                        await user_groups.update_user_group(cursor, group)
                        groups_added += 1
                        logger.info(f"Signal {signal_id} added to group {group_id} ({group.name})")
                    else:
                        logger.info(f"Signal {signal_id} already in group {group_id} ({group.name})")
                else:
                    logger.warning(f"Group with ID {group_id} not found, skipping")
                    groups_failed += 1
            except Exception as e:
                logger.error(f"Error adding signal {signal_id} to group {group_id}: {e}")
                groups_failed += 1
        
        logger.info(f"User group assignment complete for signal {signal_id}: {groups_added} successful, {groups_failed} failed")
    
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
    row = await cursor.fetchone()
    if row is None:
        return None
    return Signal(**row)


async def read_signal_with_user_groups(cursor: AsyncCursor, uid: int) -> SignalWithUserGroups | None:
    """
    Read a signal from the database with its associated user groups.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    uid : int
        An ID of the signal to retrieve data for.

    Returns
    -------
    SignalWithUserGroups | None
        A signal with its user groups if it exists, otherwise None.
    """
    logger.info(f"Fetching signal {uid} with its user groups")
    
    try:
        # First, get the signal
        signal = await read_signal(cursor, uid)
        if signal is None:
            logger.warning(f"Signal with ID {uid} not found")
            return None
        
        logger.info(f"Found signal with ID {uid}: '{signal.headline}'")
        
        # Convert to SignalWithUserGroups
        signal_with_groups = SignalWithUserGroups(**signal.model_dump())
        
        # Get all groups that have this signal in their signal_ids
        query = """
            SELECT 
                id, 
                name,
                signal_ids,
                user_ids,
                admin_ids,
                collaborator_map
            FROM 
                user_groups
            WHERE 
                %s = ANY(signal_ids)
            ORDER BY 
                name;
        """
        
        await cursor.execute(query, (uid,))
        
        # Add groups to the signal
        from . import user_groups as ug_module
        signal_with_groups.user_groups = []
        group_count = 0
        
        async for row in cursor:
            try:
                # Convert row to dict
                group_data = ug_module.handle_user_group_row(row)
                # Create UserGroup from dict
                group = UserGroup(**group_data)
                signal_with_groups.user_groups.append(group)
                group_count += 1
                logger.debug(f"Added group {group.id} ({group.name}) to signal {uid}")
            except Exception as e:
                logger.error(f"Error processing group for signal {uid}: {e}")
        
        logger.info(f"Signal {uid} is associated with {group_count} user groups")
        return signal_with_groups
        
    except Exception as e:
        logger.error(f"Error retrieving signal {uid} with user groups: {e}")
        raise


async def update_signal(cursor: AsyncCursor, signal: Signal, user_group_ids: List[int] = None) -> int | None:
    """
    Update a signal in the database, update its connected trends and update an attachment
    in the Azure Blob Storage if applicable. Optionally update the user groups the signal
    belongs to.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal : Signal
        A signal object to update. The following fields are supported:
        - secondary_location: list[str] | None
    user_group_ids : List[int], optional
        List of user group IDs to add the signal to.

    Returns
    -------
    int | None
        A signal ID if the update has been performed, otherwise None.
    """
    logger.info(f"Updating signal with ID: {signal.id}, modified by: {signal.modified_by}")
    if user_group_ids is not None:
        logger.info(f"Will update user groups for signal {signal.id}: {user_group_ids}")

    # Update signal in database
    try:
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
                 secondary_location = COALESCE(%(secondary_location)s, secondary_location),
                 score = COALESCE(%(score)s, score)
            WHERE
                id = %(id)s
            RETURNING
                id
            ;
        """
        await cursor.execute(query, signal.model_dump())
        row = await cursor.fetchone()
        if row is None:
            logger.warning(f"Signal with ID {signal.id} not found for update")
            return None
        signal_id = row["id"]
        logger.info(f"Signal {signal_id} updated successfully in database")
    except Exception as e:
        logger.error(f"Failed to update signal {signal.id}: {e}")
        raise

    # Update connected trends
    try:
        logger.info(f"Updating connected trends for signal {signal_id}")
        await cursor.execute("DELETE FROM connections WHERE signal_id = %s;", (signal_id,))
        logger.debug(f"Removed existing trend connections for signal {signal_id}")
        
        if signal.connected_trends:
            trends_added = 0
            for trend_id in signal.connected_trends:
                try:
                    query = "INSERT INTO connections (signal_id, trend_id, created_by) VALUES (%s, %s, %s);"
                    await cursor.execute(query, (signal_id, trend_id, signal.created_by))
                    trends_added += 1
                except Exception as trend_e:
                    logger.warning(f"Failed to connect trend {trend_id} to signal {signal_id}: {trend_e}")
            
            logger.info(f"Added {trends_added} trend connections to signal {signal_id}")
    except Exception as e:
        logger.error(f"Error updating trend connections for signal {signal_id}: {e}")
        # Continue execution despite trend connection errors

    # Update image attachment
    try:
        logger.info(f"Updating image attachment for signal {signal_id}")
        blob_url = await storage.update_image(signal_id, "signals", signal.attachment)
        if blob_url is not None:
            query = "UPDATE signals SET attachment = %s WHERE id = %s;"
            await cursor.execute(query, (blob_url, signal_id))
            logger.info(f"Image attachment updated successfully for signal {signal_id}")
        else:
            logger.info(f"No image attachment update needed for signal {signal_id}")
    except Exception as e:
        logger.error(f"Failed to update image for signal {signal_id}: {e}")
        # Continue execution despite attachment error
    
    # Update signal's user groups if specified
    if user_group_ids is not None:
        logger.info(f"Processing user group updates for signal {signal_id}")
        try:
            from . import user_groups
            
            # Get all groups that currently have this signal
            query = """
                SELECT id, name
                FROM user_groups
                WHERE %s = ANY(signal_ids);
            """
            await cursor.execute(query, (signal_id,))
            current_groups = {}
            async for row in cursor:
                current_groups[row["id"]] = row["name"]
            
            logger.info(f"Signal {signal_id} is currently in groups: {list(current_groups.keys())}")
            
            # Remove signal from groups not in user_group_ids
            groups_removed = 0
            groups_to_remove_from = [g for g in current_groups.keys() if g not in user_group_ids]
            for group_id in groups_to_remove_from:
                try:
                    logger.debug(f"Removing signal {signal_id} from group {group_id} ({current_groups[group_id]})")
                    group = await user_groups.read_user_group(cursor, group_id)
                    if group is not None and signal_id in group.signal_ids:
                        signal_ids = group.signal_ids.copy()
                        signal_ids.remove(signal_id)
                        group.signal_ids = signal_ids
                        await user_groups.update_user_group(cursor, group)
                        groups_removed += 1
                        logger.info(f"Signal {signal_id} removed from group {group_id} ({group.name})")
                except Exception as e:
                    logger.error(f"Failed to remove signal {signal_id} from group {group_id}: {e}")
            
            # Add signal to new groups
            groups_added = 0
            for group_id in user_group_ids:
                if group_id not in current_groups:
                    try:
                        logger.debug(f"Adding signal {signal_id} to group {group_id}")
                        group = await user_groups.read_user_group(cursor, group_id)
                        if group is not None:
                            signal_ids = group.signal_ids or []
                            if signal_id not in signal_ids:
                                signal_ids.append(signal_id)
                                group.signal_ids = signal_ids
                                await user_groups.update_user_group(cursor, group)
                                groups_added += 1
                                logger.info(f"Signal {signal_id} added to group {group_id} ({group.name})")
                        else:
                            logger.warning(f"Group with ID {group_id} not found, skipping")
                    except Exception as e:
                        logger.error(f"Failed to add signal {signal_id} to group {group_id}: {e}")
            
            logger.info(f"User group assignments updated for signal {signal_id}: {groups_added} added, {groups_removed} removed")
        except Exception as e:
            logger.error(f"Error processing user group updates for signal {signal_id}: {e}")

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
    row = await cursor.fetchone()
    if row is None:
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
    rows = await cursor.fetchall()
    return [Signal(**row) for row in rows]


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


async def can_user_edit_signal(cursor: AsyncCursor, signal_id: int, user_id: int) -> bool:
    """
    Check if a user can edit a signal.
    
    A user can edit a signal if:
    1. They created the signal
    2. They are a direct collaborator for the signal
    3. They are part of a group that can collaborate on this signal
    
    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    signal_id : int
        The ID of the signal to check.
    user_id : int
        The ID of the user to check.
        
    Returns
    -------
    bool
        True if the user can edit the signal, False otherwise.
    """
    # First, check if the user created the signal
    from ..entities import User  # Import here to avoid circular imports
    
    # Get user's email from ID
    query = "SELECT email FROM users WHERE id = %s;"
    await cursor.execute(query, (user_id,))
    row = await cursor.fetchone()
    if row is None:
        return False
    
    user_email = row[0]
    
    # Check if user created the signal
    query = "SELECT 1 FROM signals WHERE id = %s AND created_by = %s;"
    await cursor.execute(query, (signal_id, user_email))
    if await cursor.fetchone() is not None:
        return True
    
    # Check direct collaborators
    query = "SELECT 1 FROM signal_collaborators WHERE signal_id = %s AND user_id = %s;"
    await cursor.execute(query, (signal_id, user_id))
    if await cursor.fetchone() is not None:
        return True
    
    # Check group collaborators
    from . import user_groups  # Import here to avoid circular imports
    group_collaborators = await user_groups.get_signal_group_collaborators(cursor, signal_id)
    if user_id in group_collaborators:
        return True
    
    return False
