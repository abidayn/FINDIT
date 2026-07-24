"""Background reprocessing of items that were saved without AI because the
daily Gemini quota was exhausted.

There is no scheduler in this stack — Railway can idle the container, so a
cron-style timer inside the process is not dependable. Instead the sweep runs
*opportunistically*: on startup, and whenever the app asks for the item list.
In practice that means opening Fetch the next day is what drains the queue,
which is also the moment the user would notice the items were still unsorted.
"""

import threading
import time

from models.schemas import FetchedContent, Item
from services import ai, database, fetcher
from utils.logger import get_logger

logger = get_logger(__name__)

# Half the free tier's 20 daily requests, so a backlog can never eat the whole
# day's budget and leave nothing for links the user saves today. New saves
# matter more than old ones catching up.
MAX_PER_SWEEP = 10

# A sweep costs real quota, and /items is called on every app open and every
# pull-to-refresh. Without this, refreshing three times would start three
# sweeps.
MIN_SECONDS_BETWEEN_SWEEPS = 600

_lock = threading.Lock()
_last_run: float = 0.0


def _content_for(item: Item) -> FetchedContent:
    """Rebuild the AI's input for an item that is already saved.

    Prefers the stored `raw_content` — that is precisely what the column was
    added for (ARCHITECTURE.md 3.3), and it avoids re-fetching a page we have
    already read. Only items saved before their platform's fetcher worked have
    no stored text; those are worth one real fetch.

    Note the creator handle from the original fetch is not preserved (it lived
    in FetchedContent.metadata, which is not stored). It only feeds the
    low-information prompt variant, so the cost is a slightly thinner prompt on
    items that had almost no content anyway.
    """
    if item.raw_content:
        return FetchedContent(
            url=item.url,
            text=item.raw_content,
            source_platform=item.source or "other",
        )

    return fetcher.fetch_content(item.url)


def reprocess_item(item: Item) -> Item | None:
    """Re-run the AI over an already-saved item and write the result back.

    Returns the updated item, or None when the quota is *still* exhausted — in
    which case nothing is written and the row keeps waiting. None rather than
    the unchanged item so callers can tell "no quota" from "reprocessed, and
    the AI happened to produce the same thing".
    """
    result = ai.process_content(_content_for(item))

    if result is ai.QUOTA_FALLBACK_RESULT:
        return None

    status = "failed" if result is ai.FALLBACK_RESULT else "ok"
    return database.update_item_ai(item.id, result, status)


def sweep() -> int:
    """Reprocess as many quota-blocked items as the quota now allows.

    Returns how many were successfully reprocessed. Never raises: this runs in
    the background, so a failure here must not surface as a failed user
    request.
    """
    global _last_run

    # blocking=False: if a sweep is already running, this caller just leaves.
    # Waiting would pointlessly tie up a worker thread to do duplicate work.
    if not _lock.acquire(blocking=False):
        return 0

    try:
        elapsed = time.monotonic() - _last_run
        if _last_run and elapsed < MIN_SECONDS_BETWEEN_SWEEPS:
            return 0
        _last_run = time.monotonic()

        pending = database.get_pending_items(limit=MAX_PER_SWEEP)
        if not pending:
            return 0

        logger.info("Reprocessing %d quota-blocked item(s)", len(pending))
        reprocessed = 0

        for item in pending:
            if reprocess_item(item) is None:
                # Still out of quota. Stop immediately rather than working
                # through the rest — every one would fail the same way, and
                # each still costs a round trip. The items keep their
                # quota_exceeded status and wait for the next sweep.
                logger.info(
                    "Quota still exhausted, stopping after %d item(s)", reprocessed
                )
                break
            reprocessed += 1

        if reprocessed:
            logger.info("Sweep reprocessed %d item(s)", reprocessed)
        return reprocessed

    except Exception as exc:
        logger.error("Reprocess sweep failed: %s", exc)
        return 0
    finally:
        _lock.release()
