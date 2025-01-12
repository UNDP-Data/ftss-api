"""
Fixtures for setting up the tests shared across the test suite.
"""

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import psycopg
import pytest
from dotenv import load_dotenv

from src.entities import Role, User

# Load environment variables from .env
load_dotenv()

# Set default test values if not in .env
if "API_KEY" not in os.environ:
    os.environ["API_KEY"] = "test-key"
if "DB_CONNECTION" not in os.environ:
    os.environ["DB_CONNECTION"] = "postgresql://postgres:password@localhost:5432/postgres"
if "SAS_URL" not in os.environ:
    os.environ["SAS_URL"] = "https://test.blob.core.windows.net/test"

# Set development mode for testing
os.environ["ENV_MODE"] = "local"


@pytest.fixture(scope="session", params=[os.environ["API_KEY"]])
def headers(request) -> dict[str, str]:
    """Header for authentication with an API key."""
    return {"access_token": request.param}


@pytest.fixture
def headers_with_jwt():
    """Return headers with a mock JWT token."""
    return {"access_token": "test-admin-token"}


@pytest.fixture
def mock_auth():
    """Mock user authentication to always succeed with admin privileges."""
    mock_user = User(
        id=1,
        created_at="2025-01-12T10:33:39.727968",
        email="test.user@undp.org",
        name="Test User",
        role=Role.ADMIN,
    )
    
    async def mock_auth_func():
        return mock_user
    
    with patch("src.authentication.authenticate_user", mock_auth_func), \
         patch("src.dependencies.authenticate_user", mock_auth_func), \
         patch("src.dependencies.require_admin", mock_auth_func):
        yield mock_user


@pytest.fixture
def mock_user_auth():
    """Mock user authentication for a regular user."""
    def create_mock_user(email: str = "test.user@undp.org", role: Role = Role.USER):
        user = User(
            id=2,
            created_at=datetime.now().isoformat(),
            email=email,
            name="Test User",
            role=role,
        )
        
        async def mock_auth_func():
            return user
        
        return user, mock_auth_func
    
    return create_mock_user


@pytest.fixture(autouse=True)
def mock_storage():
    """Mock Azure Storage operations."""
    with patch("src.storage.get_container_client"), \
         patch("src.storage.update_image") as mock_update_image, \
         patch("src.storage.delete_image") as mock_delete_image:
        mock_update_image.return_value = None
        mock_delete_image.return_value = None
        yield


@pytest.fixture(autouse=True)
def mock_token_validation():
    """Mock JWT token validation to always succeed."""
    async def mock_decode_token(token: str) -> dict:
        if token == "test-admin-token":
            return {"unique_name": "test.user@undp.org", "name": "Test User"}
        elif token == "test-user-token":
            return {"unique_name": "test.regular@undp.org", "name": "Regular User"}
        elif token.startswith("mock-jwt-token-"):
            parts = token.split("-")
            if len(parts) >= 4:
                email = parts[2]
                return {"unique_name": email, "name": "Test User"}
        return {"unique_name": "test.visitor@undp.org", "name": "Test User"}

    with patch("src.authentication.decode_token", mock_decode_token):
        yield
