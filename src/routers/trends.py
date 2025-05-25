"""
A router for retrieving, submitting and updating trends.
"""

from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, Path, Query, status
from psycopg import AsyncCursor

from .. import database as db
from .. import exceptions, utils
from ..authentication import authenticate_user
from ..dependencies import require_curator
from ..entities import Role, Status, Trend, TrendFilters, TrendPage, User

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("")
async def get_all_trends(
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Retrieve all trends from the database. Requires authentication.
    """
    trends = await db.list_trends(cursor)
    return trends

@router.get("/search", response_model=TrendPage)
async def search_trends(
    filters: Annotated[TrendFilters, Query()],
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Search trends in the database using pagination and filters."""
    page = await db.search_trends(cursor, filters)
    return page.sanitise(user)


@router.get("/export", response_model=None, dependencies=[Depends(require_curator)])
async def export_trends(
    filters: Annotated[TrendFilters, Query()],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Export trends that match the filters from the database. You can export up to
    10k rows at once.
    """
    page = await db.search_trends(cursor, filters)

    # prettify the data
    df = pd.DataFrame([trend.model_dump() for trend in page.data])
    df = utils.binarise_columns(df, ["steep_secondary", "signature_secondary", "sdgs"])
    df["connected_signals_count"] = df["connected_signals"].str.len()
    df.drop("connected_signals", axis=1, inplace=True)

    response = utils.write_to_response(df, "trends")
    return response


@router.post("", response_model=Trend, status_code=status.HTTP_201_CREATED)
async def create_trend(
    trend: Trend,
    user: User = Depends(require_curator),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Submit a trend to the database. If the trend has a base64 encoded image
    attachment, it will be uploaded to Azure Blob Storage.
    """
    trend.created_by = user.email
    trend.modified_by = user.email
    trend_id = await db.create_trend(cursor, trend)
    return await db.read_trend(cursor, trend_id)




@router.get("/{uid}", response_model=Trend)
async def read_trend(
    uid: Annotated[int, Path(description="The ID of the trend to retrieve")],
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Retrieve a trend form the database using an ID. Signals connected to the trend
    can be retrieved using IDs from the `trend.connected_signals` field.
    """
    if (trend := await db.read_trend(cursor, uid)) is None:
        raise exceptions.not_found
    if user.role == Role.VISITOR and trend.status != Status.APPROVED:
        raise exceptions.permission_denied
    return trend


@router.put("/{uid}", response_model=Trend)
async def update_trend(
    uid: Annotated[int, Path(description="The ID of the trend to be updated")],
    trend: Trend,
    user: User = Depends(require_curator),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """Update a trend in the database."""
    if uid != trend.id:
        raise exceptions.id_mismatch
    trend.modified_by = user.email
    if (trend_id := await db.update_trend(cursor, trend=trend)) is None:
        raise exceptions.not_found
    return await db.read_trend(cursor, trend_id)


@router.delete("/{uid}", response_model=Trend, dependencies=[Depends(require_curator)])
async def delete_trend(
    uid: Annotated[int, Path(description="The ID of the trend to be deleted")],
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Delete a trend from the database using IDs. This also deletes an image attachment from
    Azure Blob Storage if there is one.
    """
    if (trend := await db.delete_trend(cursor, uid)) is None:
        raise exceptions.not_found
    return trend
