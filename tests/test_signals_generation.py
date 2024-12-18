# """
# Basic tests for generation of signals using news API and AI
# """

from typing import Literal

from fastapi.testclient import TestClient
from pytest import mark

from main import app
from src.entities import Goal, Pagination, Signal, Trend

client = TestClient(app)

@mark.parametrize("query", [
    "",  # empty query should return empty list
    "a",  # single character should return empty list 
    "climate",  # common search term
    "artificial intelligence",  # multi-word query
    "xyz123!@#",  # unusual query that likely won't match anything
])
def test_autocomplete(query: str, headers_with_jwt: dict):
    """Test the autocomplete endpoint with various queries"""
    endpoint = "/signals/autocomplete"
    
    response = client.get(
        endpoint,
        params={"query": query},
        headers=headers_with_jwt
    )
    
    # Check response status
    assert response.status_code == 200
    
    # Response should be a list
    results = response.json()
    assert isinstance(results, list)
    
    # Empty or single character queries should return empty list
    if not query or len(query) < 2:
        assert len(results) == 0
    else:
        # If we have results, verify their structure
        for item in results:
            # log if debug true
            assert isinstance(item, dict)
            assert "headline" in item
            assert "url" in item
            assert "description" in item
            assert "keywords" in item
            assert isinstance(item["keywords"], list)
            assert "location" in item
            
            # Optional fields can be None
            assert "relevance" in item
            assert "created_unit" in item
            assert "connected_trends" in item
            assert "score" in item

def test_autocomplete_unauthorized():
    """Test that unauthorized requests are rejected"""
    endpoint = "/signals/autocomplete"
    
    response = client.get(
        endpoint,
        params={"query": "test"}
    )
    
    assert response.status_code == 403
