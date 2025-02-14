from __future__ import annotations

import os
import requests
import json
from fastapi import Depends, APIRouter, Header, Request
from fastapi.responses import JSONResponse
from typing import Annotated
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from utils.classification_schema import ClassificationSchema
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from utils.logger import logger
from routes.load import (
    ClassificationSchemaPayload,
    create_classification_schema,
)

# from transformers import pipeline

router = APIRouter()
# zeroshot_classifier = pipeline(
#     "zero-shot-classification", model=os.getenv("ZEROSHOT_CLASSIFIER")
# )


# {
#   "feedback": "This is a feedback.",
#   "source_name": "kobo",
#   "source_origin": "asroL6e9wJLh62GNSJ7cHR",
#   "source_authorization": "4eca639d4031e8355f70d87a19b2382afb12f17b",
#   "source_level1": "Feedback_Type",
#   "source_level2": "Feedback_Category",
#   "source_level3": "Feedback_Code"
# }


class ClassificationPayload(ClassificationSchemaPayload):
    text_field: str = Field(
        ...,
        description="Field of request body containing text to be classified.",
    )


@router.post("/classify-text")
async def classify_text(
    request: Request,
    dependencies=Annotated[ClassificationPayload, Header()],
):
    """
    Classify text according to classification schema.
    """
    logger.info(f"Classifying text from {request.headers['source-name']}.")
    payload = await request.json()

    cs = ClassificationSchema(
        source=request.headers["source-name"],
        source_settings={k: v for k, v in request.headers.items()},
    )
    logger.info(f"Classification schema source: {cs.source}")
    logger.info(f"Classification schema settings: {cs.settings}")

    try:
        cs.load_from_cosmos()
    except CosmosResourceNotFoundError:
        logger.info("Classification schema not found in CosmosDB, loading from source.")
        create_classification_schema({k: v for k, v in request.headers.items()})
    cs.load_from_cosmos()

    text = payload[request.headers["text-field"]]
    response = {}
    hypothesis_template = "This text is about {}"
    labels_1 = cs.get_class_labels(1)
    # output = zeroshot_classifier(
    #     text,
    #     labels_1,
    #     hypothesis_template=hypothesis_template,
    #     multi_label=False,
    # )
    output = {
        "labels": ["feedback", "complaint", "suggestion"],
        "scores": [0.9, 0.05, 0.05],
    }
    label_1 = output["labels"][output["scores"].index(max(output["scores"]))]
    name_1 = cs.get_name_from_label(label_1)
    response[cs.settings["source-level1"]] = name_1
    if cs.n_levels > 1:
        labels_2 = cs.get_class_labels(2, parent=name_1)
        if len(labels_2) == 1:
            label_2 = labels_2[0]
        elif len(labels_2) > 1:
            output = zeroshot_classifier(
                text,
                labels_2,
                hypothesis_template=hypothesis_template,
                multi_label=False,
            )
            label_2 = output["labels"][output["scores"].index(max(output["scores"]))]
        else:
            label_2 = None
        name_2 = cs.get_name_from_label(label_2)
        response[cs.settings["source-level2"]] = name_2
    if cs.n_levels > 2:
        if name_2:
            labels_3 = cs.get_class_labels(3, parent=name_2)
            if len(labels_3) == 1:
                label_3 = labels_3[0]
            elif len(labels_3) > 1:
                output = zeroshot_classifier(
                    text,
                    labels_3,
                    hypothesis_template=hypothesis_template,
                    multi_label=False,
                )
                label_3 = output["labels"][
                    output["scores"].index(max(output["scores"]))
                ]
            else:
                label_3 = None
            name_3 = cs.get_name_from_label(label_3)
        else:
            name_3 = None
        response[cs.settings["source-level3"]] = name_3

    # save to source
    if cs.source.lower() == "espocrm":
        # TBI
        pass
    elif cs.source.lower() == "kobo":
        headers = {"Authorization": f"Token {cs.settings['source-authorization']}"}
        kobo_payload = {
            "submission_ids": [str(payload["_id"])],
            "data": response,
        }
        kobo_response = requests.patch(
            url=f"https://kobo.ifrc.org/api/v2/assets/{cs.settings['source-origin']}/data/bulk/",
            data={"payload": json.dumps(kobo_payload)},
            params={"fomat": "json"},
            headers=headers,
        )
        kobo_response = kobo_response.json()
        try:
            kobo_status_code = kobo_response["results"][0]["status_code"]
        except KeyError:
            kobo_status_code = 500
        response["source_response"] = {"status_code": kobo_status_code}
    return JSONResponse(content=response)
