# Architecture Document

**Project:** Stash (working name)
**Author:** Biday
**Last updated:** June 26, 2026
**Status:** Draft v1.0 — locked for MVP, will iterate after Phase 1

---

## 1. Purpose of This Document

This document explains **how the system is built**, not what it does. If `PRD.md` answers "what are we building and why," this document answers "how does it work technically and why these choices."

Audience: the builder (Biday), future contributors, and Claude Code while vibe coding. Written assuming the reader has limited industry experience — choices are explained, not just stated.

---

## 2. System Overview

### 2.1 High-level architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER'S ANDROID PHONE                       │
│                                                                  │
│  ┌──────────────┐         ┌─────────────────────────────────┐  │
│  │  TikTok / IG │         │      Stash App (React Native)   │  │
│  │  YouTube /   │ ──────▶ │                                 │  │
│  │  Chrome /etc │  share  │  - Home screen (list items)     │  │
│  └──────────────┘         │  - Search screen                │  │
│                            │  - Share intent receiver        │  │
│                            └──────────────┬──────────────────┘  │
│                                           │                      │
└───────────────────────────────────────────┼──────────────────────┘
                                            │ HTTPS
                                            │ (REST API)
                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND (Railway)                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              FastAPI Server (Python)                     │   │
│  │                                                          │   │
│  │   /save  ─┬──▶ Fetcher Service  ─┐                      │   │
│  │           │                      │                       │   │
│  │           ├──▶ AI Service        │                       │   │
│  │           │                      │                       │   │
│  │           └──▶ Database Service ─┘                      │   │
│  │                                                          │   │
│  │   /items ────▶ Database Service                          │   │
│  │   /search ───▶ Database Service                          │   │
│  └──────┬─────────────┬──────────────────┬─────────────────┘   │
│         │             │                  │                       │
└─────────┼─────────────┼──────────────────┼───────────────────────┘
          │             │                  │
          ▼             ▼                  ▼
   ┌──────────┐  ┌─────────────┐   ┌──────────────┐
   │   Jina   │  │   Gemini    │   │   Supabase   │
   │  Reader  │  │   1.5 Flash │   │  PostgreSQL  │
   │   API    │  │   API       │   │              │
   └──────────┘  └─────────────┘   └──────────────┘
   (fetch URL    (generate         (store & query
    content)     title/summary/    saved items)
                 folder)
```

### 2.2 The save flow, end-to-end

This is the most important flow in the app. Memorize this sequence.

```
1. User taps "Share" on a TikTok video
2. Android share sheet appears, user selects "Stash"
3. Stash app opens (or runs in background), receives the URL
4. App shows a "Saving..." toast/notification
5. App sends POST /save { url: "..." } to backend
6. Backend's /save endpoint:
   a. Validates the URL
   b. Calls Fetcher Service → gets content text (or empty if unfetchable)
   c. Calls AI Service with content → gets { title, summary, folder }
   d. Calls Database Service → inserts row into `items` table
   e. Returns the new item to the app
