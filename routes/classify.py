from __future__ import annotations

import os
from typing import Annotated
from fastapi import APIRouter, Header, Request, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from classification.schema import ClassificationSchema
from utils.sources import Source
from utils.logger import logger, raise_and_log
from utils.kobo import clean_kobo_data
from routes.load import CreateClassificationSchemaHeaders
from classification.classifier import Classifier
from azure.cosmos.exceptions import CosmosResourceNotFoundError

router = APIRouter()
header_API_key = APIKeyHeader(name="API-KEY")


def get_source_text(source_text, payload: dict):
    """Get text to classify from payload. Raise error if not found."""
    if source_text not in payload:
        raise_and_log(
            status_code=400,
            detail=f"Field '{source_text}' is required in request body.",
        )
    else:
        return payload[source_text]


@router.post("/classify-text", tags=["classify"])
async def classify_text(
    request: Request,
    headers: Annotated[CreateClassificationSchemaHeaders, Header()],
    key: str = Depends(header_API_key),
):
    """
    Classify text according to classification schema.
    """

    if key != os.getenv("API_KEY"):
        raise_and_log(status_code=403, detail="Invalid API key.")

    payload = await request.json()
    extra_logs = {
        "source-name": request.headers["source-name"].lower(),
        "source-origin": request.headers["source-origin"],
    }
    logger.info(
        f"Classifying text from {request.headers['source-name']}.", extra=extra_logs
    )

    # load classification schema
    schema = ClassificationSchema(source_settings=request.headers)

    try:
        schema.load_from_cosmos()
        # check that classification schema is up-to-date
        if not schema.is_up_to_date():
            logger.info(
                "Classification schema is outdated, loading schema from source and saving to CosmosDB.",
                extra=extra_logs,
            )
            schema.load_from_source()
            schema.save_to_cosmos()
    except CosmosResourceNotFoundError:
        logger.info(
            "Classification schema not found in CosmosDB, loading schema from source and saving to CosmosDB.",
            extra=extra_logs,
        )
        schema.load_from_source()
        schema.save_to_cosmos()

    # initialize classifier
    classifier = Classifier(
        schema=schema,
        translate=request.headers.get("translate", False),
    )

    # get text to classify
    if schema.source == Source.KOBO:
        if "source-text" not in request.headers:
            raise_and_log(
                status_code=400,
                detail="Header 'source-text' is required for Kobo, "
                "specifying the name of the question to be classified.",
                extra_logs=extra_logs,
            )
        source_text = request.headers["source-text"]
        text = get_source_text(source_text.lower(), clean_kobo_data(payload))
    else:
        text = get_source_text("text", payload)

    # classify text
    classification_result = classifier.classify(text=text)

    if schema.source == Source.KOBO:
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
            "provider": os.getenv("CLASSIFIER_PROVIDER"),
            "model": os.getenv("CLASSIFIER_MODEL"),
        },
    )
