"""
Functions used for dependency injection for role-based access control.
"""

import logging
from typing import Annotated

from fastapi import Depends, Path
from psycopg import AsyncCursor

from . import database as db
from . import exceptions
from .authentication import authenticate_user
from .entities import User

logger = logging.getLogger(__name__)

__all__ = [
    "require_admin",
    "require_curator",
    "require_user",
    "require_creator",
]


async def require_admin(user: User = Depends(authenticate_user)) -> User:
    """Require that the user is assigned an admin role."""
    logger.debug(f"Checking admin permissions for user {user.email} with role {user.role}")
    if not user.is_admin:
        logger.warning(f"Permission denied: User {user.email} with role {user.role} attempted admin action")
        raise exceptions.permission_denied
    logger.debug(f"Admin permission granted for user {user.email}")
    return user


async def require_curator(user: User = Depends(authenticate_user)) -> User:
    """Require that the user is assigned at least a curator role."""
    if not user.is_staff:
        raise exceptions.permission_denied
    return user


async def require_user(user: User = Depends(authenticate_user)) -> User:
    """Require that the user is assigned at least a user role and is not a visitor."""
    if not user.is_regular:
        raise exceptions.permission_denied
    return user


async def require_creator(
    uid: Annotated[int, Path(description="The ID of the signal to be updated")],
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
) -> User:
    """Require that the user is at least a curator or is the creator of the signal."""
    # admins and curators can modify all signals
    if user.is_staff:
        return user
    # check if the user created the original signal
    signal = await db.read_signal(cursor, uid)
    if signal is None:
        raise exceptions.not_found
    if signal.created_by != user.email:
        raise exceptions.permission_denied
    # regular users can modify their signals but cannot change their statuses
    if signal.status != signal.status:
        raise exceptions.permission_denied
    return user
