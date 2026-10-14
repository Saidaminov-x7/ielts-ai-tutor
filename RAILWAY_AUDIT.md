# Railway runtime and traffic audit — 2026-10-14

## Fresh snapshot (2026-10-14 22:29 Asia/Tashkent)

- Production environment health: 3 services, 0 current issues, 0 recent failures, no pending changes. n8n online; Python webhook sleeping; daily cron ready.
- Request counts over 24h: n8n 930 (647 2xx, 211 3xx, 64 4xx, 8 5xx); webhook 19 (12 2xx, 6 4xx, 1 5xx); daily trigger 0 public HTTP requests. Latest n8n hour: 166 requests, 1 5xx. This is not a full-origin/security guarantee; aggregate counts alone do not identify clients.
- Detailed n8n HTTP logs for the latest hour: 133 rows from one client source, mainly `/healthz`, `/rest/login`, and `/rest/settings`; no distinct high-volume source was observed. The sample included 10×401, 1×403, 1×502, and 1 status-0 connection; no IPs were persisted here.
- n8n resources: 0.441 GB current RAM, 0.874 GB 24h max. Webhook: 0.213 GB current RAM, 0.459 GB max. Cron is idle between executions. These are runtime metrics, not a monthly cost quote.
- Both live health endpoints returned HTTP 200. n8n volume is `/home/node/.n8n`; webhook volume is `/data`.
- Current browser sign-in could not proceed because no password was saved in Chrome. The persisted active owner was left intact. n8n workflows remain incomplete; existing daily cron was not changed.

## Fresh verification (2026-10-14 16:36 UTC)

- Service deployments: n8n `03fe6ffd-a4dd-4609-afab-5810edb45444` `SUCCESS`; webhook `e4a7b877-bc44-4184-b8e5-6707952fbf1f` currently `SLEEPING`; daily-trigger `e514f09c-1287-4112-8888-80817fd0ed2e` `SUCCESS`, cron `0 19 * * *` UTC. Both Python services map to private repo `Saidaminov-x7/ielts-ai-tutor`, SHA `7fb241a`; n8n uses `n8nio/n8n:latest`.
- n8n has its 1 GB volume at `/home/node/.n8n`. Latest one-hour metrics: RAM 0.584 GB current / 0.663 GB max; CPU current 0.058 cores; network traffic was only a few MB across the hour.
- HTTP metrics: 583 requests (370 2xx, 154 3xx, 54 4xx, 5 5xx). Across 501 detailed rows there was one client IP. Four observed 5xx rows were `/rest/push` or `/healthz` 502; authentication/editor 401s align with the user's Chrome session. No unexplained external source was seen in this bounded sample.
- n8n accepted one login (HTTP 200), then the attempted workflow save returned 401. Subsequent login attempts returned 401. Fresh CLI export confirms the sole workflow remains inactive with Schedule Trigger interval `[{}]`. No schedules or duplicate deliveries were activated.
- n8n runtime version is 2.43.5. One deployment log recorded `browserId check failed` during the earlier session. The public settings payload lacks optional license keys, but upstream merged a frontend guard in 2.34; no specific root cause can be concluded from the settings payload alone. A clean isolated login is waiting for the owner to enter credentials.
- The webhook's Railway sleep mode is enabled and it is currently asleep; the cron trigger is idle between its scheduled execution. n8n itself remains always-on and consumes ~0.58 GB current RAM; n8n Schedule Trigger requires an awake process.
- The n8n CLI security audit reported HTTP Request as a general risky built-in node, community package installation enabled, and the authenticated public API enabled. Since no community node is used, set `N8N_COMMUNITY_PACKAGES_ENABLED=false`; deployment `0bd24930-58c6-4322-a9ab-c734b0769b23` reached `SUCCESS`, `/healthz` returned 200, and repeat audit confirmed the setting is active.

## Deployment and protected-endpoint follow-up (2026-10-14 16:30 UTC)

