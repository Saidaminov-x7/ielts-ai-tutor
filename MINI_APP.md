# IELTS Mini App setup

The Mini App is served by the existing aiohttp webhook service. In production,
the React client and `/api/v1` use the same HTTPS origin; there is no separate
frontend hosting service to configure.

## Local development

1. Install the Python project and configure a local `.env` as described in
   [README.md](README.md). `TELEGRAM_BOT_TOKEN` and the numeric
   `OWNER_TELEGRAM_ID` are required for authenticated API calls. `OPENAI_API_KEY`
   is optional and is used only when the learner explicitly requests Writing
   feedback.
2. Build the static client and start the Python service in one PowerShell
   window:

   ```powershell
   cd frontend
   npm ci
   npm run build
   cd ..
   python -m app.main
   ```

   The service serves the built app from `/` and the API from `/api/v1` on its
   configured port (8080 by default).
3. For frontend iteration, run `npm run dev` from `frontend/` in a second
   window. Vite proxies `/api` to `http://localhost:8080`. See
   [frontend/README.md](frontend/README.md).
4. Open the HTTPS service through the Telegram bot's Mini App menu button or
   `/start` button. A normal browser does not have Telegram `initData`; the API
   intentionally rejects it, and there is no development authentication
   bypass.

## Railway deployment

Deploy the repository's existing webhook service with the included Dockerfile.
Its Node build stage builds the client, then the Python image serves those static
assets. Configure:

- `TELEGRAM_BOT_TOKEN` and the matching numeric `OWNER_TELEGRAM_ID`.
- `WEBHOOK_BASE_URL` as the service's public HTTPS domain.
- `WEBHOOK_SECRET_TOKEN` and `DAILY_JOB_SECRET` as generated random values of
  at least 32 characters each.
- `DATABASE_URL=sqlite:////data/ielts.db`, with the existing persistent volume
  mounted at `/data`; keep one webhook replica for SQLite.
- Railway's healthcheck path is configured as `/health`. Railway supplies `PORT`.
- `OPENAI_API_KEY` only if Writing feedback should be enabled.

On startup, the service configures the Telegram webhook and the Mini App menu
button. The existing daily-trigger service should call
`https://<service-domain>/internal/daily` using the same `DAILY_JOB_SECRET`;
do not mount the SQLite volume on that trigger service. Keep the existing
`DAILY_JOB_URL` aligned with the webhook service domain.

The Mini App routes are protected by Telegram signature validation and exact
owner matching. A valid `initData` bearer value remains usable for up to 24
hours, so treat browser credentials as sensitive. Review state currently
updates shared vocabulary rows; that is safe only while one Telegram owner is
configured. Multi-owner support needs owner-scoped review state first.

The course workbook must be imported separately. Until it is available, the UI
shows an honest empty-course state rather than generating replacement lessons.
Telegram launch, Railway deployment, and live OpenAI evaluation require
credentials and have not been verified by local build or API tests.
