"""
Database operations for user favorites.
"""

import logging
from datetime import datetime
from typing import cast

from fastapi import HTTPException
from psycopg import AsyncCursor
from psycopg.rows import DictRow

from ..entities import Signal

logger = logging.getLogger(__name__)


async def create_favourite(
    cursor: AsyncCursor[DictRow], user_email: str, signal_id: int
) -> dict:
    logger.debug("Creating/removing favourite for signal_id: %s", signal_id)

    # First check if the signal exists
    query = """
        SELECT s.*, COALESCE(array_agg(c.trend_id) FILTER (WHERE c.trend_id IS NOT NULL), ARRAY[]::integer[]) as connected_trends
        FROM signals s
        LEFT JOIN connections c ON s.id = c.signal_id
        WHERE s.id = %s
        GROUP BY s.id;
    """

    await cursor.execute(query, (signal_id,))
    signal_row = cast(DictRow | None, await cursor.fetchone())
    logger.debug("Found signal: %s", signal_row)

    if signal_row is None:
        logger.warning("Signal not found with id: %s", signal_id)
        raise HTTPException(status_code=404, detail="Signal not found")

    # Get user_id from email
    query = """
        SELECT id FROM users WHERE email = %s;
    """
    await cursor.execute(query, (user_email,))
    user_row = cast(DictRow | None, await cursor.fetchone())

    if user_row is None:
        raise HTTPException(
            status_code=404, detail="User not found with email " + user_email
        )
    user_id = user_row["id"]

    # Check if the favorite already exists
    query = """
        SELECT 1 FROM favourites WHERE user_id = %s AND signal_id = %s;
    """
    await cursor.execute(query, (user_id, signal_id))
    exists = await cursor.fetchone()

    if exists:
        logger.debug("Deleting favourite for signal_id: %s", signal_id)
        # Remove the favorite
        query = """
            DELETE FROM favourites WHERE user_id = %s AND signal_id = %s;
        """
        try:
            await cursor.execute(query, (user_id, signal_id))
            logger.debug("Deleted favourite for signal_id: %s", signal_id)
            return {"status": "deleted"}
        except Exception as e:
            logger.error("Error deleting favourite for signal_id: %s", signal_id, exc_info=True)
            raise e
    else:
        logger.debug("Adding favourite for signal_id: %s", signal_id)
        # Add to favorites
        query = """
            INSERT INTO favourites (user_id, signal_id, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, signal_id) DO NOTHING;
        """
        try:
            await cursor.execute(query, (user_id, signal_id, datetime.utcnow()))
            logger.debug("Added favourite for signal_id: %s", signal_id)
            return {"status": "created"}
        except Exception as e:
            logger.error("Error adding favourite for signal_id: %s", signal_id, exc_info=True)
            raise e


async def read_user_favourites(cursor: AsyncCursor[DictRow], user_email: str) -> list[Signal]:
    logger.debug("Reading user favourites for user_email: %s", user_email)
    query = """
        SELECT s.*, COALESCE(array_agg(c.trend_id) FILTER (WHERE c.trend_id IS NOT NULL), ARRAY[]::integer[]) as connected_trends
        FROM signals s
        LEFT JOIN connections c ON s.id = c.signal_id
        JOIN favourites f ON s.id = f.signal_id
        JOIN users u ON f.user_id = u.id
        WHERE u.email = %s
        GROUP BY s.id, f.created_at
        ORDER BY f.created_at DESC;
    """
    await cursor.execute(query, (user_email,))
    rows = await cursor.fetchall()
    logger.debug("Fetched %s rows", len(rows))
    return [Signal.model_validate(cast(DictRow, row)) for row in rows]