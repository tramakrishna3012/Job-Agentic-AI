# Architecture

## 1. Component Diagram (text)
```
CLI (jaa.py)
  -> TailorEngine   (OpenAI API call, strict prompt)
  -> ResumeRenderer (Jinja2 HTML template -> WeasyPrint PDF)
  -> DriveClient    (Google Drive API, drive.file scope)
  -> Tracker        (SQLite: applications table)
  -> Notifier       (Twilio WhatsApp API)
```
All components are plain Python modules called sequentially from `jaa.py`. No message queue or async runtime is needed at this scale — one run = one job application, a few seconds of work.

## 2. Tech Stack & Why
- **Python 3.11+** — matches your "comfortable either way" answer, and is the natural fit for LLM calls, PDF rendering, and any future scraping/parsing work — one language for the whole project.
- **OpenAI API** (you already have a key) — `gpt-4o-mini` for cost efficiency on a task that's mostly reordering/rewording existing text, not open-ended generation. Upgrade to `gpt-4o` only if match quality disappoints in practice.
- **Jinja2 + WeasyPrint** — HTML template gives full control over ATS-safe layout; WeasyPrint is a mature, dependency-light HTML→PDF converter with no external binary dependencies to fight with.
- **google-api-python-client + google-auth-oauthlib** — official Google SDKs, `drive.file` scope only (see security.md).
- **SQLite** (stdlib `sqlite3`) — zero setup, single file, plenty for single-user scale, and directly queryable later by the Phase 1 dashboard without a migration.
- **Twilio WhatsApp API** — fastest path to a working WhatsApp send for MVP; sandbox number for free-tier testing, upgrade to a paid sender later if needed.

## 3. Where It Runs
**Recommendation: run locally on your laptop for Phase 0/1.** Invoked manually, or via a simple shell alias/function.

Reasoning: the MVP is user-triggered (you paste a JD) — there's nothing for a server to do between runs, so paying for or maintaining a VM is pure overhead right now. A background service only earns its keep once there's an actual background loop to run.

Move to **GitHub Actions scheduled workflow** (free tier, minimum 15-min interval) once Phase 2 adds a monitor loop that needs to run without your laptop being open. Only reassess a dedicated VPS if you later add a hosted dashboard other people need to reach, or GitHub Actions' execution limits become a real bottleneck — unlikely at this scale.

## 4. Data Flow (single run)
1. You run `jaa.py` with company/role/JD file.
2. `TailorEngine` sends the resume JSON + JD to OpenAI, gets back tailored JSON + `fit_summary` + `match_score`.
3. `ResumeRenderer` fills the Jinja2 template; WeasyPrint outputs a PDF to a temp path.
4. `DriveClient` checks SQLite for an existing `file_id` for this company; if present, calls `update`, else creates the folder + calls `create`.
5. `Tracker` writes/updates the `applications` row (company, role, jd_hash, drive_file_id, drive_link, match_score, status, timestamps).
6. `Notifier` sends the WhatsApp template message via Twilio.

## 5. Environment Variables
```
OPENAI_API_KEY=
GOOGLE_OAUTH_CLIENT_SECRET_PATH=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=
YOUR_WHATSAPP_TO=
```
All loaded via `.env` (python-dotenv). `.env` is in `.gitignore` from the first commit — never committed.

## 6. Error Handling
- Each stage wrapped in try/except with a specific, stage-labeled failure message.
- On failure, no partial WhatsApp notification is sent — don't report success if a later stage failed.
- Retry with backoff (3 attempts) on OpenAI and Twilio calls only. Drive upload failures surface immediately rather than silently retrying, since a duplicate-folder mistake is more costly there than a delayed retry.

## 7. Logging
- Log stage transitions and timestamps only.
- Never log full resume content or full JD text (see security.md) — snippet/hash only.
- Log file stays local, never uploaded anywhere.

## 8. Phase 1 additions — Dashboard (API + frontend)
Phase 0 stays exactly as built. Phase 1 adds two new pieces on top, both reading the same `jaa.db` SQLite file the CLI already writes to — no data migration needed.

```
Next.js frontend (matches Stitch design)
  -> FastAPI backend (REST API over jaa.db)
       -> SQLite (jaa.db) — same file jaa.py already writes
```

**Backend: FastAPI**, not Flask, for this piece specifically — Phase 1 needs typed JSON responses for a React frontend to consume, and FastAPI's automatic request/response validation (Pydantic) plus auto-generated OpenAPI docs make the frontend integration faster to get right and easier to keep in sync as fields change. Flask remains fine for anything Phase 0-side; this isn't a project-wide switch.

**Frontend: Next.js (React)** — matches what Stitch exports, so your existing design work carries over directly instead of being rebuilt from scratch.

**Where it runs:** still local, still your machine, still zero paid infra. Build the Next.js app (`next build`) and have FastAPI serve both the API routes and the built frontend from one process on one port. One thing to run, one thing to secure, no separate frontend server to manage.

**Auth:** this is now a real web app, not a CLI script, so `security.md`'s "no unauthenticated dashboard" rule applies. Simplest adequate approach for a single-user tool: a shared secret token in `.env` (`DASHBOARD_TOKEN`), checked by FastAPI middleware on every route, entered once in the frontend and stored in an httpOnly cookie. No user accounts, no password reset flow, no OAuth — that's over-engineering for an audience of one. If you never expose this beyond `localhost`, the token is a second layer, not the only one; if you ever tunnel it out (e.g. to check from your phone), the token becomes load-bearing, so treat `DASHBOARD_TOKEN` with the same care as the other secrets in `.env`.

**API surface (v1):**
- `GET /api/applications` — list all applications, supports `?status=` filter
- `GET /api/applications/{id}` — single application detail
- `PATCH /api/applications/{id}` — update status only (Applied/Interview/Rejected/Offer) — the one write endpoint Phase 1 needs
- `GET /api/stats` — counts by status, for any summary cards in the design

No endpoint touches Drive, OpenAI/Gemini, or Twilio — the dashboard only ever reads/updates `jaa.db`. That keeps the blast radius of a frontend bug small.
