import os
import uuid
import requests
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()


def translate_text(text: str) -> str:
    """
    Translate some text using MS translator.

    Args:
        text (str): The text to translate.
    Returns:
        str: The translated message.
    """
    constructed_url = "https://api.cognitive.microsofttranslator.com/translate"

    params = {
        "api-version": "3.0",
        "from": [],
        "to": ["en"],
    }
    headers = {
        "Ocp-Apim-Subscription-Key": os.getenv("MSCOGNITIVE_KEY"),
        "Ocp-Apim-Subscription-Region": "westeurope",
        "Content-type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }

    response = requests.post(
        constructed_url,
        params=params,
        headers=headers,
        json=[{"text": text}],
    ).json()
    translated_text = response[0]["translations"][0]["text"]

    if not translated_text:
        raise HTTPException(
            status_code=500,
            detail=f"Translation service is down, try with translate=false.",
        )
    return translated_text
