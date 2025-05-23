"""
Dependencies for API authentication using JWT tokens from Microsoft Entra.
"""

import logging
import os
from typing import Dict, Any, Optional, cast

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
    auto_error=False,
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
    jwk_dict = jwks.get(header["kid"])
    if jwk_dict is None:
        raise ValueError("JWK could not be obtained or found")
    jwk = jwt.PyJWK.from_dict(jwk_dict, "RS256")
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
    token: Optional[str] = Security(api_key_header),
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
    logging.debug("Authenticating user with token")
    
    # For local development environment
    if os.environ.get("ENV_MODE") == "local":
        # Use test token if available
        if os.environ.get("TEST_USER_TOKEN"):
            test_token = os.environ.get("TEST_USER_TOKEN")
            if test_token is not None:
                token = test_token
                
        # Default user data for local development
        local_email = os.environ.get("TEST_USER_EMAIL", "test.user@undp.org")
        name = os.environ.get("TEST_USER_NAME", "Test User")
        unit = os.environ.get("TEST_USER_UNIT", "Data Futures Exchange (DFx)")
        acclab = os.environ.get("TEST_USER_ACCLAB", False)
        
        # Check for specific test tokens
        if token == "test-admin-token":
            return User(
                email=local_email,
                name=name,
                unit=unit,
                acclab=acclab,
                role=Role.ADMIN
            )
        elif token == "test-user-token":
            return User(
                email=local_email,
                name=name,
                unit=unit,
                acclab=acclab,
                role=Role.USER
            )
        else:
            # In local mode, if no valid token is provided, default to an admin user
            logging.info("LOCAL MODE: No valid token provided, using default admin user")
            return User(
                email=local_email,
                name=name,
                unit=unit,
                acclab=acclab,
                role=Role.ADMIN
            )

    # Check for API key access
    if token and token == os.environ.get("API_KEY"):
        if os.environ.get("ENV") == "dev":
            return User(email="name.surname@undp.org", role=Role.ADMIN)
        else:
            # dummy user object for anonymous access
            return User(email="name.surname@undp.org", role=Role.VISITOR)
    
    # If no token provided in non-local mode
    if not token:
        raise exceptions.not_authenticated
        
    # Try to decode and verify the token
    try:
        payload = await decode_token(token)
    except jwt.exceptions.PyJWTError as e:
        raise exceptions.not_authenticated from e
        
    payload_email = payload.get("unique_name")
    payload_name = payload.get("name")
    
    if payload_email is None or payload_name is None:
        raise exceptions.not_authenticated
        
    email_str = str(payload_email)  # Convert to string to satisfy type checker
    name_str = str(payload_name)    # Convert to string to satisfy type checker
    
    if (user := await db.read_user_by_email(cursor, email_str)) is None:
        user = User(email=email_str, role=Role.USER, name=name_str)
        await db.create_user(cursor, user)
    return user