7. App shows "Saved! Tagged as: [folder]"
8. User goes back to TikTok, continues scrolling
```

Total target latency: **under 5 seconds** for articles and YouTube; **under 2 seconds** for TikTok/IG (less content to fetch).

---

## 3. Component-by-Component Breakdown

### 3.1 Mobile App (React Native + Expo)

**Role:** The user-facing layer. Receives shares, displays saved items, lets user search and browse.

**Why React Native + Expo:**
- Single codebase, JavaScript/TypeScript ecosystem
- TypeScript skills transfer directly to web dev (Next.js, React)
- Expo handles 90% of the build/deploy pain that bare React Native has
- Huge community, plenty of tutorials for first-timers
- Free to develop and ship to Android

**Key libraries:**

| Library | Purpose |
|---------|---------|
| `expo` | Core Expo framework |
| `expo-router` | File-based routing (like Next.js) — screens are files in `app/` |
| `expo-share-intent` | Receives shared URLs from other apps via Android share sheet |
| `@supabase/supabase-js` | Connect to Supabase (auth + DB) |
| `react-native-async-storage` | Local cache for offline-friendly browsing |
| `nativewind` (optional) | Tailwind for React Native — fast styling |

**Why "bare workflow" instead of "managed workflow":**

Expo has two modes. Managed is easier but limits native customization. Share intent needs native config (registering the app in Android's share sheet), so we use the **bare workflow** — Expo tools + the ability to edit native Android files when needed. The `expo prebuild` command generates the native folders on demand.

**What lives where:**
- **Screens** (`app/`) — what the user sees
- **Components** (`components/`) — reusable UI pieces
- **Lib** (`lib/`) — API calls, Supabase client, helpers
- **Hooks** (`hooks/`) — shared state and data-fetching logic
- **Types** (`types/`) — TypeScript type definitions shared across files

---

### 3.2 Backend (FastAPI on Railway)

**Role:** The brain. Orchestrates fetching content, calling AI, and storing/retrieving data. Mobile app never talks to AI or content sources directly — only the backend does.

**Why FastAPI:**
- Python-native, easy for first-timers
- Automatic API documentation (free Swagger UI at `/docs`)
- Fast enough for this use case (async support)
- Python is the de facto language for AI/ML — sets up future learning paths
- Excellent type hints via Pydantic — catches bugs at development time

**Why Railway for hosting:**
- Free tier sufficient for development and personal use
- Deploy via `git push` — no Kubernetes nightmare
- Automatic HTTPS
- Environment variables managed via dashboard
- Easy to swap to Render, Fly.io, or self-host later

**API endpoints (MVP):**

| Method | Endpoint | Purpose | Request | Response |
|--------|----------|---------|---------|----------|
| POST | `/save` | Save a new URL | `{ url: string }` | `Item` object |
| GET | `/items` | Get all saved items | — | `Item[]` |
| GET | `/items?folder=X` | Filter by folder | query param | `Item[]` |
| GET | `/search?q=...` | Search items | query param | `Item[]` |
| GET | `/health` | Health check | — | `{ status: "ok" }` |
| DELETE | `/items/{id}` | Delete an item | path param | `{ deleted: true }` |

All endpoints return JSON. Errors follow a consistent shape:

```json
{
  "error": "URL could not be fetched",
  "code": "FETCH_FAILED",
  "details": "Timeout after 10s"
}
```

**Internal services (modules within FastAPI):**

#### Fetcher Service (`services/fetcher.py`)

- Takes a URL, detects the source platform (YouTube, article, TikTok, etc.)
- Routes to the appropriate fetcher:
  - **YouTube** → `youtube-transcript-api` library to get transcript
  - **Article/blog** → Jina Reader API (`https://r.jina.ai/{url}`)
  - **TikTok/IG/Twitter** → minimal: URL + any metadata from Open Graph tags
- Returns a normalized `FetchedContent` object: `{ text, source_platform, metadata }`
- Has timeout (10s max) and graceful fallback to empty content on failure

#### AI Service (`services/ai.py`)

- Takes `FetchedContent`, builds a prompt, calls Gemini 1.5 Flash
- Parses the JSON response
- Validates against expected schema (title is string, folder is from allowed list, etc.)
- Retries once on invalid JSON; returns fallback values on second failure
- Details fully specified in `AI_FEATURE_SPEC.md`

#### Database Service (`services/database.py`)

- Wraps all Supabase queries
- Functions: `insert_item`, `get_all_items`, `get_items_by_folder`, `search_items`, `delete_item`
- Centralizes DB logic so endpoints stay clean
- Uses Supabase Python client (`supabase-py`)

---

### 3.3 Database (Supabase / PostgreSQL)

**Role:** Persistent storage for saved items. Single source of truth.

**Why Supabase:**
- Free tier: 500MB database, plenty for an MVP
- Built-in PostgreSQL — real, production-grade DB (not SQLite)
- Visual dashboard for inspecting data while debugging
- Built-in authentication (we won't use it in MVP but it's there for free later)
- `pgvector` extension available for semantic search (when we upgrade search post-MVP)

