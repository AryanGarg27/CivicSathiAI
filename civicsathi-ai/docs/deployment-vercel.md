# Vercel deployment

CivicSathi is a FastAPI app. Vercel's Python runtime supports FastAPI and `requirements.txt`; import the GitHub repository with the project root set to `civicsathi-ai`. `vercel.json` includes the web pages, service data, and skill files the app reads at runtime.

## One-time setup

1. Sign in to Vercel and choose **Add New → Project**. Import `AryanGarg27/CivicSathiAI` from GitHub.
2. In project configuration, set **Root Directory** to `civicsathi-ai`. Keep the `main` branch as Production Branch and leave the Python install/build commands at their detected defaults.
3. Before deploying, connect persistent Postgres: in Vercel Marketplace/Storage, add the Neon Postgres integration and create a database on its free plan. Connect it to this Vercel project for the **Production** environment. The integration adds a connection-string environment variable; this app accepts `DATABASE_URL` or `POSTGRES_URL`.
4. In **Project → Settings → Environment Variables**, add `GEMINI_API_KEY` with the Google AI Studio API key. Add `TEXT_PROVIDER=google-gemma`, `GEMMA_TEXT_MODEL=gemma-4-26b-a4b-it`, and `GEMMA_VISION_MODEL=gemma-4-26b-a4b-it`. Optionally add `STAFF_EMAILS` with the staff account email(s) before those users sign up. Keep secrets in the provider dashboard; never commit or paste them into chat.
5. Click **Deploy**. After the first build succeeds, changes to environment variables require a new deployment.

## Persistent database

Vercel Function local storage is ephemeral. The Neon integration is listed in Vercel Marketplace and injects Postgres connection variables into connected projects. The app creates its tables at startup and uses Postgres on Vercel; local runs continue using SQLite. It intentionally refuses to start on Vercel without Postgres so user accounts and requests are never written to a disposable SQLite file.

## Environment variables

Set these in Vercel Project Settings → Environment Variables, unless the Neon integration has already supplied the database URL:

- `GEMINI_API_KEY`: Google AI key used by the hosted Gemma model.
- `GEMMA_TEXT_MODEL`: `gemma-4-26b-a4b-it`.
- `GEMMA_VISION_MODEL`: `gemma-4-26b-a4b-it`.
- `POSTGRES_URL` or `DATABASE_URL`: the Postgres Marketplace connection string.
- `STAFF_EMAILS`: optional comma-separated email allowlist, set before staff registration.
- `TEXT_PROVIDER`: `google-gemma`.

## Verify the live demo

Open `https://<your-project>.vercel.app/api/health` and confirm it reports `status: ok`, `google_configured: true`, and `persistent_database_configured: true`. Then sign up with a test account, submit one request, open Track, and confirm it appears. Redeploy once and check that the request remains. Do not use real resident information in the hackathon demo.

The deployed prototype still records demo requests only; it does not submit applications to Chandigarh government systems or confirm medical appointments.
