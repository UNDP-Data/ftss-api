"""
Database operations for user favorites.
"""

from datetime import datetime
import logging

from fastapi import HTTPException
from psycopg import AsyncCursor

from ..entities import Signal

logger = logging.getLogger(__name__)

async def create_favourite(
    cursor: AsyncCursor, user_email: str, signal_id: int
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
    signal = await cursor.fetchone()
    logger.debug("Found signal: %s", signal)
    
    if signal is None:
        logger.warning("Signal not found with id: %s", signal_id)
        raise HTTPException(status_code=404, detail="Signal not found")

    # Get user_id from email
    query = """
        SELECT id FROM users WHERE email = %s;
    """
    await cursor.execute(query, (user_email,))
    user = await cursor.fetchone()

    if user is None:
        raise HTTPException(
            status_code=404, detail="User not found with email " + user_email
        )
    user_id = user["id"]

    # Check if the signal is already favorited
    query = """
        SELECT 1 FROM favourites WHERE user_id = %s AND signal_id = %s;
    """
    await cursor.execute(query, (user_id, signal_id))
    favourite = await cursor.fetchone()

    if favourite is not None:
        # delete the favorite
        query = """
            DELETE FROM favourites WHERE user_id = %s AND signal_id = %s;
        """
        await cursor.execute(query, (user_id, signal_id))
        return {"status": "deleted"}

    # Then create the favorite
    query = """
        INSERT INTO favourites (user_id, signal_id, created_at)
        VALUES (%s, %s, %s)
        RETURNING signal_id;
    """
    await cursor.execute(query, (user_id, signal_id, datetime.utcnow()))
    result = await cursor.fetchone()

    if result is None:
        raise HTTPException(status_code=404, detail="Failed to create favourite")

    return {"status": "created"}


async def read_user_favourites(cursor: AsyncCursor, user_email: str) -> list[Signal]:
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
    return [Signal(**row) async for row in cursor]
