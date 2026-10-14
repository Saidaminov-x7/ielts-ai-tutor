# IELTS AI Tutor — deployment report

## Fresh live checkpoint (2026-10-14 22:29 Asia/Tashkent)

## Fresh deployment checkpoint (2026-10-14 23:04 Asia/Tashkent)

- Private GitHub `main` and local clean checkout point to `c59ac5d01751e1eb44514e89e7681a0588c9288a` (`fix review persistence and expose tutor commands`).
- Railway daily-trigger deployment `c932d898-08e3-470f-9af6-079bb2aa2c57` and webhook deployment `fbccb11e-a836-4817-af56-581685b51eb0` both reached `SUCCESS` on the exact commit. Production has three services, zero current issues, zero recent failures, and no pending work. n8n remains online; daily-trigger is ready; webhook is online after probe.
- Live checks: webhook `/health` returned HTTP 200 `{"status":"ok"}`; unauthenticated POST `/internal/scheduled-event` returned HTTP 403; n8n `/healthz` returned HTTP 200.
- n8n editor workflows remain blocked on owner sign-in in the isolated Chrome tab. The existing owner is retained; no further reset or registration was performed. Live Telegram and OpenAI remain blocked on owner-managed replacement credentials, and course workbook import remains blocked because the source workbook is not in the checkout.

- Railway production has three services and no pending changes: `ielts-n8n` online (`0bd24930-58c6-4322-a9ab-c734b0769b23`), `ielts-webhook` sleeping, and `ielts-daily-trigger` ready on `0 19 * * *` UTC. Platform overview reports zero current issues and zero recent failures.
- n8n is `n8nio/n8n:latest`, domain `https://ielts-n8n-production.up.railway.app`, one replica, 1 GB persistent volume at `/home/node/.n8n`. The Python webhook has a 1 GB volume at `/data` and Railway sleep enabled.
- Live health checks: n8n `/healthz` HTTP 200; webhook `/health` HTTP 200. Owner record persists in n8n SQLite. Chrome had no saved password, so owner login could not be retried and no workflow was edited or executed.
- Current 24h request counts: n8n 930, webhook 19, daily-trigger 0 public requests. Last-hour n8n count: 166. Resource snapshot: n8n 0.441 GB RAM now (0.874 GB max/24h); webhook 0.213 GB now (0.459 GB max/24h); cron idle at zero.
- Telegram/OpenAI live operation remains unavailable because the webhook lacks those variable names; the previously exposed Telegram token must be rotated first. The persistent code deployment is not the same as a fully configured live tutor.

## Fresh live checkpoint (2026-10-14 21:36 Asia/Tashkent)

- Three Railway services were rechecked: n8n deployment `03fe6ffd-a4dd-4609-afab-5810edb45444` is `SUCCESS`; Python webhook deployment is `SLEEPING`; daily-trigger deployment is `SUCCESS` at `0 19 * * *` UTC. Both Python services use the private GitHub repo on exact SHA `7fb241ac28abb0b16f314a0e5dfc1a048a8bed02`; n8n is the official `n8nio/n8n:latest` image with a 1 GB persistent volume at `/home/node/.n8n`.
- n8n owner login returned HTTP 200 once, then a workflow save returned 401 and later logins returned 401. The n8n CLI export confirms the daily draft still has an empty schedule interval. No workflow was activated; existing daily cron was left running.
- Runtime version is 2.43.5. Railway logged a `browserId check failed` during the previous browser session; the owner is not reset. A clean isolated sign-in page is ready, but the user cannot re-enter credentials at present.
- The Python service's configured variable names omit `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, and `OPENAI_API_KEY`; live delivery and AI tests cannot run until the owner adds replacement credentials directly in Railway. Do not use the previously exposed Telegram token.
- Last-hour n8n metrics: RAM 0.584 GB current, 0.663 GB max; HTTP totals 583 (370 2xx, 154 3xx, 54 4xx, 5 5xx). These values are a snapshot, not a cost forecast.
- `n8n audit` was run through Railway SSH. The community package option was enabled with no community nodes found in use; disabled it using `N8N_COMMUNITY_PACKAGES_ENABLED=false`. Deployment `0bd24930-58c6-4322-a9ab-c734b0769b23` reached `SUCCESS`, `/healthz` returned 200, and a repeat audit confirmed the setting is active.

## Production deploy follow-up (2026-10-14 21:30 Asia/Tashkent)

