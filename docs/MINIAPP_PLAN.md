# Finance Bot → Telegram Mini App: Migration Plan


## Context

The bot today is a chat-driven aiogram 3 app: inline-keyboard menus, FSM states, text/voice input, LLM (OpenRouter) categorisation, local Whisper, SQLite via aiosqlite, reports by month, category CRUD, transaction delete by text/voice. About 3.5k LOC. Every flow is a multi-message conversation, which is slow and clumsy for a finance tracker.

Goal: make a **Telegram Mini App** (web UI opened inside Telegram) the primary interface, and move all logic behind an HTTP API. Design first, then migrate backend and DB.

Decisions already made: **React + Vite + TS** frontend, **FastAPI + PostgreSQL** backend (reuse existing Python services), bot becomes **launcher only**, deploy with **Docker on a VPS, no domain**.

## Open constraint: HTTPS without a domain

Telegram requires an HTTPS URL for Mini Apps. Without owning a domain, use one of (decide in T1, default first):
1. **`<ip-dashed>.sslip.io`** (e.g. `203-0-113-5.sslip.io`) — free wildcard DNS resolving to the VPS IP; Caddy obtains a real Let's Encrypt cert automatically. Zero setup, stable as long as the IP is static. **Default.**
2. **DuckDNS** free subdomain — survives an IP change.
3. Cloudflare quick tunnel — URL changes on each restart; dev only.

The public hostname is a single env var (`PUBLIC_HOST`) so switching to a real domain later is a one-line change.

---

## 1. Target architecture

```
Telegram client ── opens ──▶ https://PUBLIC_HOST  (Mini App, React SPA)
                                   │
                              Caddy (auto-HTTPS)
                   ┌───────────────┴───────────────┐
              /  → static SPA                 /api/* → FastAPI (uvicorn)
                                                   │
                                     services (reused) ── PostgreSQL
                                          │
                                LLM (OpenRouter) · Whisper (local)

aiogram bot (separate container): /start → button "Open app" (WebAppInfo),
sets chat menu button. No business logic.
```

Containers (docker-compose): `caddy`, `api`, `bot`, `db` (postgres:16), volume for pgdata + whisper model cache. Frontend is built in a multi-stage Docker image and served by Caddy.

### Repo layout (monorepo)

```
backend/
  app/
    main.py            # FastAPI app, lifespan, CORS off (same origin)
    core/config.py     # pydantic-settings (replaces config/)
    core/security.py   # initData validation, auth dependency
    api/v1/            # routers: me, categories, transactions, reports, ai
    schemas/           # pydantic request/response models
    services/          # moved+adapted from src/services (transaction, llm, whisper, date_parser)
    llm/               # moved from src/llm (prompts, tools)
    db/                # SQLAlchemy 2.0 async models, session, repositories
  alembic/
  scripts/migrate_sqlite_to_pg.py
  tests/
bot/                   # tiny aiogram launcher (start.py only)
frontend/
  src/{app,pages,components,features,api,lib,i18n}
docker-compose.yml, Caddyfile, .env.example, docs/
```
The old `src/` tree is removed at the end (T11) once parity is verified.

## 2. Auth design (critical)

- Mini App sends `Authorization: tma <window.Telegram.WebApp.initData>` on every request.
- FastAPI dependency validates the HMAC-SHA256 signature with the bot token, rejects `auth_date` older than 24 h (configurable), and upserts the user by `telegram_id` (mirrors current `get_or_create_user`).
- No sessions/JWT in v1 — stateless per-request validation is simple and safe. Never trust `user_id` from body/query.
- Reuse `src/security/rate_limiter.py` logic as a per-user FastAPI dependency (esp. for `/ai/*` and `/voice`), and `validators.py` for input sanitising.

## 3. Data model (PostgreSQL)

Same three tables, hardened:

| Table | Changes vs. SQLite |
|---|---|
| `users` | `telegram_id BIGINT UNIQUE` (SQLite INTEGER is fine, PG needs BIGINT), `language_code`, `currency` default `UZS`, `created_at timestamptz` |
| `categories` | + `icon`/`emoji`, `color`, `is_archived`; unique `(user_id, name, type)` kept |
| `transactions` | `amount NUMERIC(14,2)` (was REAL), `occurred_at timestamptz` (user-editable date; `created_at` kept separate), keep `raw_text`, `description`; indexes `(user_id, occurred_at)`; FK `category_id ON DELETE RESTRICT` kept |

Alembic for all schema changes. The 6-month auto-cleanup becomes a scheduled task in the API (APScheduler) — confirm whether to keep it (see Risks).

Migration script `migrate_sqlite_to_pg.py`: read `data/finance_bot.db`, insert users→categories→transactions preserving IDs/relationships, then reset PG sequences; idempotent and with a dry-run count comparison.

## 4. API design (`/api/v1`, JSON)

| Method & path | Replaces bot flow |
|---|---|
| `GET /me` | `/start` user bootstrap |
| `GET/POST /categories`, `PATCH/DELETE /categories/{id}` | categories handlers (reject delete when in use → 409, as today) |
| `GET /transactions?from&to&type&category_id&q&cursor` | list + implicit "find to delete" |
| `POST /transactions` | manual add (with duplicate protection from `TransactionService`) |
| `PATCH/DELETE /transactions/{id}` | edit (new) / delete by id (no more text/voice search) |
| `POST /ai/parse` `{text}` → draft `{amount,type,category,description,date}` | `process_transaction_with_llm`; **returns a draft, does not save** — user confirms in UI |
| `POST /ai/transcribe` (multipart audio) → `{text}` | voice handlers; feed result into `/ai/parse` |
| `GET /reports/summary?from&to` , `GET /reports/by-category`, `GET /reports/monthly` | reports handler + `date_parser` |

