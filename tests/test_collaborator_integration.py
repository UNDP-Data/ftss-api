"""
Integration tests for signal collaboration functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient

from src.entities import UserGroup, User, Role, Signal
from src.app import create_application


@pytest.fixture
def app():
    """Create a test application."""
    return create_application(configure_oauth=False, debug=True)


@pytest_asyncio.fixture
async def client(app: FastAPI):
    """Create a test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_signal_owner():
    """Create a mock owner user."""
    return User(
        id=1,
        email="owner@undp.org",
        role=Role.USER,
        name="Signal Owner",
        unit="BPPS",
    )


@pytest.fixture
def mock_user_group():
    """Create a mock user group."""
    return UserGroup(
        id=1,
        name="Test Group",
        users=["member1@undp.org", "member2@undp.org"],
    )


@pytest.fixture
def mock_draft_signal():
    """Create a mock draft signal."""
    return Signal(
        id=1,
        headline="Draft Signal",
        description="This is a draft signal",
        created_by="owner@undp.org",
        is_draft=True,
        collaborators=["collaborator@undp.org", "group:1"],
    )


@pytest.mark.asyncio
@patch("src.database.user_groups.create_user_group")
@patch("src.database.user_groups.read_user_group")
@patch("src.authentication.authenticate_user")
async def test_create_group_and_add_members(
    mock_auth, mock_read_group, mock_create_group, client, mock_signal_owner, mock_user_group
):
    """Test creating a group and adding members."""
    # Configure mocks
    mock_auth.return_value = mock_signal_owner
    mock_create_group.return_value = 1
    mock_read_group.return_value = mock_user_group
    
    # Mock signal owner to be an admin to allow group creation
    mock_signal_owner.role = Role.ADMIN
    
    # Create the group
    group_response = await client.post(
        "/api/user-groups",
        json={"name": "Test Group", "users": ["member1@undp.org", "member2@undp.org"]},
    )
    assert group_response.status_code == 200
    group_data = group_response.json()
    assert group_data["id"] == 1
    assert "member1@undp.org" in group_data["users"]
    assert "member2@undp.org" in group_data["users"]
    
    # Add another member
    mock_user_group.users.append("member3@undp.org")
    add_member_response = await client.post("/api/user-groups/1/users/member3@undp.org")
    assert add_member_response.status_code == 200
    assert add_member_response.json() is True


@pytest.mark.asyncio
@patch("src.database.signals.create_signal")
@patch("src.database.signals.read_signal")
@patch("src.database.signals.add_collaborator")
@patch("src.authentication.authenticate_user")
async def test_create_draft_signal_with_collaborators(
    mock_auth, mock_add_collaborator, mock_read_signal, mock_create_signal, 
    client, mock_signal_owner, mock_draft_signal
):
    """Test creating a draft signal with collaborators."""
    # Configure mocks
    mock_auth.return_value = mock_signal_owner
    mock_create_signal.return_value = 1
    mock_read_signal.return_value = mock_draft_signal
    mock_add_collaborator.return_value = True
    
    # Create the draft signal
    signal_data = {
        "headline": "Draft Signal",
        "description": "This is a draft signal",
        "is_draft": True,
        "collaborators": ["collaborator@undp.org", "group:1"]
    }
    
    signal_response = await client.post("/api/signals", json=signal_data)
    assert signal_response.status_code == 201  # Created
    
    response_data = signal_response.json()
    assert response_data["headline"] == "Draft Signal"
    assert response_data["is_draft"] is True
    
    # Verify collaborators were added
    mock_add_collaborator.assert_any_call(
        mock_create_signal.return_value, "collaborator@undp.org"
    )
    mock_add_collaborator.assert_any_call(
        mock_create_signal.return_value, "group:1"
    )