- Private repo verified: `Saidaminov-x7/ielts-ai-tutor`. Pushed commit `7fb241a`; Railway webhook and daily-trigger each deployed the exact commit successfully.
- Live webhook checks after deploy: `/health` → HTTP 200 (cold wake succeeded); unauthenticated `/internal/scheduled-event` → HTTP 403 (expected access control).
- n8n deployment remains successful on its persistent volume. Owner registration is saved, but the login form's old prefilled email was mismatched; after correcting the email, login still returned 401. Password remains private and needs manual re-entry by the owner. No further retries or resets.
- The one saved Daily IELTS Lesson workflow is inactive and incomplete because its Schedule Trigger interval is empty. No n8n automation is claimed as live.

## Follow-up verification (2026-10-14 21:20 Asia/Tashkent)

- After repeated `401` sign-in responses, the authorized reset completed and the owner recreated the account in Chrome; the Railway log records HTTP 200 for `/rest/owner/setup`. The app now redirects to `/signin`; user must sign in directly. No password was read or entered by the assistant.
- Persistent SQLite contains one inactive `Daily IELTS Lesson` workflow with Schedule Trigger → HTTP Request nodes. The private URL and environment-based `DAILY_JOB_SECRET` header are configured, but the schedule interval is empty. No n8n credential rows exist. This workflow has not been end-to-end tested.
- n8n deployment remains `03fe6ffd-a4dd-4609-afab-5810edb45444` (`SUCCESS`) with its `/home/node/.n8n` volume. Webhook sleeps with `/data`; daily-trigger is ready on `0 19 * * *` and has zero idle resource metrics.
- Remaining: verify owner login; test the saved workflow end to end before activating it; create and test the other seven; confirm idempotency and persistence; only then consider disabling the old daily trigger. No Telegram/OpenAI credentials were added and live notification delivery is not verified.

## Current verification (2026-10-14)

- Owner recovery: owner setup completed in Chrome, then owner setup remained complete after restart (`/rest/settings` HTTP 200; `showSetupOnFirstLoad=false`). Chrome now requires sign-in again because the session was invalidated by restart/redeploy. No password was read by the assistant.
- n8n configuration fix: `N8N_PROXY_HOPS` was confirmed as `0`, then set to `1` for Railway's reverse proxy. The follow-up deployment `03fe6ffd-a4dd-4609-afab-5810edb45444` reached `SUCCESS`; its startup logs contain no previous `ERR_ERL_UNEXPECTED_X_FORWARDED_FOR` error.
- Latest hourly request audit: n8n 683 requests (519 2xx, 117 3xx, 43 4xx, 4 5xx), all sampled from one Chrome client IP. A 146-request busiest minute coincided with editor loading. Repeated `/rest/push` status 0 and three transient 502s were websocket reconnects around restart; unauthorized login/workflow checks account for the 401s. No second client or unexplained external burst appeared in the sample. See [RAILWAY_AUDIT.md](RAILWAY_AUDIT.md).
- n8n started after config deploy with `0 draft workflows, 0 published workflows`. The canvas changes made before redeploy were not saved; no workflow can be counted as created yet.

- Recovery update: the user-authorized `n8n user-management:reset` completed through Railway SSH using the explicitly registered key. The `/setup` page is now open in Chrome so the owner can create a new password directly. No password was entered by the assistant. Next verify owner login and persistence across a restart before building workflows.
- Railway SSH first closed because the CLI selected a different default identity; specifying the registered identity file fixed the connection. The reset command reported `Successfully reset the database to default user state.`
- n8n logs also contain a proxy trust validation error (`X-Forwarded-For` received while Express `trust proxy` is false). Correct `N8N_PROXY_HOPS` after owner onboarding and verify a clean runtime log.

- Railway project `ielts-ai-tutor`, production. Services: `ielts-webhook` is sleeping while idle, `ielts-daily-trigger` is ready between cron runs, and `ielts-n8n` is online on `n8nio/n8n:latest` (runtime 2.43.5).
- Active n8n deployment: `25ca0939-dd90-435b-bb29-8d93a1028cb2`, `SUCCESS`. A 1 GB Railway volume is mounted at `/home/node/.n8n`; verified `N8N_USER_FOLDER=/home/node` and `RAILWAY_RUN_UID=0` in the Railway Variables UI.
- The n8n owner setup endpoint succeeded twice before the most recent initialization; its startup log records an empty database, and the live browser is currently at `/setup`. Owner creation and post-restart persistence verification remain pending. Do not report n8n workflows as deployed yet.
- Latest 24-hour traffic snapshot: n8n 299 requests with two transient `/rest/push` 502s during redeploy; webhook 16 requests with one cold-start 502; scheduled trigger received no public requests. No unexplained request burst.
- Current local quality checks: 32 tests passed, Ruff clean, secret scan clean, diff check clean.

