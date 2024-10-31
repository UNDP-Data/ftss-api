"""
Database connection functions based on Psycopg 3 project.
"""

import os

import psycopg
from psycopg.rows import dict_row


async def get_connection() -> psycopg.AsyncConnection:
    """
    Get a connection to a PostgreSQL database.

    The connection includes a row factory to return database rows as dictionaries
    and a cursor factory that ensures client-side binding. See the
    [documentation](https://www.psycopg.org/psycopg3/docs/basic/from_pg2.html#server-side-binding)
    for details.

    Returns
    -------
    conn : psycopg.Connection
        A database connection object row and cursor factory settings.
    """
    conn = await psycopg.AsyncConnection.connect(
        conninfo=os.environ["DB_CONNECTION"],
        autocommit=False,
        row_factory=dict_row,
        cursor_factory=psycopg.AsyncClientCursor,
    )
    return conn


async def yield_cursor() -> psycopg.Cursor:
    """
    Yield a PostgreSQL database cursor object to be used for dependency injection.

    Yields
    ------
    cursor : psycopg.AsyncCursor
        A database cursor object.
    """
    # handle rollbacks from the context manager and close on exit
    async with await get_connection() as conn:
        async with conn.cursor() as cursor:
            yield cursor