@pytest.mark.asyncio
@patch("src.database.signals.read_signal")
@patch("src.database.signals.can_user_edit_signal")
@patch("src.database.signals.get_signal_collaborators")
@patch("src.authentication.authenticate_user")
async def test_non_owner_can_edit_draft_as_collaborator(
    mock_auth, mock_get_collaborators, mock_can_edit, mock_read_signal,
    client, mock_draft_signal
):
    """Test that a collaborator can edit a draft signal created by someone else."""
    # Create a collaborator user
    collaborator_user = User(
        id=2,
        email="collaborator@undp.org",
        role=Role.USER,
        name="Collaborator",
        unit="BPPS",
    )
    
    # Configure mocks
    mock_auth.return_value = collaborator_user
    mock_read_signal.return_value = mock_draft_signal
    mock_can_edit.return_value = True
    mock_get_collaborators.return_value = ["collaborator@undp.org", "group:1"]
    
    # Check if user can edit
    can_edit_response = await client.get("/api/signals/1/can-edit")
    assert can_edit_response.status_code == 200
    assert can_edit_response.json() is True
    
    # Get collaborators
    collaborators_response = await client.get("/api/signals/1/collaborators")
    assert collaborators_response.status_code == 200
    collaborators = collaborators_response.json()
    assert "collaborator@undp.org" in collaborators
    assert "group:1" in collaborators


@pytest.mark.asyncio
@patch("src.database.signals.read_signal")
@patch("src.database.signals.can_user_edit_signal")
@patch("src.authentication.authenticate_user")
async def test_non_collaborator_cannot_edit_draft(
    mock_auth, mock_can_edit, mock_read_signal,
    client, mock_draft_signal
):
    """Test that a non-collaborator cannot edit a draft signal created by someone else."""
    # Create a non-collaborator user
    non_collaborator = User(
        id=3,
        email="random@undp.org",
        role=Role.USER,
        name="Random User",
        unit="BPPS",
    )
    
    # Configure mocks
    mock_auth.return_value = non_collaborator
    mock_read_signal.return_value = mock_draft_signal
    mock_can_edit.return_value = False
    
    # Check if user can edit
    can_edit_response = await client.get("/api/signals/1/can-edit")
    assert can_edit_response.status_code == 200
    assert can_edit_response.json() is False


@pytest.mark.asyncio
@patch("src.database.signals.read_signal")
@patch("src.database.signals.remove_collaborator")
@patch("src.authentication.authenticate_user")
async def test_remove_collaborator_from_signal(
    mock_auth, mock_remove_collaborator, mock_read_signal,
    client, mock_signal_owner, mock_draft_signal
):
    """Test removing a collaborator from a signal."""
    # Configure mocks
    mock_auth.return_value = mock_signal_owner
    mock_read_signal.return_value = mock_draft_signal
    mock_remove_collaborator.return_value = True
    
    # Remove user collaborator
    user_response = await client.delete("/api/signals/1/collaborators/collaborator@undp.org")
    assert user_response.status_code == 200
    assert user_response.json() is True
    
    # Remove group collaborator
    group_response = await client.delete("/api/signals/1/collaborators/group:1")
    assert group_response.status_code == 200
    assert group_response.json() is True
    
    # Verify remove collaborator was called with correct parameters
    mock_remove_collaborator.assert_any_call(1, "collaborator@undp.org")
    mock_remove_collaborator.assert_any_call(1, "group:1")


@pytest.mark.asyncio
@patch("src.database.signals.update_signal")
@patch("src.database.signals.read_signal")
@patch("src.authentication.authenticate_user")
async def test_publish_draft_signal(
    mock_auth, mock_read_signal, mock_update_signal,
    client, mock_signal_owner, mock_draft_signal
):
    """Test publishing a draft signal."""
    # Configure mocks
    mock_auth.return_value = mock_signal_owner
    
    # For the first read_signal call (checking if user can edit)
    mock_draft_signal_copy = mock_draft_signal.model_copy()
    mock_read_signal.return_value = mock_draft_signal_copy
    
    # For the second read_signal call (after update)
    published_signal = mock_draft_signal.model_copy(update={"is_draft": False})
    mock_read_signal.side_effect = [mock_draft_signal_copy, published_signal]
    
    mock_update_signal.return_value = 1
    
    # Update signal to change from draft to published
    update_data = {
        "id": 1,
        "headline": "Draft Signal",
        "description": "This is a draft signal",
        "is_draft": False,  # Now published
        "created_by": "owner@undp.org",
        "collaborators": ["collaborator@undp.org", "group:1"],
    }
    
    update_response = await client.put("/api/signals/1", json=update_data)
    assert update_response.status_code == 200
    
    response_data = update_response.json()
    assert response_data["is_draft"] is False  # Verify it's now published 