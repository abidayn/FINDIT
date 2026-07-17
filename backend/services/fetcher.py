import re

import httpx

from config import JINA_API_KEY, YOUTUBE_API_KEY
from models.schemas import FetchedContent, Platform
from utils.logger import get_logger
from utils.url_parser import detect_platform, extract_youtube_id

logger = get_logger(__name__)

TIMEOUT = 10.0  # ARCHITECTURE.md 3.4: 10s max per fetch

# Matches any <meta ...> tag; property/content are then pulled out separately
# so attribute order in the tag doesn't matter (some sites emit
# content="..." before property="og:...").
_META_TAG = re.compile(r"<meta\s+[^>]*>", re.IGNORECASE)
_OG_PROPERTY = re.compile(r'property=["\']og:(\w+)["\']')
_CONTENT_ATTR = re.compile(r'content=["\']([^"\']*)["\']')

_HANDLE = re.compile(r"/@([\w.]+)")


def fetch_content(url: str) -> FetchedContent:
    """Fetch whatever content is available for a URL. Never raises — any
    failure degrades to empty text so the save can still proceed with AI
    running on metadata alone (TASKS.md 1.3, ARCHITECTURE.md Rule 5)."""
    platform = detect_platform(url)

    try:
        if platform == "article":
            content = _fetch_article(url, platform)
        elif platform == "youtube":
            content = _fetch_youtube(url, platform)
        else:
            content = _fetch_open_graph(url, platform)
    except Exception as exc:
        logger.warning("Fetch failed for %s (%s): %s", url, platform, exc)
        return FetchedContent(url=url, text="", source_platform=platform)

    if not content.text:
        logger.warning("Fetch returned no content for %s (%s)", url, platform)

    return content


def _fetch_article(url: str, platform: Platform) -> FetchedContent:
    """Jina Reader turns any article URL into clean Markdown text."""
    headers = {"Authorization": f"Bearer {JINA_API_KEY}"} if JINA_API_KEY else {}
    response = httpx.get(f"https://r.jina.ai/{url}", headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    return FetchedContent(url=url, text=response.text.strip(), source_platform=platform)


def _fetch_youtube(url: str, platform: Platform) -> FetchedContent:
    """Title + description + tags via YouTube Data API v3. No transcript —
    transcripts are blocked from cloud IPs (CLAUDE.md, Known Constraints)."""
    video_id = extract_youtube_id(url)
    if not video_id or not YOUTUBE_API_KEY:
        return FetchedContent(url=url, text="", source_platform=platform)

    response = httpx.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"id": video_id, "part": "snippet", "key": YOUTUBE_API_KEY},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    if not items:
        return FetchedContent(url=url, text="", source_platform=platform)

    snippet = items[0]["snippet"]
    text = "\n".join(
        filter(None, [snippet.get("title", ""), snippet.get("description", ""), " ".join(snippet.get("tags", []))])
    )
    thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url")

    return FetchedContent(url=url, text=text, source_platform=platform, thumbnail_url=thumbnail)


def _fetch_open_graph(url: str, platform: Platform) -> FetchedContent:
    """TikTok/Instagram/Twitter/unknown: whatever Open Graph tags are in the
    raw HTML. These platforms often block non-browser requests entirely —
    that's fine, it just means text stays empty and the AI falls back to its
    low-information prompt (AI_FEATURE_SPEC.md 6.3)."""
    response = httpx.get(
        url, timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}
    )
    response.raise_for_status()

    tags = {}
    for tag in _META_TAG.findall(response.text):
        prop_match = _OG_PROPERTY.search(tag)
        content_match = _CONTENT_ATTR.search(tag)
        if prop_match and content_match:
            tags[prop_match.group(1)] = content_match.group(1)

    text = "\n".join(filter(None, [tags.get("title", ""), tags.get("description", "")]))

    handle_match = _HANDLE.search(url)
    metadata = {"handle": f"@{handle_match.group(1)}"} if handle_match else {}

    return FetchedContent(
        url=url, text=text, source_platform=platform, thumbnail_url=tags.get("image"), metadata=metadata
    )
