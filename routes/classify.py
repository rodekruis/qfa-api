from __future__ import annotations

import os
from typing import Annotated
from fastapi import APIRouter, Header, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import Field
from classification.schema import ClassificationSchema
from utils.sources import Source
from utils.logger import logger
from utils.kobo import clean_kobo_data
from routes.load import CreateClassificationSchemaHeaders
from classification.classifier import Classifier
from azure.cosmos.exceptions import CosmosResourceNotFoundError

router = APIRouter()


def get_source_text(source_text, payload: dict):
    """Get text to classify from payload. Raise error if not found."""
    if source_text not in payload:
        raise HTTPException(
            status_code=400,
            detail=f"Field '{source_text}' is required in request body.",
        )
    else:
        return payload[source_text]


class ClassifyTextHeaders(CreateClassificationSchemaHeaders):
    source_text: str = Field(
        ...,
        description="Field of request body containing text to be classified.",
    )


@router.post("/classify-text", tags=["classify"])
async def classify_text(
    request: Request, headers: Annotated[ClassifyTextHeaders, Header()]
):
    """
    Classify text according to classification schema.
    """

    payload = await request.json()

    logger.info(f"Classifying text from {request.headers['source-name']}.")

    # load classification schema
    cs = ClassificationSchema(source_settings=request.headers)

    try:
        cs.load_from_cosmos()
        # check that classification schema is up-to-date
        if not cs.is_up_to_date():
            logger.info(
                "Classification schema is outdated, loading from source and saving to CosmosDB."
            )
            cs.load_from_source()
            cs.save_to_cosmos()
    except CosmosResourceNotFoundError:
        logger.info(
            "Classification schema not found in CosmosDB, loading from source and saving to CosmosDB."
        )
        cs.load_from_source()
        cs.save_to_cosmos()

    # initialize classifier
    classifier = Classifier(
        model=os.getenv("ZEROSHOT_CLASSIFIER"),
        cs=cs,
    )

    # get text to classify
    source_text = request.headers["source-text"]
    if cs.source == Source.KOBO:
        text = get_source_text(source_text.lower(), clean_kobo_data(payload))
    else:
        text = get_source_text(source_text, payload)

    # classify text
    classification_result = classifier.classify(text=text)

    if cs.source == Source.KOBO:
        # if source is Kobo, save to source
        save_result = classification_result.save_to_source(payload)
    else:
        # otherwise, return classification results
        save_result = JSONResponse(
            status_code=200, content=classification_result.results()
        )

    return save_result


@router.get("/get-classification-model", tags=["classify"])
async def get_classification_model():
    """Get classification model."""
    return JSONResponse(
        status_code=200,
        content={
            "provider": "HuggingFace",
            "model": os.getenv("ZEROSHOT_CLASSIFIER"),
        },
    )
