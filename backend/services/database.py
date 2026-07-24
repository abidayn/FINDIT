from supabase import Client, create_client

from config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from models.schemas import Item
from utils.logger import get_logger
from utils.url_parser import normalize_url

logger = get_logger(__name__)

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    # Fail at import, not at the first request. A backend that boots without
    # database credentials is a backend that lies about being healthy.
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

# One client for the whole process. It holds a connection pool, so creating a
# new one per request would be wasteful.
_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

_TABLE = "items"


def insert_item(item_data: dict) -> Item:
    """Insert one row and return it as an Item. Raises if the insert failed."""
    response = _client.table(_TABLE).insert(item_data).execute()

    if not response.data:
        raise RuntimeError("Insert returned no row")

    logger.info("Inserted item %s", response.data[0]["id"])
    return Item(**response.data[0])


def get_all_items() -> list[Item]:
    """Every item, newest first."""
    response = (
        _client.table(_TABLE)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return [Item(**row) for row in response.data]


def get_item_by_id(item_id: str) -> Item | None:
    """One item by id, or None if no row matched — the caller turns that into
    a 404. Returning None rather than raising keeps "not found" (an ordinary
    outcome) separate from "the query broke" (an actual failure)."""
    response = _client.table(_TABLE).select("*").eq("id", item_id).execute()

    if not response.data:
        return None

    return Item(**response.data[0])


def find_duplicate(url: str) -> Item | None:
    """The already-saved item that is the same link as `url`, or None.

    Matching happens in Python rather than in SQL because stored URLs are raw:
    deciding equality needs normalize_url() on both sides, and Postgres knows
    nothing about that function. Only id and url are selected, so the payload
    stays small even for a large library.

    This is a full scan on every save. That is cheap next to what it prevents —
    a content fetch plus a Gemini request — and fine at personal-library scale.
    If the table ever grows big enough for it to matter, the right fix is a
    `normalized_url` column with a unique index, which is a schema change and
    so deliberately deferred (migrations are manual in the MVP).
    """
    target = normalize_url(url)
    response = _client.table(_TABLE).select("id,url").execute()

    for row in response.data:
        if normalize_url(row["url"]) == target:
            return get_item_by_id(row["id"])

    return None


def get_items_by_folder(folder: str) -> list[Item]:
    response = (
        _client.table(_TABLE)
        .select("*")
        .eq("folder", folder)
        .order("created_at", desc=True)
        .execute()
    )
    return [Item(**row) for row in response.data]


def search_items(query: str) -> list[Item]:
    """Keyword search over title and summary (TASKS.md 2.2).

    Runs full-text search and substring matching together, because neither
    alone is good enough on its own:

    - `plfts` is PostgreSQL full-text via `plainto_tsquery`. It understands
      word stems, so "story" finds "stories" — ILIKE never would. `plfts`
      rather than `fts` because plainto_tsquery accepts free-form text; the
      plain `fts` operator expects tsquery syntax and errors on ordinary
      phrases.
    - ILIKE still earns its place for partial words: someone typing "BB"
      expects to see "BBC News", and full-text only matches whole terms.

    OR-ing all four conditions gives the union, so a query is found whichever
    way it was meant. Results stay newest-first rather than ranked by
    relevance: `ts_rank` needs raw SQL, which the Supabase client can't send
    without a database function, and on a personal library of this size
    recency is the more useful order anyway.
    """
    # PostgREST parses this filter as comma-separated conditions, and tsquery
    # has its own operator characters — so anything outside letters, digits and
    # spaces is dropped rather than escaped. Simpler, and no query the user
    # would realistically type is meaningfully worse for it.
    safe = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
    if not safe:
        return []

    response = (
        _client.table(_TABLE)
        .select("*")
        .or_(
            f"title.plfts.{safe},summary.plfts.{safe},"
            f"title.ilike.%{safe}%,summary.ilike.%{safe}%"
        )
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return [Item(**row) for row in response.data]


def get_pending_items(limit: int = 20) -> list[Item]:
    """Items that were saved without the AI running because the daily quota
    was exhausted — the reprocessing queue.

    Only `quota_exceeded`, never `failed`. Quota exhaustion is transient by
    definition and will succeed on a later attempt; a generic failure may be
    permanent (a malformed page, a link the model can't make sense of), and
    sweeping those would retry the same doomed item every day forever, burning
    quota that new saves need. Those are fixed by re-sharing instead, which is
    a deliberate act by someone who wants that specific item retried.

    Oldest first: the longest-waiting item deserves the next free request.
    """
    response = (
        _client.table(_TABLE)
        .select("*")
        .eq("ai_status", "quota_exceeded")
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return [Item(**row) for row in response.data]


def update_item_ai(item_id: str, result, ai_status: str) -> Item:
    """Write a fresh AI result over an existing row.

    Only the AI-derived columns are touched — url, source, thumbnail_url,
    raw_content and created_at are left exactly as they were, so an item keeps
    its place in the list rather than jumping to the top when it's reprocessed.
    """
    response = (
        _client.table(_TABLE)
        .update(
            {
                "title": result.title,
                "summary": result.summary,
                "folder": result.folder,
                "confidence": result.confidence,
                "ai_status": ai_status,
            }
        )
        .eq("id", item_id)
        .execute()
    )

    if not response.data:
        raise RuntimeError(f"Update matched no row with id {item_id}")

    logger.info("Reprocessed item %s -> folder=%s", item_id, result.folder)
    return Item(**response.data[0])


def delete_item(item_id: str) -> bool:
    """Delete by id. Returns False if no row matched."""
    response = _client.table(_TABLE).delete().eq("id", item_id).execute()
    deleted = bool(response.data)

    if deleted:
        logger.info("Deleted item %s", item_id)
    else:
        logger.warning("Delete found no item with id %s", item_id)

    return deleted
