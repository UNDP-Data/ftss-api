"""
Fixtures for setting up the tests shared across the test suite.
"""

import os

import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session", params=[os.environ["API_KEY"], os.environ["API_JWT"]])
def headers(request) -> dict[str, str]:
    """Header for authentication with an API key or a JWT for a regular user (not curator or admin)."""
    return {"access_token": request.param}


@pytest.fixture(scope="session")
def headers_with_jwt(request) -> dict[str, str]:
    """Header for authentication with a JWT for a regular user (not curator or admin)."""
    return {"access_token": os.environ["API_JWT"]}
