# Vercel deployment

CivicSathi is a FastAPI app. Import the repository in Vercel with the project root set to `civicsathi-ai`. The Vercel Python runtime detects `app/main.py`; `vercel.json` includes the web pages, service data, and skill files that the app reads at runtime.

## Persistent database

Vercel Function local storage is ephemeral. Connect a Postgres database from the Vercel Marketplace (Neon is suitable for a demo) and expose its connection string as `POSTGRES_URL` or `DATABASE_URL`. The app creates its tables at startup and uses Postgres in Vercel; local runs continue using SQLite. It intentionally refuses to start on Vercel without Postgres so user accounts and requests are never written to a disposable SQLite file.

## Environment variables

Set these in Vercel Project Settings → Environment Variables:

- `GEMINI_API_KEY`: Google AI key used by the hosted Gemma model.
- `GEMMA_TEXT_MODEL`: `gemma-4-26b-a4b-it`.
- `GEMMA_VISION_MODEL`: `gemma-4-26b-a4b-it`.
- `POSTGRES_URL` or `DATABASE_URL`: the Postgres Marketplace connection string.
- `STAFF_EMAILS`: optional comma-separated email allowlist, set before staff registration.
- `TEXT_PROVIDER`: `google-gemma`.

Deploy with one production application and a managed Postgres database. After deployment, verify `/api/health` reports `persistent_database_configured: true`, then register a test account, submit a request, redeploy, and confirm the request is still in Track. Never commit API keys or database URLs.

The deployed prototype still records demo requests only; it does not submit applications to Chandigarh government systems or confirm medical appointments.
