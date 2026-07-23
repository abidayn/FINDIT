from supabase import Client, create_client

from config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from models.schemas import Item
from utils.logger import get_logger

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
    """Keyword search over title and summary.

    ILIKE is case-insensitive substring matching — crude, but it needs no
    ranking logic and behaves predictably on a small personal library. The GIN
    full-text index in the schema is for Phase 2, when we swap this for
    proper ranked search (TASKS.md 2.2).
    """
    pattern = f"%{query}%"
    response = (
        _client.table(_TABLE)
        .select("*")
        .or_(f"title.ilike.{pattern},summary.ilike.{pattern}")
        .order("created_at", desc=True)
        .execute()
    )
    return [Item(**row) for row in response.data]


def delete_item(item_id: str) -> bool:
    """Delete by id. Returns False if no row matched."""
    response = _client.table(_TABLE).delete().eq("id", item_id).execute()
    deleted = bool(response.data)

    if deleted:
        logger.info("Deleted item %s", item_id)
    else:
        logger.warning("Delete found no item with id %s", item_id)

    return deleted
