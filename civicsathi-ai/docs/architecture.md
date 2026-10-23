# Architecture

FastAPI serves separate home, services, application intake, report, track, account, sign-in, sign-up and staff pages. Plain HTML/CSS/JavaScript runs same-origin; there is no frontend build.

## Accounts and authorization

Registration enforces a unique case-insensitive email and a scrypt password hash. Login creates a random opaque 14-day session cookie marked HTTP-only and SameSite=Lax; the cookie becomes Secure on HTTPS. SQLite stores only the SHA-256 digest of the session token. Logout revokes the record. A small per-process per-IP limiter slows sign-up and password guessing.

Staff roles are assigned only when an account registers with an email in `STAFF_EMAILS`. Set the allowlist before the staff account is created. All citizen APIs require a session. Cases, service requests and photo reads check owner IDs; staff can review and update both request queues. Existing pre-account cases remain unassigned and visible only to staff.

## AI intake

Text intake uses hosted Gemma 4 by default; photo upload sends a normalized, metadata-free image to the Gemini API. Validated photo analysis can create a draft without a second model call. Citizens edit and confirm every draft. When hosted AI is unavailable, the deterministic text fallback is clearly labeled.

## Database and deployment

SQLite stores users, sessions, complaint cases, service requests, both request histories and photo evidence. GMSH-16 appointment preferences, social-welfare intake and horticulture requests are prototype workflows; no official system is contacted, and the prototype does not book appointments or decide eligibility. `DB_PATH` selects the file. On Railway the app defaults to `RAILWAY_VOLUME_MOUNT_PATH/civicsathi.db`. Run one app replica with a persistent volume mounted at `/data`; SQLite does not support this app's multi-replica deployment model. Back up the volume before production changes. This supports a hackathon demo, not a high-availability civic production service.

## Safety and privacy

Same-origin writes are enforced. Case data and images require user ownership or staff role. Audit entries omit complaint text, photos, password hashes, session tokens and API keys. Upstream error details are sanitized. Google receives consented image/text inputs for inference. No municipal system is contacted.
