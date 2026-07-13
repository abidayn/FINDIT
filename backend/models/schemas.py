from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl

# The 9 fixed folders (AI_FEATURE_SPEC.md Section 5). Literal instead of a plain
# str means Pydantic itself rejects anything outside this set — the type is the
# validation.
Folder = Literal[
    "Self Growth",
    "Productivity",
    "Tech & Coding",
    "Finance",
    "Cooking & Food",
    "Fitness & Health",
    "Entertainment",
    "Learning",
    "Other",
]

Confidence = Literal["high", "medium", "low"]

Platform = Literal["youtube", "tiktok", "instagram", "twitter", "article", "other"]


class SaveRequest(BaseModel):
    """Input to POST /save. HttpUrl rejects malformed URLs before any work starts."""

    url: HttpUrl


class FetchedContent(BaseModel):
    """Output of fetcher.py, input to ai.py. Never raises — an empty `text`
    means the fetch failed, and the AI step still runs on whatever we have."""

    text: str = ""
    source_platform: Platform = "other"
    metadata: dict = Field(default_factory=dict)
    thumbnail_url: Optional[str] = None


class AIResult(BaseModel):
    """Output of ai.process_content(). Already validated against the schema in
    AI_FEATURE_SPEC.md Section 8 — by the time it is an AIResult, it is trusted."""

    title: str
    summary: str
    folder: Folder
    confidence: Confidence


class Item(BaseModel):
    """A row of the `items` table, and the response body of /save and /items."""

    id: str
    url: str
    title: str
    summary: Optional[str] = None
    folder: Folder
    source: Optional[Platform] = None
    thumbnail_url: Optional[str] = None
    raw_content: Optional[str] = None
    created_at: datetime
    user_id: Optional[str] = None
    confidence: Optional[Confidence] = None
    # "ok" when the AI ran cleanly, "failed" when we saved with fallback values
    # (AI_FEATURE_SPEC.md Section 9). Lets us re-process bad items later.
    ai_status: Optional[Literal["ok", "failed"]] = None


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: Optional[str] = None
