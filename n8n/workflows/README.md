# IELTS AI Tutor n8n workflows

These eight inactive n8n Community workflow exports are import-ready templates. They are deliberately inactive and carry no credentials until an owner imports them into the self-hosted n8n instance.

## Before activation

1. Complete n8n owner setup over HTTPS. Keep the editor private or behind authentication.
2. In n8n, create an encrypted **Header Auth** credential named `IELTS Internal API`: header name `X-Daily-Job-Secret`, value copied from the Python Railway service's `DAILY_JOB_SECRET` variable. Never put the value into an export, workflow field, URL, Git, or report.
3. Import each JSON file and replace the placeholder credential reference by selecting `IELTS Internal API` in each HTTP Request node.
4. Verify the private URL `http://ielts-webhook.railway.internal:8080` resolves from the n8n service in Railway. If Railway's assigned private endpoint differs, update the base URL in the nodes to the exact private DNS name. Do not use a secret in the URL.
5. Run one manual test for each event and inspect the Python response and SQLite `scheduled_events` row. Then activate schedules and verify a repeated event returns `already_processed`.

All cron expressions are interpreted in `Asia/Tashkent`. The daily lesson is called through the existing idempotent `/internal/daily` route at midnight. The other jobs send only an event type and local date to Python; Python owns the database, user preferences, AI budget calculation, and Telegram delivery. No Telegram Trigger is used in n8n.

The health workflow polls every 30 minutes. Its alert route is limited: if the Python service is completely unreachable, that same service cannot deliver a Telegram alert. n8n execution history is configured not to retain successful or failed payloads in these templates; Railway service logs and monitoring still need to be reviewed separately. No diagnostic schedule should be left active during testing.

All exports are inactive by default. Do not activate them until the n8n service is actually running, owner setup is complete, and the credential reference and private DNS have been verified.
