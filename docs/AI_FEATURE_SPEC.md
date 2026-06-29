# AI Feature Specification

**Project:** Stash (working name)
**Author:** Biday
**Last updated:** June 26, 2026
**Status:** Draft v1.0 — locked for MVP

---

## 1. Purpose of This Document

`PRD.md` says *what* the product does. `ARCHITECTURE.md` says *how* the system is structured. This document specifies **exactly what the AI does, how it's called, what it returns, and how the system handles its failures.**

This is the most precision-critical doc in the project. Vague AI specs = AI that hallucinates folders, produces inconsistent titles, and breaks the user experience.

Audience: the builder and Claude Code while implementing the AI service.

---

## 2. AI Tasks Overview

The AI has **one job, with three outputs**, executed in a single API call:

| Output | Type | Constraint |
|--------|------|-----------|
| `title` | string | Max 7 words, no quotes, descriptive not clickbait |
| `summary` | string | 1–2 sentences, max 200 characters |
| `folder` | string | Must be one of the predefined taxonomy values |

This is a **classification + generation** task. Not chat. Not agent. Not RAG (yet). The AI runs once per saved item, never again unless explicitly re-triggered.

### 2.1 What the AI does NOT do (MVP)

- Does not answer user questions
- Does not summarize multiple items together
- Does not suggest related items
- Does not run search queries
- Does not interact with the user directly
- Does not generate new folders (taxonomy is fixed)

These are explicitly post-MVP capabilities.

---

## 3. Model & Configuration

### 3.1 Model

**Gemini 3.5 Flash** (`gemini-3.5-flash`) via Google AI Studio API.

> Note (2026-06-29): The docs originally specified `gemini-3-flash`, but that exact ID does not exist in the API. The real stable Flash model available on the free tier is `gemini-3.5-flash`. Chosen over `gemini-3-flash-preview` because preview models can be deprecated without notice.

- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent`
- Auth: API key in query parameter (`?key=...`) or header
- Free tier (as of mid-2026): 10 RPM, 1,500 RPD, 250K TPM

### 3.2 Generation config

```json
{
  "temperature": 0.2,
  "topP": 0.95,
  "topK": 40,
  "maxOutputTokens": 300,
  "responseMimeType": "application/json"
}
```

**Why these values:**

- **Low temperature (0.2):** Classification needs consistency. Same input should give same folder. Higher temp = creative variation, which is exactly what we don't want.
- **maxOutputTokens 300:** Title + summary + folder fits comfortably in ~150 tokens. 300 gives headroom for the JSON wrapper without runaway generation.
- **responseMimeType: application/json:** Gemini natively supports JSON-only output. This prevents the model from adding "Here's your JSON:" prefixes or markdown fences.

### 3.3 Safety settings

Default Gemini safety settings are fine for MVP. No content moderation needed — the AI is processing public web content the user already chose to save.

---

## 4. Input Contract

### 4.1 What the AI receives

The AI receives a single text prompt containing:

1. **System instructions** — what the AI's job is, format requirements
2. **Folder taxonomy** — the exact list of allowed folders
3. **Content metadata** — source platform, URL
4. **Content body** — the actual text to summarize/classify

### 4.2 Content normalization before sending

Before calling the AI, the backend normalizes raw content:

- Trim whitespace
- Strip HTML tags if any leaked through
- Truncate to **8,000 characters** (roughly 2,000 tokens — keeps prompt small, leaves room for Gemini's context)
- If content is empty or under 20 characters, route to the "low-information variant" prompt (see Section 6.3)

### 4.3 Content quality tiers

Different sources yield different content quality. The AI is told upfront what quality tier the content is:

| Tier | Sources | Typical content |
|------|---------|-----------------|
| **HIGH** | Articles, blog posts | Full readable text, several hundred to several thousand words |
| **MEDIUM** | YouTube videos | Title + description + tags (description may be detailed) |
| **LOW** | TikTok, Instagram, Twitter | URL + creator handle + caption fragment if available |

The AI behaves differently per tier — see Section 6.

---

## 5. Output Contract

### 5.1 JSON schema (strict)

The AI must return JSON matching this schema exactly:

```json
{
  "title": "string (1-7 words)",
  "summary": "string (1-2 sentences, max 200 chars)",
  "folder": "Self Growth | Productivity | Tech & Coding | Finance | Cooking & Food | Fitness & Health | Entertainment | Learning | Other",
  "confidence": "high | medium | low"
}
```

### 5.2 Field rules

**`title`**
- 1 to 7 words
- Sentence case (capitalize first word and proper nouns only)
- No quotes around it
- No clickbait phrasing (no "You won't believe..." or "This one trick...")
- Descriptive of the actual content, not the medium ("Morning routine for focus" not "TikTok about mornings")

**`summary`**
- 1 to 2 complete sentences
- Maximum 200 characters total
- Describes what the content teaches, shows, or claims
- Written in present tense, third person
- No "this video shows..." preamble; just state the content

**`folder`**
- Must be EXACTLY one of the 9 predefined values
- Case-sensitive match
- If unsure, default to "Other"

**`confidence`**
- `high` — content was rich and unambiguous
- `medium` — content was partial or topic could fit multiple folders
- `low` — content was minimal (e.g., TikTok with no caption); AI guessed from metadata

The backend uses `confidence` to decide whether to show a UI hint like "We weren't sure about this one — tap to adjust."

### 5.3 Folder taxonomy (v1, fixed)

| Folder | Examples of what goes here |
|--------|---------------------------|
| **Self Growth** | Self-improvement, mindset, habits, motivation, psychology |
| **Productivity** | Time management, focus, work systems, tools, getting things done |
| **Tech & Coding** | Programming, AI/ML, software, gadgets, web development |
| **Finance** | Money, investing, budgeting, careers, salary, business basics |
| **Cooking & Food** | Recipes, food culture, kitchen tips, restaurants |
| **Fitness & Health** | Exercise, nutrition, mental health, sleep, medical info |
| **Entertainment** | Movies, music, games, books-as-entertainment, pop culture |
| **Learning** | Education, study tips, academic content, how-tos for non-tech skills |
| **Other** | Anything that doesn't clearly fit, or low-info items |

---

## 6. Prompt Design

### 6.1 Base prompt template

```
You are a content classifier and summarizer for a personal knowledge management app. Your job is to take a piece of content and produce a short title, a brief summary, and a folder classification.

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
}

