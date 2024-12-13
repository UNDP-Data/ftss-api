"""
A router for managing user's favorite signals.
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncCursor
from pydantic import BaseModel

from .. import database as db
from ..dependencies import require_user
from ..entities import Signal, User

logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter(
    prefix="/favourites",
    tags=["favourites"],
)


class FavoriteResponse(BaseModel):
    status: Literal["created", "deleted"]


# Define dependency functions to avoid Trunk linter warnings
def get_cursor():
    return Depends(db.yield_cursor)


def get_user():
    return Depends(require_user)


@router.post("/{signal_id}", response_model=FavoriteResponse)
async def create_or_remove_favourite(
    signal_id: int,
    user: User = Depends(require_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
) -> dict:
    """
    Add or remove a signal from user's favorites depending on current status.
    """
    try:
        signal = await db.read_signal(cursor, signal_id)
        logger.debug("Found signal for favourite operation: %s", signal)

        if signal:
            return await db.create_favourite(cursor, user.email, signal_id)

        logger.warning("Signal not found with id: %s", signal_id)
        raise HTTPException(status_code=404, detail="Signal not found")
    except Exception as e:
        logger.error("Error in create_or_remove_favourite: %s", str(e), exc_info=True)
        raise e


@router.get("/", response_model=list[Signal])
async def fetch_user_favourites(
    user: User = Depends(require_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
) -> list[Signal]:
    """
    Get all signals that the current user has favorited, in chronological order
    of when they were favorited.
    """
    signals = await db.read_user_favourites(cursor, user.email)

    return signals
