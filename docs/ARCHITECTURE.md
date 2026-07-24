# Architecture Document

**Project:** Fetch (working name)
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
│  │  TikTok / IG │         │      Fetch App (Flutter)        │  │
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
2. Android share sheet appears, user selects "Fetch"
3. Fetch app opens (or runs in background), receives the URL
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

### 3.1 Mobile App (Flutter)

**Role:** The user-facing layer. Receives shares, displays saved items, lets user search and browse.

**Why Flutter (switched from React Native + Expo on 2026-07-18):**
- The original React Native + Expo choice hit a real setup blocker: `create-expo-app` pulled Expo SDK 57 (released 2026-06-30), and the Expo Go app on the iOS/Android app stores hadn't caught up to support it yet — a known, documented lag in how Expo Go ships (see Expo's own changelog: the same thing happened with SDK 55 in May 2026). This was fixable (downgrading to SDK 56 got most of the way there), but it surfaced a broader decision point.
- Independent of that blocker, the builder decided to specialize: learn mobile development deeply via Flutter/Dart as its own track, and learn web development (React/Next.js) separately later, rather than staying inside one JS/TS-generalist stack for both. This is a **deliberate learning-scope decision**, not just a reaction to the Expo issue — worth being able to articulate clearly in an interview: "I chose to build depth in one mobile framework rather than stretch a single language across mobile and web."
- Flutter is compiled (AOT for release builds), so there's no "app store hasn't caught up to my SDK yet" category of problem — the app is a self-contained binary.
- Single codebase for the future iOS port (still deferred per Known Constraints, but architecturally free when the day comes).
- Excellent official documentation and a mature, stable widget/routing ecosystem (`go_router` is explicitly in Flutter-team-maintained "feature complete, stability-focused" mode as of mid-2026 — not a fast-moving target like a brand-new Expo SDK).