Current Railway check (2026-10-14): see [RAILWAY_AUDIT.md](RAILWAY_AUDIT.md) for all three service states, sleep mode, storage, HTTPS, and request-rate findings. After redeploy the n8n editor returned to `/setup`. `N8N_USER_FOLDER=/home/node` now points to the mounted persistent volume; the user must recreate owner account in Chrome and we must verify it survives restart.

Проверено: 2026-10-14.

## GitHub

- Приватный репозиторий: `https://github.com/Saidaminov-x7/ielts-ai-tutor`.
- Рабочий код находится на ветке `main`; локальное дерево было чистым при подготовке отчёта.
- GitHub Actions jobs не стартовали из-за сообщения GitHub о проблеме с платежами или spending limit.

## Railway

- Project: `ielts-ai-tutor`, production environment.
- `ielts-webhook`: приватный GitHub source, Dockerfile, домен `https://ielts-webhook-production.up.railway.app`, `sleepApplication=true`, 1 replica, persistent SQLite volume 1 GB на `/data`.
- `ielts-daily-trigger`: отдельный cron service, `0 19 * * *` UTC (00:00 Asia/Tashkent), вызывает защищённый endpoint webhook-сервиса.
- Оба последних deployment имеют статус `SUCCESS`.
- Live `GET /health`: HTTP 200 `{"status":"ok"}`.
- Usage UI на дату проверки: Hobby, $0.20 текущего resource usage, $5 included usage, $0.00 current bill. Это снимок периода Oct 11–Nov 11, не месячный прогноз.
- Self-hosted n8n Community `ielts-n8n` развернут в том же проекте как Docker image `n8nio/n8n:latest`, production region `sfo`, 1 GB volume `/home/node/.n8n`, HTTPS domain, `ALWAYS` restart, sleep disabled. Последний successful deployment: `25ca0939-dd90-435b-bb29-8d93a1028cb2`; runtime reports n8n 2.43.5 and successful migrations. Chrome currently shows first-owner setup; no IELTS workflow создан.
- Первоначальный запуск показал `EACCES` на volume; `RAILWAY_RUN_UID=0` исправил права, но первый owner bootstrap не пережил перезапуск. `N8N_USER_FOLDER=/home/node` задан явно; следующий owner bootstrap должен подтвердить сохранение в volume.
- Короткий metrics snapshot после старта: RAM current ~60 MB, max ~147 MB; среднее и min искажены предыдущими нулевыми интервалами до запуска. Это не 10-минутный steady-state замер. Выборка ещё не достаточна для точной оценки месячной стоимости.
- В Railway проекте размещён только предназначенный IELTS n8n сервис; другие проекты и службы не менялись.

## Данные и работа приложения

