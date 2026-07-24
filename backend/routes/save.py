from fastapi import APIRouter, HTTPException

from models.schemas import ErrorResponse, Item, SaveRequest
from services import ai, database, fetcher
from utils.logger import get_logger
from utils.url_parser import detect_platform

router = APIRouter()
logger = get_logger(__name__)


def _ai_status(result: ai.AIResult) -> str:
    """Which of the three AI outcomes produced this result.

    `is`, not `==`: process_content returns one of two exact module-level
    constants on failure, so identity tells us which without guessing from
    field values that a real AI result could coincidentally match.
    """
    if result is ai.QUOTA_FALLBACK_RESULT:
        return "quota_exceeded"
    if result is ai.FALLBACK_RESULT:
        return "failed"
    return "ok"


@router.post("/save", response_model=Item, responses={500: {"model": ErrorResponse}})
def save(request: SaveRequest) -> Item:
    """TASKS.md 1.6 pipeline. URL well-formedness is already enforced by
    SaveRequest's HttpUrl field — FastAPI returns 422 before this runs.

    fetch_content() and process_content() never raise (they degrade to empty
    content / fallback values instead), so this function only needs to guard
    the database write — the one step that's allowed to fail the request.
    """
    url = str(request.url)
    platform = detect_platform(url)

    fetched = fetcher.fetch_content(url)
    result = ai.process_content(fetched)

    row = {
        "url": url,
        "title": result.title,
        "summary": result.summary,
        "folder": result.folder,
        "source": platform,
        "thumbnail_url": fetched.thumbnail_url,
        "raw_content": fetched.text or None,
        "confidence": result.confidence,
        "ai_status": _ai_status(result),
    }

    try:
        return database.insert_item(row)
    except Exception as exc:
        logger.error("Failed to save item for %s: %s", url, exc)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to save item", code="DB_INSERT_FAILED", details=str(exc)
            ).model_dump(),
        )
