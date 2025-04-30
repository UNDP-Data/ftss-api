"""
Tests for user group operations and collaborator functionality.
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
def mock_admin_user():
    """Create a mock admin user."""
    return User(
        id=1,
        email="admin@undp.org",
        role=Role.ADMIN,
        name="Admin User",
        unit="BPPS",
    )


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user."""
    return User(
        id=2,
        email="user@undp.org",
        role=Role.USER,
        name="Regular User",
        unit="BPPS",
    )


@pytest.fixture
def mock_user_group():
    """Create a mock user group."""
    return UserGroup(
        id=1,
        name="Test Group",
        users=["user1@undp.org", "user2@undp.org"],
    )


@pytest.fixture
def mock_signal():
    """Create a mock signal with collaborators."""
    return Signal(
        id=1,
        headline="Test Signal",
        description="Test Description",
        created_by="user@undp.org",
        is_draft=True,
        collaborators=["collaborator@undp.org", "group:1"],
    )


class TestUserGroups:
    """Tests for user group operations."""

    @pytest.mark.asyncio
    @patch("src.database.user_groups.list_user_groups")
    @patch("src.authentication.authenticate_user")
    async def test_list_user_groups(
        self, mock_auth, mock_list_groups, client, mock_admin_user, mock_user_group
    ):
        """Test listing user groups."""
        mock_auth.return_value = mock_admin_user
        mock_list_groups.return_value = [mock_user_group]

        response = await client.get("/api/user-groups")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == mock_user_group.id
        assert data[0]["name"] == mock_user_group.name
        assert data[0]["users"] == mock_user_group.users

    @pytest.mark.asyncio
    @patch("src.database.user_groups.create_user_group")
    @patch("src.database.user_groups.read_user_group")
    @patch("src.authentication.authenticate_user")
    async def test_create_user_group(
        self, mock_auth, mock_read_group, mock_create_group, client, mock_admin_user, mock_user_group
    ):
        """Test creating a user group."""
        mock_auth.return_value = mock_admin_user
        mock_create_group.return_value = 1
        mock_read_group.return_value = mock_user_group

        response = await client.post(
            "/api/user-groups",
            json={"name": "Test Group", "users": ["user1@undp.org", "user2@undp.org"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_user_group.id
        assert data["name"] == mock_user_group.name
        assert data["users"] == mock_user_group.users

    @pytest.mark.asyncio
    @patch("src.database.user_groups.read_user_group")
    @patch("src.authentication.authenticate_user")
    async def test_read_user_group(
        self, mock_auth, mock_read_group, client, mock_admin_user, mock_user_group
    ):
        """Test reading a user group."""
        mock_auth.return_value = mock_admin_user
        mock_read_group.return_value = mock_user_group

        response = await client.get("/api/user-groups/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_user_group.id
        assert data["name"] == mock_user_group.name
        assert data["users"] == mock_user_group.users

    @pytest.mark.asyncio
    @patch("src.database.user_groups.update_user_group")
    @patch("src.database.user_groups.read_user_group")
    @patch("src.authentication.authenticate_user")
    async def test_update_user_group(
        self, mock_auth, mock_read_group, mock_update_group, client, mock_admin_user, mock_user_group
    ):
        """Test updating a user group."""
        mock_auth.return_value = mock_admin_user
        mock_update_group.return_value = 1
        mock_read_group.return_value = mock_user_group

        response = await client.put(
            "/api/user-groups/1",
            json={"id": 1, "name": "Updated Group", "users": ["user1@undp.org"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_user_group.id
        assert data["name"] == mock_user_group.name
        assert data["users"] == mock_user_group.users

    @pytest.mark.asyncio
    @patch("src.database.user_groups.delete_user_group")
    @patch("src.authentication.authenticate_user")
    async def test_delete_user_group(
        self, mock_auth, mock_delete_group, client, mock_admin_user
    ):
        """Test deleting a user group."""
        mock_auth.return_value = mock_admin_user
        mock_delete_group.return_value = True

        response = await client.delete("/api/user-groups/1")
        assert response.status_code == 200
        data = response.json()
        assert data is True

    @pytest.mark.asyncio
    @patch("src.database.user_groups.add_user_to_group")
    @patch("src.authentication.authenticate_user")
    async def test_add_user_to_group(
        self, mock_auth, mock_add_user, client, mock_admin_user
    ):
        """Test adding a user to a group."""
        mock_auth.return_value = mock_admin_user
        mock_add_user.return_value = True

        response = await client.post("/api/user-groups/1/users/user3@undp.org")
        assert response.status_code == 200
        data = response.json()
        assert data is True

    @pytest.mark.asyncio
    @patch("src.database.user_groups.remove_user_from_group")
    @patch("src.authentication.authenticate_user")
    async def test_remove_user_from_group(
        self, mock_auth, mock_remove_user, client, mock_admin_user
    ):
        """Test removing a user from a group."""
        mock_auth.return_value = mock_admin_user
        mock_remove_user.return_value = True

        response = await client.delete("/api/user-groups/1/users/user1@undp.org")
        assert response.status_code == 200
        data = response.json()
        assert data is True


class TestSignalCollaborators:
    """Tests for signal collaborator operations."""

    @pytest.mark.asyncio
    @patch("src.database.signals.read_signal")
    @patch("src.database.signals.can_user_edit_signal")
    @patch("src.database.signals.get_signal_collaborators")
    @patch("src.authentication.authenticate_user")
    async def test_get_signal_collaborators(
        self, mock_auth, mock_get_collaborators, mock_can_edit, mock_read_signal, 
        client, mock_regular_user, mock_signal
    ):
        """Test getting signal collaborators."""
        mock_auth.return_value = mock_regular_user
        mock_read_signal.return_value = mock_signal
        mock_can_edit.return_value = True
        mock_get_collaborators.return_value = ["collaborator@undp.org", "group:1"]

        response = await client.get("/api/signals/1/collaborators")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert "collaborator@undp.org" in data
        assert "group:1" in data

    @pytest.mark.asyncio
    @patch("src.database.signals.read_signal")
    @patch("src.database.signals.add_collaborator")
    @patch("src.authentication.authenticate_user")
    async def test_add_signal_collaborator(
        self, mock_auth, mock_add_collaborator, mock_read_signal, 
        client, mock_regular_user, mock_signal
    ):
        """Test adding a collaborator to a signal."""
        mock_auth.return_value = mock_regular_user
        mock_read_signal.return_value = mock_signal
        mock_add_collaborator.return_value = True

        # Test adding a user collaborator
        response = await client.post("/api/signals/1/collaborators/new_user@undp.org")
        assert response.status_code == 200
        data = response.json()
        assert data is True

        # Test adding a group collaborator
        response = await client.post("/api/signals/1/collaborators/group:2")
        assert response.status_code == 200
        data = response.json()
        assert data is True

    @pytest.mark.asyncio
    @patch("src.database.signals.read_signal")
    @patch("src.database.signals.remove_collaborator")
    @patch("src.authentication.authenticate_user")
    async def test_remove_signal_collaborator(
        self, mock_auth, mock_remove_collaborator, mock_read_signal, 
        client, mock_regular_user, mock_signal
    ):
        """Test removing a collaborator from a signal."""
        mock_auth.return_value = mock_regular_user
        mock_read_signal.return_value = mock_signal
        mock_remove_collaborator.return_value = True

        # Test removing a user collaborator
        response = await client.delete("/api/signals/1/collaborators/collaborator@undp.org")
        assert response.status_code == 200
        data = response.json()
        assert data is True

        # Test removing a group collaborator
        response = await client.delete("/api/signals/1/collaborators/group:1")
        assert response.status_code == 200
        data = response.json()
        assert data is True

    @pytest.mark.asyncio
    @patch("src.database.signals.read_signal")
    @patch("src.database.signals.can_user_edit_signal")
    @patch("src.authentication.authenticate_user")
    async def test_can_user_edit_signal(
        self, mock_auth, mock_can_edit, mock_read_signal, 
        client, mock_regular_user
    ):
        """Test checking if a user can edit a signal."""
        mock_auth.return_value = mock_regular_user
        mock_read_signal.return_value = mock_signal
        
        # Test when user can edit
        mock_can_edit.return_value = True
        response = await client.get("/api/signals/1/can-edit")
        assert response.status_code == 200
        data = response.json()
        assert data is True
        
        # Test when user cannot edit
        mock_can_edit.return_value = False
        response = await client.get("/api/signals/1/can-edit")
        assert response.status_code == 200
        data = response.json()
        assert data is False
