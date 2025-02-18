from __future__ import annotations
from fastapi import (
    APIRouter,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from utils.classification_schema import ClassificationSchema

router = APIRouter()


class CreateClassificationSchemaPayload(BaseModel):
    source_name: str = Field(
        "Kobo",
        description="Source of classification schema.",
    )
    source_origin: str = Field(
        ...,
        description="Unique identifier of source (asset ID or URL).",
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
    payload: CreateClassificationSchemaPayload,
):
    """Create a classification schema. Replace all entries if it already exists."""

    source_settings = {k.replace("_", "-"): v for k, v in payload.__dict__.items()}
    cs = ClassificationSchema(
        source=source_settings["source-name"],
        source_settings=source_settings,
    )
    cs.load_from_source()
    cs.save_to_cosmos()


@router.delete("/delete-classification-schema")
def delete_classification_schema(
    payload: CreateClassificationSchemaPayload,
):
    """Delete a classification schema."""

    source_settings = {k.replace("_", "-"): v for k, v in payload.__dict__.items()}
    cs = ClassificationSchema(
        source=source_settings["source-name"],
        source_settings=source_settings,
    )
    cs.remove_from_cosmos()

    return JSONResponse(status_code=200, content=f"Deleted classification schema.")