- SQLite хранится на persistent volume; при старте entrypoint чинит владельца `/data` и сбрасывает привилегии процесса до `appuser`.
- Daily trigger и sleep-конфигурация работают на уровне инфраструктуры, но ежедневная Telegram-доставка блокирована отсутствующими bot token/owner ID и неимпортированным XLSX.
- `OPENAI_API_KEY` не настроен, поэтому Writing Examiner не прошёл live API smoke test.
- Railway resource ставки: $10/GB RAM-месяц, $20/vCPU-месяц, $0.15/GB volume-месяц. Постоянные 0.5 GB RAM дают около $5/месяц только за память; фактическое потребление и стоимость n8n ещё не измерены.
- n8n Cloud `saidaminov.app.n8n.cloud` показывает `Your trial is over`; апгрейд не оформлялся.
- Python integration commit `98088aa` запушен в `main`; Railway webhook deployment `b19a6de1-f992-49bf-9fbc-f90a94ae9fe6` и daily trigger `33860a39-2663-4a93-9e67-0b6a48ada079` получили `SUCCESS` на этом SHA.
- Live smoke: `/health` вернул HTTP 200; POST `/internal/scheduled-event` с неверным внутренним секретом вернул HTTP 403. Валидный production event не отправлялся.
- n8n deployment `25ca0939-dd90-435b-bb29-8d93a1028cb2` получил `SUCCESS`, n8n 2.43.5 завершил миграции и слушает порт 5678. Owner setup пока не сохраняется к моменту текущей проверки; явно настроен `N8N_USER_FOLDER` для persistent volume.
- На 2026-10-14 14:42 UTC короткий metrics snapshot после запуска: RAM current 0.060 GB, max 0.147 GB. Усреднение за час содержит интервалы до deployment, поэтому точное устойчивое среднее ещё не установлено; собрать не менее 10 минут свежих метрик.
- Публичного домена нет; owner bootstrap, workflow import и credentials остаются невыполненными. Секретные значения не читались и не помещались в отчёт.
- В репозитории есть восемь workflow схем для проверки, но пользователь запросил сборку визуальных nodes непосредственно в n8n, поэтому JSON не импортировался. Текущие `tests/test_n8n_workflow_exports.py`: 2 passed; `scripts/scan_secrets.py` не нашёл вероятных секретов.
- Получен живой 24-часовой snapshot памяти Python webhook: average 0.0047 GB, max 0.2524 GB, current 0.2313 GB; это не метрика n8n. Для ежедневного trigger все метрики были нулевыми в срезе. Фактическая память n8n измерима только после его deployment.

## Следующие действия

1. Владелец добавляет три отсутствующие переменные бота/OpenAI в Railway Variables и передаёт исходную книгу курса.
2. Владелец повторно создаёт owner в `/setup`; затем проверить login persistence после restart. Не вводить пароль вместо пользователя.
3. Измерить расход n8n и сверить прогноз с лимитом ~$5/month без изменения Railway тарифа.
4. Настроить проверенное резервное копирование и тест восстановления persistent volume.
5. Повторить live Telegram/OpenAI smoke tests и E2E workflow tests после конфигурации.

## Повторная проверка 2026-10-14 14:49 UTC

- Текущий статус Railway environment: 3 сервиса, 0 критических/предупреждений и 0 недавних падений; Python Online, daily cron Ready, n8n Online. Активные deployment: webhook `8286e427-16c3-4702-bc84-d8e4cfbc5076`, cron `74e814f6-e500-4bcc-ac5c-53ea1d4fbf8d`, n8n `ee398c7c-d463-4949-b709-6209ce206e17` — все `SUCCESS`.
- n8n local health endpoint и приватный запрос из n8n в `http://ielts-webhook.railway.internal:8080/health` вернули HTTP 200.
- Railway metrics за 1 час (61 samples): n8n RAM current 0.452 GB, max 0.874 GB; CPU current 0.0017, max 0.1745. Среднее RAM 0.077 GB и min 0 содержат интервалы до запуска n8n и не являются полезной steady-state оценкой. Пик выше 0.5 GB; для проверки бюджета нужно наблюдать дольше.
- GitHub `main` commit `72c7f6` уже развернут; рабочее дерево чистое.

## Реализация weekly logic

Последнее изменение кода реализует недельный отчёт по событиям последних семи дней и формирует smart reminder из фактически незавершённых блоков. В Railway текущая ревизия этой правки ещё не выкатывалась на момент создания этого отчёта; после push проверить deployment и health.
# Latest live status — 2026-10-14

Railway production environment has no pending changes. `ielts-webhook` is `SLEEPING` (persistent volume `/data`), `ielts-daily-trigger` is `SUCCESS` with cron `0 19 * * *`, and `ielts-n8n` is `SUCCESS` (deployment `0bd24930-58c6-4322-a9ab-c734b0769b23`, persistent volume `/home/node/.n8n`). The n8n domain is reachable, but owner sign-in/editor access is still blocked; the owner said they cannot enter the password now. No workflows were activated and no additional reset was attempted. This is a deployment health snapshot, not proof of complete application functionality.

At 16:46 UTC, one-hour metrics showed n8n memory 0.413–0.663 GB (current 0.437 GB) and average CPU ~0.023 core. The bounded HTTP-log sample peaked at 146 requests/minute during a Chrome editor load, with 501 returned entries all from one client IP; 5 HTTP 502 responses were associated with `/rest/push` or `/healthz` during the redeploy window. The full request sample and limitations are in `RAILWAY_AUDIT.md`.
