"""
CRUD operations for trend entities.
"""

from psycopg import AsyncCursor, sql

from .. import storage
from ..entities import Trend, TrendFilters, TrendPage

__all__ = [
    "search_trends",
    "create_trend",
    "read_trend",
    "update_trend",
    "delete_trend",
]


async def search_trends(cursor: AsyncCursor, filters: TrendFilters) -> TrendPage:
    """
    Search signals in the database using filters and pagination.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    filters : TrendFilters
        Query filters for search, including pagination.

    Returns
    -------
    page : TrendPage
        Paginated search results for trends.
    """
    query = """
        SELECT 
            *, COUNT(*) OVER() AS total_count
        FROM
            trends AS t
        LEFT OUTER JOIN (
            SELECT
                trend_id, array_agg(signal_id) AS connected_signals
            FROM
                connections
            GROUP BY
                trend_id
            ) AS c
        ON
            t.id = c.trend_id
        WHERE
             (%(ids)s IS NULL OR id = ANY(%(ids)s))
             AND status = ANY(%(statuses)s)
             AND (%(created_by)s IS NULL OR created_by = %(created_by)s)
             AND (%(created_for)s IS NULL OR created_for = %(created_for)s)
             AND (%(steep_primary)s IS NULL OR steep_primary = %(steep_primary)s)
             AND (%(steep_secondary)s IS NULL OR steep_secondary && %(steep_secondary)s)
             AND (%(signature_primary)s IS NULL OR signature_primary = %(signature_primary)s)
             AND (%(signature_secondary)s IS NULL OR signature_secondary && %(signature_secondary)s)
             AND (%(sdgs)s IS NULL OR sdgs && %(sdgs)s)
             AND (%(assigned_to)s IS NULL OR assigned_to = %(assigned_to)s)
             AND (%(time_horizon)s IS NULL OR time_horizon = %(time_horizon)s)
             AND (%(impact_rating)s IS NULL OR impact_rating = %(impact_rating)s)
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
    page = TrendPage.from_search(rows, filters)
    return page


async def create_trend(cursor: AsyncCursor, trend: Trend) -> int:
    """
    Insert a trend into the database, connect it to signals and upload an attachment
    to Azure Blob Storage if applicable.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    trend : Trend
        A trend object to insert.

    Returns
    -------
    trend_id : int
        An ID of the trend in the database.
    """
    query = """
        INSERT INTO trends (
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
            assigned_to,
            time_horizon,
            impact_rating, 
            impact_description
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
            %(assigned_to)s,
            %(time_horizon)s,
            %(impact_rating)s,
            %(impact_description)s
        )
        RETURNING
            id
        ;
    """
    await cursor.execute(query, trend.model_dump())
    row = await cursor.fetchone()
    trend_id = row["id"]

    # add connected signals if any are present
    for signal_id in trend.connected_signals or []:
        query = "INSERT INTO connections (signal_id, trend_id, created_by) VALUES (%s, %s, %s);"
        await cursor.execute(query, (signal_id, trend_id, trend.created_by))

    # upload an image
    if trend.attachment is not None:
        try:
            blob_url = await storage.upload_image(trend_id, "trends", trend.attachment)
        except Exception as e:
            print(e)
        else:
            query = "UPDATE trends SET attachment = %s WHERE id = %s;"
            await cursor.execute(query, (blob_url, trend_id))
    return trend_id


async def read_trend(cursor: AsyncCursor, uid: int) -> Trend | None:
    """
    Read a trend from the database using an ID.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    uid : int
        An ID of the trend to retrieve data for.

    Returns
    -------
    Trend | None
        A trend if it exits, otherwise None.
    """
    query = """
    SELECT 
        * 
    FROM 
        trends AS t
    LEFT OUTER JOIN (
        SELECT
            trend_id, array_agg(signal_id) AS connected_signals
        FROM
            connections
        GROUP BY
            trend_id
        ) AS c
    ON
        t.id = c.trend_id 
    WHERE 
        id = %s
    ;
    """
    await cursor.execute(query, (uid,))
    if (row := await cursor.fetchone()) is None:
        return None
    return Trend(**row)


async def update_trend(cursor: AsyncCursor, trend: Trend) -> int | None:
    """
    Update a trend in the database, update its connected signals and update an attachment
    in the Azure Blob Storage if applicable.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    trend : Trend
        A trend object to update.

    Returns
    -------
    int | None
        A trend ID if the update has been performed, otherwise None.
    """
    query = """
        UPDATE
            trends
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
             assigned_to = COALESCE(%(assigned_to)s, assigned_to),
             time_horizon = COALESCE(%(time_horizon)s, time_horizon),
             impact_rating = COALESCE(%(impact_rating)s, impact_rating),
             impact_description = COALESCE(%(impact_description)s, impact_description)
        WHERE
            id = %(id)s
        RETURNING
            id
        ;
    """
    await cursor.execute(query, trend.model_dump())
    if (row := await cursor.fetchone()) is None:
        return None
    trend_id = row["id"]

    # update connected signals if any are present
    await cursor.execute("DELETE FROM connections WHERE trend_id = %s;", (trend_id,))
    for signal_id in trend.connected_signals or []:
        query = "INSERT INTO connections (signal_id, trend_id, created_by) VALUES (%s, %s, %s);"
        await cursor.execute(query, (signal_id, trend_id, trend.created_by))

    # upload an image if it is not a URL to an existing image
    blob_url = await storage.update_image(trend_id, "trends", trend.attachment)
    query = "UPDATE trends SET attachment = %s WHERE id = %s;"
    await cursor.execute(query, (blob_url, trend_id))

    return trend_id


async def delete_trend(cursor: AsyncCursor, uid: int) -> Trend | None:
    """
    Delete a trend from the database and, if applicable, an image from
    Azure Blob Storage, using an ID.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.
    uid : int
        An ID of the signal to delete.

    Returns
    -------
    Trend | None
        A deleted trend object if the operation has been successful, otherwise None.
    """
    query = "DELETE FROM trends WHERE id = %s RETURNING *;"
    await cursor.execute(query, (uid,))
    if (row := await cursor.fetchone()) is None:
        return None
    trend = Trend(**row)
    if trend.attachment is not None:
        await storage.delete_image(entity_id=trend.id, folder_name="trends")
    return trend
