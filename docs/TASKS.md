# Tasks Breakdown

**Project:** Fetch (working name)
**Author:** Biday
**Last updated:** July 24, 2026
**Status:** Active build plan

---

## How to Use This Document

This document breaks the project into 5 phases (0–4). Each phase has:
- **Goal** — what "done" looks like for the phase
- **Tasks** — checklist items, ordered by dependency
- **Definition of Done** — concrete acceptance criteria
- **Common pitfalls** — things to avoid

Each task is sized to be a single conversation with Claude Code (or a single focused work session). If a task feels bigger than that, split it.

Mark tasks as you complete them. Don't skip ahead — phases are ordered for a reason.

**Vibe coding note:** When you ask Claude Code for help, reference the relevant section of `PRD.md`, `ARCHITECTURE.md`, or `AI_FEATURE_SPEC.md`. Don't make Claude Code re-derive what's already documented.

---

## Phase 0 — Project Setup

**Goal:** Both projects (mobile + backend) initialized, connected to each other, with a "hello world" round-trip working. No real features yet.

**Estimated time:** 2–3 days

**Why this phase exists:** Setup is where most first-timers waste days. Knock it out cleanly, then never touch it again.

### 0.1 Repository setup

- [x] Create new GitHub repo named `fetch` (or final project name) — actually named `FINDIT` (github.com/abidayn/FINDIT); the repo name was never changed to match the app name
- [x] Add `.gitignore` covering Python (`__pycache__`, `.env`, `venv/`) and Flutter/Dart (`.dart_tool/`, `build/`, `android/local.properties`, `*.iml`)
- [x] Add empty `README.md` with project name and one-line description
- [x] Create root folder structure: `mobile/`, `backend/`, `docs/`
- [x] Move `PRD.md`, `ARCHITECTURE.md`, `AI_FEATURE_SPEC.md`, and this file into `docs/`
- [x] First commit, push to main

### 0.2 Supabase project setup

- [x] Create account at supabase.com (free)
- [x] Create new project named `stash` (region: closest to Indonesia — Singapore) — note: kept the original `stash` name in the Supabase dashboard even after the app was renamed to Fetch (2026-07-23); renaming the project there isn't worth the churn
- [x] Save the **Project URL** and **anon key** and **service key** somewhere secure
- [x] Open the SQL Editor and run the schema from `ARCHITECTURE.md` Section 3.3 to create the `items` table and indexes
- [x] Manually insert one test row via the dashboard to confirm the table works
- [x] (Skip Row Level Security for MVP — single user, no auth)

### 0.3 Google AI Studio (Gemini) setup

- [x] Go to aistudio.google.com, sign in
- [x] Create new API key, save securely
- [x] Test the key with a curl command to confirm it works — since verified far more thoroughly than a curl: the live `/save` pipeline returns real AI-generated titles and summaries with `ai_status: "ok"`:
  ```bash
  curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash:generateContent?key=YOUR_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"contents":[{"parts":[{"text":"Say hi in 3 words"}]}]}'
  ```
- [x] Verify your free tier limits in AI Studio dashboard — **answered the hard way 2026-07-24: it is 20 requests/day, not ~1,500.** Measured by hitting it during TikTok testing; the 429 response names the quota explicitly: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: 20`, model `gemini-3.5-flash`. One save costs 1 request, or 2 if the AI retries — so **10–20 saves per day**. Past that, every save silently falls back to "Untitled saved item" with folder "Other". This is the real ceiling on daily dogfooding (Phase 4.1 targets 50+ items, which will take several days minimum)

### 0.4 Google Cloud / YouTube Data API setup

- [x] Go to console.cloud.google.com, create a new project named `stash` (same note as 0.2 — still named `stash` in the GCP console after the rename to Fetch)
- [x] Enable "YouTube Data API v3" for the project
- [x] Create an API key (Credentials → Create credentials → API key)
- [x] Restrict the key to YouTube Data API v3 only (for safety)
- [x] Test with curl:
  ```bash
  curl "https://www.googleapis.com/youtube/v3/videos?id=dQw4w9WgXcQ&part=snippet&key=YOUR_KEY"
  ```
- [x] Save the key — it's a different key from the Gemini one

### 0.5 Backend project init (FastAPI)

- [x] In `backend/`, create Python virtual environment: `python -m venv venv && source venv/bin/activate`
- [x] Install dependencies: `pip install fastapi uvicorn python-dotenv supabase google-genai httpx pydantic`
- [x] Create `requirements.txt`: `pip freeze > requirements.txt`
- [x] Create `main.py` with a minimal FastAPI app:
  - Single `GET /health` endpoint returning `{"status": "ok"}`
  - CORS middleware allowing all origins (lock down later)
- [x] Create `.env` file with `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- [x] Create `.env.example` with the same keys but empty values (commit this one)
- [x] Run locally: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- [x] Visit `http://localhost:8000/health` in browser, confirm response
- [x] Visit `http://localhost:8000/docs` to see auto-generated Swagger UI — also live in production: `https://findit-production-7ab0.up.railway.app/docs` returns 200

