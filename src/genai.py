"""
Functions for generating signals from web content using Azure OpenAI.
"""

import json
import os

from openai import AsyncAzureOpenAI

from .entities import Signal

__all__ = ["get_system_message", "get_client", "generate_signal"]


def get_system_message() -> str:
    """
    Get a system message for generating a signal from web content.

    Returns
    -------
    system_message : str
        A system message that can be used to generate a signal.
    """
    schema = Signal.model_json_schema()
    schema.pop("example", None)
    # generate content only for the following fields
    fields = {
        "headline",
        "description",
        "steep_primary",
        "steep_secondary",
        "signature_primary",
        "signature_secondary",
        "sdgs",
        "keywords",
    }
    schema["properties"] = {
        k: v for k, v in schema["properties"].items() if k in fields
    }
    system_message = f"""
    You are a Signal Scanner within the Strategy & Futures Team at the United Nations Development Programme.
    Your task is to generate a Signal from web content provided by the user. A Signal is defined as a single
    piece of evidence or indicator that points to, relates to, or otherwise supports a trend.
    It can also stand alone as a potential indicator of future change in one or more trends.
    
    ### Rules
    1. Your output must be a valid JSON string object without any markdown that can be directly passed to `json.loads`.
    2. The JSON string must conform to the schema below.
    3. The response must be in English, so translate content if necessary.
    4. For `headline` and `description`, do not just copy-paste text, instead summarize the information 
    in a concise yet insightful manner.
    
    ### Signal Schema 
    
    ```json
    {json.dumps(schema, indent=2)}
    ```
    """.strip()
    return system_message


def get_client() -> AsyncAzureOpenAI:
    """
    Get an asynchronous Azure OpenAI client.

    Returns
    -------
    client : AsyncAzureOpenAI
        An asynchronous client for Azure OpenAI.
    """
    client = AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version="2024-02-15-preview",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        timeout=10,
    )
    return client


async def generate_signal(text: str) -> Signal:
    """
    Generate a signal from a text.

    Parameters
    ----------
    text : str
        A text, i.e., web content, to be analysed.

    Returns
    -------
    signal : Signal
        A signal entity generated from the text.
    """
    client = get_client()
    system_message = get_system_message()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": text},
        ],
        temperature=0.3,  # vary the output to alleviate occasional errors
    )
    content = response.choices[0].message.content
    signal = Signal(**json.loads(content))
    return signal
