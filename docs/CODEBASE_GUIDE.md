# Codebase Guide — What We've Actually Built

**Purpose of this doc:** `ARCHITECTURE.md` describes the *intended* design. This doc describes **what actually exists in the repo right now**, file by file, so you can open any file and already know why it's there and what talks to what. Where "current state" differs from the full architecture (e.g. endpoints not built yet), it's called out explicitly.

This is a learning artifact — read it once fully, then use it as a map whenever you forget "wait, why does this file exist."

---

## 1. The one flow that explains 90% of the codebase

Every file in `backend/` exists to serve exactly one journey:

```
Flutter app → POST /save {url} → main.py → routes/save.py
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
            utils/url_parser.py      services/fetcher.py       services/ai.py
            (which platform?)        (get raw content)        (title/summary/folder)
                    │                         │                         │
                    └─────────────────────────┴─────────────────────────┘
                                              ▼
                                   services/database.py
                                   (write row to Supabase)
                                              ▼
                                   models/schemas.py (Item)
                                              ▼
                                   ...back to the Flutter app
```

`models/schemas.py` isn't in that pipeline visually, but it's the one file **every other file imports from** — it defines the shape of data at each handoff point. Read it first if you're re-orienting yourself.

Keep this diagram in your head. Everything below is detail on top of it.

---

## 2. Backend (`backend/`) — file by file

### 2.1 `config.py` — the only file allowed to read `.env`

