from __future__ import annotations
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from classification.schema import ClassificationSchema
from typing import Annotated

router = APIRouter()


class CreateClassificationSchemaHeaders(BaseModel):
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
    translate: bool = Field(
        default=False,
        description="Translate schema to English before saving.",
    )


@router.post("/create-classification-schema", tags=["classify"])
def create_classification_schema(
    request: Request, headers: Annotated[CreateClassificationSchemaHeaders, Header()]
):
    """Create a classification schema. Replace all entries if it already exists."""

    cs = ClassificationSchema(source_settings=request.headers)
    cs.load_from_source()
    cs.save_to_cosmos()

    return JSONResponse(status_code=200, content=f"Created classification schema.")


class DeleteClassificationSchemaHeaders(BaseModel):
    source_origin: str = Field(
        ...,
        description="Unique identifier of source (asset ID or URL).",
    )


@router.delete("/delete-classification-schema", tags=["classify"])
def delete_classification_schema(
    request: Request,
    headers: Annotated[CreateClassificationSchemaHeaders, Header()],
):
    """Delete a classification schema."""

    cs = ClassificationSchema(source_settings=request.headers)
    cs.remove_from_cosmos()

    return JSONResponse(status_code=200, content=f"Deleted classification schema.")
