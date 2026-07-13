from typing import Optional
from urllib.parse import parse_qs, urlparse

from models.schemas import Platform

# Domain suffix -> platform. We match on suffix so every subdomain works without
# listing them all: "m.youtube.com" and "music.youtube.com" both end in
# "youtube.com". This is why we compare with endswith() rather than equality.
_DOMAIN_MAP: dict[str, Platform] = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "tiktok.com": "tiktok",
    "instagram.com": "instagram",
    "twitter.com": "twitter",
    "x.com": "twitter",
}


def _hostname(url: str) -> str:
    """Lowercased hostname with a leading 'www.' stripped, or '' if unparseable."""
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def detect_platform(url: str) -> Platform:
    """Classify a URL by its domain.

    Anything with a hostname that we don't recognize is treated as "article" —
    the fetcher will try Jina Reader on it, which works for most of the web.
    "other" is reserved for URLs we cannot even parse a host out of.
    """
    host = _hostname(url)
    if not host:
        return "other"

    for domain, platform in _DOMAIN_MAP.items():
        if host == domain or host.endswith("." + domain):
            return platform

    return "article"


def extract_youtube_id(url: str) -> Optional[str]:
    """Pull the 11-character video ID out of a YouTube URL, or None.

    Handles the three shapes YouTube actually ships:
      youtube.com/watch?v=ID   -> query param
      youtu.be/ID              -> first path segment
      youtube.com/shorts/ID    -> second path segment (also /embed/ID, /live/ID)
    """
    parsed = urlparse(url)
    host = _hostname(url)

    if host == "youtu.be" or host.endswith(".youtu.be"):
        segments = [s for s in parsed.path.split("/") if s]
        return segments[0] if segments else None

    video_id = parse_qs(parsed.query).get("v", [None])[0]
    if video_id:
        return video_id

    segments = [s for s in parsed.path.split("/") if s]
    if len(segments) >= 2 and segments[0] in {"shorts", "embed", "live", "v"}:
        return segments[1]

    return None