**Schema for MVP (v1):**

```sql
-- Table: items
CREATE TABLE items (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url           TEXT NOT NULL,
  title         TEXT NOT NULL,
  summary       TEXT,
  folder        TEXT NOT NULL,
  source        TEXT,                    -- 'youtube' | 'tiktok' | 'instagram' | 'article' | 'twitter' | 'other'
  thumbnail_url TEXT,                    -- nullable; may not always be available
  raw_content   TEXT,                    -- the fetched content, kept for future re-processing
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  user_id       UUID                     -- nullable in MVP (no auth); used later
);

CREATE INDEX idx_items_folder ON items(folder);
CREATE INDEX idx_items_created_at ON items(created_at DESC);
CREATE INDEX idx_items_user_id ON items(user_id);

-- Full-text search index for basic keyword search
CREATE INDEX idx_items_search ON items USING gin(
  to_tsvector('english', coalesce(title, '') || ' ' || coalesce(summary, ''))
);
```

**Note on `user_id`:** Stored as nullable in MVP. Single-device, single-user. Auth gets added in a future iteration if/when the app opens to others. Adding the column now is cheaper than migrating later.

**Note on `raw_content`:** Stored to allow future re-processing if we improve the AI pipeline or want to add semantic search later without re-fetching. Optional, but cheap insurance.

---

### 3.4 External Services

#### Jina Reader API

- URL: `https://r.jina.ai/{url}`
- Free tier with rate limits (sufficient for personal use)
- Returns clean Markdown text from any article URL
- No API key needed for basic use; optional key for higher limits
- Fallback: if Jina fails, use `httpx` to fetch raw HTML and `BeautifulSoup` to extract main content

#### Gemini 3 Flash (Google AI Studio)

- Free tier (as of mid-2026): 10 RPM, 250K TPM, 1,500 RPD
- Endpoint: https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash:generateContent
- Note: Google has revised free-tier limits multiple times (Dec 2025 cut quotas 50-80%, April 2026 removed Pro from free tier entirely). Verify current limits in Google AI Studio before relying on these numbers.
- Alternative: Gemini 3.1 Flash-Lite (15 RPM) if classification/extraction is the bottleneck

#### YouTube Data API v3

- Endpoint: https://www.googleapis.com/youtube/v3/videos
- Free tier: 10,000 units/day (one video fetch = 1 unit; effectively unlimited for personal use)
- Returns: title, description, tags, channel name, thumbnail URL
- Requires API key from Google Cloud Console (free, no billing required)
- Why not transcripts: youtube-transcript-api is frequently blocked when called from cloud provider IPs (Railway, Render, Fly). Residential proxies cost money. Official Data API doesn't provide auto-generated captions without OAuth as video owner. Title + description + tags from serious creators (especially educational/long-form) is dense enough for high-quality AI output.
- Stored in backend .env as YOUTUBE_API_KEY

---

## 4. Data Flow Examples

### 4.1 User saves a YouTube video

```
1. User: shares https://youtube.com/watch?v=abc123 from YouTube app
2. App receives URL via expo-share-intent
3. App: POST /save { "url": "https://youtube.com/watch?v=abc123" }
4. Backend /save:
   a. Validates URL → OK
   b. Fetcher.fetch_content(url):
      - detects platform: "youtube"
      - extracts video ID: "abc123"
      - calls YouTube Data API v3 /videos?id=abc123&part=snippet
      - returns FetchedContent{ text: "[title + description + tags]", source: "youtube", thumbnail_url: "..." }
   c. AI.process(fetched_content):
      - builds prompt with transcript
      - calls Gemini API
      - receives JSON: { title: "...", summary: "...", folder: "Learning" }
   d. Database.insert_item({ url, title, summary, folder, source: "youtube", raw_content: transcript })
      - returns new item with generated UUID
   e. Returns item to app
5. App: shows toast "Saved to Learning"
6. App: refreshes home screen (or appends to local cache)
```

