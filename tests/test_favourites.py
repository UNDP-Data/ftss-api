"""
Tests for user favorites functionality.
"""
from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient
from pytest import mark

from main import app
from src.entities import Goal, Signal, Trend
from src.entities.utils import Horizon, Rating, Signature, Status, Steep

client = TestClient(app)

@pytest.fixture
def test_signal() -> Signal:
    """Fixture to create a test signal."""
    signal_data = {
        "headline": "The cost of corruption",
        "description": "Corruption is one of the scourges of modern life. Its costs are staggering.",
        "status": Status.NEW.value,
        "url": "https://undp.medium.com/the-cost-of-corruption-a827306696fb",
        "relevance": "Of the approximately US$13 trillion that governments spend on public spending, up to 25 percent is lost to corruption.",
        "keywords": ["economy", "governance"],
        "location": "Global",
        "steep_primary": Steep.ECONOMIC.value,
        "steep_secondary": [Steep.SOCIAL.value],
        "signature_primary": Signature.GOVERNANCE.value,
        "signature_secondary": [Signature.POVERTY.value, Signature.RESILIENCE.value],
        "sdgs": [Goal.G16.value, Goal.G17.value]
    }
    return Signal.model_validate(signal_data)

@pytest.fixture
def test_trends(headers_with_jwt: dict) -> Generator[list[Dict[str, Any]], None, None]:
    """Fixture that creates test trends."""
    trends = []
    base_trend_data = {
        "headline": "Test Trend",
        "description": "Test Description",
        "status": Status.NEW.value,
        "steep_primary": Steep.ECONOMIC.value,
        "steep_secondary": [Steep.SOCIAL.value],
        "signature_primary": Signature.GOVERNANCE.value,
        "signature_secondary": [Signature.POVERTY.value],
        "sdgs": [Goal.G16.value],
        "time_horizon": Horizon.SHORT.value,
        "impact_rating": Rating.HIGH.value,
        "impact_description": "Test impact"
    }
    
    for i in range(2):
        trend_data = {**base_trend_data, "headline": f"Test Trend {i}"}
        trend = Trend.model_validate(trend_data)
        response = client.post("/trends", json=trend.model_dump(), headers=headers_with_jwt)
        if response.status_code == 201:
            trends.append(response.json())
        else:
            pytest.skip("User does not have permission to create trends")
    
    if not trends:
        pytest.skip("No trends were created")
    
    yield trends
    
    # Cleanup - don't assert status code since trends might be deleted
    for trend_data in trends:
        endpoint = f"/trends/{trend_data['id']}"
        client.delete(endpoint, headers=headers_with_jwt)

@pytest.fixture
def created_signal(test_signal: Signal, headers_with_jwt: dict) -> Generator[Dict[str, Any], None, None]:
    """Fixture that creates and cleans up a test signal."""
    # Create the signal
    response = client.post("/signals", json=test_signal.model_dump(), headers=headers_with_jwt)
    assert response.status_code == 201
    signal_data = response.json()
    
    yield signal_data
    
    # Cleanup - don't assert status code since signal might already be deleted
    endpoint = f"/signals/{signal_data['id']}"
    client.delete(endpoint, headers=headers_with_jwt)

@pytest.fixture
def created_signals(headers_with_jwt: dict) -> Generator[list[Dict[str, Any]], None, None]:
    """Fixture that creates multiple test signals with different statuses."""
    signals = []
    statuses = [Status.DRAFT.value, Status.NEW.value, Status.APPROVED.value]
    base_signal_data = {
        "headline": "Test Signal",
        "description": "Test Description",
        "url": "https://undp.medium.com/test",
        "relevance": "Test relevance",
        "keywords": ["test"],
        "location": "Global",
        "steep_primary": Steep.ECONOMIC.value,
        "steep_secondary": [Steep.SOCIAL.value],
        "signature_primary": Signature.GOVERNANCE.value,
        "signature_secondary": [Signature.POVERTY.value],
        "sdgs": [Goal.G16.value]
    }
    
    for i, status in enumerate(statuses):
        signal_data = {**base_signal_data, "status": status, "headline": f"Test Signal {i}"}
        signal = Signal.model_validate(signal_data)
        response = client.post("/signals", json=signal.model_dump(), headers=headers_with_jwt)
        assert response.status_code == 201
        signals.append(response.json())
    
    yield signals
    
    # Cleanup
    for signal_data in signals:
        endpoint = f"/signals/{signal_data['id']}"
        response = client.delete(endpoint, headers=headers_with_jwt)
        assert response.status_code == 200

