# Design — Functional & UX

> Note: I couldn't pull the actual Stitch mockup (the link needs an authorized session and the tool call came back unapproved). This doc reflects our conversation so far. If your Stitch screens differ — especially on the Phase 1 dashboard layout — send screenshots/exports and I'll reconcile this file.

## 1. Master Resume — Source of Truth
Store your resume as structured JSON/YAML, not just a PDF, so the tailoring step edits *content*, not formatting:
```yaml
name: ...
contact: {email, phone, linkedin, portfolio}
summary: ...
experience:
  - company: ...
    title: ...
    dates: ...
    bullets: [...]
education: [...]
skills: [...]
projects: [...]
```
This structured source is what makes "reorder/rephrase, don't invent" enforceable — the LLM only ever selects, reorders, and rewords bullets that already exist here. It never writes new facts.

## 2. Tailoring Prompt Contract
The system prompt must enforce, strictly:
- Only use facts present in the source resume JSON.
- May reorder sections/bullets and rephrase wording to mirror the JD's terminology.
- Must not add skills, tools, titles, or metrics not present in the source.
- Output: same JSON schema back, reordered/reworded, plus a `fit_summary` (one sentence) and `match_score` (0–100, rough JD-keyword overlap).

## 3. Resume Rendering (ATS-safe rules)
- Single column, no tables, no text boxes, no header/footer contact info (ATS parsers frequently drop header/footer content).
- Standard section headers: Summary, Experience, Education, Skills, Projects.
- Standard fonts (Arial/Calibri-equivalent), no icons for contact details.
- Keep the plain structured text easily derivable from the same source, so you can sanity-check ATS re-parseability independent of the PDF.

## 4. Drive Folder Convention
```
/JobApplications/
  /Acme Corp/
    YourName.pdf
  /Beta Inc/
    YourName.pdf
```
Re-running for the same company **updates** the existing Drive file (using the file ID stored in SQLite) rather than creating a new one — no `YourName(1).pdf` duplicates.

## 5. WhatsApp Message Template
```
✅ Resume tailored: {Role} @ {Company}
Match score: {score}/100
{fit_summary}
📄 {drive_link}
```

## 6. CLI UX (MVP)
```
python jaa.py --company "Acme Corp" --role "Backend Engineer" --jd jd.txt
```
Prints progress inline (tailoring... rendering... uploading... notifying...) so any failure is immediately locatable to a stage.

## 7. Phase 1 Dashboard

> Still pending: I haven't been able to pull your actual Stitch mockup (Drive access keeps failing on my end). Everything below is the data contract the frontend needs to satisfy, regardless of visual design — export your Stitch screens/code when you can and I'll reconcile the visual details against this.

**Minimum viable layout (functional requirements, not visual spec):**
- Table view: Company | Role | Date Applied | Status | Match Score | Resume Link
- Filter by status (Applied / Interview / Rejected / Offer)
- Row-level "days since last update" to surface follow-ups due
- A simple token-entry gate before the dashboard loads (see architecture.md section 8 — `DASHBOARD_TOKEN`)

**API contract the frontend consumes** (see architecture.md section 8 for full detail):
```
GET  /api/applications?status=Applied
     -> [{ id, company, role, date_applied, status, match_score, drive_link, days_since_update }]

GET  /api/applications/{id}
     -> { id, company, role, date_applied, status, match_score, drive_link, jd_hash, fit_summary }

PATCH /api/applications/{id}
      body: { status: "Interview" }
      -> updated record

GET  /api/stats
     -> { applied: N, interview: N, rejected: N, offer: N }
```
Build the frontend against this contract now; swap in your Stitch-exact components/styling once the export is available — the data shape shouldn't need to change either way.

## 8. Portfolio Website (later, optional — not in MVP)
If added: a static site generator (Astro/Eleventy) reading the same applications data to show something like "recently applied to" or a projects section. Deliberately excluded from MVP scope.