### 4.2 User searches "morning routine"

```
1. User types "morning routine" in search bar
2. App: GET /search?q=morning+routine
3. Backend /search:
   a. Database.search_items("morning routine"):
      - runs PostgreSQL full-text search on title + summary
      - returns matching items ordered by relevance
   b. Returns Item[]
4. App: renders results in list
```

### 4.3 User shares a TikTok video (low-information case)

```
1. User shares TikTok URL
2. App: POST /save { url }
3. Backend /save:
   a. Fetcher detects "tiktok"
   b. Returns FetchedContent{ text: "", source: "tiktok", metadata: { creator: "@xyz" } }
   c. AI.process called with minimal content
   d. AI uses URL + metadata to make best-effort guess
   e. If AI confidence is low → folder defaults to "Other", title becomes "[TikTok by @xyz]"
4. App: shows "Saved! (limited info available — tap to view)"
```

---

## 5. Folder Structure (Full)

```
stash/
│
├── mobile/                              # React Native + Expo app
│   ├── app/                             # Screens (file-based routing)
│   │   ├── _layout.tsx                  # Root layout (tab navigation, theme)
│   │   ├── index.tsx                    # Home screen
│   │   ├── search.tsx                   # Search screen
│   │   └── item/[id].tsx                # Item detail (future)
│   │
│   ├── components/
│   │   ├── ItemCard.tsx                 # Single item in the list
│   │   ├── FolderBadge.tsx              # Colored badge per folder
│   │   ├── SearchBar.tsx                # Search input
│   │   ├── EmptyState.tsx               # When list is empty
│   │   └── LoadingState.tsx             # Loading spinner / skeleton
│   │
│   ├── lib/
│   │   ├── api.ts                       # HTTP client (axios or fetch wrapper)
│   │   ├── supabase.ts                  # Supabase client (used directly for reads, optional)
│   │   └── constants.ts                 # Folder list, API base URL
│   │
│   ├── hooks/
│   │   ├── useItems.ts                  # Fetch & cache items
│   │   ├── useSearch.ts                 # Search logic
│   │   └── useShareIntent.ts            # Listen for incoming shared URLs
│   │
│   ├── types/
│   │   └── index.ts                     # Item, Folder, ApiResponse, etc.
│   │
│   ├── assets/                          # Icons, splash screens
│   │
│   ├── app.json                         # Expo config (incl. share intent setup)
│   ├── babel.config.js
│   ├── tsconfig.json
│   ├── package.json
│   └── .env                             # EXPO_PUBLIC_API_URL, etc.
│
├── backend/                             # FastAPI server
│   ├── main.py                          # FastAPI app instance, CORS, routers
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── save.py                      # POST /save
│   │   ├── items.py                     # GET /items, /items/{id}, DELETE /items/{id}
│   │   └── search.py                    # GET /search
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── fetcher.py                   # Content fetching (Jina, YouTube, etc.)
│   │   ├── ai.py                        # Gemini calls + prompt building
│   │   └── database.py                  # Supabase queries
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py                   # Pydantic models (Item, SaveRequest, etc.)
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── url_parser.py                # Detect platform from URL
│   │   └── logger.py                    # Centralized logging
│   │
│   ├── config.py                        # Reads env vars, exposes settings
│   ├── requirements.txt                 # Python dependencies
│   ├── .env                             # GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
│   ├── .env.example                     # Template (committed to git)
│   ├── Dockerfile                       # For Railway deployment
│   └── railway.json                     # Railway config (optional)
│
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md                  # ← this file
│   ├── AI_FEATURE_SPEC.md
│   └── TASKS.md
│
├── CLAUDE.md                            # Instructions for Claude Code
├── README.md                            # Project intro, setup instructions
├── .gitignore
└── LICENSE                              # MIT or similar
```

---

## 6. Environment & Configuration

### 6.1 Environment variables

**Backend (`backend/.env`):**
```
GEMINI_API_KEY=...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=...
JINA_API_KEY=...          # optional, only if hitting rate limits
ALLOWED_ORIGINS=*         # CORS; lock down in prod
LOG_LEVEL=INFO
YOUTUBE_API_KEY=...        # YouTube Data API v3
```

