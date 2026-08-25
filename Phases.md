# Build Phases

## Phase 0 — MVP (target: 1 weekend, ~10–15 hrs)
**Scope:** CLI tool, single command, tailor → PDF → Drive → WhatsApp → SQLite log.

**Acceptance criteria:**
- [ ] Paste a real JD, get a tailored PDF matching JD keywords without fabricated content
- [ ] File lands in the correct Drive folder with the correct name
- [ ] WhatsApp message arrives within 60s
- [ ] Row appears in the SQLite `applications` table

**Exit condition to move to Phase 1:** you've run it on 5+ real applications and trust the output enough to actually send it.

## Phase 1 — Tracking Dashboard (target: 1.5–2 weeks part-time)
**Scope:** FastAPI backend (read/write over the existing `jaa.db`) + Next.js frontend matching your Stitch design. See `architecture.md` section 8 and `design.md` for the API contract and layout.

**Acceptance criteria:**
- [ ] See all applications in one table, filterable by status
- [ ] Mark status manually (Applied / Interview / Rejected / Offer) via the one PATCH endpoint
- [ ] Follow-up reminder surfaced after N days with no status change
- [ ] Dashboard requires the shared `DASHBOARD_TOKEN` to load — no unauthenticated access
- [ ] Runs as a single local process (FastAPI serving the built Next.js app) on one port

## Phase 2 — Faster Discovery (target: 1–2 weeks, only after Phase 0/1 prove valuable)
**Scope:** read-only, anonymous/public sources only — RSS feeds, your own Gmail job-alert emails (via Gmail API — this is your inbox, not scraping a platform), public company career-page diffs.

**Explicitly excluded:** logged-in scraping of LinkedIn/Naukri/Wellfound sessions.

**Acceptance criteria:**
- [ ] New matching postings trigger the Phase 0 pipeline automatically
- [ ] Failure alerting: if zero new postings surface in 48h, you get notified something's likely broken

## Phase 3 — Outreach Drafts (target: 1 week)
**Scope:** given a company + role, draft one recruiter/hiring-manager message and one "current employee" referral-ask message. Drafts only — you review, personalize, and send manually.

**Acceptance criteria:**
- [ ] Draft references specific, real details from the JD/company — no generic filler
- [ ] Nothing is ever sent automatically — draft-only, always

## Phase 4 — Re-evaluate scope (a decision point, not a build phase)
Before building anything resembling auto-apply or platform automation: review Phase 0–3 usage data and decide if it's still worth the account-ban risk. Default answer, unless the data strongly says otherwise: **no.**
