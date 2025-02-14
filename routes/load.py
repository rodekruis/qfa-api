from __future__ import annotations
from fastapi import (
    Depends,
    APIRouter,
    Header,
)
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from utils.classification_schema import ClassificationSchema
from utils.logger import logger
import os

router = APIRouter()

# key_query_scheme = APIKeyHeader(name="Authorization")

# {
#   "source_name": "EspoCRM",
#   "source_origin": "https://cea.feedbackmechanism.demo.510.global/",
#   "source_authorization": "d6c4cd86ea8509325e802cfdf6094853",
#   "source_level1": "FeedbackType",
#   "source_level2": "FeedbackCategory",
#   "source_level3": "FeedbackCode"
# }

# {
#   "source_name": "kobo",
#   "source_origin": "asroL6e9wJLh62GNSJ7cHR",
#   "source_authorization": "4eca639d4031e8355f70d87a19b2382afb12f17b",
#   "source_level1": "Feedback_Type",
#   "source_level2": "Feedback_Category",
#   "source_level3": "Feedback_Code"
# }


class ClassificationSchemaPayload(BaseModel):
    source_name: str = Field(
        "EspoCRM",
        description="Source of classification schema.",
    )
    source_origin: str = Field(
        ...,
        description="URL or unique identifier of source.",
    )
    source_authorization: str = Field(
        ...,
        description="Authorization token of source.",
    )
    source_level1: str = Field(
        ...,
        description="Field or entity name of level 1.",
    )
    source_level2: str = Field(
        ...,
        description="Field or entity name of level 2.",
    )
    source_level3: str = Field(
        ...,
        description="Field or entity name of level 3.",
    )


@router.post("/create-classification-schema")
def create_classification_schema(
    payload: ClassificationSchemaPayload,
    # headers: Annotated[
    #     ClassificationSchemaHeaders, Header()
    # ],  # , api_key: str = Depends(key_query_scheme)
):
    """Create a classification schema. Replace all entries if it already exists."""

    # if api_key != os.environ["API_KEY"]:
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    source_settings = {k.replace("_", "-"): v for k, v in payload.items()}
    cs = ClassificationSchema(
        source=source_settings["source-name"],
        source_settings=source_settings,
    )
    cs.load_from_source()
    cs.save_to_cosmos()


@router.delete("/delete-classification-schema")
def delete_classification_schema(
    payload: ClassificationSchemaPayload,  # , api_key: str = Depends(key_query_scheme)
):
    """Delete a classification schema."""

    # if api_key != os.environ["API_KEY"]:
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    # ...

    return JSONResponse(status_code=200, content=f"Deleted classification schema.")
