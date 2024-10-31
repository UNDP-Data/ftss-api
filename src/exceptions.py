"""
Exceptions raised by API endpoints.
"""

from fastapi import HTTPException, status

__all__ = [
    "id_mismatch",
    "not_authenticated",
    "permission_denied",
    "not_found",
    "content_error",
    "generation_error",
]

id_mismatch = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Resource ID in body does not match path ID.",
)

not_authenticated = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
)

permission_denied = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You do not have permissions to perform this action.",
)

not_found = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="The requested resource could not be found.",
)

content_error = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="The content from the URL could not be fetched.",
)

generation_error = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="A signal could not be generated from the content.",
)
