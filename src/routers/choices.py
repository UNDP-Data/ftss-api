"""
A router for obtaining valid choice options.
"""

from fastapi import APIRouter, Depends
from psycopg import AsyncCursor

from .. import database as db
from .. import exceptions
from ..authentication import authenticate_user
from ..entities import utils

router = APIRouter(prefix="/choices", tags=["choices"])


CREATED_FOR = [
    "General scanning",
    "Global Signals Spotlight 2024",
    "Global Signals Spotlight 2023",
    "HDR 2023",
    "Sustainable Finance Hub 2023",
]


@router.get("", response_model=dict, dependencies=[Depends(authenticate_user)])
async def read_choices(cursor: AsyncCursor = Depends(db.yield_cursor)):
    """
    List valid options for all fields.
    """
    choices = {
        name.lower(): [member.value for member in getattr(utils, name)]
        for name in utils.__all__
    }
    choices["created_for"] = CREATED_FOR
    choices["unit_name"] = await db.get_unit_names(cursor)
    choices["unit_region"] = await db.get_unit_regions(cursor)
    choices["location"] = await db.get_location_names(cursor)
    return choices


@router.get(
    "/{name}", response_model=list[str], dependencies=[Depends(authenticate_user)]
)
async def read_field_choices(name: str, cursor: AsyncCursor = Depends(db.yield_cursor)):
    """
    List valid options for a given field.
    """
    match name:
        case "unit_name":
            choices = await db.get_unit_names(cursor)
        case "unit_region":
            choices = await db.get_unit_regions(cursor)
        case "location":
            choices = await db.get_location_names(cursor)
        case name if name.capitalize() in utils.__all__:
            choices = [member.value for member in getattr(utils, name.capitalize())]
        case _:
            raise exceptions.not_found
    return choices
