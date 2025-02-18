from __future__ import annotations

import os
import requests
import json
from fastapi import APIRouter, Header, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import Field
from utils.classification_schema import ClassificationSchema
from utils.classification_result import ClassificationResult
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from utils.logger import logger
from routes.load import CreateClassificationSchemaPayload
from utils.classifier import Classifier

router = APIRouter()


class ClassifyTextPayload(CreateClassificationSchemaPayload):
    text_field: str = Field(
        ...,
        description="Field of request body containing text to be classified.",
    )


@router.post("/classify-text")
async def classify_text(
    request: Request,
    headers: ClassifyTextPayload = Header(),
):
    """
    Classify text according to classification schema.
    """

    # check if headers are valid
    for required_header in vars(headers).keys():
        if required_header.replace("_", "-") not in request.headers:
            return JSONResponse(
                content={"error": f"Header '{required_header}' is required."},
                status_code=400,
            )

    payload = await request.json()

    # check if text field is in payload
    if request.headers["text-field"] not in payload:
        return JSONResponse(
            content={
                "error": f"Field '{request.headers['text-field']}' is required in request body."
            },
            status_code=400,
        )

    logger.info(f"Classifying text from {request.headers['source-name']}.")

    # load classification schema
    cs = ClassificationSchema(
        source=request.headers["source-name"],
        source_settings={k: v for k, v in request.headers.items()},
    )
    try:
        cs.load_from_cosmos()
    except CosmosResourceNotFoundError:
        logger.info(
            "Classification schema not found in CosmosDB, loading from source and saving to CosmosDB."
        )
        cs = ClassificationSchema(
            source=request.headers["source-name"],
            source_settings=request.headers,
        )
        cs.load_from_source()
        cs.save_to_cosmos()

    # initialize classifier
    classifier = Classifier(
        model=os.getenv("ZEROSHOT_CLASSIFIER"),
        cs=cs,
    )

    # classify text
    result = classifier.classify(text=payload[request.headers["text-field"]])

    return result.save_to_source(payload)
