"""
Unit tests for user groups database methods.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.entities import UserGroup
from src.database.user_groups import (
    create_user_group,
    read_user_group,
    update_user_group,
    delete_user_group,
    list_user_groups,
    add_user_to_group,
    remove_user_from_group,
    get_user_groups,
    get_group_users,
)


@pytest.fixture
def mock_cursor():
    """Create a mock database cursor."""
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock()
    cursor.fetchall = AsyncMock()
    return cursor


@pytest.fixture
def mock_user_group():
    """Create a mock user group."""
    return UserGroup(
        id=1,
        name="Test Group",
        users=["user1@undp.org", "user2@undp.org"],
    )


class TestUserGroupsDatabaseMethods:
    """Tests for user groups database methods."""

    @pytest.mark.asyncio
    async def test_create_user_group(self, mock_cursor, mock_user_group):
        """Test creating a user group."""
        # Mock the database response
        mock_cursor.fetchone.return_value = (1,)
        
        # Call the function
        group_id = await create_user_group(mock_cursor, mock_user_group)
        
        # Check the result
        assert group_id == 1
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "INSERT INTO user_groups" in args[0]
        assert kwargs["name"] == mock_user_group.name

    @pytest.mark.asyncio
    async def test_read_user_group(self, mock_cursor, mock_user_group):
        """Test reading a user group."""
        # Mock the database response
        mock_cursor.fetchone.return_value = (1, "Test Group", ["user1@undp.org", "user2@undp.org"])
        
        # Call the function
        group = await read_user_group(mock_cursor, 1)
        
        # Check the result
        assert group.id == mock_user_group.id
        assert group.name == mock_user_group.name
        assert group.users == mock_user_group.users
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "FROM user_groups" in args[0]
        assert args[1] == (1,)

    @pytest.mark.asyncio
    async def test_read_user_group_not_found(self, mock_cursor):
        """Test reading a non-existent user group."""
        # Mock the database response
        mock_cursor.fetchone.return_value = None
        
        # Call the function
        group = await read_user_group(mock_cursor, 99)
        
        # Check the result
        assert group is None
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "FROM user_groups" in args[0]
        assert args[1] == (99,)

    @pytest.mark.asyncio
    async def test_update_user_group(self, mock_cursor, mock_user_group):
        """Test updating a user group."""
        # Mock the database response
        mock_cursor.fetchone.return_value = (1,)
        
        # Call the function
        group_id = await update_user_group(mock_cursor, mock_user_group)
        
        # Check the result
        assert group_id == 1
        
        # Verify the SQL was executed with the correct parameters
        assert mock_cursor.execute.call_count >= 2  # Update + delete existing members
        
        # Check the update query
        args, kwargs = mock_cursor.execute.call_args_list[0]
        assert "UPDATE user_groups" in args[0]
        assert kwargs["id"] == mock_user_group.id
        assert kwargs["name"] == mock_user_group.name

    @pytest.mark.asyncio
    async def test_delete_user_group(self, mock_cursor):
        """Test deleting a user group."""
        # Mock the database response
        mock_cursor.fetchone.return_value = (1,)
        
        # Call the function
        result = await delete_user_group(mock_cursor, 1)
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        assert mock_cursor.execute.call_count == 2  # Delete members + delete group
        
        # Check the delete query
        args, kwargs = mock_cursor.execute.call_args_list[1]
        assert "DELETE FROM user_groups" in args[0]
        assert args[1] == (1,)

    @pytest.mark.asyncio
    async def test_list_user_groups(self, mock_cursor, mock_user_group):
        """Test listing user groups."""
        # Mock the database cursor behavior
        mock_row = (1, "Test Group", ["user1@undp.org", "user2@undp.org"])
        
        # We need to make the cursor iterable to simulate async for loop
        mock_cursor.__aiter__.return_value = [mock_row]
        
        # Call the function
        groups = await list_user_groups(mock_cursor)
        
        # Check the result
        assert len(groups) == 1
        assert groups[0].id == mock_user_group.id
        assert groups[0].name == mock_user_group.name
        assert groups[0].users == mock_user_group.users
        
        # Verify the SQL was executed
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "FROM user_groups" in args[0]

    @pytest.mark.asyncio
    async def test_add_user_to_group(self, mock_cursor):
        """Test adding a user to a group."""
        # Mock the database responses for each query
        mock_cursor.fetchone.side_effect = [(1,), (1,), (1,)]
        
        # Call the function
        result = await add_user_to_group(mock_cursor, 1, "user3@undp.org")
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        assert mock_cursor.execute.call_count == 3  # Check user + check group + add
        
        # Check the insert query
        args, kwargs = mock_cursor.execute.call_args_list[2]
        assert "INSERT INTO user_group_members" in args[0]
        assert args[1] == (1, "user3@undp.org")

    @pytest.mark.asyncio
    async def test_remove_user_from_group(self, mock_cursor):
        """Test removing a user from a group."""
        # Mock the database response
        mock_cursor.fetchone.return_value = (1,)
        
        # Call the function
        result = await remove_user_from_group(mock_cursor, 1, "user1@undp.org")
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "DELETE FROM user_group_members" in args[0]
        assert args[1] == (1, "user1@undp.org")

    @pytest.mark.asyncio
    async def test_get_user_groups(self, mock_cursor, mock_user_group):
        """Test getting groups for a user."""
        # Mock the database cursor behavior
        mock_row = (1, "Test Group", ["user1@undp.org", "user2@undp.org"])
        
        # We need to make the cursor iterable to simulate async for loop
        mock_cursor.__aiter__.return_value = [mock_row]
        
        # Call the function
        groups = await get_user_groups(mock_cursor, "user1@undp.org")
        
        # Check the result
        assert len(groups) == 1
        assert groups[0].id == mock_user_group.id
        assert groups[0].name == mock_user_group.name
        assert groups[0].users == mock_user_group.users
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "WHERE m.user_email = %s" in args[0]
        assert args[1] == ("user1@undp.org",)

    @pytest.mark.asyncio
    async def test_get_group_users(self, mock_cursor):
        """Test getting users in a group."""
        # Mock the database cursor behavior
        mock_cursor.__aiter__.return_value = [("user1@undp.org",), ("user2@undp.org",)]
        
        # Call the function
        users = await get_group_users(mock_cursor, 1)
        
        # Check the result
        assert len(users) == 2
        assert "user1@undp.org" in users
        assert "user2@undp.org" in users
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "WHERE m.group_id = %s" in args[0]
 