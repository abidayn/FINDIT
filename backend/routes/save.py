from fastapi import APIRouter, HTTPException

from models.schemas import ErrorResponse, Item, SaveRequest
from services import ai, database, fetcher, reprocess
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
    content / fallback values instead), so the only step allowed to fail the
    request is the database write. The duplicate lookup can raise, but is
    caught and ignored — it is an optimisation, not a requirement.
    """
    url = str(request.url)
    platform = detect_platform(url)

    # Checked before fetching, not after: an already-saved link needs neither a
    # content fetch nor a Gemini request, and the free tier only allows 20 of
    # the latter per day. Re-sharing something also returns instantly, which
    # reads as the app being fast rather than as an error.
    try:
        existing = database.find_duplicate(url)
    except Exception as exc:
        # Never let the convenience check cost the user their save (Core Rule 5).
        # A duplicate row is a far better outcome than a lost link.
        logger.warning("Duplicate check failed for %s, saving anyway: %s", url, exc)
        existing = None

    if existing:
        if existing.ai_status != "ok":
            # Re-sharing a link whose AI never ran is how the user asks for a
            # retry. Without this the duplicate check would hand back the
            # unprocessed item forever, making it unfixable — the queue sweep
            # only covers quota_exceeded, so a plain 'failed' item has no other
            # route back. Falls back to the stored row if quota is still out.
            logger.info("Duplicate of item %s with ai_status=%s, retrying AI",
                        existing.id, existing.ai_status)
            return reprocess.reprocess_item(existing) or existing

        logger.info("Duplicate of item %s, not saving again: %s", existing.id, url)
        return existing

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
