# PRD: Job Application Assistant (JAA) — Personal Tailoring & Notify Pipeline

## 1. Problem Statement
Manually tailoring a resume for every job description is slow, inconsistent, and easy to skip when applying to many roles — which lowers response rates. This tool automates the tailoring + filing + notification steps while deliberately keeping the actual "click apply" step manual, because full automation of that step risks account bans on job platforms (see Non-Goals).

## 2. Goals (MVP)
- **G1:** Given a job description + master resume, produce an ATS-safe, truthfully-tailored resume PDF in under 60 seconds.
- **G2:** Auto-file it in Google Drive under `/JobApplications/{CompanyName}/{YourName}.pdf`.
- **G3:** Notify you on WhatsApp with a summary + Drive link the moment it's ready.
- **G4:** Track every tailored application in a simple local record (company, role, date, status, resume link).

## 3. Non-Goals (explicitly out of scope for MVP, and why)
- **NG1 — No automated form-filling/submission.** Bot-detection ban risk on Naukri/LinkedIn/Wellfound; you apply manually after being notified.
- **NG2 — No logged-in scraping of job platforms.** ToS violation risk. Phase 2 uses public/anonymous or your-own-inbox sources only.
- **NG3 — No bulk cold-emailing.** Spam-law risk (CAN-SPAM / India IT Act) and worse response quality than targeted 1:1 outreach. Outreach stays draft-only, human-sent.
- **NG4 — No multi-user support.** Single user, single set of credentials.

## 4. Users
You. Solo user, solo dev.

## 5. Success Metrics
- Time-to-tailored-resume < 60s from pasting a JD.
- Zero fabricated claims in generated resumes (weekly spot-check).
- You actually keep using it for 2+ weeks — adoption is the first real signal it's worth extending.
- Informal comparison: response rate on tailored-resume applications vs. your prior baseline.

## 6. Functional Requirements (MVP)
- **FR1:** Accept a job description as raw text (file or stdin) plus company name + role title.
- **FR2:** Load your master resume from a structured source (JSON/YAML), not just a PDF — see design.md.
- **FR3:** Call the OpenAI API with a constrained "reorder & rephrase only, never invent" system prompt.
- **FR4:** Render tailored content into a single-column, ATS-safe HTML → PDF resume.
- **FR5:** Upload PDF to Drive: create `/JobApplications/{Company}/` if missing, save as `{YourName}.pdf`, overwrite on re-run (no duplicates).
- **FR6:** Log the application (company, role, JD hash, timestamp, Drive link, status) to local SQLite.
- **FR7:** Send a WhatsApp message via Twilio: company, role, Drive link, 1-line fit summary, match score.
- **FR8:** Single command runs the whole pipeline:
  `python jaa.py --company "Acme" --role "Backend Engineer" --jd jd.txt`

## 7. Non-Functional Requirements
- Zero paid infra beyond OpenAI + Twilio usage; runs on your laptop.
- Every credential in environment variables — never in code, never in logs.
- Target cost: under ~$0.05 in OpenAI tokens per resume.
- Re-running for the same company/role updates the existing record rather than duplicating it.

## 8. Future Phases
See `Phases.md`.

## 9. Risks
- **LLM hallucination in resume content** → mitigated by a strict prompt contract + mandatory human spot-check before sending.
- **API cost creep** if usage scales → mitigated by per-run cost logging and provider-side spend caps.
- **Platform ban risk** from any future automation layer → deliberately deferred and scoped carefully; see Phase 4 in Phases.md.