Errors: consistent `{code, message}`; messages localised on the client via `code` (moves `lexicon_ru.py` to frontend i18n; RU first, UZ/EN later).

## 5. Frontend / UX design

- **Stack:** React 18, Vite, TypeScript, React Router, TanStack Query (cache + optimistic updates), Tailwind + shadcn/ui, Recharts, `@telegram-apps/sdk-react` (theme params → CSS variables so it follows Telegram light/dark), i18next.
- **Screens (bottom tab bar):**
  1. **Home** — month selector, balance / income / expense cards, recent transactions, floating **＋** button.
  2. **Add** (bottom sheet) — income/expense toggle, amount keypad, category chips, date, note; **"Magic" input**: type a sentence or hold the mic → `/ai/parse` → prefilled form → Confirm. Telegram `MainButton` = Save, `BackButton` for navigation, haptics on success.
  3. **History** — grouped by day, filters, search, swipe-to-delete with confirm.
  4. **Reports** — month/range picker, donut by category, income-vs-expense bars, top categories; tap slice → filtered history.
  5. **Categories** — two tabs (income/expense), add/edit/delete with emoji+colour.
- **Voice in a WebView:** `MediaRecorder` (webm/opus on Android, mp4/aac on iOS) → upload → server ffmpeg normalises → Whisper. Must be tested on iOS Telegram; text input is always the fallback if mic permission is denied.
- Skeleton loaders, offline/error states, `Telegram.WebApp.ready()/expand()`, safe-area insets.

## 6. Task breakdown (in order)

**Phase A — Design (no production code)**
- **T0** Copy this plan to `docs/MINIAPP_PLAN.md`; supersede `docs/ARCHITECTURE.md`/`roadmap.md` sections.
- **T1** Fix hosting details: choose sslip.io vs DuckDNS, create bot in BotFather (`/newapp` or menu button), collect env vars list.
- **T2** Write OpenAPI-first contract (`docs/openapi.yaml` or generated stubs) covering §4 and get sign-off.
- **T3** UI wireframes for the 5 screens (Figma or low-fi in docs); confirm flows, esp. AI-draft confirm step.

**Phase B — Backend + DB migration**
- **T4** Scaffold `backend/` (FastAPI, pydantic-settings, SQLAlchemy async, Alembic, pytest, ruff); Postgres in docker-compose.
- **T5** DB layer: models + first Alembic migration (§3) + repositories replacing `src/db/database.py`.
- **T6** Auth: initData validation dependency + user upsert + rate limiter dependency; unit tests with a signed fixture.
- **T7** Port services: `TransactionService` (validation, duplicate check), category logic, `date_parser`, `formatting`; expose categories/transactions/reports routers; tests.
- **T8** AI endpoints: adapt `llm_service` + `prompts`/`tools` to return a draft instead of writing; `whisper_service` behind `/ai/transcribe` (run in threadpool, size/duration limits, temp-file cleanup).
- **T9** `migrate_sqlite_to_pg.py` + verification (row counts, sum of amounts per user/month equal to SQLite).

**Phase C — Frontend**
- **T10a** Scaffold Vite app, Telegram SDK, theming, i18n, API client with `tma` auth header, TanStack Query.
- **T10b** Categories screen → **T10c** Add flow (manual) → **T10d** History → **T10e** Reports → **T10f** Magic/voice input.

**Phase D — Bot, infra, cutover**
- **T11a** Reduce bot to `bot/` launcher (`/start`, WebApp button, menu button); delete old handlers/keyboards/states/lexicon.
- **T11b** Dockerfiles (api, bot, frontend build), `docker-compose.yml`, `Caddyfile`, `.env.example`; healthchecks hit `/api/health` and `pg_isready` (current healthcheck checks a wrong DB filename — `finance.db` vs `finance_bot.db`).
- **T12** Deploy to VPS, run data migration, smoke test on iOS + Android + Desktop Telegram.
- **T13** Remove legacy `src/`, `requirements.txt` split, update README/DEPLOYMENT; tag release.

## 7. Risks / decisions to confirm during T1–T3

- **Whisper on the VPS:** local `turbo` model needs ~1–2 GB RAM (compose currently limits to 1 GB) and is slow on CPU. Options: keep local with bigger VPS, use `small` model, or switch to a hosted STT API. Decide before T8.
- **Auto-delete after 6 months** is destructive for a finance app; default plan keeps it configurable and **off** unless you want it retained.
- **Multi-currency:** app is UZS-only today; schema keeps a `currency` column for later but v1 UI is UZS.
- **Existing users' history** is preserved by mapping on `telegram_id`.
- Repo has uncommitted work (date parser, formatting, reports/transactions edits, requirements moves) — commit or stash before T4 so the port starts from a clean base.

## 8. Verification

- Backend: `pytest` (auth signature valid/invalid/expired, transaction rules, duplicate window, category delete conflict, report totals); `alembic upgrade head` on empty DB; migration script parity check.
- Contract: frontend types generated from OpenAPI; CI fails on drift.
- Frontend: `tsc`, `vitest` for the amount keypad/parsers, manual pass through all 5 screens in Telegram Desktop (light/dark) and one iOS + one Android device (voice included).
- End-to-end: `docker compose up` on the VPS, open bot → Open app → add via text, via voice, delete, view report; compare totals against the migrated SQLite data.