**Key packages** (verify exact versions on [pub.dev](https://pub.dev) at implementation time — same lesson learned from the Expo SDK incident: don't assume a package choice from documentation is still the actively-maintained one):

| Package | Purpose |
|---------|---------|
| `flutter` (SDK) | Core framework |
| `go_router` | Declarative routing — official Flutter-recommended package |
| `receive_sharing_intent` | Receives shared URLs from other apps via Android share sheet. As of mid-2026 the original package was reported unmaintained; check pub.dev for whether `receive_sharing_intent_plus` (a maintained fork) or a newer alternative is the current best choice before installing |
| `supabase_flutter` | Official Supabase SDK for Dart (auth + DB) |
| `http` or `dio` | HTTP client for calling the backend API |
| `shared_preferences` | Local cache for offline-friendly browsing |

**What lives where:**
- **Screens** (`lib/screens/`) — full-page widgets, what the user sees
- **Widgets** (`lib/widgets/`) — reusable UI pieces
- **Services** (`lib/services/`) — API calls, Supabase client, helpers
- **Models** (`lib/models/`) — Dart classes mirroring `backend/models/schemas.py`
- **Android native config** (`android/`) — where the share-sheet intent filter is registered (Flutter always has a real native Android project, unlike Expo's managed workflow — there's no separate "prebuild" step to opt into)

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
- $5 free credit lasts ~3–4 months for a small personal app (usage-based, not time-based)
- Deploy via `git push` — no Kubernetes nightmare
- Automatic HTTPS
- Environment variables managed via dashboard
- After credit: Hobby plan $5/month. Worth it if the app has real users.

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
  - **TikTok** → the official public oEmbed endpoint (`https://www.tiktok.com/oembed?url=...`), which returns the caption, creator, and thumbnail as JSON. **Open Graph does not work for TikTok** — a video page serves ~400KB of JavaScript with only three `<meta>` tags and no `og:` properties at all. Discovered 2026-07-24 after every TikTok save came back empty while Instagram worked fine
  - **IG/Twitter** → minimal: URL + any metadata from Open Graph tags (these two *do* serve `og:title`/`og:description`)
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
  user_id       UUID,                    -- nullable in MVP (no auth); used later
  confidence    TEXT,                    -- 'high' | 'medium' | 'low' (AI_FEATURE_SPEC.md 4.4)
  ai_status     TEXT DEFAULT 'ok'        -- 'ok' | 'failed' | 'quota_exceeded'; the last two saved with fallback values
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

**Note on `confidence` / `ai_status`:** Added after the initial schema was written. `AI_FEATURE_SPEC.md` Sections 8–9 depend on both, so they belong in the table rather than being recomputed. `ai_status = 'failed'` marks items saved with fallback values, so a future job can re-process them.

`'quota_exceeded'` was added 2026-07-24 as a third value, distinct from `'failed'`, after the Gemini free tier (20 requests/day) ran out mid-session and the app reported it identically to a genuine AI malfunction. The distinction matters twice over: the user is told to wait rather than to worry, and a re-processing job can prioritise these items since nothing is actually wrong with them. No migration was needed — the column is plain `TEXT` with no `CHECK` constraint (verified by inserting the new value against the live database).

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
- Endpoint: https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent (model id: `gemini-3.5-flash` — `gemini-3-flash` does not exist; see AI_FEATURE_SPEC Section 3.1)
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
2. App receives URL via receive_sharing_intent (or current equivalent — see 3.1)
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
fetch/
│
├── mobile/                              # Flutter app
│   ├── lib/
│   │   ├── main.dart                    # App entry point, router setup
│   │   │
│   │   ├── screens/
│   │   │   ├── home_screen.dart         # Home screen (item list)
│   │   │   ├── search_screen.dart       # Search screen
│   │   │   ├── save_screen.dart         # "Saving..." screen shown after a share
│   │   │   └── item_detail_screen.dart  # Item detail (future)
│   │   │
│   │   ├── widgets/
│   │   │   ├── item_card.dart           # Single item in the list
│   │   │   ├── folder_badge.dart        # Colored badge per folder
│   │   │   ├── search_bar.dart          # Search input
│   │   │   ├── empty_state.dart         # When list is empty
│   │   │   └── loading_state.dart       # Loading spinner / skeleton
│   │   │
│   │   ├── services/
│   │   │   ├── api_client.dart          # HTTP client wrapper for the backend
│   │   │   ├── supabase_client.dart     # Supabase client (used directly for reads, optional)
│   │   │   └── share_intent_service.dart # Listens for incoming shared URLs
│   │   │
│   │   └── models/
│   │       └── item.dart                # Item, Folder, ApiResponse, etc. — mirrors backend/models/schemas.py
│   │
│   ├── android/                         # Native Android project (share intent filter lives in AndroidManifest.xml here)
│   ├── assets/                          # Icons, splash screens
│   │
│   ├── pubspec.yaml                     # Dependencies + app metadata (Flutter's package.json equivalent)
│   └── analysis_options.yaml            # Dart lint rules
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
│   └── Procfile                         # Railway/Heroku start command
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
API_URL=https://xxxxx.up.railway.app
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=...
```

**Decision (2026-07-19, task 0.7):** `flutter_dotenv`, not `--dart-define`. A gitignored `mobile/.env` holds real values; a committed `mobile/.env.example` holds the same keys with empty values — mirroring the backend's `.env`/`.env.example` pattern exactly. Loaded once at startup in `main.dart`, before `runApp()`:
```dart
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  runApp(const FetchApp());
}
```
Rejected `--dart-define`: it has no single source-of-truth file — values would need to be re-typed or scripted into every `flutter run`/`flutter build` invocation — so it doesn't mirror the backend convention the builder already relies on. The `.env` file is registered as a normal Flutter asset in `pubspec.yaml` (`flutter: assets: - .env`); no Android manifest changes are needed — asset declarations are bundled into the APK by the Flutter build tool itself, the same mechanism used for images or fonts, with no native permission model involved.

Same three values travel with the mobile build as before: backend API URL, Supabase URL, Supabase anon/publishable key. Same security rule as before: anon/publishable key only, never the service key. Currently only `API_URL` is read by any code (`lib/services/api_client.dart`) — `SUPABASE_URL`/`SUPABASE_ANON_KEY` are present in both files as blank placeholders until Supabase is wired up on the mobile side.

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
flutter pub get
flutter run
# requires an Android device (USB debugging enabled) or emulator connected;
# `flutter devices` lists what's available
```

**Note:** Unlike Expo, there's no separate "dev client" concept — `flutter run` always builds and installs a real (debug-mode) native app on the connected device, so share intent works from the very first run once the Android manifest is configured. No prebuild step needed.

---

## 7. Deployment Strategy

### 7.1 Backend deployment (Railway)

1. Push backend code to GitHub
2. Create new project on railway.app, connect GitHub repo
3. Set root directory to `backend/`, Railway auto-detects Python via `requirements.txt` and reads `Procfile`
4. Add environment variables in Railway dashboard
5. Railway provides a public URL (`https://xxx.up.railway.app`); copy to `EXPO_PUBLIC_API_URL`
6. $5 free credit — lasts ~3–4 months for a small app. Hobby plan $5/month after.

### 7.2 Mobile distribution

- **Development:** `flutter run` installs a debug build directly to a USB-connected device
- **Self / friends:** `flutter build apk --release` produces a standalone APK, sideloaded via direct file transfer (no build service needed — this is a local command, free, no account required)
- **Play Store:** Deferred. Requires $25 one-time fee + listing assets, and a release build signed with a proper keystore (`flutter build appbundle`).

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
- Mobile bundle size (Flutter's default release build settings are reasonable for a personal app)
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

- Same Flutter codebase
- Add iOS share extension config (separate from Android, more complex — Flutter's `receive_sharing_intent`-style packages typically need a native iOS Share Extension target added in Xcode, not just a manifest entry like Android)
- Pay $99/year Apple Developer fee
- Build via `flutter build ipa` → distribute via TestFlight

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
| Mobile framework | Flutter | React Native + Expo (original MVP choice, switched 2026-07-18), native Kotlin | Deliberate specialization: builder chose to build depth in one mobile framework rather than stretch JS/TS across mobile and a future separate web-dev track. Also sidesteps a real, documented pain point hit with the original choice — Expo Go's app-store build lagging behind brand-new Expo SDK releases (see 3.1 for the full incident). Flutter release builds are self-contained binaries, not dependent on a separate "preview app" catching up to SDK version. |
| Backend framework | FastAPI | Express (Node), Django | Python for AI ecosystem, lightweight, great DX |
| Database | Supabase (PostgreSQL) | Firebase, MongoDB Atlas | Free tier, real SQL, pgvector for future, dashboard |
| AI provider | Gemini 3 Flash | GPT-4o-mini, Claude Haiku, Gemini 3.1 Flash-Lite | Most generous free tier remaining (1,500 RPD), structured JSON support, multimodal-ready for future image features |
| Article fetcher | Jina Reader | Custom scraper, Diffbot | Free, no maintenance, clean output |
| Hosting | Railway | Render, Fly.io, Vercel | $5 credit lasts ~3–4 months for personal use; $5/month Hobby after; deploys from GitHub, supports long-running Python |
| Language (mobile) | Dart | — (Flutter has no realistic alternative language) | Dart is Flutter's native language; null safety and strong typing give the same "catch bugs early" benefit TypeScript would have on the web side |
| Language (backend) | Python | Node, Go | AI library ecosystem, Pydantic for type safety |

---

## 12. Glossary

**API** — Application Programming Interface. How two programs talk to each other over the network.

**Backend** — The server-side code that runs on a computer in the cloud, not on the user's phone.

**Embedding** — A numerical representation of text (a list of numbers) that captures its meaning. Two pieces of text with similar meanings will have similar embeddings.

**Endpoint** — A specific URL the backend exposes that does one thing. E.g., `POST /save` is an endpoint that saves an item.

**FastAPI** — A Python web framework for building APIs.

**Flutter** — Google's UI toolkit for building natively-compiled mobile (and desktop/web) apps from a single Dart codebase. Renders its own widgets rather than wrapping native platform UI components.

**Dart** — The programming language Flutter apps are written in. Statically typed, null-safe, compiled ahead-of-time for release builds.

**Widget** — Flutter's fundamental building block. Everything on screen — text, layout, buttons, even padding — is a widget, composed into a tree.

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
