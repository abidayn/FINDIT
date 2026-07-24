import json
import re
import time

from google import genai
from google.genai import types

from config import GEMINI_API_KEY
from models.schemas import AIResult, FetchedContent, Platform
from utils.logger import get_logger

logger = get_logger(__name__)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set")

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-3.5-flash"

ALLOWED_FOLDERS = {
    "Self Growth",
    "Productivity",
    "Tech & Coding",
    "Finance",
    "Cooking & Food",
    "Fitness & Health",
    "Entertainment",
    "Learning",
    "Other",
}

# AI_FEATURE_SPEC.md Section 4.3 — the AI is told upfront how good its input is,
# so it knows whether to commit to an answer or hedge with low confidence.
_QUALITY_TIER: dict[Platform, str] = {
    "article": "HIGH",
    "youtube": "MEDIUM",
    "tiktok": "LOW",
    "instagram": "LOW",
    "twitter": "LOW",
    "other": "LOW",
}

MAX_CONTENT_CHARS = 8_000
MIN_CONTENT_CHARS = 20

FALLBACK_RESULT = AIResult(
    title="Untitled saved item",
    summary="Could not generate summary. Tap to view original.",
    folder="Other",
    confidence="low",
)

# A separate object from FALLBACK_RESULT so routes/save.py can tell the two
# apart by identity. Running out of daily quota is not a malfunction — the item
# is fine and would process correctly tomorrow — and saying so is the difference
# between a user waiting it out and a user reporting a bug.
QUOTA_FALLBACK_RESULT = AIResult(
    title="Untitled saved item",
    summary="Daily AI limit reached. Tap to view original.",
    folder="Other",
    confidence="low",
)

_INSTRUCTIONS = """You are a content classifier and summarizer for a personal knowledge management app. Your job is to take a piece of content and produce a short title, a brief summary, and a folder classification.

RULES:
- Return ONLY valid JSON matching the schema below
- Do not include markdown, code fences, or any text outside the JSON
- Title: 1-7 words, sentence case, descriptive
- Summary: 1-2 sentences, max 200 characters, describes what the content is about
- Folder: must be EXACTLY one of the listed values
- Confidence: assess how clearly the content fits a folder

ALLOWED FOLDERS:
- Self Growth: self-improvement, mindset, habits, motivation, psychology
- Productivity: time management, focus, work systems, tools, GTD
- Tech & Coding: programming, AI/ML, software, gadgets, web development
- Finance: money, investing, budgeting, careers, salary, business
- Cooking & Food: recipes, food culture, kitchen tips, restaurants
- Fitness & Health: exercise, nutrition, mental health, sleep, medical
- Entertainment: movies, music, games, books, pop culture
- Learning: education, study tips, academic content, non-tech how-tos
- Other: anything that doesn't clearly fit

OUTPUT SCHEMA:
{
  "title": "string",
  "summary": "string",
  "folder": "string",
  "confidence": "high | medium | low"
}"""

# Appended on the retry attempt only (AI_FEATURE_SPEC.md Section 9.1: "retry once
# with a slightly stricter prompt").
_STRICTER_SUFFIX = "\n\nIMPORTANT: Your previous response was not valid JSON. Respond with the raw JSON object only. No prose, no markdown, no code fences."

_HTML_TAG = re.compile(r"<[^>]+>")


def _normalize(text: str) -> str:
    """AI_FEATURE_SPEC.md Section 4.2 — strip stray HTML, collapse whitespace,
    cap length. The cap keeps the prompt small (cost) and well inside the
    model's context."""
    cleaned = _HTML_TAG.sub(" ", text)
    cleaned = " ".join(cleaned.split())
    return cleaned[:MAX_CONTENT_CHARS]