### 0.6 Backend deployment (Railway)

- [x] Create account at railway.app — sign up with GitHub
- [x] New Project → Deploy from GitHub repo → select `abidayn/FINDIT`
- [x] Set root directory to `backend/` in service settings
- [x] Add all environment variables in Railway dashboard (same keys as `backend/.env`)
- [x] Confirm deploy succeeds — check logs for `Application startup complete`
- [x] Visit the Railway-provided URL + `/health`, confirm it works publicly
- [x] Save the Railway URL — this is the backend API URL the mobile app will call

### 0.7 Mobile project init (Flutter)

- [x] Install the Flutter SDK and Android SDK/toolchain (Android Studio, or standalone `cmdline-tools` + `adb`) if not already present
- [x] Run `flutter doctor` and resolve any blockers before continuing (missing Android licenses, missing `adb`, etc.)
- [x] In the repo root, run `flutter create mobile` (creates the full Flutter project, including a real `android/` native folder — no separate "prebuild" step exists in Flutter)
- [x] Add `go_router` to `pubspec.yaml` (`flutter pub add go_router`), set up a minimal router in `lib/main.dart`
- [x] Replace the default counter-app `lib/main.dart` with a basic hello-world screen (`lib/screens/home_screen.dart`)
- [x] Add `supabase_flutter` and a share-intent package (verify current maintained choice on pub.dev — see `ARCHITECTURE.md` 3.1) via `flutter pub add`
- [x] Decide and document the config-injection approach (`--dart-define` vs bundled non-committed asset file — see `ARCHITECTURE.md` 6.1) for the backend API URL and Supabase URL/anon key — chose `flutter_dotenv`, mirrors backend's `.env`/`.env.example` pattern
- [x] Run `flutter run` with a USB-connected Android device (or emulator) — this installs a real debug build directly, no separate preview app needed
- [x] Confirm the hello-world screen renders on the device (verified on physical Infinix Note 30 Pro, 2026-07-19; had to bump `compileSdk` to 37 in `android/app/build.gradle.kts` because `receive_sharing_intent` requires it)

### 0.8 Connect mobile to backend (the round-trip)

- [x] In `mobile/lib/services/api_client.dart`, create a function `fetchHealth()` that calls `{API_URL}/health`
- [x] In the home screen, call it on load (e.g., in `initState` or a `FutureBuilder`) and display the response
- [x] Confirm on device: app loads → calls Railway backend → shows "status: ok" (verified on physical Infinix, 2026-07-19 — screen showed "Backend status: ok")
- [x] This is the moment your two systems are talking. Celebrate small.

### Phase 0 — Definition of Done

✅ Phone-installed app calls Railway-deployed backend successfully
✅ Backend can read from Supabase database
✅ All API keys (Gemini, YouTube, Supabase) tested and working independently
✅ Repo structure matches `ARCHITECTURE.md`
✅ Environment variables properly separated (mobile vs backend)
✅ All secrets in `.env`, none committed to git

### Phase 0 — Common Pitfalls

- **Committing `.env` to git** — double-check `.gitignore` BEFORE first commit
- **Mixing up Supabase keys** — `anon` key is for client (mobile), `service` key is for server (backend). Never put service key on mobile.
- **Railway idle sleep** — backend may take 10s to respond after inactivity on free credit. Normal.
- **Android toolchain setup friction** — `flutter doctor` catches most issues (missing SDK, unaccepted licenses, no connected device) before they turn into confusing runtime errors. Run it first whenever something mobile-side won't build.
- **Forgetting CORS** — backend must allow requests from mobile origin. For MVP set `allow_origins=["*"]`.

---

## Phase 1 — Core Save Flow

**Goal:** User can share a URL from any app → backend processes it → it's saved in the database. No UI for viewing yet.

**Estimated time:** 1 week (5–7 days)

**Why this phase exists:** This is the core value loop. If this works, everything else is decoration. If this fails, the product doesn't exist.

### 1.1 Backend — Pydantic models and schemas

- [x] Create `backend/models/schemas.py`
- [x] Define `SaveRequest` (input: `url`)
- [x] Define `FetchedContent` (intermediate: `text`, `source_platform`, `metadata`, `thumbnail_url`)
- [x] Define `AIResult` (intermediate: `title`, `summary`, `folder`, `confidence`)
- [x] Define `Item` (database row + response: id, url, title, summary, folder, source, thumbnail_url, raw_content, created_at, confidence, ai_status)
- [x] Define `ErrorResponse` (output: `error`, `code`, `details`)

### 1.2 Backend — URL parser utility

