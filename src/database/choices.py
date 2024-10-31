"""
Functions for reading data related to choice lists.
"""

from psycopg import AsyncCursor

__all__ = ["get_unit_names", "get_unit_regions", "get_location_names"]


async def get_unit_names(cursor: AsyncCursor) -> list[str]:
    """
    Read unit names from the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.

    Returns
    -------
    list[str]
        A list of unit names.
    """
    await cursor.execute("SELECT name FROM units ORDER BY name;")
    return [row["name"] async for row in cursor]


async def get_unit_regions(cursor: AsyncCursor) -> list[str]:
    """
    Read unit regions from the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.

    Returns
    -------
    list[str]
        A list of unique unit regions.
    """
    await cursor.execute("SELECT DISTINCT region FROM units ORDER BY region;")
    return [row["region"] async for row in cursor]


async def get_location_names(cursor: AsyncCursor) -> list[str]:
    """
    Read location names from the database.

    Parameters
    ----------
    cursor : AsyncCursor
        An async database cursor.

    Returns
    -------
    list[str]
        A list of location names that includes geographic regions,
        countries and territories based on UNSD M49.
    """
    # do not order by so that regions to appear first
    await cursor.execute("SELECT name FROM locations;")
    return [row["name"] async for row in cursor]