def build_prompt(content: FetchedContent, stricter: bool = False) -> str:
    """Fill the template from AI_FEATURE_SPEC.md Section 6.1."""
    body = _normalize(content.text)
    tier = _QUALITY_TIER.get(content.source_platform, "LOW")

    if len(body) < MIN_CONTENT_CHARS:
        # Low-information variant (Section 6.3). We tell the model outright that
        # it has almost nothing to work with, which is what stops it from
        # inventing a plausible-sounding summary for a video it cannot see.
        tier = "LOW"
        handle = content.metadata.get("handle", "")
        platform_label = content.source_platform
        body = (
            f"The user saved a {platform_label} item. No transcript or description is available. "
            f"Make your best guess from the URL pattern"
            + (f" and creator handle ({handle})" if handle else "")
            + '. If you cannot reasonably classify, use folder "Other" and confidence "low".'
        )

    prompt = (
        f"{_INSTRUCTIONS}\n\n"
        f"CONTENT QUALITY: {tier}\n"
        f"SOURCE PLATFORM: {content.source_platform}\n"
        f"URL: {content.url}\n\n"
        f"CONTENT:\n{body}"
    )

    return prompt + _STRICTER_SUFFIX if stricter else prompt


def call_gemini(prompt: str) -> str:
    """Raw call. Returns the model's text. Raises on network/API failure."""
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            max_output_tokens=300,
            response_mime_type="application/json",
            # Gemini 3.x thinks before answering, and those thinking tokens are
            # charged against max_output_tokens. Left on, thinking alone ate
            # ~270 of our 300 and the actual JSON came back truncated to "".
            # Classifying into 9 fixed folders needs no deliberation, so we turn
            # it off: faster, cheaper, and more consistent.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return response.text or ""


def validate(raw: str) -> AIResult | None:
    """AI_FEATURE_SPEC.md Section 8.1. Returns None when the response is
    unusable — the caller turns that into a retry, then a fallback.

    The AI's output is untrusted input, exactly like a request body from a
    stranger. Everything recoverable is repaired (bad folder -> "Other"); only
    the unrecoverable returns None.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("AI returned non-JSON output")
        return None

    if not isinstance(data, dict):
        return None

    required = {"title", "summary", "folder", "confidence"}
    if not required.issubset(data.keys()):
        logger.warning("AI response missing fields: %s", required - data.keys())
        return None

    if not all(isinstance(data[k], str) for k in required):
        logger.warning("AI response had a non-string field")
        return None

    if not data["title"] or len(data["title"].split()) > 8:
        logger.warning("AI title unusable: %r", data["title"])
        return None

    if len(data["summary"]) > 250:
        # Trim at the last sentence boundary so we don't cut mid-word.
        data["summary"] = data["summary"][:200].rsplit(".", 1)[0] + "."

    if data["folder"] not in ALLOWED_FOLDERS:
        logger.warning("AI hallucinated folder %r, correcting to Other", data["folder"])
        data["folder"] = "Other"

    if data["confidence"] not in {"high", "medium", "low"}:
        data["confidence"] = "low"

    return AIResult(
        title=data["title"],
        summary=data["summary"],
        folder=data["folder"],
        confidence=data["confidence"],
    )


def _is_quota_error(exc: Exception) -> bool:
    """True when Gemini refused the call for quota rather than a real fault.

    Checks the typed `code` first and falls back to matching the message,
    because the SDK does not guarantee a typed error for every transport path
    (a raw HTTP error can surface as a plain Exception).
    """
    return getattr(exc, "code", None) == 429 or "RESOURCE_EXHAUSTED" in str(exc)


def process_content(content: FetchedContent) -> AIResult:
    """The single public entry point to the AI (Core Architectural Rule 1).

    One retry, then fallback — never a loop. A save must always complete, so
    this function does not raise: a total AI failure still yields a saveable
    item with the URL intact.
    """
    for attempt in (1, 2):
        try:
            raw = call_gemini(build_prompt(content, stricter=attempt == 2))
            result = validate(raw)
            if result:
                logger.info(
                    "AI ok (attempt %d): folder=%s confidence=%s",
                    attempt,
                    result.folder,
                    result.confidence,
                )
                return result
        except Exception as exc:
            if _is_quota_error(exc):
                # Retrying is pointless: the daily counter does not reset for
                # hours, so a second call would fail identically and only slow
                # the save down. Bail out with the distinct quota result.
                logger.error(
                    "Gemini quota exhausted, saving %s without AI: %s", content.url, exc
                )
                return QUOTA_FALLBACK_RESULT
            logger.warning("Gemini call failed (attempt %d): %s", attempt, exc)

        if attempt == 1:
            time.sleep(1)  # Section 9.1: back off once before retrying.

    logger.error("AI failed for %s, using fallback", content.url)
    return FALLBACK_RESULT
