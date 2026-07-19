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
app = FastAPI(title="Stash API")
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

**Mirrors to:** `mobile/lib/models/item.dart` is supposed to mirror `Item` on the Dart side (per `ARCHITECTURE.md` §3.1). That file doesn't exist yet — it's part of Phase 1 task 1.10, not yet built.

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

Everything here is early — Phase 0 scaffold only, no real features yet. The app currently does one thing: show the text "Stash" on screen.

### 3.1 `pubspec.yaml` — Flutter's `package.json`

Declares the SDK version (`^3.12.2`), the four real dependencies, and dev dependencies. Worth knowing what each dependency is *for*, since none of them are wired up yet except implicitly via the scaffold:

| Package | What it's for | Status |
|---|---|---|
| `go_router` | Declarative routing between screens | Wired up in `main.dart`, one route only (`/`) |
| `supabase_flutter` | Talk to Supabase directly from the app (for reads, per `ARCHITECTURE.md` open question §13) | Installed, **not used yet** |
| `receive_sharing_intent` | Receive shared URLs from other apps (the core feature — Phase 1 task 1.8) | Installed, **not used yet** |
| `cupertino_icons` | iOS-style icon font, comes with every Flutter template | Unused, harmless default |
| `flutter_lints` | Recommended lint rules (dev-only, not shipped in the app) | Active via `analysis_options.yaml` |

**Current-state gap:** the whole point of installing `receive_sharing_intent` is Phase 1 task 1.8 (share sheet integration) — that's the next real feature to build after confirming `flutter run` works end-to-end.

### 3.2 `lib/main.dart` — entry point + router

```dart
void main() { runApp(const StashApp()); }

final _router = GoRouter(routes: [
  GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
]);

class StashApp extends StatelessWidget {
  Widget build(BuildContext context) {
    return MaterialApp.router(title: 'Stash', routerConfig: _router);
  }
}
```

Mirrors `backend/main.py`'s role exactly: wire things together, no business logic. One route (`/` → `HomeScreen`) exists so far. Every future screen (`save_screen.dart`, `search_screen.dart`, etc., per `ARCHITECTURE.md` §5) gets added as another `GoRoute` entry here.

### 3.3 `lib/screens/home_screen.dart` — the only screen that exists

```dart
class HomeScreen extends StatelessWidget {
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: Text('Stash', style: TextStyle(fontSize: 24))),
    );
  }
}
```

`StatelessWidget` because it currently has no state to manage — it's a static label. It'll become `StatefulWidget` (or use a `FutureBuilder`) once it starts fetching items from the backend (Phase 2 task 2.6), because rendering a list that depends on an async network call needs to react to loading/loaded/error states.

**Current-state gap:** Phase 0 task 0.8 (`fetchHealth()` calling the Railway `/health` endpoint and displaying it) isn't done yet — this is the very next milestone: proving the phone and backend can actually talk. There's no `lib/services/api_client.dart` yet.

### 3.4 `test/widget_test.dart` — the one test that exists

```dart
testWidgets('Home screen shows the app name', (tester) async {
  await tester.pumpWidget(const StashApp());
  expect(find.text('Stash'), findsOneWidget);
});
```

A widget test: builds the widget tree in memory (no real device needed) and asserts the text "Stash" appears once. This is Flutter's default scaffold test, still accurate since the home screen still just renders that text. Run it with `flutter test`. As screens gain real logic, more tests like this get added — but per `CLAUDE.md`, full test infra is explicitly post-MVP; this is the "manual curl command" equivalent for mobile.

### 3.5 `android/app/build.gradle.kts` — Android build config

The file we just edited together. Key lines:
- `namespace`/`applicationId = "com.stash.mobile"` — the app's unique Android package ID.
- `compileSdk = 37` — **just changed from the Flutter-default `36`** because the `receive_sharing_intent` plugin requires SDK 37. This was the exact build failure we debugged.
- `minSdk`/`targetSdk = flutter.minSdkVersion/.targetSdkVersion` — still deferring to Flutter's defaults (unlike `compileSdk`, these didn't need overriding).
- `signingConfig = signingConfigs.getByName("debug")` under `release` — release builds currently sign with the debug key, which is fine for personal use (`flutter run --release`) but **would need a real keystore before any Play Store submission** (`ARCHITECTURE.md` §7.2, explicitly deferred).

### 3.6 `android/app/src/main/AndroidManifest.xml` — Android's permission/entry manifest

Declares `MainActivity` as the launcher activity, sets the launch theme, and — important for later — has a `<queries>` block for `android.intent.action.PROCESS_TEXT`. That's unrelated to our share-intent feature; it's a default Flutter includes so the engine's built-in text-selection plugin can query other apps. **Phase 1 task 1.8 will add a new `<intent-filter>` here** for `ACTION_SEND` with `text/plain` — that's the actual line that makes "Stash" appear in Android's share sheet when you tap "Share" from TikTok. Doesn't exist yet.

### 3.7 Files not worth deep-diving, but here's why they exist

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
| `README.md` | Repo landing page. **Currently stale** — still says "React Native + Expo" under Stack; should be updated to Flutter now that the pivot (commit `25c7aa7`) happened. Worth a quick fix. |
| `.gitignore` | Covers `.env`, `venv/`, `__pycache__/`, `.dart_tool/`, `build/`, `android/local.properties`, etc. — confirmed before any commit per Core Rule 7. |
| `CLAUDE.md` | Working agreement — not app code, but the rules this guide itself was written under (learning-first framing, phase discipline, architectural rules referenced throughout this doc). |

---

## 6. Where we actually are right now (Phase 0 → Phase 1 boundary)

Cross-referencing `TASKS.md`'s checkboxes with what's on disk:

**Done and verified:**
- Supabase project + schema + one test row (0.2)
- Backend fully scaffolded and all of Phase 1's backend work — schemas, fetcher, AI service, database service, `/save` endpoint — built and manually tested (1.1–1.7)
- Railway deployment live, `/health` and `/save` confirmed public (0.6)
- Flutter project scaffolded, `compileSdk` bumped to 37, app installs and runs on a real device (0.7, just completed this session)

**Not started yet (in order of what's next):**
- 0.7 remainder: config-injection decision for API URL / Supabase keys (`--dart-define` vs bundled file) — not decided yet
- 0.8: `api_client.dart` + calling `/health` from the home screen — the actual mobile↔backend round-trip, still unverified
- 1.8–1.10: share intent integration, save screen, full API client — the actual core feature

**Notably not yet built despite being "done" in the backend:** `routes/items.py`, `routes/search.py` — the DB functions exist (§2.8) but nothing calls them. That's correctly scoped for Phase 2, not a bug.

The single most important next step, per `TASKS.md`'s own ordering: **0.8, the hello-world round-trip** (phone calls Railway, displays "status: ok"). Everything after that — share intent, save screen — depends on the API client this step creates.