- [x] Create `backend/utils/url_parser.py`
- [x] Function `detect_platform(url: str) -> str` returns one of: `"youtube"`, `"tiktok"`, `"instagram"`, `"twitter"`, `"article"`, `"other"`
- [x] Use simple domain matching (urllib.parse)
- [x] Handle edge cases: youtu.be short URLs, m.youtube.com, mobile.twitter.com, x.com
- [x] Add a `extract_youtube_id(url)` helper for YouTube URLs

### 1.3 Backend — Fetcher service

- [x] Create `backend/services/fetcher.py`
- [x] Implement `fetch_content(url: str) -> FetchedContent`
- [x] For articles: call Jina Reader (`https://r.jina.ai/{url}`), parse markdown response
- [x] For YouTube: call YouTube Data API v3 `/videos?id={id}&part=snippet`, concatenate title + description + tags
- [x] For TikTok/Instagram/Twitter: extract minimal Open Graph metadata via `httpx` + simple HTML parse
- [x] All fetches must have a 10-second timeout
- [x] On any failure, return `FetchedContent(text="", source_platform=detected, metadata={})` — never raise
- [x] Log warnings for failures so you can debug later

### 1.4 Backend — AI service

- [x] Create `backend/services/ai.py`
- [x] Implement everything specified in `AI_FEATURE_SPEC.md` Section 10.2
- [x] Constant `ALLOWED_FOLDERS` matching the taxonomy
- [x] `build_prompt(content)` — uses template from spec Section 6.1
- [x] Handle low-info variant (spec Section 6.3)
- [x] `call_gemini(prompt)` — actual API call with config from spec Section 3.2
- [x] `validate(raw)` — strict validation per spec Section 8.1
- [x] `process_content(content) -> AIResult` — the single public function, with one retry and fallback

### 1.5 Backend — Database service

- [x] Create `backend/services/database.py`
- [x] Initialize Supabase client from env vars
- [x] Function `insert_item(item_data: dict) -> Item`
- [x] Function `get_all_items() -> list[Item]`
- [x] Function `get_items_by_folder(folder: str) -> list[Item]`
- [x] Function `search_items(query: str) -> list[Item]` — uses PostgreSQL `ILIKE` for now on title + summary
- [x] Function `delete_item(item_id: str) -> bool`
- [x] All functions raise on failure — caller handles errors

### 1.6 Backend — `/save` endpoint

- [x] Create `backend/routes/save.py`
- [x] `POST /save` accepts `SaveRequest`, returns `Item` (or `ErrorResponse`)
- [x] Pipeline:
  1. Validate URL is well-formed
  2. Detect platform via url_parser
  3. Call `fetcher.fetch_content(url)`
  4. Call `ai.process_content(fetched)`
  5. Build database row and call `database.insert_item(...)`
  6. Return the new item
- [x] Handle errors at each step — failed fetch should still try AI; failed AI should still save; failed DB returns error
- [x] Wire the route into `main.py`

### 1.7 Backend — Test the save flow manually

- [x] Use Swagger UI (`/docs`) or curl to POST a URL to `/save`
- [x] Test with an article URL (should be HIGH quality output)
- [x] Test with a YouTube URL (should be MEDIUM quality output)
- [x] Test with a TikTok URL (should be LOW quality output, use fallback)
- [x] Test with an invalid URL (should return error gracefully)
- [x] Check Supabase dashboard — rows should be appearing
- [x] Check Railway logs — should see one log line per request

### 1.8 Mobile — Share intent integration

- [x] Add the chosen share-intent package (see `ARCHITECTURE.md` 3.1) to `pubspec.yaml` — `receive_sharing_intent` ^1.9.0
- [x] In `android/app/src/main/AndroidManifest.xml`, add an intent filter for `ACTION_SEND` with MIME type `text/plain` so the app appears in the Android share sheet
- [x] In `lib/services/share_intent_service.dart`, listen for incoming shared text/URLs per the package's API (typically a stream you subscribe to at app start)
- [x] On receiving a shared URL, navigate (via `go_router`) to the save screen with the URL as a parameter
- [x] Test: open TikTok → share a video → "Share to" → see Fetch in the list → tap it → app opens with the URL (verified on physical Infinix 2026-07-23 via `adb am start -a android.intent.action.SEND`; both cold start and warm start deliver the URL to `SaveScreen`. Also confirmed registered as a system share target via `adb shell cmd package query-activities`)

### 1.9 Mobile — Save screen

- [x] Create `lib/screens/save_screen.dart`, registered as a `go_router` route
- [x] Receives URL via route parameter — passed as `state.extra` rather than a path param, so a URL inside a URL needs no escaping
- [x] Shows "Saving..." state with the URL displayed
- [x] Calls backend `POST /save` via `api_client.dart` (`saveItem()`, 45s timeout to cover fetch + AI retry + Railway cold start)
- [x] On success: shows the result (title, summary, folder badge) and "Done" button
- [x] On failure: shows error message and "Retry" button
- [x] After save, allow user to return to source app (or close) — "Done" calls `SystemNavigator.pop()`, which exits the app rather than just popping the route

