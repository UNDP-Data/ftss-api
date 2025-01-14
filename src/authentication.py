"""
Dependencies for API authentication using JWT tokens from Microsoft Entra.
"""

import logging
import os

import httpx
import jwt
from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from psycopg import AsyncCursor

from . import database as db
from . import exceptions
from .entities import Role, User

api_key_header = APIKeyHeader(
    name="access_token",
    description="The API access token for the application.",
    auto_error=True,
)


async def get_jwks() -> dict[str, dict]:
    """
    Get JSON Web Key Set (JWKS) containing the public keys.

    Returns
    -------
    keys : dict[str, dict]
        A mapping of kid to JWKS.
    """
    # obtain OpenID configuration
    tenant_id = os.environ["TENANT_ID"]
    endpoint = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint)
        configuration = response.json()

        # get the JSON Web Keys
        response = await client.get(configuration["jwks_uri"])
        response.raise_for_status()
        jwks = response.json()

    # get a mapping of key IDs to keys
    keys = {key["kid"]: key for key in jwks["keys"]}
    return keys


async def get_jwk(token: str) -> jwt.PyJWK:
    """
    Obtain a JSON Web Key (JWK) for a token.

    Parameters
    ----------
    token : str
        A JSON Web Tokens issued by Microsoft Entra.

    Returns
    -------
    jwk : jwt.PyJWK
        A ready-to-use JWK object.
    """
    header = jwt.get_unverified_header(token)
    try:
        jwks = await get_jwks()
    except httpx.HTTPError:
        jwks = {}
    jwk = jwks.get(header["kid"])
    if jwk is None:
        raise ValueError("JWK could not be obtained or found")
    jwk = jwt.PyJWK.from_dict(jwk, "RS256")
    return jwk


async def decode_token(token: str) -> dict:
    """
    Decode and verify a payload of a JSON Web Token (JWT).

    Parameters
    ----------
    token : str
        A JSON Web Tokens issued by Microsoft Entra.

    Returns
    -------
    payload : dict
        The decoded payload that should include email
        and name for further authentication.
    """
    jwk = await get_jwk(token)
    tenant_id = os.environ["TENANT_ID"]
    payload = jwt.decode(
        jwt=token,
        key=jwk.key,
        algorithms=["RS256"],
        audience=os.environ["CLIENT_ID"],
        issuer=f"https://sts.windows.net/{tenant_id}/",
        options={
            "verify_signature": True,
            "verify_aud": True,
            "verify_exp": True,
            "verify_iss": True,
        },
    )
    return payload


async def authenticate_user(
    token: str = Security(api_key_header),
    cursor: AsyncCursor = Depends(db.yield_cursor),
) -> User:
    """
    Authenticate a user with a valid JWT token from Microsoft Entra ID.

    The function is used for dependency injection in endpoints to authenticate incoming requests.
    The tokens must be issued by Microsoft Entra ID. For a list of available attributes, see
    https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference

    Parameters
    ----------
    token : str
        Either a predefined api_key to access "public" endpoints or a valid signed JWT.
    cursor : AsyncCursor
        An async database cursor.

    Returns
    -------
    user : User
        Pydantic model for a User object (if authentication succeeded).
    """
    logging.debug(f"Authenticating user with token")
    if os.environ.get("TEST_USER_TOKEN"): 
        token = os.environ.get("TEST_USER_TOKEN")
    if os.environ.get("ENV_MODE") == "local":
        # defaul user data
        user_data = {
            "email": "test.user@undp.org",
            "name": "Test User",
            "unit": "Data Futures Exchange (DFx)",
            "acclab": False,
        }
        if token == "test-admin-token":
            user_data["role"] = Role.ADMIN
            return User(**user_data)
        elif token == "test-user-token":
            user_data["role"] = Role.USER
            return User(**user_data)

    if token == os.environ.get("API_KEY"):
      if os.environ.get("ENV_MODE") == "local":
            return User(email="name.surname@undp.org", role=Role.ADMIN)
        else:
            # dummy user object for anonymous access
            return User(email="name.surname@undp.org", role=Role.VISITOR)
    try:
        payload = await decode_token(token)
    except jwt.exceptions.PyJWTError as e:
        raise exceptions.not_authenticated from e
    email, name = payload.get("unique_name"), payload.get("name")
    if email is None or name is None:
        raise exceptions.not_authenticated
    if (user := await db.read_user_by_email(cursor, email)) is None:
        user = User(email=email, role=Role.USER, name=name)
        await db.create_user(cursor, user)
    return user
