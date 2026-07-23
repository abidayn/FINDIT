from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models.schemas import ErrorResponse, Folder, Item
from services import database
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/items", response_model=list[Item])
def list_items(folder: Optional[Folder] = Query(default=None)) -> list[Item]:
    """All items newest-first, or just one folder's when ?folder= is given.

    Typing the parameter as `Folder` (the Literal of 9 names) means FastAPI
    rejects an unknown folder with a 422 before this function runs — no
    hand-written validation, same trick as SaveRequest.url being HttpUrl.
    """
    try:
        if folder is None:
            return database.get_all_items()
        return database.get_items_by_folder(folder)
    except Exception as exc:
        logger.error("Failed to list items: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to load items", code="DB_QUERY_FAILED", details=str(exc)
            ).model_dump(),
        )


@router.get("/items/{item_id}", response_model=Item, responses={404: {"model": ErrorResponse}})
def get_item(item_id: str) -> Item:
    try:
        item = database.get_item_by_id(item_id)
    except Exception as exc:
        logger.error("Failed to load item %s: %s", item_id, exc)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to load item", code="DB_QUERY_FAILED", details=str(exc)
            ).model_dump(),
        )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(error="Item not found", code="ITEM_NOT_FOUND").model_dump(),
        )

    return item


@router.delete("/items/{item_id}", status_code=204, responses={404: {"model": ErrorResponse}})
def remove_item(item_id: str) -> None:
    """204 No Content on success — there's nothing meaningful to return once
    the row is gone."""
    try:
        deleted = database.delete_item(item_id)
    except Exception as exc:
        logger.error("Failed to delete item %s: %s", item_id, exc)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to delete item", code="DB_DELETE_FAILED", details=str(exc)
            ).model_dump(),
        )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(error="Item not found", code="ITEM_NOT_FOUND").model_dump(),
        )
