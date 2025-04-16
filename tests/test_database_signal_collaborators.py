"""
Unit tests for signal collaborator database methods.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.entities import Signal
from src.database.signals import (
    add_collaborator,
    remove_collaborator,
    get_signal_collaborators,
    can_user_edit_signal,
)


@pytest.fixture
def mock_cursor():
    """Create a mock database cursor."""
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock()
    cursor.fetchall = AsyncMock()
    return cursor


@pytest.fixture
def mock_signal():
    """Create a mock signal with collaborators."""
    return Signal(
        id=1,
        headline="Test Signal",
        description="Test Description",
        created_by="owner@undp.org",
        is_draft=True,
        collaborators=["collaborator@undp.org", "group:1"],
    )


class TestSignalCollaboratorsDatabaseMethods:
    """Tests for signal collaborators database methods."""

    @pytest.mark.asyncio
    async def test_add_collaborator_user(self, mock_cursor):
        """Test adding a user collaborator to a signal."""
        # Mock the database response
        mock_cursor.fetchone.side_effect = [(1,), (1,), (1,)]
        
        # Call the function
        result = await add_collaborator(mock_cursor, 1, "collaborator@undp.org")
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        assert mock_cursor.execute.call_count == 3  # Check signal + check user + add
        
        # Check the insert query
        args, kwargs = mock_cursor.execute.call_args_list[2]
        assert "INSERT INTO signal_collaborators" in args[0]
        assert args[1] == (1, "collaborator@undp.org")

    @pytest.mark.asyncio
    async def test_add_collaborator_group(self, mock_cursor):
        """Test adding a group collaborator to a signal."""
        # Mock the database response
        mock_cursor.fetchone.side_effect = [(1,), (1,)]
        
        # Call the function
        result = await add_collaborator(mock_cursor, 1, "group:2")
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        assert mock_cursor.execute.call_count == 2  # Check signal + add
        
        # Check the insert query
        args, kwargs = mock_cursor.execute.call_args_list[1]
        assert "INSERT INTO signal_collaborator_groups" in args[0]
        assert args[1] == (1, 2)

    @pytest.mark.asyncio
    async def test_add_collaborator_signal_not_found(self, mock_cursor):
        """Test adding a collaborator to a non-existent signal."""
        # Mock the database response
        mock_cursor.fetchone.return_value = None
        
        # Call the function
        result = await add_collaborator(mock_cursor, 99, "collaborator@undp.org")
        
        # Check the result
        assert result is False
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "SELECT 1 FROM signals" in args[0]
        assert args[1] == (99,)

    @pytest.mark.asyncio
    async def test_remove_collaborator_user(self, mock_cursor):
        """Test removing a user collaborator from a signal."""
        # Mock the database response
        mock_cursor.fetchone.return_value = (1,)
        
        # Call the function
        result = await remove_collaborator(mock_cursor, 1, "collaborator@undp.org")
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "DELETE FROM signal_collaborators" in args[0]
        assert args[1] == (1, "collaborator@undp.org")

    @pytest.mark.asyncio
    async def test_remove_collaborator_group(self, mock_cursor):
        """Test removing a group collaborator from a signal."""
        # Mock the database response
        mock_cursor.fetchone.return_value = (1,)
        
        # Call the function
        result = await remove_collaborator(mock_cursor, 1, "group:2")
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "DELETE FROM signal_collaborator_groups" in args[0]
        assert args[1] == (1, 2)

    @pytest.mark.asyncio
    async def test_get_signal_collaborators(self, mock_cursor):
        """Test getting collaborators for a signal."""
        # Mock the database cursor behavior for user collaborators
        mock_cursor.__aiter__.side_effect = [
            [("user1@undp.org",), ("user2@undp.org",)],  # First query result
            [(1,), (2,)]  # Second query result
        ]
        
        # Call the function
        collaborators = await get_signal_collaborators(mock_cursor, 1)
        
        # Check the result
        assert len(collaborators) == 4
        assert "user1@undp.org" in collaborators
        assert "user2@undp.org" in collaborators
        assert "group:1" in collaborators
        assert "group:2" in collaborators
        
        # Verify the SQL was executed with the correct parameters
        assert mock_cursor.execute.call_count == 2
        args1, kwargs1 = mock_cursor.execute.call_args_list[0]
        assert "FROM signal_collaborators" in args1[0]
        assert args1[1] == (1,)
        
        args2, kwargs2 = mock_cursor.execute.call_args_list[1]
        assert "FROM signal_collaborator_groups" in args2[0]
        assert args2[1] == (1,)

    @pytest.mark.asyncio
    async def test_can_user_edit_signal_creator(self, mock_cursor):
        """Test checking if the creator can edit a signal."""
        # Mock the database response
        mock_cursor.fetchone.return_value = (1,)
        
        # Call the function
        result = await can_user_edit_signal(mock_cursor, 1, "owner@undp.org")
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        mock_cursor.execute.assert_called_once()
        args, kwargs = mock_cursor.execute.call_args
        assert "WHERE id = %s AND created_by = %s" in args[0]
        assert args[1] == (1, "owner@undp.org")

    @pytest.mark.asyncio
    async def test_can_user_edit_signal_collaborator(self, mock_cursor):
        """Test checking if a collaborator can edit a signal."""
        # Mock the database responses
        mock_cursor.fetchone.side_effect = [None, (1,)]
        
        # Call the function
        result = await can_user_edit_signal(mock_cursor, 1, "collaborator@undp.org")
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        assert mock_cursor.execute.call_count == 2
        
        # First check creator
        args1, kwargs1 = mock_cursor.execute.call_args_list[0]
        assert "WHERE id = %s AND created_by = %s" in args1[0]
        assert args1[1] == (1, "collaborator@undp.org")
        
        # Then check direct collaborator
        args2, kwargs2 = mock_cursor.execute.call_args_list[1]
        assert "FROM signal_collaborators" in args2[0]
        assert args2[1] == (1, "collaborator@undp.org")

    @pytest.mark.asyncio
    async def test_can_user_edit_signal_group_member(self, mock_cursor):
        """Test checking if a group member can edit a signal."""
        # Mock the database responses
        mock_cursor.fetchone.side_effect = [None, None, (1,)]
        
        # Call the function
        result = await can_user_edit_signal(mock_cursor, 1, "group_member@undp.org")
        
        # Check the result
        assert result is True
        
        # Verify the SQL was executed with the correct parameters
        assert mock_cursor.execute.call_count == 3
        
        # First check creator
        args1, kwargs1 = mock_cursor.execute.call_args_list[0]
        assert "WHERE id = %s AND created_by = %s" in args1[0]
        
        # Then check direct collaborator
        args2, kwargs2 = mock_cursor.execute.call_args_list[1]
        assert "FROM signal_collaborators" in args2[0]
        
        # Finally check group member
        args3, kwargs3 = mock_cursor.execute.call_args_list[2]
        assert "FROM signal_collaborator_groups" in args3[0]
        assert "JOIN user_group_members" in args3[0]
        assert args3[1] == (1, "group_member@undp.org")

    @pytest.mark.asyncio
    async def test_can_user_edit_signal_no_permission(self, mock_cursor):
        """Test checking if a user without permission can edit a signal."""
        # Mock the database responses
        mock_cursor.fetchone.side_effect = [None, None, None]
        
        # Call the function
        result = await can_user_edit_signal(mock_cursor, 1, "random@undp.org")
        
        # Check the result
        assert result is False
        
        # Verify all three checks were performed
 