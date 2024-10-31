"""
Miscellaneous utilities for data wrangling.
"""

import base64
from datetime import UTC, datetime
from io import BytesIO
from typing import Literal

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from fastapi.responses import StreamingResponse
from PIL import Image
from sklearn.preprocessing import MultiLabelBinarizer


def convert_to_thumbnail(image_string: str) -> bytes:
    """
    Convert an image to a JPEG thumbnail no larger than HD quality.

    Parameters
    ----------
    image_string : str
        Base64 encoded image string.

    Returns
    -------
    image_data : bytes
        The image thumbnail encoded as JPEG.
    """
    # read the original image
    buffer = BytesIO(base64.b64decode(image_string))
    image = Image.open(buffer)

    # resize, save in-memory and return bytes
    buffer = BytesIO()
    image.thumbnail((1280, 720))
    image.convert("RGB").save(buffer, format="jpeg")
    image_data = buffer.getvalue()
    return image_data


async def scrape_content(url: str) -> str:
    """
    Scrape content of a web page to be fed to an OpenAI model.

    Parameters
    ----------
    url : str
        A publicly accessible URL.

    Returns
    -------
    str
        Web content of a page "as is".
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(headers=headers, timeout=10) as client:
        response = await client.get(url)
    soup = BeautifulSoup(response.content, features="lxml")
    return soup.text


def format_column_name(prefix: str, value: str) -> str:
    """
    Format column names for dummy columns created by MultiLabelBinarizer.

    This function is used for prettifying exports.

    Parameters
    ----------
    prefix : str
        A prefix to assign to a column.
    value : str
        The original column name value.

    Returns
    -------
    str
        Formated column name.
    """
    value = value.split("–")[0]
    value = value.strip().lower()
    value = value.replace(" ", "_")
    return f"{prefix}_{value}"


def binarise_columns(df: pd.DataFrame, columns: list[str]):
    """
    Binarise columns containing array values.

    Parameters
    ----------
    df : pd.DataFrame
        Arbitrary dataframe.
    columns : list[str]
        Columns to binarise.

    Returns
    -------
    df : pd.DataFrame
        Mutated data frame.
    """
    for column in columns:
        mlb = MultiLabelBinarizer()
        # fill in missing values with an empty list
        values = mlb.fit_transform(df[column].apply(lambda x: x or []))
        df_dummies = pd.DataFrame(values, columns=mlb.classes_)
        df_dummies.rename(lambda x: format_column_name(column, x), axis=1, inplace=True)
        df = df.join(df_dummies)
    df.drop(columns, axis=1, inplace=True)
    return df


def write_to_response(
    df: pd.DataFrame,
    kind: Literal["signals", "trends"],
) -> StreamingResponse:
    """
    Write a data frame to an Excel file in a Streaming response that can be returned by the API.

    Parameters
    ----------
    df : pd.DataFrame
        A data frame of exported signals/trends.
    kind : Literal["signals", "trends"]
        A kind of the data being exported to include in the file name.

    Returns
    -------
    response : StreamingResponse
        A response object containing the exported data that can be returned by the API.
    """
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    file_name = f"ftss-{kind}-{datetime.now(UTC):%y-%m-%d}.xlsx"
    response = StreamingResponse(
        BytesIO(buffer.getvalue()),
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": f"attachment; filename={file_name}"},
    )
    return response
