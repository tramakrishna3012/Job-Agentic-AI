# Security

## 1. Secrets
- All API keys/tokens live in `.env`, loaded via `python-dotenv`. `.env` is in `.gitignore` from the very first commit.
- Never hardcode secrets in source, notebooks, or committed config files.
- If you later move to a shared repo or hosted runner (GitHub Actions), use encrypted repo secrets — never a checked-in `.env`.

## 2. Google Drive
- OAuth scope: `https://www.googleapis.com/auth/drive.file` **only**. This restricts access to files the app itself creates, not your entire Drive. Do not widen this scope even if it's more convenient.
- Store the OAuth refresh token locally, outside the git repo, with restrictive file permissions (`chmod 600`).

## 3. OpenAI
- Don't send more personal data than necessary in prompts — resume + JD is unavoidable, but avoid adding extra PII (e.g. full home address) if it's not needed for tailoring.
- Set a monthly spend cap in the OpenAI dashboard as a safety net against bugs causing runaway calls (e.g. a retry loop gone wrong).

## 4. Twilio / WhatsApp
- Sandbox credentials are still real credentials — treat them with the same care as production keys.
- If you ever add an inbound webhook (e.g. replying to the WhatsApp message to trigger an action), verify Twilio's request signature on every incoming call. Without this, anyone who finds the webhook URL can trigger your pipeline.

## 5. Data at Rest
- The SQLite DB contains company names, roles, and Drive links — not highly sensitive, but keep it out of any public repo regardless.
- No resume content or full JD text in logs — hashes/snippets only, for dedup checks.

## 6. Dependency Hygiene
- Run `pip-audit` periodically (or on every dependency bump) to catch known-vulnerable packages. Low effort, worth doing given this tool handles your personal data and live credentials.
- Pin dependency versions in `requirements.txt`; don't float on `latest`.

## 7. What NOT to Build (security reasons, not just scope reasons)
- No feature that logs into LinkedIn/Naukri/Wellfound programmatically and stores your session cookie — a leaked session cookie is equivalent to a leaked password and bypasses 2FA entirely.
- No public-facing dashboard without authentication. Even a "just for me" Streamlit app, if deployed anywhere reachable from the internet, needs at least basic auth in front of it.

## 8. Incident Response (lightweight, solo-dev version)
If any key leaks (e.g. accidentally committed): rotate it immediately — OpenAI, Twilio, and Google all support key/token revocation from their dashboards — then scrub git history if it was committed (`git filter-repo` or BFG Repo-Cleaner).
