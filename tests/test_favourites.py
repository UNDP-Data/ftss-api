"""
Tests for user favorites functionality.
"""
from fastapi.testclient import TestClient

from main import app
from src.entities import Signal

client = TestClient(app)

def test_favourite_crud(headers_with_jwt: dict):
    """Test creating, reading, and deleting favorites."""
    # First create two test signals to favorite
    signal1 = Signal(**Signal.model_config["json_schema_extra"]["example"])
    signal2 = Signal(**Signal.model_config["json_schema_extra"]["example"])


    print("___ signal2 ___", signal2)

    # Create the signals
    endpoint = "/signals"
    response1 = client.post(
        endpoint, json=signal1.model_dump(), headers=headers_with_jwt
    )
    assert response1.status_code == 201
    signal1_data = response1.json()

    response2 = client.post(
        endpoint, json=signal2.model_dump(), headers=headers_with_jwt
    )
    assert response2.status_code == 201
    signal2_data = response2.json()

    # Favorite both signals
    endpoint = f"/favourites/{signal1_data['id']}"
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    assert response.json()["status"] == "created"

    endpoint = f"/favourites/{signal2_data['id']}"
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    assert response.json()["status"] == "created"

    # Get list of favorites
    endpoint = "/favourites"
    response = client.get(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    favorites = response.json()
    assert len(favorites) == 2
    assert favorites[0]["id"] in {signal1_data["id"], signal2_data["id"]}
    assert favorites[1]["id"] in {signal1_data["id"], signal2_data["id"]}

    # Unfavorite one signal
    endpoint = f"/favourites/{signal1_data['id']}"
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    # Verify only one favorite remains
    endpoint = "/favourites"
    response = client.get(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    favorites = response.json()
    assert len(favorites) == 1
    assert favorites[0]["id"] == signal2_data["id"]

    # Clean up created signals
    for signal_id in [signal1_data["id"], signal2_data["id"]]:
        endpoint = f"/signals/{signal_id}"
        response = client.delete(endpoint, headers=headers_with_jwt)
        assert response.status_code == 200


def test_favourite_nonexistent_signal(headers_with_jwt: dict):
    """Test attempting to favorite a nonexistent signal."""
    endpoint = "/favourites/99999"  # Using an ID that shouldn't exist
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_favourites_unauthorized():
    """Test accessing favorites endpoints without authentication."""
    # Try to get favorites without auth
    endpoint = "/favourites"
    response = client.get(endpoint)
    assert response.status_code == 401

    # Try to create favorite without auth
    endpoint = "/favourites/1"
    response = client.post(endpoint)
    assert response.status_code == 401