CONTENT QUALITY: {quality_tier}
SOURCE PLATFORM: {source_platform}
URL: {url}

CONTENT:
{content}
```

### 6.2 Variables to fill in at runtime

| Variable | Source |
|----------|--------|
| `{quality_tier}` | Determined by source: HIGH / MEDIUM / LOW |
| `{source_platform}` | "article", "youtube", "tiktok", "instagram", "twitter", "other" |
| `{url}` | The original URL the user shared |
| `{content}` | Normalized content from the fetcher service |

### 6.3 Low-information variant

When content is empty or under 20 characters (e.g., TikTok with no accessible caption), the backend sends a different content block:

```
CONTENT QUALITY: LOW
SOURCE PLATFORM: tiktok
URL: https://www.tiktok.com/@username/video/12345

CONTENT:
The user saved a TikTok video. No transcript or description is available. Make your best guess from the URL pattern and creator handle (@username). If you cannot reasonably classify, use folder "Other" and confidence "low". Title should reference the creator: "TikTok by @username".
```

This explicitly tells the AI: don't hallucinate, accept low confidence, use a templated title.

---

## 7. Example Inputs and Outputs

### 7.1 Example A: High-quality article

**Input content** (truncated):
```
"How to Build a Morning Routine That Actually Sticks
By Sarah Chen, posted 3 days ago

Most morning routines fail because they're too ambitious. You watch a YouTube video about someone waking at 5 AM, doing yoga, journaling, cold plunging, and reading 50 pages — and you try to replicate the entire thing on Monday. By Wednesday, you've quit.