def test_favourite_crud(headers_with_jwt: dict, created_signal: Dict[str, Any]):
    """Test basic create, read, and delete operations for favorites."""
    signal_id = created_signal['id']
    
    # Add to favorites
    endpoint = f"/favourites/{signal_id}"
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "created"
    
    # Verify it appears in favorites list
    response = client.get("/favourites", headers=headers_with_jwt)
    assert response.status_code == 200
    favorites = response.json()
    assert len(favorites) == 1
    favorite_signal = Signal.model_validate(favorites[0])
    assert favorite_signal.id == signal_id
    
    # Remove from favorites
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "deleted"
    
    # Verify it's removed from favorites list
    response = client.get("/favourites", headers=headers_with_jwt)
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_favourite_idempotency(headers_with_jwt: dict, created_signal: Dict[str, Any]):
    """Test that favoriting/unfavoriting operations are idempotent."""
    signal_id = created_signal['id']
    endpoint = f"/favourites/{signal_id}"
    
    # First favorite operation should create
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "created"
    
    # Second favorite operation should delete
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "deleted"
    
    # Third favorite operation should create again
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "created"
    
    # Verify only one favorite exists
    response = client.get("/favourites", headers=headers_with_jwt)
    assert len(response.json()) == 1

@mark.parametrize("invalid_id", [-1, 0, 99999])
def test_favourite_invalid_signals(headers_with_jwt: dict, invalid_id: int):
    """Test favoriting non-existent or invalid signals."""
    endpoint = f"/favourites/{invalid_id}"
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 404
    response_data = response.json()
    assert "not found" in response_data["detail"].lower()

def test_favourites_ordering(headers_with_jwt: dict):
    """Test that favorites are returned in chronological order (most recent first)."""
    # Create multiple test signals
    signals = []
    base_signal_data = {
        "headline": "Test Signal",
        "description": "Test Description",
        "url": "https://undp.medium.com/test",
        "relevance": "Test relevance",
        "keywords": ["test"],
        "location": "Global",
        "status": Status.NEW.value,
        "steep_primary": Steep.ECONOMIC.value,
        "steep_secondary": [Steep.SOCIAL.value],
        "signature_primary": Signature.GOVERNANCE.value,
        "signature_secondary": [Signature.POVERTY.value],
        "sdgs": [Goal.G16.value]
    }
    
    for i in range(3):
        signal_data = {**base_signal_data, "headline": f"Test Signal {i}"}
        signal = Signal.model_validate(signal_data)
        response = client.post("/signals", json=signal.model_dump(), headers=headers_with_jwt)
        assert response.status_code == 201
        signals.append(response.json())
    
    # Favorite them in a specific order
    for signal_data in signals:
        endpoint = f"/favourites/{signal_data['id']}"
        response = client.post(endpoint, headers=headers_with_jwt)
        assert response.status_code == 200
    
    # Verify they're returned in reverse chronological order
    response = client.get("/favourites", headers=headers_with_jwt)
    assert response.status_code == 200
    favorites = response.json()
    assert len(favorites) == 3
    
    # Extract headlines from favorites
    favorite_signals = [Signal.model_validate(favorite) for favorite in favorites]
    favorite_headlines = [signal.headline for signal in favorite_signals]
    
    assert favorite_headlines == [
        "Test Signal 2",
        "Test Signal 1",
        "Test Signal 0"
    ]
    
    # Cleanup
    for signal_data in signals:
        endpoint = f"/signals/{signal_data['id']}"
        response = client.delete(endpoint, headers=headers_with_jwt)
        assert response.status_code == 200

def test_favourites_unauthorized():
    """Test accessing favorites endpoints without authentication."""
    # Try to get favorites without auth
    endpoint = "/favourites"
    response = client.get(endpoint)
    assert response.status_code in {401, 403}  # Accept either status code
    assert "not" in response.json()["detail"].lower()
    
    # Try to create favorite without auth
    endpoint = "/favourites/1"
    response = client.post(endpoint)
    assert response.status_code in {401, 403}  # Accept either status code
    assert "not" in response.json()["detail"].lower()

