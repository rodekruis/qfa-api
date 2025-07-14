from __future__ import annotations
from fastapi import APIRouter, Header, Request, Depends, HTTPException
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from classification.schema import ClassificationSchema
from typing import Annotated
from utils.logger import logger
import os

router = APIRouter()
header_API_key = APIKeyHeader(name="API-KEY")


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
        description="Translate text to English.",
    )


@router.post("/create-classification-schema", tags=["classify"])
def create_classification_schema(
    request: Request,
    headers: Annotated[CreateClassificationSchemaHeaders, Header()],
    key: str = Depends(header_API_key),
):
    """Create a classification schema. Replace all entries if it already exists."""

    if key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403)
    extra_logs = {
        "source-name": request.headers["source-name"].lower(),
        "source-origin": request.headers["source-origin"],
    }
    logger.info(
        f"Loading classification schema and saving to CosmosDB.",
        extra=extra_logs,
    )
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
    key: str = Depends(header_API_key),
):
    """Delete a classification schema."""

    if key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403)

    cs = ClassificationSchema(source_settings=request.headers)
    cs.remove_from_cosmos()

    return JSONResponse(status_code=200, content=f"Deleted classification schema.")
