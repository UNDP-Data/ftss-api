"""
Utilities for interacting with Azure Blob Storage for uploading and deleting image attachments.
"""

import os
from typing import Literal
from urllib.parse import urlparse

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import ContainerClient

from .utils import convert_to_thumbnail

__all__ = [
    "upload_image",
    "delete_image",
    "update_image",
]


def get_folder_path(folder_name: Literal["signals", "trends"]) -> str:
    """
    Get a path to an image folder derived from a database connection string.

    This allows to manage images from staging and production environments differently.

    Returns
    -------
    str
        A folder path to save signal/trend images to.
    """
    database_name = urlparse(os.getenv("DB_CONNECTION")).path.strip("/")
    return f"{database_name}/{folder_name}"


def get_container_client() -> ContainerClient:
    """
    Get a asynchronous container client for Azure Blob Storage.

    Returns
    -------
    client : ContainerClient
        An asynchronous container client.
    """
    client = ContainerClient.from_container_url(container_url=os.environ["SAS_URL"])
    return client


async def upload_image(
    entity_id: int,
    folder_name: Literal["signals", "trends"],
    image_string: str,
) -> str:
    """
    Upload a thumbnail JPEG version of an image to Azure Blob Storage and return a (public) URL.

    The function converts the image to a JPEG format and rescales it to 720p.

    Parameters
    ----------
    entity_id : str
        Signal or trend ID for which an image is uploaded.
    folder_name : Literal['signals', 'trends']
        Folder name to save the image to.
    image_string : str
        Base64-encoded image data.

    Returns
    -------
    blob_url : str
        A (public) URL pointing to the image file on Blob Storage
        that can be used to embed the image in HTML.
    """
    # decode the image string
    image_string = image_string.split(sep=",", maxsplit=1)[-1]
    image_data = convert_to_thumbnail(image_string)

    # connect and upload to the storage
    async with get_container_client() as client:
        folder_path = get_folder_path(folder_name)
        blob_client = await client.upload_blob(
            name=f"{folder_path}/{entity_id}.jpeg",
            data=image_data,
            blob_type="BlockBlob",
            overwrite=True,
            content_settings=ContentSettings(content_type="image/jpeg"),
        )

    # remove URL parameters that expose a SAS token
    blob_url = blob_client.url.split("?")[0]
    return blob_url


async def delete_image(
    entity_id: int,
    folder_name: Literal["signals", "trends"],
) -> bool:
    """
    Remove an image from Azure Blob Storage.

    Parameters
    ----------
    entity_id : str
        Signal or trend ID whose image is to be deleted.
    folder_name : Literal['signals', 'trends']
        Folder name to delete the image from.

    Returns
    -------
    True if the blob has been deleted and False otherwise.
    """
    folder_path = get_folder_path(folder_name)
    async with get_container_client() as client:
        try:
            await client.delete_blob(f"{folder_path}/{entity_id}.jpeg")
        except ResourceNotFoundError:
            return False
    return True


async def update_image(
    entity_id: int,
    folder_name: Literal["signals", "trends"],
    attachment: str | None,
) -> str | None:
    """
    Update an image attachment on Azure Blob Storage.

    If the attachment is None, the attachment will be deleted, if it is a base64-encoded
    image, the attachment will be updated, it is a URL to an image, no action will be taken.

    Parameters
    ----------
    entity_id : str
        Signal or trend ID whose image is to be updated.
    folder_name : Literal['signals', 'trends']
        Folder name to delete the image from.
    attachment : str | None
        A base64-encoded image data, existing attachment URL or None.

    Returns
    -------
    str | None
        A string to the current/updated image or None if it has been deleted or update failed.
    """
    if attachment is None:
        await delete_image(entity_id, folder_name)
        return None
    if attachment.startswith("https"):
        return attachment

    try:
        blob_url = await upload_image(
            entity_id=entity_id,
            folder_name=folder_name,
            image_string=attachment,
        )
    except Exception as e:
        print(e)
        return None
    return blob_url
