"""
Basic tests for choices endpoints.
"""

from enum import StrEnum

from fastapi.testclient import TestClient
from pytest import mark

from main import app
from src.entities import Goal, Role, Status

client = TestClient(app)

enums = [("status", Status), ("role", Role), ("goal", Goal)]


def test_choices(headers: dict):
    endpoint = "/choices"
    response = client.get(endpoint, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    for k, v in data.items():
        assert isinstance(k, str)
        assert isinstance(v, list)
    for name, enum in enums:
        assert name in data
        assert data[name] == [x.value for x in enum]


@mark.parametrize("name,enum", enums)
def test_choice_name(name: str, enum: StrEnum, headers: dict):
    endpoint = f"/choices/{name}"
    response = client.get(endpoint, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert data == [x.value for x in enum]
