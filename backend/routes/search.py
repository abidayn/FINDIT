from fastapi import APIRouter, HTTPException, Query

from models.schemas import ErrorResponse, Item
from services import database
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Below this length a query matches almost everything, which is noise rather
# than a result set (TASKS.md 2.2).
_MIN_QUERY_LENGTH = 2


@router.get("/search", response_model=list[Item])
def search(q: str = Query(default="")) -> list[Item]:
    """Keyword search over title and summary.

    An empty query returns everything (the natural "cleared the search box"
    behaviour); one or two stray characters return nothing rather than
    flooding the screen.
    """
    query = q.strip()

    if not query:
        try:
            return database.get_all_items()
        except Exception as exc:
            logger.error("Failed to list items for empty search: %s", exc)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Search failed", code="DB_QUERY_FAILED", details=str(exc)
                ).model_dump(),
            )

    if len(query) < _MIN_QUERY_LENGTH:
        return []

    try:
        return database.search_items(query)
    except Exception as exc:
        logger.error("Search failed for %r: %s", query, exc)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Search failed", code="DB_QUERY_FAILED", details=str(exc)
            ).model_dump(),
        )