All five states verified on physical Infinix 2026-07-23: loading, success (BBC News article → AI returned real title/summary/folder), error (invalid URL → HTTP 422), retry (returns to loading), and Done (activity exits to launcher). Also created `lib/models/item.dart` here — listed under 1.10, but 1.9 can't render title/summary/folder without it.

### 1.10 Mobile — API client

- [x] In `mobile/lib/services/api_client.dart`, create typed functions:
  - [x] `Future<Item> saveItem(String url)` — built and verified in 1.9
  - [ ] `Future<List<Item>> getAllItems()` — **deferred to Phase 2**
  - [ ] `Future<List<Item>> searchItems(String query)` — **deferred to Phase 2**
  - [ ] `Future<void> deleteItem(String id)` — **deferred to Phase 2**
- [x] Wrap all calls with error handling — throw typed exceptions the UI can catch and display
- [x] Mirror types from `backend/models/schemas.py` as Dart classes in `mobile/lib/models/item.dart`

**Deferral decision (2026-07-23):** the three read/delete functions are deliberately not built yet. Their backend endpoints (`GET /items`, `GET /search`, `DELETE /items/{id}`) don't exist either — those are Phase 2 task 2.1 — and no screen calls them until Phase 2. Writing them now would mean three untestable functions against endpoints that aren't there. Per Principle 2 (build only what was asked), each gets written alongside the screen that uses it, so a mistake surfaces immediately instead of a week later. `saveItem()` was built now because 1.9 genuinely needed it.

### Phase 1 — Definition of Done

✅ User can share a URL from TikTok/IG/YouTube/Chrome → it appears in Supabase with correct AI processing — confirmed: the live table holds items sourced from tiktok, instagram, youtube, and article
⬜ Save flow completes in under 5 seconds for articles and YouTube — **never measured.** Observed saves felt closer to 10–20s. Worth timing before Phase 3's performance pass
✅ TikTok/IG URLs save successfully even when content fetch fails (graceful degradation) — confirmed: TikTok rows exist with titles like "Saved TikTok video", summary "no available transcript or description", folder "Other", confidence "low"
✅ Invalid URLs return clear error messages — 422 from FastAPI, surfaced on the save screen with a Retry button
✅ Backend logs are clean and readable for each request
✅ At least 10 real items saved to the database by manual testing — 17 items as of 2026-07-23

**Known quality issue, not a blocker:** folder accuracy is imperfect. An FDE roadmap doc was filed under "Productivity" when "Tech & Coding" arguably fits better, and several articles default to "Other". This is prompt tuning, which `TASKS.md` deliberately schedules for task 4.3 after ~50 items — one or two misses aren't enough signal to tell a biased prompt from a genuinely ambiguous item.

### Phase 1 — Common Pitfalls

- **Share intent needs a real device or emulator with Google Play services.** Not all emulator images support the share sheet properly — test on a real device if the emulator behaves oddly.
- **CORS errors after deploy.** Backend on Railway, mobile testing on phone — different origins. Confirm CORS allows your Railway URL.
- **API keys in mobile bundle.** Only the backend API URL and Supabase anon/publishable key belong in the mobile build config. Gemini and YouTube keys ONLY in backend.
- **Forgetting to handle the "AI returns junk JSON" case.** The validation logic in spec is there for a reason — test it.
- **Building UI polish in Phase 1.** Save screen can be ugly. We polish in Phase 3.

---

## Phase 2 — View & Search

**Goal:** User can browse all their saved items on the home screen, filter by folder, and search by keyword.

**Estimated time:** 1 week (5–7 days)

### 2.1 Backend — `/items` and `/search` endpoints

- [x] Create `backend/routes/items.py`
- [x] `GET /items` returns all items (latest first)
- [x] `GET /items?folder=Self+Growth` filters by folder — typed as the `Folder` Literal, so an unknown folder is rejected with 422 before the handler runs
- [x] `GET /items/{id}` returns single item (404 when missing) — needed a new `database.get_item_by_id()`, which didn't exist
- [x] `DELETE /items/{id}` removes an item (204 on success, 404 when missing)
- [x] Create `backend/routes/search.py`
- [x] `GET /search?q=morning+routine` — upgraded to full-text in task 2.2 (see below). Empty query returns all, queries under 2 chars return nothing
- [x] All endpoints wired into `main.py`

Verified against the live database 2026-07-23 (17 real items): folder filter returned the 3 Finance items, an invalid folder gave 422, search "BBC" gave 3 hits, a 1-character query gave 0, an empty query gave all 17, GET by bad id gave 404, and DELETE returned 204 then 404 on re-fetch.