The science of habit formation says the opposite approach works..."
```

**Expected AI output:**
```json
{
  "title": "Why simple morning routines stick",
  "summary": "Argues that ambitious morning routines fail and small habits compound better. Cites habit formation research.",
  "folder": "Self Growth",
  "confidence": "high"
}
```

### 7.2 Example B: YouTube video metadata

**Input content:**
```
Title: How I Learned to Code in 6 Months (No CS Degree)
Channel: TechWithLena
Description: In this video I share the exact 6-month roadmap I used to land my first software engineering job without a CS degree. I cover: choosing a language (Python), building 5 portfolio projects, contributing to open source, and the cold email script that got me interviews. Timestamps: 0:00 Intro, 2:14 Why Python first, 8:30 Project list, 15:00 Cold email script.
Tags: coding, self-taught programming, career change, python, software engineering
```

**Expected AI output:**
```json
{
  "title": "Six-month self-taught coding roadmap",
  "summary": "A self-taught engineer breaks down their 6-month plan to landing a software job, including projects and cold email tactics.",
  "folder": "Tech & Coding",
  "confidence": "high"
}
```

### 7.3 Example C: Low-info TikTok

**Input content:**
```
The user saved a TikTok video. No transcript or description is available. Make your best guess from the URL pattern and creator handle (@chef.mariko). If you cannot reasonably classify, use folder "Other" and confidence "low".
```

**Expected AI output:**
```json
{
  "title": "TikTok by @chef.mariko",
  "summary": "Saved video from @chef.mariko. Content details unavailable; based on creator handle, likely food-related.",
  "folder": "Cooking & Food",
  "confidence": "low"
}
```

### 7.4 Example D: Ambiguous content

**Input content:**
```
"3 Stretches to Do Before Coding Sessions"
A short video showing 3 desk stretches: neck rolls, wrist circles, and shoulder shrugs. Demonstrated by a software developer who mentions doing these between focus blocks.
```

**Expected AI output:**
```json
{
  "title": "Three desk stretches for coders",
  "summary": "Three quick stretches — neck rolls, wrist circles, shoulder shrugs — designed to do between coding focus blocks.",
  "folder": "Fitness & Health",
  "confidence": "medium"
}
```

Note the `medium` confidence — could also reasonably be "Productivity" or "Tech & Coding". AI picked the primary topic (physical stretches) but flagged ambiguity.

---

## 8. Validation Logic (Backend-Side)

After receiving the AI response, the backend performs **strict validation** before saving:

### 8.1 Validation steps

```python
def validate_ai_output(raw_response: str) -> AIResult | None:
    # Step 1: Parse JSON
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        return None  # Will trigger retry

    # Step 2: Check required fields exist
    required = {"title", "summary", "folder", "confidence"}
    if not required.issubset(data.keys()):
        return None

    # Step 3: Type checks
    if not all(isinstance(data[k], str) for k in required):
        return None

    # Step 4: Constraint checks
    if not data["title"] or len(data["title"].split()) > 8:
        return None  # 8 to allow slight overrun; reject extreme cases
    if len(data["summary"]) > 250:  # Slight buffer over the 200 target
        data["summary"] = data["summary"][:200].rsplit(".", 1)[0] + "."
    if data["folder"] not in ALLOWED_FOLDERS:
        data["folder"] = "Other"  # Auto-correct
    if data["confidence"] not in {"high", "medium", "low"}:
        data["confidence"] = "low"  # Default conservative

    return AIResult(**data)
```

### 8.2 Why this much validation?

LLMs occasionally:
- Return malformed JSON (missing comma, trailing comma)
- Add a markdown code fence around the JSON despite instructions
- Hallucinate a folder name that doesn't exist
- Produce overlong titles that wouldn't fit in the UI

Backend treats AI output as **untrusted input** — same as user input. Validate everything.

---

## 9. Fallback & Error Handling

### 9.1 Failure modes and responses

| Failure | What happens | User experience |
|---------|--------------|-----------------|
| Network error calling Gemini | Retry once after 1s backoff. If fails again, use fallback. | Item saves with placeholder metadata; UI shows "Couldn't process — tap to retry" |
| Gemini returns 429 (rate limit) | Wait 5s, retry once. If still failing, queue for later. | Item saves with placeholder; background re-processes when quota frees |
| Gemini returns malformed JSON | Retry once with a slightly stricter prompt. If still fails, use fallback. | Item saves with fallback values |
| Validation fails on retry | Save with fallback values | Item visible but flagged as low-confidence |
| Gemini returns hallucinated folder | Auto-correct to "Other" silently | User sees item in "Other" |

### 9.2 Fallback values

```python
FALLBACK_RESULT = AIResult(
    title="Untitled saved item",
    summary="Could not generate summary. Tap to view original.",
    folder="Other",
    confidence="low"
)
```

### 9.3 Re-processing later

Items saved with fallback values are marked with `ai_status = "failed"` in the database. A future feature can let the user manually trigger re-processing, or a background job can retry failed items during off-peak times.

For MVP: failed items simply stay as fallback. The URL is preserved, so the user always has the original content.

---

## 10. Where the AI is Called

### 10.1 Call sites

The AI is called from exactly **one place** in the codebase:

```
backend/services/ai.py → function process_content(fetched_content: FetchedContent) -> AIResult
```

This function is called by:
- `routes/save.py` → during the `/save` endpoint flow

No other code path calls the AI directly. This single-call-site rule makes:
- Cost tracking easy (count calls in one place)
- Prompt iteration safe (change once, applies everywhere)
- Testing easier (mock one function)

### 10.2 Pseudocode for the AI service

```python
# backend/services/ai.py

from google import genai
from models.schemas import FetchedContent, AIResult

client = genai.Client(api_key=settings.GEMINI_API_KEY)

ALLOWED_FOLDERS = {
    "Self Growth", "Productivity", "Tech & Coding", "Finance",
    "Cooking & Food", "Fitness & Health", "Entertainment",
    "Learning", "Other"
}

def build_prompt(content: FetchedContent) -> str:
    # Returns the full prompt string with all variables filled in
    ...

def call_gemini(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config={
            "temperature": 0.2,
            "max_output_tokens": 300,
            "response_mime_type": "application/json"
        }
    )
    return response.text