**Mobile (`mobile/.env`):**
```
EXPO_PUBLIC_API_URL=https://stash-backend.up.railway.app
EXPO_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=...
```

### 6.2 Security notes

- **Backend `.env` is NEVER committed to git.** Add to `.gitignore` from day one.
- **`SUPABASE_SERVICE_KEY`** has full DB access — only used by backend, never by mobile.
- **`SUPABASE_ANON_KEY`** is safe to ship in mobile builds (it's public by design, gated by Row Level Security).
- **`GEMINI_API_KEY`** lives only on backend. If exposed, anyone can drain the quota.

### 6.3 Local development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Mobile (in a separate terminal)
cd mobile
npm install
npx expo start
# scan QR code with Expo Go app, OR
# npx expo run:android (to build native build with share intent)
```

**Important:** Share intent only works in a **dev client build**, not in Expo Go. First time setup:
```bash
npx expo prebuild --platform android
npx expo run:android
```

---

## 7. Deployment Strategy

### 7.1 Backend deployment (Railway)

1. Push backend code to GitHub
2. Connect repo to Railway project
3. Set environment variables in Railway dashboard
4. Railway auto-detects Python, builds via `requirements.txt`, runs `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Railway provides a public URL; copy to `EXPO_PUBLIC_API_URL`

### 7.2 Mobile distribution

- **Development:** EAS Build (Expo's build service, free tier) → APK file → install on builder's phone
- **Self / friends:** Same APK, sideloaded via direct link or shared file
- **Play Store:** Deferred. Requires $25 one-time fee + listing assets.

### 7.3 Database

Supabase is hosted by default. No deployment required. Schema changes managed via SQL Editor in Supabase dashboard for MVP (migrations come later).

---

## 8. Logging, Errors, and Observability

### 8.1 What to log

**Backend logs (per request):**
- Timestamp
- Endpoint hit
- Request payload (sanitized — no PII beyond URL)
- Outcome (success / error code)
- Total latency
- For AI calls: token count, model used, latency

**Mobile logs:**
- Network errors with status code
- Share intent received events
- Search queries (anonymized)

### 8.2 Error categories

| Code | Meaning | User-facing message |
|------|---------|---------------------|
| `INVALID_URL` | URL malformed or unsupported | "That doesn't look like a valid link" |
| `FETCH_FAILED` | Content fetch timed out or errored | "Couldn't load that link, but we saved it anyway" |
| `AI_FAILED` | Gemini call failed or returned junk | "Saved with basic info — tap to view" |
| `DB_FAILED` | Database write/read failed | "Something went wrong, please try again" |

### 8.3 Tooling

- MVP: print + Railway's built-in log viewer is enough
- Future: Sentry free tier for crash reporting (mobile + backend)

---

## 9. Performance Considerations

### 9.1 Where the time goes (rough estimate per save)

| Step | Time |
|------|------|
| Network round-trip phone → backend | 100–300ms |
| URL fetch (Jina / YouTube) | 500–2000ms |
| AI call (Gemini Flash) | 800–1500ms |
| Database insert | 50–150ms |
| Return to phone | 100–300ms |
| **Total** | **1.5–4 seconds** |

### 9.2 Optimizations (post-MVP)

- Return early to mobile after DB write, before AI processing completes (optimistic UI)
- Cache fetched content per URL (so re-saves are free)
- Batch process if user shares many at once
- Move heavy AI to a background job queue (Redis + worker) once volume is real

### 9.3 What we are NOT optimizing for MVP

- Concurrent users (single user, no contention)
- Sub-second response times (5s is fine for a "save and forget" action)
- Mobile bundle size (Expo handles reasonable defaults)
- Database query optimization beyond basic indexes

---

## 10. Future Architecture Considerations

These are not in MVP, but the architecture should not block them.

### 10.1 Semantic search (RAG)

- Add `embedding` column to `items` table (pgvector type, 768 or 1536 dims depending on model)
- At save time, also generate embedding for `title + summary` and store
- At search time, generate embedding for query, do vector similarity search
- Free embedding option: Gemini's embedding model (text-embedding-004)

### 10.2 Multi-user / auth

- Use Supabase Auth (free, built-in)
- Add Row Level Security policies on `items` table — users only see their own rows
- Mobile already has Supabase client; just enable auth flow

### 10.3 iOS support

- Same React Native codebase
- Add iOS share extension config (separate from Android, more complex)
- Pay $99/year Apple Developer fee
- Build via EAS Build → distribute via TestFlight

### 10.4 Screenshot / image support

- Add `image_url` column or separate `attachments` table
- Use Gemini's multimodal capability — same API, just pass image
- Storage via Supabase Storage (free tier: 1GB)

### 10.5 Weekly digest

- Add a scheduled job (Railway cron or Supabase Edge Function)
- Query items from past week, group by folder, send push notification or email
- Requires user accounts and notification tokens — defer until auth is added

---

## 11. Technology Decision Log

For each major choice, why this over alternatives:

| Decision | Chosen | Considered | Why |
|----------|--------|------------|-----|
| Mobile framework | React Native + Expo | Flutter, native Kotlin | JS/TS transferable, huge ecosystem, easier solo dev |
| Backend framework | FastAPI | Express (Node), Django | Python for AI ecosystem, lightweight, great DX |
| Database | Supabase (PostgreSQL) | Firebase, MongoDB Atlas | Free tier, real SQL, pgvector for future, dashboard |
| AI provider | Gemini 3 Flash | GPT-4o-mini, Claude Haiku, Gemini 3.1 Flash-Lite | Most generous free tier remaining (1,500 RPD), structured JSON support, multimodal-ready for future image features |
| Article fetcher | Jina Reader | Custom scraper, Diffbot | Free, no maintenance, clean output |
| Hosting | Railway | Render, Fly.io, Vercel | Free tier, simplest deploy, supports long-running Python |
| Language (mobile) | TypeScript | JavaScript | Type safety catches bugs early, mandatory at this scale |
| Language (backend) | Python | Node, Go | AI library ecosystem, Pydantic for type safety |

---

## 12. Glossary

**API** — Application Programming Interface. How two programs talk to each other over the network.

**Backend** — The server-side code that runs on a computer in the cloud, not on the user's phone.

**Embedding** — A numerical representation of text (a list of numbers) that captures its meaning. Two pieces of text with similar meanings will have similar embeddings.

**Endpoint** — A specific URL the backend exposes that does one thing. E.g., `POST /save` is an endpoint that saves an item.

**Expo** — A framework on top of React Native that handles a lot of the painful native setup.

**FastAPI** — A Python web framework for building APIs.

**RAG** — Retrieval-Augmented Generation. A pattern where you fetch relevant context first, then send it to an LLM. Used for "chat with your data" features.

**Schema** — The structure of a database table (columns, types, constraints).

**Share intent** — Android's mechanism for one app to send data to another via the share sheet.

**Supabase** — A "Backend-as-a-Service" built on top of PostgreSQL. Database + auth + storage + more.

---

## 13. Open Architecture Questions

Deferred decisions to revisit after Phase 2:

- Should the mobile app talk to Supabase directly for reads (fast, less backend load) or always go through the backend (consistent, easier to evolve)?
- Should AI processing be synchronous (block the save flow) or asynchronous (queue and update later)?
- Should we cache fetched content to avoid hitting Jina/YouTube repeatedly for the same URL?
- When the predefined folder list proves limiting, do we allow user-created folders or let AI propose new ones with approval?

---

## 14. Document References

- Product goals and user stories → `PRD.md`
- AI prompt design, response format, fallbacks → `AI_FEATURE_SPEC.md`
- Phased build plan with tasks → `TASKS.md`
- Working agreement with Claude Code → `CLAUDE.md`

---

*End of ARCHITECTURE v1.0*
