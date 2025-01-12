"""
A router for retrieving, submitting and updating signals.
"""

import logging
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, Path, Query
from psycopg import AsyncCursor

from .. import database as db
from .. import exceptions, genai, utils
from ..authentication import authenticate_user
from ..dependencies import require_creator, require_curator, require_user
from ..entities import Role, Signal, SignalFilters, SignalPage, Status, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/search", response_model=SignalPage)
async def search_signals(
    filters: Annotated[SignalFilters, Query()],
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Search signals in the database using pagination and filters."""
    page = await db.search_signals(cursor, filters)
    return page.sanitise(user)


@router.get("/export", response_model=None, dependencies=[Depends(require_curator)])
async def export_signals(
    filters: Annotated[SignalFilters, Query()],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Export signals that match the filters from the database. You can export up to
    10k rows at once.
    """
    page = await db.search_signals(cursor, filters)

    # prettify the data
    df = pd.DataFrame([signal.model_dump() for signal in page.data])
    df = utils.binarise_columns(df, ["steep_secondary", "signature_secondary", "sdgs"])
    df["keywords"] = df["keywords"].str.join(" ;")
    df["connected_trends"] = df["connected_trends"].str.join("; ")

    # add acclab indicator variable
    emails = await db.users.get_acclab_users(cursor)
    df["acclab"] = df["created_by"].isin(emails)

    response = utils.write_to_response(df, "signals")
    return response


@router.get("/generation", response_model=Signal)
async def generate_signal(
    url: str = Query(
        description="A public webpage URL whose content will be used to generate a signal."
    ),
    user: User = Depends(require_user),
):
    """Generate a signal from web content using OpenAI."""
    try:
        content = await utils.scrape_content(url)
    except Exception as e:
        print(e)
        raise exceptions.content_error
    try:
        signal = await genai.generate_signal(content)
    except Exception as e:
        print(e)
        raise exceptions.generation_error
    signal.created_by = user.email
    signal.created_unit = user.unit
    signal.url = url
    return signal


@router.post("", response_model=Signal, status_code=201)
async def create_signal(
    signal: Signal,
    user: User = Depends(require_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Submit a signal to the database. If the signal has a base64 encoded image
    attachment, it will be uploaded to Azure Blob Storage.
    """
    signal.created_by = user.email
    signal.modified_by = user.email
    signal.created_unit = user.unit
    signal_id = await db.create_signal(cursor, signal)
    return await db.read_signal(cursor, signal_id)


@router.get("/me", response_model=list[Signal])
async def read_my_signals(
    status: Status = Query(),
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Retrieve signal with a given status submitted by the current user.
    """
    return await db.read_user_signals(cursor, user.email, status)


@router.get("/{uid}", response_model=Signal)
async def read_signal(
    uid: Annotated[int, Path(description="The ID of the signal to retrieve")],
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Retrieve a signal form the database using an ID. Trends connected to the signal
    can be retrieved using IDs from the `signal.connected_trends` field.
    """
    logger.info("Reading signal with ID: %s for user: %s", uid, user.email)
    
    if (signal := await db.read_signal(cursor, uid)) is None:
        logger.warning("Signal not found with ID: %s", uid)
        raise exceptions.not_found
        
    logger.info("Retrieved signal: %s", signal.model_dump())
    
    if user.role == Role.VISITOR and signal.status != Status.APPROVED:
        logger.warning(
            "Permission denied - visitor trying to access non-approved signal. Status: %s",
            signal.status
        )
        raise exceptions.permission_denied
    
    # Check if the signal is favorited by the user
    logger.info("Checking favorite status for signal %s and user %s", uid, user.email)
    is_favorite = await db.is_signal_favorited(cursor, user.email, uid)
    logger.info("Favorite status result: %s", is_favorite)
    
    signal.favorite = is_favorite
    logger.info("Final signal with favorite status: %s", signal.model_dump())
    
    return signal


@router.put("/{uid}", response_model=Signal)
async def update_signal(
    uid: Annotated[int, Path(description="The ID of the signal to be updated")],
    signal: Signal,
    user: User = Depends(require_creator),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Update a signal in the database."""
    if uid != signal.id:
        raise exceptions.id_mismatch
    signal.modified_by = user.email
    if (signal_id := await db.update_signal(cursor, signal)) is None:
        raise exceptions.not_found
    return await db.read_signal(cursor, signal_id)


@router.delete("/{uid}", response_model=Signal, dependencies=[Depends(require_creator)])
async def delete_signal(
    uid: Annotated[int, Path(description="The ID of the signal to be deleted")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Delete a signal from the database using IDs. This also deletes an image attachment from
    Azure Blob Storage if there is one.
    """
    if (signal := await db.delete_signal(cursor, uid)) is None:
        raise exceptions.not_found
    return signal