### 2.2 Backend — Search implementation

- [x] In `database.py`, use the GIN full-text index from schema — via PostgREST's `plfts` operator (`plainto_tsquery`), which hits the existing `idx_items_search` GIN index. No DB migration needed; the index was already in the schema.
- [x] Query — implemented as `plfts` OR `ilike` on both title and summary, not raw SQL. Full-text alone can't do partial words ("BB" → "BBC"); ILIKE alone can't stem ("story" → "stories"). The OR gives the union. **Deviation from the spec line:** no `ts_rank` ordering — that needs raw SQL the Supabase client can't send without a DB function, so results stay newest-first, which is more useful on a personal library anyway. `LIMIT 50` kept.
- [x] If query is empty string, return all items (handled in `routes/search.py`)
- [x] If query has fewer than 2 characters, return empty list (handled in `routes/search.py`)

Verified on Railway production 2026-07-24: "story" matched "stories" (2 rows — proves stemming, which plain ILIKE could never do), "BB" matched "BBC" (2 rows — proves substring still works), "global stories" (multi-word) worked, and `"tik'tok--;DROP"` returned 0 rows rather than erroring (query is stripped to alphanumerics + spaces before hitting PostgREST).

### 2.3 Mobile — Item model and data services

- [x] In `mobile/lib/models/item.dart`, mirror the `Item` shape from backend (a plain Dart class with a `fromJson` factory)
- [x] Define `Folder` as a Dart `enum` with the 9 allowed values
- [x] In `api_client.dart` (or a small `items_repository.dart`), expose functions to fetch all items and search — plain `Future`-returning functions are enough; no hooks equivalent needed for an app this size
- [x] For search debouncing (300ms), use a `Timer` that gets cancelled/reset on each keystroke in the search screen's state
- [x] Create `mobile/lib/constants.dart` exporting the folder list and per-folder colors

### 2.4 Mobile — ItemCard widget

- [x] Create `mobile/lib/widgets/item_card.dart`
- [x] Constructor params: `item` (Item), `onTap` (VoidCallback)
- [x] Layout: thumbnail (or platform icon as fallback) on left, title + summary on right, folder badge at top-right
- [x] Wrap in `InkWell`/`GestureDetector` to trigger `onTap`
- [x] Long-press shows a delete option (post-MVP polish, skip for now)
- [x] Use platform-appropriate icons for source (YouTube logo, TikTok logo, link icon for articles)

### 2.5 Mobile — FolderBadge widget

- [x] Create `mobile/lib/widgets/folder_badge.dart`
- [x] Constructor param: `folder` (Folder)
- [x] Renders a small colored pill with the folder name
- [x] Colors mapped from `constants.dart`

### 2.6 Mobile — Home screen