def test_favourite_deleted_signal(headers_with_jwt: dict, created_signal: Dict[str, Any]):
    """Test behavior when a favorited signal is deleted."""
    signal_id = created_signal['id']
    
    # Favorite the signal
    endpoint = f"/favourites/{signal_id}"
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    
    # Delete the signal
    endpoint = f"/signals/{signal_id}"
    response = client.delete(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    
    # Verify the favorite is no longer returned
    response = client.get("/favourites", headers=headers_with_jwt)
    assert response.status_code == 200
    favorites = response.json()
    assert len(favorites) == 0

def test_favourite_signal_with_trends(headers_with_jwt: dict, created_signal: Dict[str, Any], test_trends: list[Dict[str, Any]]):
    """Test favoriting signals that have connected trends."""
    signal_id = created_signal['id']
    
    # Update signal with connected trends
    signal_data = created_signal.copy()
    signal_data["connected_trends"] = [trend["id"] for trend in test_trends]
    endpoint = f"/signals/{signal_id}"
    response = client.put(endpoint, json=signal_data, headers=headers_with_jwt)
    assert response.status_code == 200
    
    # Favorite the signal
    endpoint = f"/favourites/{signal_id}"
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    
    # Verify the favorite includes connected trends
    response = client.get("/favourites", headers=headers_with_jwt)
    assert response.status_code == 200
    favorites = response.json()
    assert len(favorites) == 1
    favorite_signal = Signal.model_validate(favorites[0])
    # Compare sets of trend IDs since order doesn't matter
    assert favorite_signal.connected_trends is not None
    assert set(favorite_signal.connected_trends) == set(trend["id"] for trend in test_trends)

def test_favourite_signals_with_different_statuses(headers_with_jwt: dict, created_signals: list[Dict[str, Any]]):
    """Test favoriting signals with different statuses."""
    # Favorite all signals
    for signal_data in created_signals:
        endpoint = f"/favourites/{signal_data['id']}"
        response = client.post(endpoint, headers=headers_with_jwt)
        assert response.status_code == 200
    
    # Verify all signals are in favorites regardless of status
    response = client.get("/favourites", headers=headers_with_jwt)
    assert response.status_code == 200
    favorites = response.json()
    assert len(favorites) == 3
    
    # Verify all statuses are present
    favorite_signals = [Signal.model_validate(favorite) for favorite in favorites]
    statuses = {signal.status for signal in favorite_signals}
    
    expected_statuses = {Status.DRAFT, Status.NEW, Status.APPROVED}
    assert statuses == expected_statuses

def test_favourite_signal_updates(headers_with_jwt: dict, created_signal: Dict[str, Any]):
    """Test that favorites reflect signal updates."""
    signal_id = created_signal['id']
    
    # Favorite the signal
    endpoint = f"/favourites/{signal_id}"
    response = client.post(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    
    # Update the signal
    signal_data = created_signal.copy()
    signal_data["headline"] = "Updated Headline"
    signal_data["description"] = "Updated Description"
    
    endpoint = f"/signals/{signal_id}"
    response = client.put(endpoint, json=signal_data, headers=headers_with_jwt)
    assert response.status_code == 200
    
    # Verify the favorite reflects the updates
    response = client.get("/favourites", headers=headers_with_jwt)
    assert response.status_code == 200
    favorites = response.json()
    assert len(favorites) == 1
    favorite_signal = Signal.model_validate(favorites[0])
    assert favorite_signal.headline == "Updated Headline"
    assert favorite_signal.description == "Updated Description"

def test_favourite_status_in_signal_response(headers_with_jwt: dict, created_signal: Dict[str, Any]):
    """Test that signal responses include correct favorite status."""
    signal_id = created_signal['id']
    
    # Initially signal should not be favorited
    response = client.get(f"/signals/{signal_id}", headers=headers_with_jwt)
    assert response.status_code == 200
    signal_data = response.json()
    assert signal_data["favorite"] is False
    
    # Add to favorites
    response = client.post(f"/favourites/{signal_id}", headers=headers_with_jwt)
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    
    # Signal should now show as favorited
    response = client.get(f"/signals/{signal_id}", headers=headers_with_jwt)
    assert response.status_code == 200
    signal_data = response.json()
    assert signal_data["favorite"] is True
    
    # Remove from favorites
    response = client.post(f"/favourites/{signal_id}", headers=headers_with_jwt)
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    
    # Signal should no longer show as favorited
    response = client.get(f"/signals/{signal_id}", headers=headers_with_jwt)
    assert response.status_code == 200
    signal_data = response.json()
    assert signal_data["favorite"] is False
