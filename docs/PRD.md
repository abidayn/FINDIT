# Product Requirements Document (PRD)

**Project codename:** FINDIT (working name: FINDIT)
**Author:** Biday
**Last updated:** June 26, 2026
**Status:** Draft — MVP scope locked, document in active iteration

---

## 1. Overview

### 1.1 What is this product?

A mobile app (Android-first) that lets users save links from any platform — TikTok, Instagram Reels, YouTube, articles, anywhere — into one organized place. The app uses AI to automatically generate a title, summary, and folder for every saved item, so users can find what they saved later using natural language search.

In one sentence: **"Share any link to this app, and it auto-organizes it so you can actually find it again."**

### 1.2 Why does this exist?

People save content all the time and never go back to it. The native "Saved" features in TikTok, Instagram, and YouTube are flat lists with zero search or organization. Users end up with hundreds of saved items they can't find when they need them. Existing apps that try to solve this (PickTok, TikReel, Sftir, ReelRecall) either rely on manual folders or focus narrowly on transcript search — none nail the "auto-organize at the moment of capture" experience.

### 1.3 Project context

This is a **learning project first, product second.** The primary goal is for the builder (Biday) to learn end-to-end product development across the modern AI stack: mobile development, backend APIs, LLM integration, content processing, and deployment. A working product with real users is a bonus outcome, not the success criteria.

---

## 2. Problem Statement

### 2.1 The core problem

Modern short-form content is dense and useful, but the platforms hosting it treat "Save" as a dead-end feature. Users save items in good faith — intending to learn from them, revisit them, or apply them — but the saved content disappears into an unsearchable, unorganized list. The save action becomes performative; the value of the saved content is never realized.

This happens across three dimensions:

1. **Capture is fragmented.** A user might save a self-growth video on TikTok, another on Instagram, and an article on a browser. Three separate locations, no unified view.
2. **Organization requires effort that never happens.** Existing apps offer manual folders, but users don't categorize at the moment of saving — and they never go back to organize later.
3. **Retrieval is broken.** Even if a user remembers they saved something, finding it requires manually scrolling through a chronological list with no search.

### 2.2 Why now?

Short-form content consumption is at an all-time high. The volume of "saved-but-forgotten" content per user has grown faster than the tools to manage it. Meanwhile, LLMs have made it practical and cheap to auto-summarize and auto-classify content at scale — meaning the technical solution that was impossible 3 years ago is now trivially buildable.

---

## 3. Target User

### 3.1 Primary persona: The Intentional Saver

- Age 18–28, mobile-first, heavy short-form content consumer
- Saves content with genuine intent to revisit (recipes, tutorials, advice, inspiration)
- Has tried Apple Notes, Telegram Saved Messages, Notion, or screenshots as ad-hoc systems
- Mildly frustrated with current state but not actively searching for a solution (the friction is normalized)
- Comfortable installing a new app if it solves a real pain

### 3.2 Anti-persona (who this is NOT for)

- Casual scrollers who never save anything
- Professional researchers needing deep PKM features (use Obsidian/Notion)
- Users who want a social feed or sharing layer
- Power users who already have a working system

### 3.3 Geographic focus

