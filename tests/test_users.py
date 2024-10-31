"""
Basic tests for user endpoints.
"""

from fastapi.testclient import TestClient
from pytest import mark

from main import app
from src.entities import Role, User

client = TestClient(app)


def test_me(headers: dict):
    endpoint = "/users/me"
    response = client.get(endpoint, headers=headers)
    assert response.status_code == 200

    user = User(**response.json())
    assert user.role in {Role.VISITOR, Role.USER}
    assert not user.is_admin
    assert not user.is_staff


@mark.parametrize(
    "unit",
    [
        "Bureau for Policy and Programme Support (BPPS)",
        "Chief Digital Office (CDO)",
        "Executive Office (ExO)",
    ],
)
@mark.parametrize("acclab", [True, False])
def test_update(unit: str, acclab: bool, headers_with_jwt: dict):
    # get the user data from the database
    endpoint = "/users/me"
    response = client.get(endpoint, headers=headers_with_jwt)
    assert response.status_code == 200
    user = User(**response.json())
    assert user.role == Role.USER, "The JWT must belong to a regular user"

    # regular users should be able to update their profile
    endpoint = f"/users/{user.id}"
    user.acclab = acclab
    user.unit = unit
    response = client.put(endpoint, json=user.model_dump(), headers=headers_with_jwt)
    assert response.status_code == 200
    data = response.json()
    assert user.id == data["id"]
    assert user.is_regular
    assert user.acclab == acclab
    assert user.unit == unit

    # regular users should not be able to change their role
    user.role = Role.ADMIN
    response = client.put(endpoint, json=user.model_dump(), headers=headers_with_jwt)
    assert response.status_code == 403
