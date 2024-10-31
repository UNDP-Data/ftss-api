"""
Basic tests for search and CRUD operations on signals and trends.
"""

from typing import Literal

from fastapi.testclient import TestClient
from pytest import mark

from main import app
from src.entities import Goal, Pagination, Signal, Trend

client = TestClient(app)


@mark.parametrize("path", ["signals", "trends"])
@mark.parametrize("page", [None, 1, 2])
@mark.parametrize("per_page", [None, 10, 20])
@mark.parametrize("goal", [None, Goal.G13])
@mark.parametrize("query", [None, "climate"])
@mark.parametrize("ids", [None, list(range(100))])
def test_search(
    path: Literal["signals", "trends"],
    page: int | None,
    per_page: int | None,
    goal: Goal | None,
    query: str | None,
    ids: list[int] | None,
    headers_with_jwt: dict,
):
    endpoint = f"/{path}/search"
    params = {
        "page": page,
        "per_page": per_page,
        "goal": goal,
        "query": query,
        "ids": ids,
    }
    params = {k: v for k, v in params.items() if v is not None}

    # ensure the pagination values are set to defaults if not used in the request
    page = page or Pagination.model_fields["page"].default
    per_page = per_page or Pagination.model_fields["per_page"].default

    response = client.get(endpoint, params=params, headers=headers_with_jwt)
    assert response.status_code == 200
    results = response.json()
    assert results.get("current_page") == page
    assert results.get("per_page") == per_page
    assert isinstance(results.get("data"), list)
    assert 0 < len(results["data"]) <= per_page
    match path:
        case "signals":
            entity = Signal(**results["data"][0])
        case "trends":
            entity = Trend(**results["data"][0])
        case _:
            raise ValueError(f"Unknown path: {path}")
    assert entity.id == results["data"][0]["id"]


@mark.parametrize("path", ["signals", "trends"])
@mark.parametrize("uid", list(range(10, 20)))
def test_read_by_id(
    path: Literal["signals", "trends"],
    uid: int,
    headers_with_jwt: dict,
):
    endpoint = f"/{path}/{uid}"
    response = client.get(endpoint, headers=headers_with_jwt)
    assert response.status_code in {200, 404}
    if response.status_code == 200:
        data = response.json()
        signal = Signal(**data)
        assert signal.id == data["id"]


def test_crud(headers_with_jwt: dict):
    """Currently, testing for signals only as a staff role is required to manage trends."""
    # instantiate a test object
    entity = Signal(**Signal.model_config["json_schema_extra"]["example"])

    # create
    endpoint = "/signals"
    response = client.post(endpoint, json=entity.model_dump(), headers=headers_with_jwt)
    assert response.status_code == 201
    data = response.json()
    assert entity.headline == data["headline"]
    assert entity.description == data["description"]
    assert entity.sdgs == data["sdgs"]

    # read
    endpoint = "/signals/{}".format(data["id"])
    response = client.get(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    data = response.json()
    assert entity.headline == data["headline"]
    assert entity.description == data["description"]
    assert entity.sdgs == data["sdgs"]

    # update
    endpoint = "/signals/{}".format(data["id"])
    data |= {
        "headline": "New Headline",
        "description": "Lorem opsum " * 10,
        "sdgs": [Goal.G1, Goal.G17],
    }
    response = client.put(endpoint, json=data, headers=headers_with_jwt)
    assert response.status_code == 200
    data = response.json()
    assert entity.headline != data["headline"]
    assert entity.description != data["description"]
    assert entity.sdgs != data["sdgs"]

    # delete
    endpoint = "/signals/{}".format(data["id"])
    response = client.delete(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    response = client.get(endpoint, headers=headers_with_jwt)
    assert response.status_code == 404