def validate(raw: str) -> AIResult | None:
    # See Section 8.1
    ...

def process_content(content: FetchedContent) -> AIResult:
    prompt = build_prompt(content)

    for attempt in range(2):  # one retry
        try:
            raw = call_gemini(prompt)
            result = validate(raw)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"AI call attempt {attempt} failed: {e}")

    logger.error("AI processing failed after retry, using fallback")
    return FALLBACK_RESULT
```

---

## 11. Testing Strategy

### 11.1 Manual test cases (must pass before shipping)

Run these by hand against the deployed AI service. Each should produce a sensible output matching expectations.

| # | Input | Expected folder | Expected confidence |
|---|-------|-----------------|---------------------|
| 1 | Article about morning routines | Self Growth | high |
| 2 | YouTube video on Python tutorials (with description) | Tech & Coding | high |
| 3 | YouTube video, title only, no description | (varies) | medium |
| 4 | TikTok URL with no content available | Other | low |
| 5 | Article about a movie review | Entertainment | high |
| 6 | Recipe blog post | Cooking & Food | high |
| 7 | Article comparing index funds vs ETFs | Finance | high |
| 8 | Article that's an ad/clickbait with no real topic | Other | low |
| 9 | Content longer than 8K chars (test truncation) | (varies) | high or medium |
| 10 | Empty content string | Other | low |

### 11.2 Automated tests (post-MVP, optional)

If/when test infrastructure is added:

- Unit test `validate()` with malformed JSON inputs
- Unit test `build_prompt()` produces expected string format
- Integration test the full `process_content()` path with mocked Gemini responses
- Snapshot test: a fixed set of inputs should produce stable outputs

### 11.3 Eval after 50 real saves

After using the app personally for 1–2 weeks (50+ saved items), review:

- Are titles useful or generic?
- Is the folder distribution skewed (too much in "Other"?)
- Are summaries accurate or hallucinated?
- Where does AI get confused?

Adjust prompt based on real failure patterns. The prompt is meant to evolve.

---

## 12. Cost & Performance

### 12.1 Per-call cost estimate

Free tier: $0 per call up to 1,500 RPD.

If migrating to paid tier (Gemini 3 Flash paid rates, mid-2026):
- Input: ~$0.15 per 1M tokens
- Output: ~$0.60 per 1M tokens
- Per save: ~2,000 input tokens + ~150 output tokens
- Cost per save: roughly $0.0004 — about $0.40 per 1,000 saves

For solo personal use, the free tier is effectively infinite. Even for 50 early users averaging 5 saves a day = 250 calls/day, well within free quota.

### 12.2 Latency budget

| Phase | Target |
|-------|--------|
| Prompt construction | <10ms |
| Gemini API call | 800–1500ms |
| Validation | <5ms |
| **Total AI time per save** | **~1 second** |

This fits within the overall 5-second save budget (see ARCHITECTURE.md Section 9.1).

---

## 13. Prompt Iteration Log

This section is intentionally left empty in v1. As the prompt is tuned during real use, each meaningful change should be logged here with:

- Date
- What changed
- Why
- Observed impact (if any)

Example entry format:

```
2026-07-15 — Added "do not use clickbait phrasing" to title rule.
Reason: AI was generating titles like "You won't believe these stretches" for fitness content.
Impact: Titles became more descriptive; no regressions in folder accuracy.
```

---

## 14. Future Enhancements (Post-MVP)

### 14.1 Semantic search (RAG)

- Add `text-embedding-004` (Gemini's free embedding model) call alongside Gemini 3 Flash
- Generate embedding for `title + summary` at save time
- Store in `pgvector` column on `items` table
- At search time, embed query and run vector similarity search

### 14.2 Smart re-classification

- Periodically re-run AI on items that came back with `confidence: low`
- Allow user to trigger "re-process" on individual items
- A/B test different prompt versions silently

### 14.3 Custom user folders

- Allow user to define their own folder names
- AI taxonomy becomes dynamic: predefined + user-created
- Requires teaching AI about user folders via few-shot examples in the prompt

### 14.4 Multi-modal (images / screenshots)

- Gemini 3 Flash supports image input natively
- Same API call, just include the image as a content part
- Useful for screenshot saving (post-MVP feature)

### 14.5 Chat with saved items

- Full RAG implementation: retrieve top-k items semantically, send to Gemini as context
- "What did I save about morning routines?" → conversational answer with citations
- Significant scope expansion; only after MVP is stable

---

## 15. Document References

- Product goals and user stories → `PRD.md`
- System architecture and service boundaries → `ARCHITECTURE.md`
- Phased build plan with tasks → `TASKS.md`
- Working agreement with Claude Code → `CLAUDE.md`

---

*End of AI_FEATURE_SPEC v1.0*