Indonesia first (builder's network, Android-dominant market), but the product is language-agnostic and globally relevant. No Indonesia-specific features at MVP.

---

## 4. Goals & Non-Goals

### 4.1 Goals (in priority order)

1. **Learning:** Build hands-on experience across React Native, FastAPI, Supabase, LLM APIs, and content-processing pipelines.
2. **Self-use:** Builder uses the app daily for own saved content within 4 weeks of build start.
3. **Working MVP:** End-to-end flow (share → process → save → search) functioning reliably on Android.
4. **Resume artifact:** A real, deployed project to discuss in internship interviews with concrete technical decisions to defend.
5. **Optional: real users.** If the MVP works well, expand to a small group of early users (friends, network) to gather feedback.

### 4.2 Non-goals (explicitly out of scope for this iteration)

- Monetization, pricing, or business model
- iOS support (Android-first; iOS only if/when ready to pay Apple Developer fee)
- Web app, browser extension, or desktop client
- Multi-user features (sharing, collaboration, public collections)
- Social/feed features
- Onboarding flows beyond minimum viable (no tutorial screens, no marketing pages)
- Analytics, A/B testing, or user tracking infrastructure
- App Store / Play Store launch
- Marketing, growth, or user acquisition strategy

---

## 5. User Stories

### 5.1 Core stories (MVP)

**As a user:**

- I want to share a link from any app to this app, so I don't need to switch contexts when saving.
- I want the app to automatically figure out what the content is about, so I don't have to type anything.
- I want my saved items to be grouped by topic, so I can browse what I've collected.
- I want to search using normal words like "that video about morning routines," so I don't need to remember exact titles.
- I want to tap a saved item to open the original link, so I can rewatch or reread the full content.

### 5.2 Out-of-scope stories (not for MVP)

- I want to save screenshots and have OCR extract the text.
- I want a weekly digest of what I saved.
- I want to add my own notes to saved items.
- I want to share my collections with friends.
- I want to export my data to Notion.

---

## 6. Functional Requirements (MVP Scope)

### 6.1 MUST HAVE (without these, the app has no value)

| ID | Requirement | Why |
|----|-------------|-----|
| F1 | App appears in Android share sheet when user taps "Share" in TikTok, Instagram, YouTube, Chrome, or any app that shares URLs | This is the core capture mechanism |
| F2 | App accepts a shared URL and sends it to the backend | Foundation of the save flow |
| F3 | Backend fetches readable content from the URL (article text or video transcript where available) | AI needs content to process |
| F4 | Backend uses LLM to generate: short title (max 7 words), 1–2 sentence summary, single folder category | This is the "auto-organize" value prop |
| F5 | Saved item is persisted in the database with: URL, title, summary, folder, timestamp, source platform | Required to retrieve later |
| F6 | Home screen displays all saved items as cards, grouped or filterable by folder | The primary view |
| F7 | Tapping a saved item opens the original URL in the source app or browser | Items must remain useful |
| F8 | Search bar performs text search across title and summary fields | Minimum viable retrieval |
| F9 | App handles errors gracefully: URL invalid, content can't be fetched, AI call fails | Real-world robustness |

### 6.2 NICE TO HAVE (post-MVP)

- Semantic / RAG-based search (find items by meaning, not just keywords)
- Manual folder editing or custom tags
- Screenshot support with OCR
- Per-item notes from the user
- Weekly digest notification
- Item preview thumbnails fetched from source URL
- Multi-device sync
- Dark mode
- Bulk import from existing TikTok/IG saved lists (if technically feasible)

### 6.3 EXPLICITLY OUT OF SCOPE

- iOS app
- Web app
- User accounts beyond single-device storage (auth via Supabase added only when needed)
- Any social or sharing features
- Any feature requiring server-side video download or transcription of TikTok/IG (not legally or technically feasible at this stage)

---

## 7. Non-Functional Requirements

### 7.1 Performance

- Save flow (share → confirmation) should complete in under 5 seconds for articles and YouTube videos
- Home screen should load in under 1 second after app open
- Search should return results in under 500ms for libraries up to 500 items

### 7.2 Cost

- Total monthly running cost: $0 during development and personal use
- Acceptable cost ceiling if opened to early users: under $10/month
- All services used must have free tiers sufficient for the development phase

### 7.3 Reliability

- App should not crash on malformed URLs or unreachable websites
- Failed saves should be retryable
- No data loss on app restart

### 7.4 Privacy

- All saved data belongs to the user; no telemetry, no third-party analytics
- API keys never exposed in client code
- No sharing of user data with third parties beyond the AI provider for the processing call itself

---

## 8. AI Behavior Requirements

### 8.1 What the AI does

The AI has three jobs:

1. **Generate a title** — concise, descriptive, max 7 words
2. **Generate a summary** — 1–2 sentences capturing the core value/topic
3. **Classify into a folder** — pick one from a predefined list, or assign "Other"

### 8.2 Predefined folder taxonomy (v1)

To keep classification stable and prevent folder sprawl, the v1 folder list is fixed:

- Self Growth
- Productivity
- Tech & Coding
- Finance
- Cooking & Food
- Fitness & Health
- Entertainment
- Learning
- Other

This list will be revisited after 2 weeks of self-use based on what content actually gets saved.

### 8.3 AI failure handling

- If AI returns invalid JSON: retry once, then save with fallback values ("Untitled", "No summary available", "Other")
- If AI is unreachable: save raw URL with placeholder metadata; flag for re-processing later
- The item must save successfully even if AI processing fails — the URL itself is the minimum viable data

Full AI specification is in `AI_FEATURE_SPEC.md`.

---

## 9. Content Source Handling

### 9.1 What content can be fetched per platform

| Platform | Content available | Quality of AI output |
|----------|-------------------|----------------------|
| Articles / blogs | Full text via Jina Reader | High |
| YouTube | Title + description + tags via Data API v3 | Medium-High |
| Twitter / X | Tweet text + metadata | Medium |
| TikTok | URL + thumbnail + caption (if public) | Low |
| Instagram Reels | URL + minimal metadata | Low |

### 9.2 Handling low-information sources (TikTok / IG)

For platforms where content isn't accessible, the app degrades gracefully:

- Saves the URL with whatever metadata is available (account name, hashtags, caption text)
- Auto-classifies using available signals
- Optional: prompts the user to add a one-line note at save time (post-MVP)

---

## 10. Success Metrics

Because this is a learning project with no business goals, success is measured in learning and usability terms, not growth metrics.

### 10.1 Build-phase success

- All Phase 0–3 milestones completed (see `TASKS.md`)
- App runs reliably on builder's own Android device
- Builder can explain every component of the stack in an interview without referring to code

### 10.2 Usage-phase success

- Builder personally uses the app at least 3 times per week for 2 consecutive weeks
- Builder finds and revisits at least 5 saved items via the app's search/browse features
- App handles 50+ saved items without performance degradation

### 10.3 Optional early-user success

- 5–10 friends/network members install and try the app
- At least 2 of them use it more than once unprompted
- Qualitative feedback collected from all early users

---

## 11. Constraints & Assumptions

### 11.1 Constraints

- **Budget:** $0 monthly during build phase. Tooling and services must have viable free tiers.
- **Skill level:** First serious project. Builder is technically savvy but has no industry experience. Stack choices must be learnable, well-documented, and have strong community support.
- **Time:** Built during summer break, in parallel with internship search and other commitments. Realistic build window: 4–6 weeks for MVP.
- **Platform:** Android only. iOS deferred indefinitely.
- **No team:** Solo project. No designer, no co-developer.

### 11.2 Assumptions

- The Android share sheet integration is achievable with publicly available React Native libraries (e.g., `expo-share-intent`).
- Jina Reader API remains free and reliable for article extraction.
- YouTube Data API v3 free tier (10,000 units/day) is sufficient for personal volume.
- Gemini 3 Flash free tier (10 RPM, 1,500 RPD as of mid-2026) is sufficient for development volume. Limits may shift; verify current quotas in Google AI Studio before launch.
- Supabase free tier (500MB DB, 50K monthly active users) is more than enough.

### 11.3 Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Share extension is harder than expected on Android | Medium | Build a manual "paste URL" fallback first; share extension second |
| TikTok/IG content extraction yields too little data for useful AI output | High | Already accepted as a known limitation; degrade gracefully |
| AI hallucinates folder/summary | Medium | Predefined folder list prevents drift; fallback values prevent breakage |
| Free tiers change or are removed | Low | Document migration paths in `ARCHITECTURE.md` |
| Builder loses motivation / scope creeps | High | Strict adherence to MVP scope; nice-to-haves explicitly deferred |

---

## 12. Open Questions

These are decisions deferred until MVP is functional:

- Should the app allow editing AI-generated titles and folders, or treat them as read-only?
- Should there be a "review queue" for newly saved items before they enter the main library?
- How should duplicate URLs be handled — reject, merge, or save again?
- Should the search bar default to keyword search or upgrade to semantic search after a threshold (e.g., 50 items)?
- Is the predefined folder taxonomy too restrictive? Should users be able to create custom folders?

---

## 13. Out-of-Scope Document References

- Technical architecture and stack details → `ARCHITECTURE.md`
- AI feature behavior, prompts, and fallback logic → `AI_FEATURE_SPEC.md`
- Phased build plan and task breakdown → `TASKS.md`
- Working agreement with Claude Code → `CLAUDE.md`

---

## 14. Appendix: Competitive Landscape Summary

| Product | What it does | Gap exploited |
|---------|-------------|---------------|
| TikTok / IG / YouTube native | Flat saved lists, no search | Everything |
| PickTok, TikReel | Manual color-coded folders | No AI, requires user effort |
| Sftir, ReelRecall | AI transcription + spoken-word search | Transcription-only; no auto-organize at capture |
| Notion / Apple Notes | General notes apps | Too much friction; no share integration |
| Raindrop, Pocket | Bookmark managers | No video support, no AI organization |
| Showcase | Multi-platform bookmarking | No AI, no smart organization |

**Differentiator for this project:** Zero-friction capture (via share sheet) + automatic organization at the moment of saving + natural language retrieval. No other product combines all three for a B2C audience.

---

*End of PRD v1.0*
