"""
A router for retrieving, submitting and updating signals.
"""

import logging
from typing import Annotated, List

import pandas as pd
from fastapi import APIRouter, Depends, Path, Query, HTTPException, status
from psycopg import AsyncCursor

from .. import database as db
from .. import exceptions, genai, utils
from ..authentication import authenticate_user
from ..dependencies import require_admin, require_creator, require_curator, require_user
from ..entities import (
    Role, Signal, SignalFilters, SignalPage, Status, User, UserGroup, 
    SignalWithUserGroups, SignalCreate, SignalUpdate
)

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
    signal_data: SignalCreate,
    user: User = Depends(require_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Submit a signal to the database. If the signal has a base64 encoded image
    attachment, it will be uploaded to Azure Blob Storage.
    
    Optionally, the signal can be added to one or more user groups by specifying
    user_group_ids in the request body.
    """
    logger.info(f"Creating new signal requested by user: {user.email}")
    
    # Extract standard Signal fields and user_group_ids
    signal = Signal(**signal_data.model_dump(exclude={"user_group_ids"}))
    user_group_ids = signal_data.user_group_ids
    
    if user_group_ids:
        logger.info(f"With user_group_ids: {user_group_ids}")
    
    try:
        # Prepare the signal object
        signal.created_by = user.email
        signal.modified_by = user.email
        signal.created_unit = user.unit
        
        # Create the signal in the database with user groups if specified
        signal_id = await db.create_signal(cursor, signal, user_group_ids)
        logger.info(f"Signal created successfully with ID: {signal_id}")
        
        # Read back the created signal to return it
        created_signal = await db.read_signal(cursor, signal_id)
        if not created_signal:
            logger.error(f"Failed to read newly created signal with ID: {signal_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Signal was created but could not be retrieved"
            )
        
        return created_signal
    
    except Exception as e:
        logger.error(f"Error creating signal: {str(e)}")
        # Raise HTTPException with appropriate status code
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create signal: {str(e)}"
        )


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


@router.get("/{uid}/with-user-groups", response_model=SignalWithUserGroups)
async def read_signal_with_user_groups(
    uid: Annotated[int, Path(description="The ID of the signal to retrieve")],
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Retrieve a signal from the database along with all user groups it belongs to.
    This endpoint provides a comprehensive view of a signal including its group associations.
    """
    logger.info("Reading signal with user groups for ID: %s, user: %s", uid, user.email)
    
    try:
        # Fetch signal with user groups
        signal = await db.read_signal_with_user_groups(cursor, uid)
        
        if signal is None:
            logger.warning("Signal not found with ID: %s", uid)
            raise exceptions.not_found
        
        # Check permissions
        if user.role == Role.VISITOR and signal.status != Status.APPROVED:
            logger.warning(
                "Permission denied - visitor trying to access non-approved signal. Status: %s",
                signal.status
            )
            raise exceptions.permission_denied
        
        # Check if the signal is favorited by the user
        try:
            is_favorite = await db.is_signal_favorited(cursor, user.email, uid)
            signal.favorite = is_favorite
            logger.debug(f"Favorite status for signal {uid}, user {user.email}: {is_favorite}")
        except Exception as fav_e:
            logger.error(f"Failed to check favorite status: {str(fav_e)}")
            # Continue even if favorite check fails
            signal.favorite = False
        
        logger.info(f"Successfully retrieved signal {uid} with {len(signal.user_groups)} user groups")
        return signal
        
    except exceptions.not_found:
        raise
    except exceptions.permission_denied:
        raise
    except Exception as e:
        logger.error(f"Error retrieving signal {uid} with user groups: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve signal with user groups: {str(e)}"
        )


@router.put("/{uid}", response_model=Signal)
async def update_signal(
    uid: Annotated[int, Path(description="The ID of the signal to be updated")],
    signal_data: SignalUpdate,
    user: User = Depends(require_creator),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Update a signal in the database.
    
    Optionally, the signal's user group associations can be updated by specifying
    user_group_ids in the request body. If provided, the signal will only belong
    to the specified groups, replacing any previous group associations.
    """
    logger.info(f"Updating signal {uid} requested by user: {user.email}")
    
    # Extract signal data and user_group_ids from the request body
    signal = Signal(**signal_data.model_dump(exclude={"user_group_ids"}))
    user_group_ids = signal_data.user_group_ids
    
    if user_group_ids is not None:
        logger.info(f"With user_group_ids: {user_group_ids}")
    
    try:
        # Verify ID match
        if uid != signal.id:
            logger.warning(f"ID mismatch: URL ID {uid} doesn't match payload ID {signal.id}")
            raise exceptions.id_mismatch
        
        # Update metadata
        signal.modified_by = user.email
        
        # Update the signal in the database
        logger.info(f"Updating signal {uid} in database")
        signal_id = await db.update_signal(cursor, signal, user_group_ids)
        
        if signal_id is None:
            logger.warning(f"Signal {uid} not found during update")
            raise exceptions.not_found
        
        logger.info(f"Signal {uid} updated successfully")
        
        # Read back the updated signal
        updated_signal = await db.read_signal(cursor, signal_id)
        if not updated_signal:
            logger.error(f"Failed to read updated signal with ID: {signal_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Signal was updated but could not be retrieved"
            )
        
        return updated_signal
        
    except exceptions.id_mismatch:
        raise
    except exceptions.not_found:
        raise
    except Exception as e:
        logger.error(f"Error updating signal {uid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update signal: {str(e)}"
        )


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


@router.get("/{uid}/collaborators", response_model=List[int])
async def get_signal_collaborators(
    uid: Annotated[int, Path(description="The ID of the signal")],
    user: User = Depends(require_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Get all user IDs who can collaborate on a signal.
    
    Only signal creators, admins, curators, and current collaborators can access this endpoint.
    """
    # Check if signal exists
    if await db.read_signal(cursor, uid) is None:
        raise exceptions.not_found
    
    # Check if user is authorized to view collaborators
    if not user.is_admin and not user.is_staff and not await db.can_user_edit_signal(cursor, uid, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view collaborators for this signal",
        )
    
    collaborators = await db.get_signal_collaborators(cursor, uid)
    return collaborators


@router.post("/{uid}/collaborators/{user_id}", response_model=bool)
async def add_signal_collaborator(
    uid: Annotated[int, Path(description="The ID of the signal")],
    user_id: Annotated[int, Path(description="The ID of the user to add as collaborator")],
    user: User = Depends(require_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Add a collaborator to a signal.
    
    Only signal creators, admins, and curators can add collaborators.
    """
    # Check if signal exists
    signal = await db.read_signal(cursor, uid)
    if signal is None:
        raise exceptions.not_found
    
    # Check if user is authorized to add collaborators
    if not user.is_admin and not user.is_staff and signal.created_by != user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add collaborators to this signal",
        )
    
    # Add collaborator
    if not await db.add_collaborator(cursor, uid, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid collaborator or signal",
        )
    
    return True


@router.delete("/{uid}/collaborators/{user_id}", response_model=bool)
async def remove_signal_collaborator(
    uid: Annotated[int, Path(description="The ID of the signal")],
    user_id: Annotated[int, Path(description="The ID of the user to remove as collaborator")],
    user: User = Depends(require_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Remove a collaborator from a signal.
    
    Only signal creators, admins, and curators can remove collaborators.
    """
    # Check if signal exists
    signal = await db.read_signal(cursor, uid)
    if signal is None:
        raise exceptions.not_found
    
    # Check if user is authorized to remove collaborators
    if not user.is_admin and not user.is_staff and signal.created_by != user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to remove collaborators from this signal",
        )
    
    # Remove collaborator
    if not await db.remove_collaborator(cursor, uid, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collaborator not found or signal does not exist",
        )
    
    return True


@router.get("/{uid}/can-edit", response_model=bool)
async def can_user_edit_signal(
    uid: Annotated[int, Path(description="The ID of the signal")],
    user: User = Depends(authenticate_user),
    cursor: AsyncCursor = Depends(db.yield_cursor),
):
    """
    Check if the current user can edit a signal.
    
    A user can edit a signal if:
    1. They created the signal
    2. They are an admin or curator
    3. They are in the collaborators list
    4. They are part of a group that can collaborate on this signal
    """
    # Admins and curators can edit any signal
    if user.is_admin or user.is_staff:
        return True
    
    # Check if signal exists
    if await db.read_signal(cursor, uid) is None:
        raise exceptions.not_found
    
    return await db.can_user_edit_signal(cursor, uid, user.id)
