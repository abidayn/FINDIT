# Tasks Breakdown

**Project:** Fetch (working name)
**Author:** Biday
**Last updated:** June 26, 2026
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

- [ ] Create new GitHub repo named `fetch` (or final project name)
- [ ] Add `.gitignore` covering Python (`__pycache__`, `.env`, `venv/`) and Flutter/Dart (`.dart_tool/`, `build/`, `android/local.properties`, `*.iml`)
- [ ] Add empty `README.md` with project name and one-line description
- [ ] Create root folder structure: `mobile/`, `backend/`, `docs/`
- [ ] Move `PRD.md`, `ARCHITECTURE.md`, `AI_FEATURE_SPEC.md`, and this file into `docs/`
- [ ] First commit, push to main

### 0.2 Supabase project setup

- [x] Create account at supabase.com (free)
- [x] Create new project named `stash` (region: closest to Indonesia — Singapore) — note: kept the original `stash` name in the Supabase dashboard even after the app was renamed to Fetch (2026-07-23); renaming the project there isn't worth the churn
- [x] Save the **Project URL** and **anon key** and **service key** somewhere secure
- [x] Open the SQL Editor and run the schema from `ARCHITECTURE.md` Section 3.3 to create the `items` table and indexes
- [x] Manually insert one test row via the dashboard to confirm the table works
- [x] (Skip Row Level Security for MVP — single user, no auth)

### 0.3 Google AI Studio (Gemini) setup

- [ ] Go to aistudio.google.com, sign in
- [ ] Create new API key, save securely
- [ ] Test the key with a curl command to confirm it works:
  ```bash
  curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash:generateContent?key=YOUR_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"contents":[{"parts":[{"text":"Say hi in 3 words"}]}]}'
  ```
- [ ] Verify your free tier limits in AI Studio dashboard (should show ~1,500 RPD for Gemini 3 Flash)

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
- [ ] Visit `http://localhost:8000/docs` to see auto-generated Swagger UI

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

✅ User can share a URL from TikTok/IG/YouTube/Chrome → it appears in Supabase with correct AI processing
✅ Save flow completes in under 5 seconds for articles and YouTube
✅ TikTok/IG URLs save successfully even when content fetch fails (graceful degradation)
✅ Invalid URLs return clear error messages
✅ Backend logs are clean and readable for each request
✅ At least 10 real items saved to the database by manual testing

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

- [ ] Create `backend/routes/items.py`
- [ ] `GET /items` returns all items (latest first)
- [ ] `GET /items?folder=Self+Growth` filters by folder
- [ ] `GET /items/{id}` returns single item
- [ ] `DELETE /items/{id}` removes an item
- [ ] Create `backend/routes/search.py`
- [ ] `GET /search?q=morning+routine` — uses PostgreSQL full-text search index from schema
- [ ] All endpoints wired into `main.py`

### 2.2 Backend — Search implementation

- [ ] In `database.py`, use the GIN full-text index from schema
- [ ] Query: `SELECT * FROM items WHERE to_tsvector('english', title || ' ' || summary) @@ plainto_tsquery('english', $1) ORDER BY ts_rank(...) DESC LIMIT 50`
- [ ] If query is empty string, return all items
- [ ] If query has fewer than 2 characters, return empty list (avoid noisy results)

### 2.3 Mobile — Item model and data services

- [ ] In `mobile/lib/models/item.dart`, mirror the `Item` shape from backend (a plain Dart class with a `fromJson` factory)
- [ ] Define `Folder` as a Dart `enum` with the 9 allowed values
- [ ] In `api_client.dart` (or a small `items_repository.dart`), expose functions to fetch all items and search — plain `Future`-returning functions are enough; no hooks equivalent needed for an app this size
- [ ] For search debouncing (300ms), use a `Timer` that gets cancelled/reset on each keystroke in the search screen's state
- [ ] Create `mobile/lib/constants.dart` exporting the folder list and per-folder colors

### 2.4 Mobile — ItemCard widget

- [ ] Create `mobile/lib/widgets/item_card.dart`
- [ ] Constructor params: `item` (Item), `onTap` (VoidCallback)
- [ ] Layout: thumbnail (or platform icon as fallback) on left, title + summary on right, folder badge at top-right
- [ ] Wrap in `InkWell`/`GestureDetector` to trigger `onTap`
- [ ] Long-press shows a delete option (post-MVP polish, skip for now)
- [ ] Use platform-appropriate icons for source (YouTube logo, TikTok logo, link icon for articles)

### 2.5 Mobile — FolderBadge widget

- [ ] Create `mobile/lib/widgets/folder_badge.dart`
- [ ] Constructor param: `folder` (Folder)
- [ ] Renders a small colored pill with the folder name
- [ ] Colors mapped from `constants.dart`

### 2.6 Mobile — Home screen

- [ ] Update `lib/screens/home_screen.dart` to be the home screen
- [ ] Fetch all items on load (`FutureBuilder` or a simple `StatefulWidget` + `setState` after an async call)
- [ ] Show loading skeleton (or spinner) while loading
- [ ] Show empty state if no items: "Nothing saved yet. Share a link to get started."
- [ ] `ListView.builder` of `ItemCard`s (lazy by default — no extra config needed for basic performance)
- [ ] Tap card → open original URL in browser (`url_launcher` package's `launchUrl`)
- [ ] Header has a search icon → navigates to search screen via `go_router`
- [ ] Wrap the list in a `RefreshIndicator` for pull-to-refresh

### 2.7 Mobile — Folder filter

- [ ] Add a horizontal scrollable row of folder chips above the list (`ListView` with `scrollDirection: Axis.horizontal`, or Flutter's `ChoiceChip` widgets)
- [ ] "All" chip is default selected
- [ ] Tapping a folder chip filters the list to that folder
- [ ] Show count next to each folder (e.g., "Self Growth (12)")
- [ ] State management: local Flutter state (`setState`) is enough — no external state management package needed yet

### 2.8 Mobile — Search screen

- [ ] Create `lib/screens/search_screen.dart`, registered as a `go_router` route
- [ ] Search input at top (`TextField`, e.g. inside the `AppBar`)
- [ ] Below: results list from the debounced search call in 2.3
- [ ] Empty state when no query: "Type to search your saves"
- [ ] Empty state when no results: "No matches for 'XYZ'"
- [ ] Same `ItemCard` widget for results
- [ ] Tap result → open original URL

### 2.9 Manual testing

- [ ] Save 20+ items across different folders
- [ ] Verify all show on home screen
- [ ] Filter by each folder, confirm correct items appear
- [ ] Search for keywords from titles, confirm results
- [ ] Test pull-to-refresh
- [ ] Test tapping items opens original URLs in correct app (TikTok URL opens TikTok app, YouTube opens YouTube)

### Phase 2 — Definition of Done

✅ Home screen lists all saved items with title, summary, folder badge
✅ Folder filter chips work
✅ Search returns relevant results in under 500ms
✅ Tapping any item opens the original URL
✅ Empty states are handled (no items, no search results)
✅ App is usable end-to-end for personal use, even if not pretty

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
- [ ] AI processing failures show "Saved with limited info" non-blockingly
- [ ] All error states have a retry action

### 3.3 Empty states

- [ ] Home screen empty: friendly illustration + instructions ("Share a link from any app to get started")
- [ ] Folder filter with 0 items: "Nothing in [folder] yet"
- [ ] Search no results: "No matches for '[query]'"

### 3.4 Edge case handling

- [ ] Duplicate URLs: if same URL already exists, return the existing item (don't double-save)
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