- Private GitHub repo `Saidaminov-x7/ielts-ai-tutor` is confirmed private. Commit `7fb241ac28abb0b16f314a0e5dfc1a048a8bed02` was pushed to `main`; Railway webhook and daily-trigger deployments for that exact SHA both reached `SUCCESS`.
- Live `GET /health` returned 200 after the webhook woke from sleep. A POST to `/internal/scheduled-event` without the required auth header returned 403; no protected event was accepted.
- n8n remains `SUCCESS`, webhook returns to idle sleep when traffic stops, and daily-trigger remains scheduled at `0 19 * * *` UTC. n8n owner creation succeeded, but login with the form's previous email failed. The correct account email has been identified in the database and used once; login still returned 401, indicating the remaining issue is the user-entered password. No more attempts are being made pending manual password re-entry.
- Current workflow inventory is one inactive, incomplete `Daily IELTS Lesson`; its Schedule Trigger interval is empty. This has no scheduled effect yet. No other workflows are stored or active.

## Follow-up snapshot (2026-10-14 16:20 UTC)

- Railway production inventory reconfirmed all three services with no staged changes: `ielts-n8n` deployment `03fe6ffd-a4dd-4609-afab-5810edb45444` is `SUCCESS`; `ielts-webhook` is `SLEEPING`; `ielts-daily-trigger` deployment `377402b4-d488-4cbc-8c8b-963c2ceeda13` is `SUCCESS`, scheduled at `0 19 * * *` UTC with no public domain.
- n8n retains its 1 GB volume at `/home/node/.n8n`. Read-only SQLite metadata inspection found one inactive `Daily IELTS Lesson` workflow with two nodes (Schedule Trigger and HTTP Request); the auth header references `DAILY_JOB_SECRET` by expression and has no literal value. No credential records exist. Workflow remains inactive pending owner login and testing.
- `n8n user-management:reset` returned success. Chrome then submitted owner setup successfully (HTTP 200); `/rest/settings` now reports first-load setup disabled and Chrome redirects to sign-in. SQLite has one owner row; no password/hash/email value was read by the assistant.
- The saved workflow targets `POST http://ielts-webhook.railway.internal:8080/internal/daily` and includes the environment-based secret header. Its Schedule Trigger interval is empty, and the workflow is inactive, so it is not yet runnable as a daily schedule.
- Railway 24-hour resource metrics: n8n RAM current 0.457 GB / max 0.874 GB, webhook 0.213 GB / 0.459 GB, daily trigger zero while idle. These measurements do not establish monthly billing.
- Recent n8n HTTP logs include failed owner sign-ins (401) from the same Chrome client as editor requests. The earlier 683-request hour was a short browser-driven editor/reconnect burst; sampled logs did not show a second client. Webhook logs include cold-wake 499/502 errors and deliberate invalid-secret 403s; daily trigger received no public HTTP requests. This narrows observed traffic but does not prove future absence of external requests.

## Recovery and live request audit (2026-10-14 16:10 UTC)

- The user created the n8n owner in Chrome. After the authorized Railway restart and a later config redeploy, public `/rest/settings` returned HTTP 200 with `showSetupOnFirstLoad=false`, proving the owner setup state is stored on the persistent volume. The browser session itself is not logged in after restart; Chrome currently shows `/signin`, so workflow editing needs the owner to sign in again.
- The n8n restart and config redeploy both reached `SUCCESS`. Startup reports n8n 2.43.5 and the editor listening over HTTPS. The latest config change set `N8N_PROXY_HOPS=1` (it was `0`); the new deployment has no `ERR_ERL_UNEXPECTED_X_FORWARDED_FOR` startup error.
- Railway counted 683 n8n HTTP requests in the latest hour: 519 2xx, 117 3xx, 43 4xx, and 4 5xx. All sampled requests came from the same source IP and Chrome user agent. The busiest minute was 146 requests while the owner entered n8n and the editor loaded. 74 `GET /rest/push` requests ended with status 0 during websocket reconnects; health polls and UI assets account for much of the remainder. Login/workflow 401s and three `/rest/push` 502s align with the browser session and restarts. This was a real short browser-driven spike, with no evidence of traffic from other clients in the sampled logs.
- `ielts-webhook` logged 2 health requests in the recent-hour sample; `ielts-daily-trigger` had no public HTTP requests and reports zero CPU/RAM while idle. In the 24-hour query Railway exposed only the same two n8n buckets (683 total), so it does not provide a complete independent 24-hour history in this capture.
- The new editor canvas draft was not saved: startup after the config redeploy reported `0 draft workflows, 0 published workflows`. No IELTS workflows are currently stored. Recreate the workflow after sign-in and verify it appears in the persistent database before proceeding.