- [x] Update `lib/screens/home_screen.dart` to be the home screen
- [x] Fetch all items on load (`FutureBuilder` or a simple `StatefulWidget` + `setState` after an async call)
- [x] Show loading skeleton (or spinner) while loading
- [x] Show empty state if no items: "Nothing saved yet. Share a link to get started."
- [x] `ListView.builder` of `ItemCard`s (lazy by default — no extra config needed for basic performance)
- [x] Tap card → open original URL in browser (`url_launcher` package's `launchUrl`)
- [x] Header has a search icon → navigates to search screen via `go_router`
- [x] Wrap the list in a `RefreshIndicator` for pull-to-refresh

### 2.7 Mobile — Folder filter

- [x] Add a horizontal scrollable row of folder chips above the list (`ListView` with `scrollDirection: Axis.horizontal`, or Flutter's `ChoiceChip` widgets)
- [x] "All" chip is default selected
- [x] Tapping a folder chip filters the list to that folder
- [x] Show count next to each folder (e.g., "Self Growth (12)")
- [x] State management: local Flutter state (`setState`) is enough — no external state management package needed yet

### 2.8 Mobile — Search screen

- [x] Create `lib/screens/search_screen.dart`, registered as a `go_router` route
- [x] Search input at top (`TextField`, e.g. inside the `AppBar`)
- [x] Below: results list from the debounced search call in 2.3
- [x] Empty state when no query: "Type to search your saves"
- [x] Empty state when no results: "No matches for 'XYZ'"
- [x] Same `ItemCard` widget for results
- [x] Tap result → open original URL

### 2.9 Manual testing

**Status: partially verified on device (2026-07-24).** The app was run on the physical Infinix and the builder confirmed the two highest-risk items work: the saved items render on the home screen, and tapping one opens the original URL. The remaining checks below haven't been individually reported yet — they're lower-risk (folder filter is in-memory over an already-rendered list, and the search screen reuses the same `ItemCard` that's now proven to render), but they are *not* confirmed.

- [ ] Save 20+ items across different folders — 17 exist; needs a few more, saved *from the phone*
- [x] Verify all show on home screen — **confirmed on device 2026-07-24** ("udah muncul semua"). This also implicitly proves `getAllItems()`, JSON parsing into `Item`, `Folder.fromLabel`, `ItemCard`, and `FolderBadge` all work against real data
- [ ] Filter by each folder, confirm correct items appear — not individually reported; backend folder filter separately confirmed, and the chips filter the in-memory list that's now known to render
- [ ] Search for keywords from titles, confirm results — backend search verified on production; the search screen UI not individually reported
- [ ] Test pull-to-refresh — not individually reported
- [x] Test tapping items opens original URLs in correct app — **confirmed on device 2026-07-24** ("bisa dibuka"). This was the highest-risk item: `LaunchMode.externalApplication` behaviour can only be observed on a real device

### Phase 2 — Definition of Done

**Code complete; the core loop is verified on device, two secondary criteria are not.**

✅ Home screen lists all saved items with title, summary, folder badge — confirmed on the physical Infinix 2026-07-24
✅ Tapping any item opens the original URL — confirmed on device 2026-07-24
⏳ Folder filter chips work — built and running in the same screen that renders correctly, but the chips themselves weren't individually exercised
⏳ Search returns relevant results in under 500ms — backend verified fast on production; the search screen UI wasn't opened, and on-device latency was never measured
⏳ Empty states are handled (no items, no search results) — built (`_Message`, "No matches for…"); can't be seen while the library has 17 items in it
✅ App is usable end-to-end for personal use, even if not pretty — share → save → browse → open all work on a real phone

**Verdict: Phase 2 is functionally complete.** The unchecked items are confirmation gaps, not known defects, and none of them block starting Phase 3 — in fact 3.1–3.3 (loading, error, and empty states) will force each one to be opened and exercised anyway.

### Phase 2 — Common Pitfalls

- **Re-fetching on every screen mount.** Cache the last fetch in state that survives navigation (e.g., hoist it above the route, or a simple in-memory cache) rather than re-hitting the backend every time a screen builds.
- **Search firing on every keystroke.** Debounce (300ms) — otherwise you'll hit the backend on every letter.
- **`ListView` performance with 100+ items.** Always use `ListView.builder` (lazy), never `ListView(children: [...])` with a fully-materialized list.
- **Opening TikTok URLs in browser instead of TikTok app.** `url_launcher`'s `launchUrl` should default to the native handler, but test on a real device.

---

## Phase 3 — Polish

**Goal:** App is reliable, looks reasonable, handles edge cases gracefully. Ready to use daily without frustration.

**Estimated time:** 3–4 days

### 3.1 Loading states

- [ ] Replace generic spinners with skeleton loaders on home screen
- [ ] "Saving..." screen has progress indicator and shows the URL being saved
- [ ] Search shows inline loading indicator without clearing previous results

### 3.2 Error states

- [ ] Network errors show "No connection — check your internet"
- [ ] Backend errors show "Something went wrong — try again"
- [x] AI processing failures show "Saved with limited info" non-blockingly — and, since 2026-07-24, **distinguish quota exhaustion from genuine AI failure**. Both save fine (Rule 5), but only one is worth waiting out. Backend detects the 429, skips the pointless retry, and records `ai_status = "quota_exceeded"`; the save screen then says the daily limit was reached instead of implying the link is broken. Prompted by mistaking exactly this for a retrieval bug. Verified: quota path returns the distinct result object in 1.6s (no wasted retry) and the DB accepts the new value with no migration
- [ ] All error states have a retry action

### 3.3 Empty states

- [ ] Home screen empty: friendly illustration + instructions ("Share a link from any app to get started")
- [ ] Folder filter with 0 items: "Nothing in [folder] yet"
- [ ] Search no results: "No matches for '[query]'"

### 3.4 Edge case handling

- [x] **TikTok captions were never being read at all** (found by dogfooding 2026-07-24, fixed same day). Every TikTok save landed in "Other" with "no available transcript or description", while Instagram worked fine even on short captions — that asymmetry was the tell that this was our bug, not a platform limit. Cause: `_fetch_open_graph` was used for TikTok, but a TikTok video page has **zero `og:` tags** (~400KB of JS, three `<meta>` tags, none useful). Fix: a dedicated `_fetch_tiktok()` using TikTok's official public oEmbed endpoint, which returns caption + creator + thumbnail as clean JSON with no API key. Verified end-to-end: a roast-beef video now classifies as "Cooking & Food" (high confidence) and a design video as "Tech & Coding", where both were previously "Other". Deleted/private videos return 400 and still degrade gracefully. **Side benefit:** TikTok items now get real thumbnails, which they never had
- [x] Duplicate URLs: if same URL already exists, return the existing item (don't double-save) — **done 2026-07-24.** Checked *before* the fetch, so a re-share costs neither a content fetch nor a Gemini request (which matters a lot at 20 free requests/day). Naive string equality would have missed the most common case: Instagram share links carry an `igsh=` token that is regenerated on every share, so the same post shared twice yields two different URL strings. Added `normalize_url()` in `utils/url_parser.py` — lowercases scheme/host, drops `www.`, strips tracking params (`igsh`, `img_index`, `_t`, `si`, `utm_*`, …), sorts the rest, drops trailing slash and fragment. Verified: 8/8 normalization cases, and end-to-end a re-shared IG post returned the original item in 1.4s while a genuinely different URL still saved. **Not handled (deliberate):** different URL *forms* of the same content, e.g. `youtu.be/ID` vs `youtube.com/watch?v=ID`, or a `vt.tiktok.com` short link vs the full URL it redirects to — that needs redirect resolution or per-platform special-casing
- [x] **Items blocked by the AI quota get reprocessed automatically** (2026-07-24). Found by the builder asking the right question: *"once the AI limit resets, will these reorganize themselves or stay stuck in Other?"* The answer was stay stuck — `ai_status` was recorded but nothing ever read it back, so `AI_FEATURE_SPEC` 9.3's "a future job can re-process them" had never been built. Worse, the duplicate check added earlier the same day had just closed the one accidental workaround (re-sharing used to create a fresh row that processed normally). Now: `services/reprocess.py` sweeps `quota_exceeded` items using their stored `raw_content`, triggered at startup and after `GET /items`; and re-sharing any non-`ok` item re-runs the AI in place. Verified — a queued item moved Other → Tech & Coding with `created_at`/`url` untouched, the queue drained, the 10-minute rate limit held, and a re-share reprocessed in place without creating a duplicate row
- [ ] Very long titles: truncate with ellipsis in UI
- [ ] Items with no thumbnail: use platform-specific fallback icon
- [ ] Items with no summary: hide the summary line gracefully
- [ ] Network offline: show cached items, queue saves for later (optional, can defer)

### 3.5 Visual polish

- [ ] Pick a single accent color and apply consistently
- [ ] Folder badges have distinct, accessible colors
- [ ] Card spacing and typography feel intentional, not default
- [ ] Add subtle haptic feedback on tap (Flutter's built-in `HapticFeedback` class — no extra package needed)
- [ ] App icon and splash screen replaced from Flutter defaults (use `flutter_launcher_icons` package, or manually replace the assets in `android/app/src/main/res/`)

### 3.6 Performance check

- [ ] Save 100+ items and confirm home screen still loads in under 1 second
- [ ] Search latency remains under 500ms
- [ ] No frame drops while scrolling
- [ ] Memory usage stays reasonable (check with Flutter DevTools or the Android Studio profiler if curious)

### 3.7 Refactor and cleanup

- [ ] Remove all leftover `print`/`debugPrint` debug statements
- [ ] Move all hardcoded strings to `constants.dart`
- [ ] Extract repeated styles into shared `ThemeData`/`TextStyle` objects
- [ ] Ensure `flutter analyze` is clean (no unresolved type or null-safety warnings)
- [ ] Run `dart format .` for consistent formatting

### Phase 3 — Definition of Done

✅ App handles errors gracefully without crashing
✅ All loading and empty states are handled
✅ Visual style is consistent across screens
✅ App icon and splash screen are not Flutter defaults
✅ Performance is acceptable with 100+ items
✅ Code is clean enough to share publicly on GitHub

### Phase 3 — Common Pitfalls

- **Over-polishing.** Spending 3 days making the perfect icon is the wrong tradeoff. Get it to "good enough" and move on.
- **Adding features instead of polishing.** Resist the urge to add nice-to-haves listed in PRD Section 6.2. Polish only.
- **Skipping the duplicate URL check.** This bug becomes really annoying really fast in personal use.

---

## Phase 4 — Personal Use & Iterate

**Goal:** Use the app daily for 2+ weeks. Discover what's broken or missing. Fix the most important issues.

**Estimated time:** Ongoing (2+ weeks of daily use)

This is where the product becomes real.

**Where to look when something breaks** (answered 2026-07-24):

| | Railway | Supabase |
|---|---|---|
| Holds | our application logs — every `logger.info/warning/error` | the saved rows + Postgres logs |
| Answers | **"why did it fail?"** | **"what got saved?"** |
| Example | `429 RESOURCE_EXHAUSTED`, `Fetch failed for … 400` | `ai_status = 'quota_exceeded'` |

Railway is the debugging surface; Supabase shows the consequence. The quota incident was the textbook case — Supabase said `ai_status: failed`, Railway said *why*.

**Two gaps that only bite once there are real users** (not worth fixing while solo):
- **No request ID or user ID in log lines.** With 20 users you would see "AI failed" with no way to tell whose save it was or which database row it became. Fix: generate a request ID per `/save` and include it in every log line *and* on the stored row.
- **Railway log retention is short.** A bug reported a week later has no surviving logs. Fix: ship logs somewhere persistent, or record failure reasons on the row itself (which `ai_status` already begins to do).

**Cost, if the app gets ~20 active users** (measured 2026-07-24, not estimated): a social-media save costs ~382 input tokens, an article ~3,023 (it is truncated at `MAX_CONTENT_CHARS = 8_000`), output ~100. At 20 users × 5 saves/day ≈ 3,000 saves/month: `gemini-3.5-flash` ≈ **$9/mo**, `gemini-3.5-flash-lite` ≈ **$2/mo**. Flash-lite is the better fit — the AI's job here is classification plus a two-sentence summary, with no reasoning, so the extra capability of the larger model is paid for and never requested. Verify by running the same ~10 URLs through both and comparing before switching. **Note it is not a drop-in swap:** `gemini-3.5-flash-lite` and `gemini-3.6-flash` both reject our `thinking_config=ThinkingConfig(thinking_budget=0)` with `400 INVALID_ARGUMENT` (found 2026-07-24); removing that line makes flash-lite work. That setting only exists because Gemini 3.5 Flash's thinking tokens ate `max_output_tokens`, so it may be unnecessary on lite anyway — but it has to be handled, not assumed away. **The larger untouched lever is `MAX_CONTENT_CHARS`:** articles cost 8× a TikTok purely because we send 8,000 characters to produce two sentences.

### 4.1 Daily use commitment

- [ ] Install the latest build on your daily-driver phone
- [ ] Use it for every link/video you would normally save
- [ ] Don't use the native TikTok/IG/YouTube "save" features as a parallel system — force yourself to use Fetch
- [ ] Goal: 50+ items saved by end of week 2

### 4.2 Feedback collection

- [ ] Keep a running note (in Fetch itself or in your phone) of friction points
- [ ] Categorize each as: bug, missing feature, AI mistake, UX issue
- [ ] Note specific examples (e.g., "AI keeps putting fitness videos in Self Growth")

### 4.3 AI prompt iteration

- [ ] After ~50 items, review the folder distribution
- [ ] Are too many items going to "Other"? (Prompt might be too cautious)
- [ ] Is one folder over-used? (Prompt might bias toward it)
- [ ] Are titles generic? (Tighten the title rule in the prompt)
- [ ] Update `AI_FEATURE_SPEC.md` Section 13 with each change

### 4.4 Bug fixes (as discovered)

- [ ] Fix the top 3 most frequent bugs you encounter
- [ ] Each fix → commit → deploy → confirm fix on device
- [ ] Don't fix every small thing; prioritize what affects daily use

### 4.5 Decide on nice-to-haves

- [ ] After 2 weeks, review PRD Section 6.2 (nice-to-haves)
- [ ] Pick the ONE that would most improve your daily use
- [ ] Build only that one. Repeat.

### 4.6 Optional: open to early users

- [ ] Generate an APK build via `flutter build apk --release`
- [ ] Share with 3–5 friends or networks members
- [ ] Get their feedback after 1 week of their use
- [ ] Decide: keep going, pivot, or wind down

### 4.7 Optional: write about it

- [ ] Write a short post on LinkedIn, Twitter, or personal blog about:
  - What you built and why
  - One technically interesting decision you made
  - One thing you learned
- [ ] This is the resume artifact. The product is the means; the writing is what gets seen in interviews.

### Phase 4 — Definition of Done (Soft)

Phase 4 has no clean "done." It ends when:
- You stop using the app yourself (signal: something is wrong, pivot or wind down)
- OR you've used it for 4+ weeks consistently and you have a clear next direction (signal: keep building)

---

## Cross-Phase Conventions

### Git commit hygiene

- One commit per atomic change
- Commit message format: `[phase X] short description` (e.g., `[phase 1] add fetcher service for YouTube`)
- Push at least once per work session
- Never commit `.env` files

### When stuck

1. Re-read the relevant section of `PRD.md`, `ARCHITECTURE.md`, or `AI_FEATURE_SPEC.md`
2. Search the error message verbatim
3. Ask Claude Code with full context (paste error, paste relevant code, link to the spec section)
4. If still stuck after 30 minutes, write down what you've tried and ask for help (DM friends, post in dev communities)

### When tempted to scope-creep

Read PRD Section 4.2 (Non-goals). If the feature you want to add is in there, **don't build it**.

If the feature isn't in either Section 4.2 or Section 6.1, it's an open question — but default to **no**, finish the current phase first.

---

## Document References

- Product goals and constraints → `PRD.md`
- System architecture and stack rationale → `ARCHITECTURE.md`
- AI prompt design and validation → `AI_FEATURE_SPEC.md`
- Working agreement with Claude Code → `CLAUDE.md` (next document)

---

*End of TASKS v1.0*