Reads every secret (`GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `YOUTUBE_API_KEY`, `JINA_API_KEY`) once via `os.getenv()`. Every other backend file imports the already-loaded variable from here — nothing else calls `os.getenv()` directly.

**Why it matters:** if you ever change *how* secrets are supplied (e.g. Railway env vars vs a local `.env` file), you edit one file, not eight.

### 2.2 `main.py` — the entry point, 22 lines on purpose

```python
app = FastAPI(title="Fetch API")
app.add_middleware(CORSMiddleware, ...)
app.include_router(save_router)

@app.get("/health")
def health(): return {"status": "ok"}
```

Three jobs: create the FastAPI app, attach CORS (so the Flutter app's requests aren't blocked), and mount `save_router`. `/health` is the endpoint Railway/you ping to confirm the server is alive (already verified working in commit `9224ca9`).

**Notice what's *not* here:** no business logic. That's intentional — `main.py` wires things together, `routes/` does the work. This is Core Architectural Rule 6 (one responsibility per file) applied at the top level.

**Current-state gap:** `ARCHITECTURE.md` §3.2 lists `/items`, `/search`, and `DELETE /items/{id}` as MVP endpoints. Those don't exist yet — only `save_router` is mounted. They're Phase 2 (`TASKS.md` §2.1), not built yet.

### 2.3 `models/schemas.py` — the shared vocabulary

Pydantic models. No logic, just shape definitions — but **every single backend file imports something from here**. This is the actual load-bearing file of the whole backend.

| Class | Represents | Used by |
|---|---|---|
| `Folder` (a `Literal` of 9 strings) | The fixed folder taxonomy | `ai.py`, `schemas.Item` |
| `SaveRequest` | Body of `POST /save` — just `url: HttpUrl` | `routes/save.py` |
| `FetchedContent` | Output of `fetcher.py`, input to `ai.py` | `fetcher.py`, `ai.py` |
| `AIResult` | Output of `ai.process_content()` | `ai.py`, `routes/save.py` |
| `Item` | One row of the `items` table / the `/save` response | `database.py`, `routes/save.py` |
| `ErrorResponse` | Shape of any error body | `routes/save.py` |

Two details worth understanding, because they're the kind of thing that comes up in an interview:

- `Folder = Literal["Self Growth", "Productivity", ...]` instead of `Folder = str`. This means Pydantic **rejects** any folder value outside the 9 allowed ones automatically — the validation lives in the type system, not in an `if` statement you'd have to remember to write.
- `SaveRequest.url` is typed `HttpUrl`, not `str`. FastAPI uses this to reject malformed URLs with a 422 **before your code runs at all**.

**Mirrors to:** `mobile/lib/models/item.dart` mirrors `Item` on the Dart side (see §3.7). Keep them in sync — the Dart class omits `raw_content` and `user_id` on purpose, but every other field must match.

### 2.4 `utils/url_parser.py` — pure functions, no network calls

Two functions:
- `detect_platform(url)` — looks at the hostname, matches against a small dict (`youtube.com` → `"youtube"`, etc.). Unrecognized hostname → `"article"` (assume it's a normal webpage Jina can handle). No parseable hostname at all → `"other"`.
- `extract_youtube_id(url)` — pulls the video ID out of the three URL shapes YouTube actually uses (`youtu.be/ID`, `?v=ID`, `/shorts/ID`).

Both are called from `fetcher.py` and `routes/save.py`. Nothing here touches the network — that's why it lives in `utils/` and not `services/`: `services/` is for things that call out to the world, `utils/` is for logic that doesn't.

### 2.5 `services/fetcher.py` — "fetcher fetches," nothing else

One public function: `fetch_content(url) -> FetchedContent`. Internally routes by platform:

```
"article"  → _fetch_article()     → Jina Reader API
"youtube"  → _fetch_youtube()     → YouTube Data API v3
anything else → _fetch_open_graph() → scrape <meta property="og:*"> tags via regex
```

**The one rule that matters here:** `fetch_content()` never raises. Every failure path (timeout, 403, garbage HTML) is caught and turned into `FetchedContent(text="")`, not an exception. That's why `routes/save.py` can call it with no try/except of its own — the contract is "this always returns something usable."

`_fetch_open_graph` is the "ugliest" one on purpose — TikTok/Instagram frequently block non-browser requests, so this is a best-effort regex scrape of two meta tags, not a real HTML parser. Bringing in BeautifulSoup for two tags would be overkill (Principle 2: simplicity first).

### 2.6 `services/ai.py` — the only file allowed to call Gemini (Core Rule 1)

The most complex file, structured as three stages: **build prompt → call Gemini → validate output.**

- `build_prompt(content, stricter=False)` — assembles the prompt from `AI_FEATURE_SPEC.md` §6.1. Has a branch for when fetched content is too short (`< 20` chars — the TikTok/IG case where fetch failed): it switches to a prompt that tells Gemini outright "you have almost nothing, don't invent a summary." Without this, Gemini would happily hallucinate a plausible-sounding summary for a video it never saw.
- `call_gemini(prompt)` — the raw API call. `thinking_budget=0` (line ~145) turns off Gemini 3.x's default "think before answering" behavior — discovered during development that thinking tokens were eating the whole 300-token output budget, leaving the actual JSON truncated to nothing. Classifying into 9 fixed folders doesn't need deliberation.
- `validate(raw)` — this *is* Core Architectural Rule 4 ("AI output is untrusted input") in code form. Checks JSON parses, required fields exist, title isn't too long, folder is one of the 9 allowed (auto-corrects to `"Other"` if not — never rejects the whole item over a bad folder), confidence is valid. Only returns `None` (unrecoverable) when the JSON itself is broken or fields are missing.
- `process_content(content) -> AIResult` — the single public entry point (Core Rule 1: nothing else in the codebase calls Gemini). Tries twice max (`for attempt in (1, 2)`), with a stricter prompt on the retry. If both fail, returns `FALLBACK_RESULT` — a hardcoded constant, never an exception. This is why `routes/save.py` doesn't need a try/except around this call either.

### 2.7 `routes/save.py` — the orchestrator

This is where the diagram in §1 becomes actual code. Five real lines:

```python
platform = detect_platform(url)
fetched = fetcher.fetch_content(url)
result = ai.process_content(fetched)
row = {...}  # merge fetched + result into one dict
return database.insert_item(row)
```

Only `database.insert_item()` is wrapped in try/except. Why only that one? Because §2.5 and §2.6 already guaranteed their functions never raise — the *only* step that's allowed to genuinely fail the request is the database write. If that fails, it returns `HTTPException(500)`.

One line worth understanding:
```python
"ai_status": "failed" if result is ai.FALLBACK_RESULT else "ok",
```
`is` checks object identity, not value equality. This distinguishes "the AI genuinely failed and we used the fallback" from "the AI succeeded and coincidentally produced similar-looking text" — a real AI response could never *be* the same object as the module-level `FALLBACK_RESULT` constant.

### 2.8 `services/database.py` — the only file that touches Supabase

Five functions: `insert_item`, `get_all_items`, `get_items_by_folder`, `search_items`, `delete_item`. All go through one `Client` created once at import time (not per-request — connection pooling).

Notice it **crashes on import** if `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` are missing (`raise RuntimeError` at module level, not inside a function). Deliberate: "a backend that boots without database credentials is a backend that lies about being healthy" — better to fail loudly at startup than have `/health` say OK while `/save` silently fails on every request.

`search_items()` uses SQL `ILIKE` (substring match) rather than the GIN full-text index that's already in the Supabase schema (`ARCHITECTURE.md` §3.3). That upgrade is explicitly deferred to Phase 2 (`TASKS.md` §2.2) — `ILIKE` is "good enough" for now and simpler.

**Current-state gap:** `get_all_items`, `get_items_by_folder`, `search_items`, `delete_item` exist in this file but **nothing calls them yet** — there's no `routes/items.py` or `routes/search.py` wired into `main.py`. They were written ahead of the routes that will use them (Phase 2), which is fine — the schema and DB layer were natural to finish together in Phase 1.

### 2.9 `utils/logger.py` — thin wrapper around Python's `logging`

One function, `get_logger(name)`, called by every file with its own `__name__` so log lines show their origin. The `if not logger.handlers` guard (line 16) exists because Python caches logger objects by name — without the guard, calling this twice for the same module would double every log line.

### 2.10 Files not worth deep-diving, but here's why they exist

| File | Why it's there |
|---|---|
| `models/__init__.py`, `routes/__init__.py`, `services/__init__.py`, `utils/__init__.py` | Empty files that turn each folder into an importable Python package. Standard Python mechanism, no logic. |
| `requirements.txt` | Pinned list of Python packages (`fastapi`, `uvicorn[standard]`, `python-dotenv`, `supabase`, `google-genai`, `httpx`, `pydantic`). Railway reads this to know what to install. |
| `Procfile` | Tells Railway (or any Heroku-style platform) the command to start the server. |
| `.env.example` | Same variable names as `.env`, empty values — committed to git so you (or anyone cloning the repo) knows what secrets to fill in, without leaking the real ones. |
| `.env` | The real secrets. **Never committed** — confirm `.gitignore` covers it (it does — see §5). |

---

## 3. Mobile (`mobile/`) — file by file

Phase 0 is complete and task 1.8 (share intent) is done. The app now: loads config from `.env`, calls the Railway backend's `/health` on startup and displays the result, and appears in Android's share sheet — receiving a shared URL opens a placeholder save screen.

### 3.1 `pubspec.yaml` — Flutter's `package.json`

Declares the SDK version (`^3.12.2`), the real dependencies, and dev dependencies:

| Package | What it's for | Status |
|---|---|---|
| `go_router` | Declarative routing between screens | Wired up in `main.dart`, two routes (`/`, `/save`) |
| `receive_sharing_intent` | Receive shared URLs from other apps (the core feature) | **In use** via `services/share_intent_service.dart` |
| `flutter_dotenv` | Loads `mobile/.env` as a bundled asset at startup | **In use** — loaded in `main.dart`, read in `api_client.dart` |
| `http` | HTTP client for calling the backend | **In use** in `api_client.dart`. Note it's a *direct* dependency now — it was previously only transitive (via `supabase_flutter`), which is fragile: a future `supabase_flutter` upgrade could drop it and break the build |
| `supabase_flutter` | Talk to Supabase directly from the app (for reads, per `ARCHITECTURE.md` open question §13) | Installed, **not used yet** |
| `cupertino_icons` | iOS-style icon font, comes with every Flutter template | Unused, harmless default |
| `flutter_lints` | Recommended lint rules (dev-only, not shipped in the app) | Active via `analysis_options.yaml` |

The `flutter: assets:` block registers `.env` so it gets bundled into the APK — without that line, `dotenv.load()` throws at startup because the file isn't in the build.

### 3.2 `lib/main.dart` — entry point + router + share-intent wiring

Three jobs now:

1. **Load config before the app starts.** `main()` is `async` and awaits `dotenv.load()` before `runApp()`, so `API_URL` is guaranteed available by the time any screen builds. `WidgetsFlutterBinding.ensureInitialized()` is required first — loading an asset needs the Flutter engine's platform channels, which don't exist until the binding is initialized.
2. **Declare routes.** `/` → `HomeScreen`, `/save` → `SaveScreen`. The save route takes its URL via `state.extra` rather than a path parameter (`/save/:url`) — a URL inside a URL would need escaping, and `extra` passes the raw string with no encoding concerns.
3. **Subscribe to share intents.** `FetchApp` is a `StatefulWidget` (was stateless) because it now owns a stream subscription that must be cancelled in `dispose()` — an un-cancelled stream is a memory leak.

### 3.3 `lib/services/share_intent_service.dart` — the share-sheet listener

Wraps `receive_sharing_intent` and exposes only what Fetch needs: a URL string. Two entry points, because Android delivers shares two different ways:

- `getInitialSharedUrl()` — **cold start.** The app wasn't running; Android launched it *with* the share attached. Read once at startup via `getInitialMedia()`, then `reset()` tells the plugin it's consumed so it isn't redelivered on the next resume.
- `listen(callback)` — **warm start.** The app was already in memory; the share arrives as a stream event.

Miss either one and shares silently fail in exactly half the real-world cases. Both paths are verified working on device.

Everything is wrapped in try/catch returning `null` on failure — needed because the plugin talks over a platform channel that doesn't exist in widget tests, so an un-caught call would break `flutter test`.

### 3.4 `lib/services/api_client.dart` — the backend HTTP client

Two public functions: `fetchHealth()` and `saveItem(url)`. Both **throw** on failure rather than returning null or a sentinel — that's deliberate, because `FutureBuilder`'s `snapshot.hasError` then handles all error display with no extra plumbing.

The two timeouts differ on purpose, and the reasoning is worth internalising:

| Function | Timeout | Why |
|---|---|---|
| `fetchHealth()` | 15s | Returns a fixed `{"status":"ok"}`. The only slow case is a Railway cold start. |
| `saveItem()` | 45s | The backend chains a content fetch (up to 10s) with a Gemini call that may retry once, plus the DB write — on top of a possible cold start. |

Giving `saveItem()` 15s would produce **false timeouts**: the request succeeds server-side while the phone gives up early. A timeout should reflect the slowest reasonable work, not a round number.

`_baseUrl()` is the shared helper reading `API_URL` from dotenv. Its null/empty guard has a useful side effect: in widget tests `dotenv.load()` never runs, so it throws *before* any network call — no hanging requests or pending-timer warnings at test teardown.

**Current-state gap:** `getAllItems()`, `searchItems()`, `deleteItem()` are listed in `TASKS.md` 1.10 but deliberately **not built** — their backend endpoints don't exist yet either (Phase 2 task 2.1). Each gets written alongside the screen that uses it.

### 3.5 `lib/screens/home_screen.dart`

Now a `StatefulWidget` that calls `fetchHealth()` in `initState()` and renders the result through a `FutureBuilder` with three states: spinner while waiting, error text on failure, `Backend status: ok` on success.

The `Future` is stored in a `late final` field assigned in `initState()`, **not** created inline in `build()`. This matters: `build()` can run many times (on every rebuild), and creating the Future there would fire a new HTTP request each time.

Polished error/loading states are Phase 3 (§3.1–3.2) — this is deliberately minimal.

### 3.6 `lib/screens/save_screen.dart` — where the core loop closes

Receives the shared URL, POSTs it to `/save`, and renders one of three states via `FutureBuilder`: `_Saving` (spinner + the URL), `_SaveFailed` (message + Retry), `_SaveSucceeded` (folder badge, title, summary, Done).

Three details worth understanding:

- **Retry works by assigning a *new* Future inside `setState`.** `FutureBuilder` re-runs only when the Future's *identity* changes — calling `setState(() {})` alone would rebuild the UI with the same stale result and fire no new request. Same reason the Future is created in `initState()` and not in `build()`: `build()` runs on every rebuild, so creating it there would fire a fresh HTTP request each time.
- **"Done" calls `SystemNavigator.pop()`, not `Navigator.pop()`.** The first exits the app and returns the user to whatever they shared from; the second would just pop back to Fetch's home screen. For a share flow, saving a link is a side errand — the user wants to land back in TikTok.
- **`ai_status == 'failed'` is surfaced, not hidden.** The backend always saves, falling back to `"Untitled saved item"` when the AI fails (Core Rule 5). Rendering that placeholder as though it were a real title would be lying to the user, so the screen says the AI details are unavailable instead.

The folder badge is a small private widget here rather than `widgets/folder_badge.dart` — it's used in exactly one place so far. Phase 2 task 2.5 extracts it once the item list needs it too.

### 3.7 `lib/models/item.dart` — mirrors the backend `Item`

A plain Dart class with a `fromJson` factory, matching `backend/models/schemas.py`'s `Item`. Keep the two in sync when either changes.

Two backend fields are deliberately **not** mirrored: `raw_content` (the full fetched article text — potentially huge, and no screen displays it) and `user_id` (always null until auth exists). `fromJson` ignores unmapped JSON keys, so omitting them costs nothing. A client model doesn't have to be a perfect mirror of the server — take what the UI needs.

### 3.8 `test/widget_test.dart` — the one test that exists

```dart
testWidgets('Home screen shows the app name', (tester) async {
  await tester.pumpWidget(const FetchApp());
  expect(find.text('Fetch'), findsOneWidget);
});
```

A widget test: builds the widget tree in memory (no real device needed) and asserts the text "Fetch" appears once. It calls `FetchApp()` directly, never `main()` — so `dotenv.load()` never runs in tests, which is exactly why `api_client.dart` and `share_intent_service.dart` both need to fail gracefully when config/platform channels are absent. Run it with `flutter test`. Per `CLAUDE.md`, full test infra is explicitly post-MVP.

### 3.9 `android/app/build.gradle.kts` — Android build config

The file we just edited together. Key lines:
- `namespace`/`applicationId = "com.fetch.mobile"` — the app's unique Android package ID.
- `compileSdk = 37` — **just changed from the Flutter-default `36`** because the `receive_sharing_intent` plugin requires SDK 37. This was the exact build failure we debugged.
- `minSdk`/`targetSdk = flutter.minSdkVersion/.targetSdkVersion` — still deferring to Flutter's defaults (unlike `compileSdk`, these didn't need overriding).
- `signingConfig = signingConfigs.getByName("debug")` under `release` — release builds currently sign with the debug key, which is fine for personal use (`flutter run --release`) but **would need a real keystore before any Play Store submission** (`ARCHITECTURE.md` §7.2, explicitly deferred).

### 3.10 `android/app/src/main/AndroidManifest.xml` — Android's permission/entry manifest

Declares `MainActivity` as the launcher activity, sets `android:label="Fetch"` (the name shown in the launcher *and* the share sheet), and sets the launch theme.

**The share-sheet registration lives here** — this is the piece that has no Dart equivalent:

```xml
<intent-filter>
    <action android:name="android.intent.action.SEND"/>
    <category android:name="android.intent.category.DEFAULT"/>
    <data android:mimeType="text/plain"/>
</intent-filter>
```

An *intent filter* is how an Android app advertises a capability to the OS. This one says "Fetch can receive a SEND action carrying `text/plain`." Android reads it at **install time** and adds Fetch to its system-wide registry of share targets — which is why the share sheet can list your app without ever running it, and why changing this file requires a full reinstall (a hot reload won't do it; the OS-level registry only updates on install).

`android:launchMode="singleTop"` matters for the warm-start path: without it, every share would spawn a *new* activity instance instead of delivering the intent to the running one.

The separate `<queries>` block for `android.intent.action.PROCESS_TEXT` is unrelated — a Flutter default so the engine's text-selection plugin can query other apps.

### 3.11 Files not worth deep-diving, but here's why they exist

| File | Why it's there |
|---|---|
| `android/build.gradle.kts` (root) | Top-level Gradle config — repository sources (`google()`, `mavenCentral()`), shared build directory location. Rarely touched. |
| `android/settings.gradle.kts` | Tells Gradle where the Flutter SDK lives (`local.properties`) and declares plugin versions (Android Gradle Plugin, Kotlin). Rarely touched. |
| `analysis_options.yaml` | Turns on `flutter_lints`' recommended rule set for `flutter analyze`. Standard Flutter boilerplate. |
| `android/app/src/debug/AndroidManifest.xml`, `.../profile/AndroidManifest.xml` | Per-build-mode manifest overrides (e.g. debug mode gets an extra `INTERNET` permission automatically). Auto-generated, not hand-edited. |
| `android/app/src/main/res/**` (`styles.xml`, `launch_background.xml`) | The native splash screen shown for a split second before Flutter's engine takes over. Flutter defaults — Phase 3 task 3.5 replaces these with real branding. |
| `mobile/README.md` | The default `flutter create` README (links to Flutter's own getting-started docs). Not project-specific; safe to ignore or replace later. |

---

## 4. `docs/` — the four documents that govern this project

| File | What it answers | When to read it |
|---|---|---|
| `PRD.md` | *What* are we building, for whom, and what's explicitly out of scope | Before considering any new feature |
| `ARCHITECTURE.md` | *How* the full system is designed to work, including parts not built yet | Before touching a new subsystem, or when this guide says "current-state gap" |
| `AI_FEATURE_SPEC.md` | Exact prompt template, JSON schema, validation rules for `ai.py` | Before changing anything in `services/ai.py` |
| `TASKS.md` | The phased build checklist (0–4), what's checked off | To know what's next / whether something is in-scope for the current phase |
| `CODEBASE_GUIDE.md` | This file — what's actually in the repo right now | Whenever you've lost track of what a file does |

`CLAUDE.md` (repo root) is a fifth document, but it's the working agreement for how Claude Code should behave in this project, not project knowledge itself.

---

## 5. Root-level files

| File | Purpose |
|---|---|
| `README.md` | Repo landing page. Stack section updated to Flutter during the Fetch rename (2026-07-23). |
| `.gitignore` | Covers `.env`, `venv/`, `__pycache__/`, `.dart_tool/`, `build/`, `android/local.properties`, etc. — confirmed before any commit per Core Rule 7. |
| `CLAUDE.md` | Working agreement — not app code, but the rules this guide itself was written under (learning-first framing, phase discipline, architectural rules referenced throughout this doc). |

---

## 6. Where we actually are right now (mid Phase 1)

Cross-referencing `TASKS.md`'s checkboxes with what's on disk:

**Done and verified:**
- Supabase project + schema + one test row (0.2)
- Backend fully scaffolded and all of Phase 1's backend work — schemas, fetcher, AI service, database service, `/save` endpoint — built and manually tested (1.1–1.7)
- Railway deployment live, `/health` and `/save` confirmed public (0.6)
- Flutter project scaffolded, `compileSdk` bumped to 37, app installs and runs on a real device (0.7)
- **Phase 0 complete:** config injection via `flutter_dotenv` decided and documented (0.7), and the mobile↔backend round-trip verified on device — home screen shows `Backend status: ok` from Railway (0.8)
- **Task 1.8 complete:** share intent integration — Fetch is registered as a system share target, and both cold-start and warm-start shares deliver the URL to `SaveScreen` (verified on device 2026-07-23)
- Project renamed Stash → Fetch, including Android `applicationId` → `com.fetch.mobile` (2026-07-23)

- **Task 1.9 complete:** real save screen — share → POST `/save` → AI processes → row in Supabase → result on screen. All five states (loading, success, error, retry, done) verified on device 2026-07-23. This is the core value loop working end to end.
- **Task 1.10 partially complete:** `models/item.dart` and `saveItem()` built. The three read/delete functions are deliberately deferred to Phase 2 (see the deferral note in `TASKS.md` 1.10).

**Not started yet (in order of what's next):**
- Phase 1 Definition of Done still has unverified items: save latency hasn't been measured, a TikTok/IG URL hasn't been saved *from the phone* (only via the backend directly in 1.7), sharing hasn't been tested from a real source app's share sheet (only simulated via `adb am start`), and the "10+ real items" bar isn't met yet.
- Phase 2 task 2.1: `GET /items`, `GET /search`, `DELETE /items/{id}` on the backend — the DB functions already exist (§2.8), they just need routes.

**Notably not yet built despite being "done" in the backend:** `routes/items.py`, `routes/search.py` — the DB functions exist (§2.8) but nothing calls them. That's correctly scoped for Phase 2, not a bug.

The next step: **close out Phase 1's Definition of Done by actually using the app** — share from a real TikTok/Chrome share sheet rather than `adb`, confirm graceful degradation on a TikTok URL, and build up 10+ saved items. That's dogfooding, not coding, and it's where real bugs surface. Then Phase 2 task 2.1 (the read endpoints) begins.
