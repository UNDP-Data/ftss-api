"""
Basic tests to ensure the authentication is required and API key works for specific endpoints.
Currently, the tests do not cover JWT-based authentication.
"""

import re
from typing import Literal

from fastapi.testclient import TestClient
from pytest import mark

from main import app

client = TestClient(app)


def get_endpoints(pattern: str, method: Literal["GET", "POST", "PUT"] | None = None):
    """
    Convenience method to get all endpoints for a specific method.

    Parameters
    ----------
    pattern : str
        A regex pattern to match against endpoint path.
    method : Literal["GET", "POST", "PUT"] | None
        An optional type of HTTP method to filter endpoints.

    Returns
    -------
    endpoints : list[tuple[str, str]]
        A list of tuples containing endpoint path and method name.
    """
    endpoints = []
    for route in app.routes:
        if re.search(pattern, route.path):
            if method is None or {method} & route.methods:
                endpoints.append((route.path, list(route.methods)[0]))
    return endpoints


def test_read_docs():
    """Ensure the documentation page is accessible without authentication."""
    response = client.get("/")
    assert response.status_code == 200, "Documentation page is inaccessible"


@mark.parametrize(
    "endpoint,method",
    get_endpoints(r"signals|trends|users|choices"),
)
def test_authentication_required(endpoint: str, method: str):
    """Check if endpoints, except for documentation, require authentication."""
    response = client.request(method, endpoint)
    assert response.status_code == 403


@mark.parametrize(
    "endpoint,status_code",
    [
        ("/signals/search", 200),
        ("/signals/export", 403),
        ("/signals/10", 200),
        ("/trends/search", 200),
        ("/trends/export", 403),
        ("/trends/10", 200),
        ("/users/search", 403),
        ("/users/me", 200),
        ("/users/1", 403),
        ("/choices", 200),
        ("/choices/status", 200),
    ],
)
def test_authentication_get(endpoint: str, status_code: int, headers: dict):
    """
    Check if authentication for GET endpoints works as expected.
    """
    response = client.get(endpoint, headers=headers)
    assert response.status_code == status_code