## Fresh snapshot (2026-10-14)

Production request totals for the last 24 hours: `ielts-n8n` 299 (234 2xx, 58 3xx, 5 4xx, 2 5xx); `ielts-webhook` 16 (11 2xx, 4 4xx, 1 5xx); `ielts-daily-trigger` 0 public HTTP requests. Metrics show the scheduled trigger at zero CPU and memory while idle. No sustained request burst was visible.

The n8n 502 is tied to `GET /rest/push` connection dial timeouts during the 15:28 deployment transition; `/healthz` returned 200 immediately afterward. The webhook 502 is a 15-second cold-wake timeout at 14:20; the next `/health` returned 200. Four webhook 403s are intentional invalid-secret checks. n8n 4xx include unauthenticated login/setup-path diagnostics.

The current n8n deployment is `25ca0939-dd90-435b-bb29-8d93a1028cb2` (`SUCCESS`), one SFO replica, `ALWAYS` restart, HTTPS domain, and a 1 GB volume at `/home/node/.n8n`. Railway UI values confirm `N8N_USER_FOLDER=/home/node` and `RAILWAY_RUN_UID=0`. The `/setup` screen and fresh-database startup log show that the owner was not retained across a previous redeploy; restart persistence remains unverified until the final owner setup is submitted.

## Current production services

| Service | Runtime | Observed state | Deployment | Persistent data / scheduling |
|---|---|---|---|---|
| `ielts-webhook` | Python, from `Saidaminov-x7/ielts-ai-tutor@main` | Sleeping after idle; wakes for HTTP requests | `d88dbff` (`SUCCESS`) | 1 GB volume at `/data`; Railway sleep enabled |
| `ielts-daily-trigger` | Python cron, same repository and SHA | Ready; no running replica between jobs | `d88dbff` (`SUCCESS`) | `0 19 * * *` UTC |
| `ielts-n8n` | Self-hosted n8n Community, `n8nio/n8n:latest` (runtime reported 2.43.5) | Online | `25ca0939-dd90-435b-bb29-8d93a1028cb2` (`SUCCESS`) | 1 GB volume at `/home/node/.n8n`; `N8N_USER_FOLDER=/home/node`; always running for native n8n schedules |

All three services are in Railway project `ielts-ai-tutor`. The two Python services use the same GitHub repository; n8n is an image-based service, so there are three Railway services but not three separate Git repositories.

The n8n service has HTTPS at `https://ielts-n8n-production.up.railway.app`. After a redeploy the editor returned to `/setup`, so the previous owner setup was not retained in the database currently read by n8n. The volume is mounted at `/home/node/.n8n`; `N8N_USER_FOLDER=/home/node` is now explicit and a fresh deployment completed. The editor still shows first-owner setup. No workflows have been created or activated. The setup form requires the user to enter their own password in Chrome.

## Traffic and resource snapshot

Railway request analytics were checked over the prior 24 hours and 7 days on 2026-10-14:

- Python webhook: 16 HTTP requests total in the 7-day window. The busiest 30-minute bucket contained 10 requests. Paths were `/health` and `/internal/scheduled-event`; there was no unexplained request burst.
- Response counts: 11 successful, 4 client errors and 1 server error. The 4xx responses were negative tests of the protected scheduled-event endpoint. The single 5xx was a health request during a sleep/cold-start connection timeout. A 499 was also logged when the health-check client closed before the service woke. Subsequent health requests returned 200.
- n8n and the daily cron had no public HTTP requests before the n8n domain was added. The first n8n browser session fetched the setup page and static assets successfully; the unauthenticated `/rest/login` check returned 401.
- n8n RAM at the latest reading was 0.466 GB; its observed 7-day maximum was 0.874 GB. The average includes pre-deployment zeros and is not a steady-state estimate. n8n remains always-on because native schedule triggers cannot run while that service sleeps.
- Latest n8n traffic totals 231 requests over 7 days (204 2xx, 26 3xx, 1 4xx, 0 5xx); this includes interactive editor traffic. No high-volume burst is visible in the aggregate sample. Daily cron had no public HTTP requests and used zero observed CPU/RAM between runs.
- The daily cron had zero CPU, memory and network use between runs in the observed window.

