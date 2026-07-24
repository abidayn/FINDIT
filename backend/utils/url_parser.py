from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from models.schemas import Platform

# Query parameters that identify *who shared it*, not *what it is*. Share
# sheets regenerate these every time, so the same Instagram post shared twice
# produces two different URL strings — which is exactly what would defeat a
# naive duplicate check. Anything starting with "utm_" is stripped too.
_TRACKING_PARAMS = {
    "igsh", "igshid", "img_index",  # Instagram (img_index picks a carousel slide, same post)
    "_t", "_r", "is_from_webapp", "sender_device", "web_id",  # TikTok
    "si", "feature", "pp",  # YouTube
    "fbclid", "gclid", "ref", "ref_src", "s", "source",  # generic
}

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


def normalize_url(url: str) -> str:
    """A stable key for "is this the same link?" — for comparison only.

    The original URL is always what gets stored and opened; this is purely a
    comparison key, so it is allowed to throw away parts that a browser needs.

    Normalizes: lowercased scheme and host, "www." dropped, tracking params
    removed, remaining params sorted, trailing slash and #fragment dropped.

    Deliberately NOT handled: different URL *forms* of the same content, e.g.
    youtu.be/ID vs youtube.com/watch?v=ID, or a vt.tiktok.com share link vs the
    full URL it redirects to. Catching those means resolving redirects or
    special-casing each platform, which is a much larger job for a rarer case.
    Unparseable input is returned unchanged rather than raising — the caller is
    deduplicating, and a URL it cannot normalize simply never matches anything.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return url

    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if parsed.port:
        host = f"{host}:{parsed.port}"

    kept = {
        key: values
        for key, values in parse_qs(parsed.query).items()
        if key.lower() not in _TRACKING_PARAMS and not key.lower().startswith("utm_")
    }
    # Sorted so ?a=1&b=2 and ?b=2&a=1 produce the same key.
    query = urlencode(sorted((k, v) for k, vs in kept.items() for v in vs))

    path = parsed.path.rstrip("/")

    return urlunparse((parsed.scheme.lower(), host, path, "", query, ""))


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
