# CivicSathi AI — Chandigarh civic service companion

A multi-page civic service application with individual accounts, AI-assisted photo/text complaints, trackable GMSH-16 appointment requests, social-welfare application intake, horticulture requests, a Sampark service directory, SQLite persistence and a staff status queue.

**Independent prototype, not an official municipal service.** No municipal submission or government integration occurs. Google-hosted Gemma performs AI inference over the internet; the web application and database run on your laptop.

## Run on Windows

From this project folder, in PowerShell:

```powershell
.\run.ps1
```

The launcher uses `.venv`, installs requirements and creates `.env` if missing. It preserves existing AI settings. Open [CivicSathi](http://127.0.0.1:8000).

Before starting, set `GEMINI_API_KEY` in that same PowerShell session or in the local `.env` file. Do not commit or share your key. Existing environment variables take precedence over `.env`. If a server is already running on port 8000, stop it with Ctrl+C first, or use `./run.ps1 -Port 8001`.

If PowerShell does not allow running scripts, run these commands directly:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\configure_local.py
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Restart the server after changing `.env`. No Ollama process or model download is needed with the defaults.

## Configuration

| Setting | Purpose / default |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio API key; required for hosted AI |
| `TEXT_PROVIDER` | `google-gemma` (default) or `ollama`; overrides legacy `MODEL_PROVIDER` |
| `GEMMA_TEXT_MODEL` | `gemma-4-26b-a4b-it` |
| `GEMMA_VISION_MODEL` | `gemma-4-26b-a4b-it`; `gemma-4-31b-it` can also be configured |
| `OLLAMA_URL`, `OLLAMA_MODEL` | Optional local text provider; localhost:11434, gemma3:1b |
| `STAFF_EMAILS` | Comma-separated staff email allowlist; set before those people register |
| `DB_PATH` | `./civicsathi.db` |
| `AUDIT_LOG_PATH` | `./logs/audit.jsonl` |

The health banner reports whether a key is configured, not whether the provider is reachable or has quota. `/api/health` never returns credentials. Photo analysis uses the Gemini API directly; the older OpenRouter and Gemini adapter files are retained for reference but are not part of the active workflow.

## Demo walkthrough

1. Create an account at **Sign up** or sign in at **Sign in**. Browse the home page and **Services** without signing in; applications, reports, tracking and account details require your account.
2. For photos, agree to Google processing and local evidence storage. **Prepare complaint draft** analyzes the photo automatically. **Analyze photograph** lets you inspect findings first.
3. Review the summary, category and location. A photo alone cannot supply the location. Unrelated images are categorized `other` and must not be forced into a complaint.
4. Check the suggested service and possible duplicates. Recheck after editing. Confirm the details, then **Create demo case**. Keep the tracking ID private.
5. Staff members use the same sign-in page. Add staff emails to `STAFF_EMAILS` before they register. Staff can move cases to **Under review**, **In progress** and **Resolved**; resolution or rejection requires a note.
6. From **Services**, try a GMSH-16 appointment preference, a senior-citizen/disability/pension request, or a horticulture request. Requests are saved to your account and can be tracked on **Track**. Staff can update their status on the separate **Staff** page.

Health and social-welfare service names are grounded in Chandigarh e-Sampark's published service list. These forms are a local demo intake only: they do not book a hospital visit, verify eligibility, accept official documents or submit anything to a government system. Use e-Sampark to confirm live requirements, fees, holidays and centres.

When AI is unavailable, photos remain attachable and text intake uses a clearly labeled keyword fallback. No fake AI result or official success is reported. Photo findings are schema-validated and never independently submit cases. One photo-assisted draft uses one vision call rather than requiring a second text model call.

## Validation

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
node --check web/app.js
```

The suite isolates the database and logs and covers the image-to-case workflow, provider failures, upload validation, consent, status transitions, persistence and migration. It does not measure real-world image accuracy. Re-run it after the account-system changes before relying on those changes for a live deployment.

A live smoke test on 23 October 2026 used the running server's Google API key and `gemma-4-26b-a4b-it`; a blank synthetic image returned a validated `other` classification. This proves that the provider integration works, not that civic-photo accuracy has been benchmarked. See [evaluation protocol](docs/evaluation.md) for the required labeled-image evaluation.

## Accounts and stored data

Visitors can browse the home page and service directory without an account. Reporting, image analysis, service applications, account pages and tracking require sign-in. Each account has a unique, case-insensitive email and a scrypt password hash. Login sessions use random opaque, HTTP-only, same-site cookies and are stored by hash in SQLite. Passwords and session tokens are never stored as plain text. Sign-up and sign-in have basic per-IP attempt limits.

Each complaint and service request belongs to its creator. Citizens can view only their own complaints, photos and service requests; authorized staff can view the queues and record status updates. SQLite stores users, sessions, cases, service requests, history and photos in one database. Existing complaints from before account support remain available to staff but are not assigned to a citizen automatically. Back up `civicsathi.db` before manual migration.

## Prepare a live Railway deployment

The Docker image listens on Railway's injected `PORT` and uses a mounted volume for SQLite. Deploy as a **single replica** and attach a persistent volume at `/data`. Configure `/api/health` as the health check and generate an HTTPS public domain. Set these runtime variables in Railway's private Variables settings:

| Variable | Value |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio key |
| `TEXT_PROVIDER` | `google-gemma` |
| `GEMMA_TEXT_MODEL` | `gemma-4-26b-a4b-it` |
| `GEMMA_VISION_MODEL` | `gemma-4-26b-a4b-it` |
| `STAFF_EMAILS` | Comma-separated authorized operator emails; set before their registration |
| `DB_PATH` | `/data/civicsathi.db` |
| `AUDIT_LOG_PATH` | `/data/audit.jsonl` |

The `.env` file is excluded from Docker and Git. Never put API keys in source code. Before inviting judges, verify HTTPS, sign up with a test citizen account, submit a test report, sign out, and verify staff access using a configured staff email. Railway documents its [persistent volumes](https://docs.railway.com/volumes).

**Publishing is not connected yet:** this workspace has no Git repository, GitHub CLI, Railway CLI, Docker CLI or linked hosting account. Once the code is pushed to a repository accessible to your Railway account and the volume/runtime variables are configured, Railway can build the included Dockerfile.

## Docker (optional; not needed on a low-memory laptop)

```powershell
docker compose up --build
```

Create `.env` first. This starts only the application and uses hosted Gemma. SQLite and audit logs use a named volume. The bind address is localhost. The Docker build excludes secrets, local databases and `.venv`.

## Scope and limits

- Service descriptions and portal links are provisional, not verified current procedures or fees.
- Duplicate matching is lexical, bounded to the latest 1,000 cases, with a different-sector exclusion. It is not multilingual semantic deduplication.
- Photos are decoded, resized to a 1280-pixel longest edge, and re-encoded without metadata. Unsubmitted uploads older than 24 hours are cleaned on startup and subsequent uploads. Attached photos persist with cases.
- Citizens must be signed in and owner checks protect their cases and photos. Staff role is granted only to emails in `STAFF_EMAILS` when those accounts register.
- Google HTTP 500/502/503/504 errors receive one automatic retry. Quota and authorization errors are not retried; the UI reports the failure and allows manual continuation. Before handling real residents, add account recovery, email verification, deletion/export controls, stronger edge rate limits, backups and a privacy review.
- Existing SQLite cases are preserved through additive migrations. Back up `civicsathi.db` before moving or deploying the app.

See [architecture](docs/architecture.md) and [privacy](docs/privacy-and-safety.md).