## Limits and follow-up

- The Railway analytics window contains low traffic, so it can rule out a large recent spike but cannot prove future traffic behavior.
- Recheck n8n access after owner setup. The user requested building the eight workflows directly in the n8n editor, so do not import JSON. Build and verify them visually, bind the internal Railway variable, and test deduplication/notifications before activation.
- Recheck webhook health and request counts after the owner rotates the exposed Telegram token and adds the replacement directly in Railway Variables. Never copy that token into this report.
# Свежий аудит Railway (2026-10-14 16:46 UTC)

Повторно прочитан production environment `ielts-ai-tutor` (без изменений конфигурации):

| Сервис | Состояние | За последний час |
|---|---|---|
| `ielts-webhook` | `SLEEPING`, том `/data` 1 GB | 3 HTTP записи: `/health` 200 и два пробных неверных внутренних секрета 403; подтверждённого всплеска нет |
| `ielts-daily-trigger` | `SUCCESS`, cron `0 19 * * *` | HTTP запросов нет; cron-процесс простаивает между запусками |
| `ielts-n8n` | `SUCCESS`, том `/home/node/.n8n` 1 GB | 501 возвращённая HTTP запись; наблюдаемый максимум 146 запросов в минуту при открытии редактора в 16:01 UTC, позднее максимум 45/мин |

В просмотренной выборке n8n 501 запись пришла с одного клиентского адреса. В ней 338 ответов 200, 111 — 304, 29 — 401, 2 — 403, 2 — 404, 5 — 502 и 14 долгих соединений без HTTP-кода. Пять 502 относятся к `/rest/push` и `/healthz` во время/после деплоя; новые записи из браузера показывают `/rest/login` 401. Это указывает на пользовательскую активность в браузере и не показывает внешний распределённый всплеск, но это ограниченная выборка логов, а не гарантия отсутствия атак.

Метрики Railway за один час: n8n RAM 0.413–0.663 GB (сейчас 0.437 GB), средняя CPU ~0.023 ядра, максимум ~0.20; webhook RAM сейчас ~0.213 GB, CPU почти нулевая; у cron сервиса метрики нулевые между запусками. Запросы к webhook в выборке включают два 403 от неверного секрета — не успешная доставка workflow.

Открытая Chrome-вкладка `https://ielts-n8n-production.up.railway.app/signin` показывает поля Email/Password и кнопку Sign in. Пароль не вводился. Редактор недоступен без успешной аутентификации, поэтому workflow правок/запусков не было.

## Повторная проверка статистики Railway (2026-10-14 16:48 UTC)

Chrome по-прежнему показывает `/signin`; форма авторизации не пройдена. Runtime-логи последнего n8n deployment подтверждают `n8n ready` и версию `2.43.5`; процесс завершился без явной startup error.

Проверена отдельная агрегированная статистика Railway, чтобы не полагаться только на ограниченный список HTTP-логов. За 1 час: n8n — 486 запросов, 342 ответа 2xx, 110 ответов 3xx, 29 ответов 4xx и 5 ответов 5xx (1.03%). Максимальный минутный bucket — 145 запросов около 16:01 UTC, совпадает с открытием страницы/редактора Chrome. За 24 часа — 930 запросов и 8 ответов 5xx (0.86%); сервис развернут недавно и Railway вернул лишь 4 непустых временных bucket, поэтому это ещё не репрезентативная недельная базовая линия. Webhook: 19 запросов за 24 часа, 1 ответ 5xx (cold start), 6 ответов 4xx; за последний час 3 записи (1 ответ 200, 2 ответа 403 от отрицательных проверок секрета). Daily-trigger не имеет входящих HTTP запросов; это cron-сервис.

Вывод: зафиксирован краткий, объяснимый burst при загрузке Chrome; в наблюдаемом трафике не найден необъяснённый всплеск с разных клиентов. Ошибки 5xx не нулевые и должны контролироваться после стабилизации n8n. Список логов и метрики имеют ограниченное временное разрешение; нельзя делать вывод об отсутствии любой подозрительной активности.
