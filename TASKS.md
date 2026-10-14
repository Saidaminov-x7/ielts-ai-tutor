# IELTS AI Tutor — план и статус

## Fresh code checkpoint (2026-10-14 22:59 Asia/Tashkent)

- Исправлена потеря последнего ответа в SRS: финальный callback теперь коммитит ответ, журнал активности, курсор и streak. Добавлен regression test.
- Добавлены slash-команды `/help`, `/today`, `/words`, `/review`, `/test`, `/writing`, `/progress`, `/mistakes`, `/settings`, использующие те же обработчики, что и кнопки меню. `/time` теперь валидирует время через `strptime`.
- Устранены mypy-ошибки в POSIX entrypoint и явно помечены зависимости без опубликованных type stubs.
- Локальная проверка: `pytest -q` **35 passed**; Ruff clean; mypy clean; compileall clean; secret scan clean; `git diff --check` clean.
- Эти изменения пока локальные и ещё не развернуты. Следующий шаг — commit/push в приватный `main` и проверка Railway webhook/cron deployment. n8n workflow automation остаётся ограничена входом владельца в чистой Chrome-вкладке и отсутствующими Telegram/OpenAI credentials/course workbook.

## Fresh live checkpoint (2026-10-14 22:29 Asia/Tashkent)

- Railway production inventory rechecked: `ielts-n8n` online (`0bd24930-58c6-4322-a9ab-c734b0769b23`), `ielts-webhook` sleeping with `/data` volume, and `ielts-daily-trigger` ready on `0 19 * * *` UTC. Railway reports 0 service issues, 0 recent failures, and no pending changes.
- n8n SQLite is on the persistent `/home/node/.n8n` volume. Read-only metadata confirms one active `global:owner` account with a password configured and one saved workflow; no credential rows. Password/hash/email were not read. Chrome's isolated n8n sign-in has no saved password, so do not reset or re-register the owner again.
- Auth investigation: upstream n8n issue #35194 describes a similar settings-store crash when public `/rest/settings` omits `license.planName`, but its fix (#35281) was merged and released before the deployed 2.43.5 version. Therefore this issue is not established as the current root cause; the earlier `browserId check failed` log and repeated 401s still need an authenticated browser console/network trace to diagnose.
- Follow-up log inspection confirms Railway recorded `browserId check failed` on `/rest/workflows/:workflowId` and `/rest/settings` during the reported session. Prepared a new isolated Chrome sign-in context with a freshly generated browser ID and no saved password. This safely avoids stale browser storage/cookies; the owner still must enter the existing account credentials once. No reset or auth bypass was applied.
- Only one workflow exists: inactive `Daily IELTS Lesson`; its Schedule Trigger is incomplete (`[{}]`). Keep the existing daily-trigger service enabled until an n8n replacement is saved, tested, and deduplication is proven. The other seven workflows remain uncreated.
- Fresh 24h traffic: n8n 930 requests (647 2xx, 211 3xx, 64 4xx, 8 5xx), webhook 19 (12 2xx, 6 4xx, 1 5xx), daily-trigger 0 public requests. The last-hour n8n sample is 166 requests with 1 5xx; no unexplained external client was established from aggregate metrics. These short-window metrics are not proof against future traffic.
- Bounded detailed n8n HTTP logs (last 60 minutes) returned 133 rows from one client source: 80×200, 40×304, 10×401, 1×403, 1×502, and 1 status-0 connection. The busiest paths were `/healthz` (32), `/rest/login` (9), and `/rest/settings` (7). This matches browser/editor activity in the sample; no client addresses were copied into reports.
- Latest health probes returned HTTP 200 for n8n `/healthz` and Python `/health`. Railway 24h health overview reports no deployment failures. RAM: n8n ~0.441 GB current / 0.874 GB max; sleeping webhook ~0.213 GB current / 0.459 GB max; cron idle at zero.
- Local verification: `pytest -q` 32 passed; Ruff clean; secret scanner found no likely hard-coded secrets. A first health-probe command failed due to PowerShell quoting, then the corrected probe succeeded. `git diff --check` still needs a final run after these documentation edits.
- Still blocked: stable n8n owner login requires the account owner to enter the password in Chrome; user said they cannot do so right now. Live Telegram/OpenAI remain blocked until the exposed Telegram token is rotated and replacement credentials are added directly to Railway. No credentials were viewed or tested.
- Next: when the owner can sign in, save and test workflows visually in n8n; verify internal call, state, idempotency, and notification; only then consider switching off the Railway daily trigger. Do not reset the existing owner again.

## Fresh live checkpoint (2026-10-14 21:36 Asia/Tashkent)

- n8n accepted an owner login once (`POST /rest/login` HTTP 200 at 16:29 UTC; `GET /rest/login` 200 at 16:31 UTC), then the editor save returned HTTP 401 at 16:34 UTC. Later sign-in attempts returned 401. This points to an expiring/invalid session or proxy/auth issue; it is not evidence that the user's password was wrong. No more resets or guessed password attempts.
- Deployed n8n version is 2.43.5. `/rest/settings` omits optional license fields, but the matching n8n frontend fix was merged and released in 2.34; that response shape alone does not prove this is the cause. Railway did log `browserId check failed` during the earlier session. A clean isolated sign-in page is prepared; the user cannot re-enter credentials right now, so owner login remains unresolved.
- The n8n editor showed the one `Daily IELTS Lesson` graph. A visual attempt to set 19:00 could not be saved before the session expired. A fresh export from the Railway volume confirms it is still inactive with `Schedule Trigger` interval `[{}]`; no other workflows exist. The old Railway daily trigger remains active at `0 19 * * *` UTC, so duplicate notifications were not introduced.
- Current Railway HTTP sample for n8n: 583 requests in the last hour (370 2xx, 154 3xx, 54 4xx, 5 5xx). Of 501 detailed log rows, all used one client IP; 4 5xx were `/rest/push` or `/healthz` 502s during connection/restart behavior. The 401s match the user's n8n login/editor session activity. No unexplained external client source appeared in this sample; this is a point-in-time check.
- Current n8n RAM is 0.584 GB (1-hour max 0.663 GB); it must stay awake to run n8n schedules. The Python webhook is configured for Railway sleep and is currently `SLEEPING`; daily-trigger is successful and idle between its cron runs.
- Railway variable names show `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, and `OPENAI_API_KEY` are not configured on the Python service. Thus real Telegram/OpenAI delivery and cost tests remain blocked. The exposed old Telegram token must be revoked/rotated before enabling delivery.
- Rerun checks: `pytest -q` 32 passed; Ruff clean; `scripts/scan_secrets.py` found no likely hard-coded secrets; `git diff --check` clean. Changes in this checkpoint are documentation only and are not deployed.
- `n8n audit` completed. It flagged the built-in HTTP Request node as generally capable of arbitrary network access (required for the private Python API), and reported community-node installation enabled. Set `N8N_COMMUNITY_PACKAGES_ENABLED=false`; deployment `0bd24930-58c6-4322-a9ab-c734b0769b23` reached `SUCCESS`, `/healthz` returned 200, and a repeat audit confirmed community packages disabled. The audit also reports the authenticated public API enabled; no workflow credentials or unsafe webhook were reported.
- Next: diagnose n8n session/proxy behavior without resetting the owner; once a stable authenticated session is available, save/test workflows visually. Only switch off the existing daily trigger after end-to-end delivery and idempotency pass.

## Latest live checkpoint (2026-10-14 21:30 Asia/Tashkent)

- Committed and pushed all reviewed local work to the private GitHub repo `Saidaminov-x7/ielts-ai-tutor`, commit `7fb241a` (`main`). GitHub API reports `private=true`.
- Railway webhook and daily-trigger deployments both built from exact SHA `7fb241ac28abb0b16f314a0e5dfc1a048a8bed02` and reached `SUCCESS`. Live webhook `/health` returned HTTP 200 after waking; unauthenticated `/internal/scheduled-event` returned HTTP 403, confirming the secret gate rejects unauthorized calls.
- Owner setup returned HTTP 200, but sign-in failed after the correct registered email was filled (the browser's previously prefilled email did not match the owner row). Do not make further login attempts until the user manually re-enters the chosen password. No password was read.
- n8n contains one inactive incomplete `Daily IELTS Lesson` workflow: Schedule Trigger interval is empty; HTTP Request points to private `POST /internal/daily` and references the Railway secret via expression. It has not been run. Other seven workflows remain uncreated.
- Current local checks: 32 pytest passed, Ruff clean, secret scanner clean, diff check clean before commit. Google Sheets instructions are in `GOOGLE_SHEETS_INTEGRATION.md`; direct Sheets API sync is not implemented yet. The source 182-day course workbook is still absent.
- Next: after successful owner login, configure and test the existing daily workflow, then create remaining workflows and verify deduplication, persistence and delivery. Keep the old daily cron until the new workflow passes.

## Latest live checkpoint (2026-10-14 21:20 Asia/Tashkent)

- The user-authorized `n8n user-management:reset` completed. The user then created the owner via Chrome; Railway logged `POST /rest/owner/setup` HTTP 200 and SQLite shows email/password fields present (their values were not read). n8n redirects to `/signin`; the user needs to sign in directly before editing. Do not reset again.
- Read-only SQLite inspection found one workflow (`Daily IELTS Lesson`), inactive, with Schedule Trigger and HTTP Request nodes. Its private URL targets `POST /internal/daily`; its `X-Daily-Job-Secret` header references `DAILY_JOB_SECRET` via expression, with no literal secret. No n8n credential rows exist. The schedule node has an empty interval object, so the saved workflow is incomplete and must be configured in the visual editor before testing or activation.
- Current Railway states: n8n `SUCCESS` with 1 GB volume at `/home/node/.n8n`; Python webhook `SLEEPING` with `/data` volume; daily trigger `SUCCESS` on `0 19 * * *`, `restartPolicyType=NEVER`. The three services are not three Git repositories: both Python services use the same GitHub repo; n8n uses `n8nio/n8n:latest`.
- Fresh 24-hour metrics: n8n RAM current 0.457 GB, max 0.874 GB; webhook current 0.213 GB, max 0.459 GB; daily trigger zero between executions. n8n HTTP logs sampled in Railway were from the user's Chrome session and included recent login 401s. The earlier short browser-driven request burst was not an unexplained external source. Webhook logs include cold-wake 502/499 and deliberate invalid-secret 403 checks.
- Local regression/security checks were rerun: pytest 32 passed; Ruff clean; `scripts/scan_secrets.py` found no likely hard-coded secrets; `git diff --check` clean.
- Next: user signs in; configure the saved daily schedule in the visual editor; test the private request and idempotency; then create the remaining seven workflows. Keep the daily trigger enabled until the n8n replacement is fully proven.

## Latest live checkpoint (2026-10-14 21:10 Asia/Tashkent)

- Owner setup finished in Chrome and persisted to Railway's `/home/node/.n8n` volume. After restart/redeploy, `/rest/settings` reports `showSetupOnFirstLoad=false`; Chrome is now at `/signin` because the browser session was reset. User needs to sign in directly in Chrome; do not ask for or handle the password.
- Fixed Railway proxy trust configuration: `N8N_PROXY_HOPS` was `0`, changed to `1`. Follow-up deployment `03fe6ffd-a4dd-4609-afab-5810edb45444` is `SUCCESS`; no new proxy trust validation error appears in startup logs.
- Live traffic: latest hour n8n 683 requests (519 2xx, 117 3xx, 43 4xx, 4 5xx), with all sampled requests from the single Chrome client IP. Peak minute 146 during editor load; most are UI/health requests and `/rest/push` reconnects. No other source IP or unexplained client traffic found. Webhook sleeping, daily cron idle with 0 CPU/RAM.
- No workflows were saved: latest n8n startup says `0 draft workflows, 0 published workflows`. Recreate workflows in the editor after sign-in; validate saving before publishing. Avoid duplicate daily delivery while the existing Railway cron is enabled.
- Next: owner sign-in, then build the eight visual workflows, resolve execution access to `DAILY_JOB_SECRET` without exposing its value, test private Python calls/dedupe and delivery, and review/disable the duplicate daily cron only after the n8n replacement is proven.

## Latest continuation checkpoint (2026-10-14 21:00 Asia/Tashkent)

- n8n recovery completed: `railway ssh` initially used the wrong default identity and the server closed the connection. Retried with the Railway-registered identity file explicitly (`--identity-file`); `n8n user-management:reset` returned `Successfully reset the database to default user state.`
- This reset is intentionally limited to n8n user accounts; workflows and the rest of the persistent database were not deleted by the command. The n8n owner must now be created once in the browser, with the user entering the password directly.
- Railway n8n remains `SUCCESS`, volume `ielts-n8n-data` mounted at `/home/node/.n8n`; Python webhook is sleeping while idle; daily-trigger is ready on cron `0 19 * * *`.
- Latest sampled n8n request logs were generated by the owner's Chrome IP: repeated `/rest/push` HTTP status 0 during reconnect, static assets, and failed `/rest/login` 401. No suspicious external burst is established by this sample. One proxy-trust validation error remains to fix after owner onboarding.
- No IELTS workflows exist in the active n8n database yet. Next: owner setup in Chrome, then create the eight requested workflows visually and verify each execution and deduplication.

## Latest continuation checkpoint (2026-10-14 20:49 Asia/Tashkent)

- Owner setup is complete and persisted: after Railway deployment `25ca0939-dd90-435b-bb29-8d93a1028cb2` restarted, `/rest/settings` returned HTTP 200 with first-load setup disabled. Do not register a second owner.
- Current blocker is n8n sign-in, not owner setup. The existing Chrome tab redirects to `/signin`; the password is user-held and was not retrieved. The editor cannot be used until the user signs in again in Chrome.
- Current n8n deployment and `/healthz` are healthy (HTTP 200). There are no published/draft IELTS workflows in this database yet.
- Railway inventory confirms 3 live services: Python webhook is SLEEPING when idle with `/data` volume; daily-trigger is SUCCESS with cron `0 19 * * *` and zero CPU/memory while idle; n8n is SUCCESS with `/home/node/.n8n` volume. No staged Railway changes.
- Environment variable names show `DAILY_JOB_SECRET` exists on both n8n and webhook. Required bot/OpenAI owner variables (`TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, `OPENAI_API_KEY`) are absent on the webhook; real Telegram/OpenAI tests and active reminders remain blocked until user adds them in Railway Variables. Values were never read.
- During Chrome reconnect, the n8n page produced repeated `/rest/push` requests with HTTP status 0 about every 2 seconds while `/healthz` stayed 200. This is consistent with a browser websocket reconnect loop, not evidence of an unexplained external request spike; closed the extra DevTools page. Recheck after sign-in.
- Last two-hour Railway resource snapshot: n8n memory current 0.443 GB, max 0.874 GB; webhook current 0.213 GB, max 0.459 GB and currently 0 CPU; daily-trigger current/max 0 CPU and 0 GB.
- Still pending: sign in to the existing n8n owner account; create eight workflows in the visual editor; verify each execution and idempotency; rotate the previously exposed Telegram token; configure missing live credentials; repeat request-spike audit after editor connection stabilizes.
- Follow-up from the owner sign-in screenshot: login was rejected. The official `/forgot-password` page says email recovery is unavailable because SMTP is not configured. n8n's documented `n8n user-management:reset` is the recovery path, but it removes all n8n user accounts; it requires Railway SSH into the service. No CLI/key registration or user reset has been performed. Keep workflows/database intact and hand off password creation to the user if an account reset is authorized.

## Current checkpoint (2026-10-14)

- n8n owner setup has returned to `/setup` after two successful `POST /rest/owner/setup` responses (HTTP 200). The latest n8n deployment started a fresh SQLite database (`version change: (none) -> 2.43.5`), so the owner was not present in the active database.
- Verified current persistence configuration in Railway: `ielts-n8n-data` is mounted at `/home/node/.n8n`, `N8N_USER_FOLDER=/home/node`, and `RAILWAY_RUN_UID=0`. The active deployment is `25ca0939-dd90-435b-bb29-8d93a1028cb2` (`SUCCESS`). A one-time owner setup in Chrome is still required, then restart and verify `/rest/login` no longer returns 401.
- Current local verification: `pytest -q` 32 passed; `ruff check app tests scripts migrations` clean; `scripts/scan_secrets.py` found no likely hard-coded secrets; `git diff --check` clean.
- Latest 24-hour Railway snapshot: n8n 299 HTTP requests (234 2xx, 58 3xx, 5 4xx, 2 5xx); webhook 16 (11 2xx, 4 4xx, 1 5xx); daily-trigger 0 public HTTP requests and zero CPU/RAM while idle. The two n8n 502s were `/rest/push` connection timeouts during deployment; webhook 502 was a cold wake timeout. No sustained request spike observed.
- Still pending: owner registration handoff; restart-based persistence proof; eight workflows built directly in the n8n canvas and end-to-end verified; real Telegram/OpenAI credentials and source Excel required for live feature tests.

Latest runtime check (2026-10-14): all three Railway services have healthy deployment states; Python webhook sleeps when idle, cron is ready between scheduled runs, and self-hosted n8n is online. Seven-day request audit: webhook 16 requests (11 2xx, 4 deliberate auth-test 4xx, 1 cold-start 5xx); n8n 231 (204 2xx, 26 3xx, 1 4xx, no 5xx); cron 0 public HTTP requests. No unexplained burst was visible. Details: [RAILWAY_AUDIT.md](RAILWAY_AUDIT.md).

Latest n8n blocker: after redeploy Chrome returned to `/setup`. Persistent volume is `/home/node/.n8n`; `N8N_USER_FOLDER=/home/node` is now explicit. Railway deployment succeeded, but the editor still offers first-owner setup, so prior account data was not retained in the active database path. No IELTS workflows have been created yet. The user asked for direct visual workflow creation in n8n, not JSON import. Password entry remains a user handoff.

Исходный проект был пустым, Git-репозитория и файла `IELTS_7_5_250_istoriy_26_nedel_182_dnya_PRO.xlsx` нет. Переменные `TELEGRAM_BOT_TOKEN` и `OPENAI_API_KEY` не настроены. Исходные материалы курса не создаются и не подменяются вымышленными.

## Дополнение: n8n, эксплуатация и security status (2026-10-14)

- [x] Проверить открытые Chrome вкладки и подключения: Railway авторизован; n8n Cloud доступен как завершившийся trial; GitHub browser просит включить 2FA.
- [x] Проверить n8n workflows/credentials без чтения секретных значений: один пустой неактивный workflow без триггеров и Telegram/Header Auth credential metadata.
- [x] Проверить Railway проекты, workload, цену, sleep и health endpoint; посторонние проекты не менялись.
- [x] После исправления прав `/data` оба IELTS Railway сервиса успешно развернулись; `/health` вернул HTTP 200.
- [x] Создать `TEST_REPORT.md`, `SECURITY_REPORT.md`, `DEPLOYMENT_REPORT.md`, `N8N_WORKFLOWS.md`.
- [x] Развернуть отдельный Railway сервис self-hosted n8n Community и persistent volume 1 GB; private networking, `ALWAYS` restart, sleep off, timezone Asia/Tashkent, encryption key и execution pruning настроены.
- [x] Исправить права Railway volume через `RAILWAY_RUN_UID=0` после подтверждённого `EACCES`; повторный deployment `ee398c7c-d463-4949-b709-6209ce206e17` получил `SUCCESS`, миграции завершились, editor слушает `0.0.0.0:5678`.
- [x] Снять текущие метрики Railway после запуска: n8n RAM current ~452 MB, max ~874 MB за выборку 1 час; среднее ~77 MB искажено нулями до запуска, поэтому для оценки постоянной нагрузки использовать нельзя. CPU current ~0.0017, max ~0.1745.
- [x] Проверить Railway private networking из n8n: `ielts-webhook.railway.internal:8080/health` вернул HTTP 200; n8n `/healthz` также HTTP 200.
- [x] Исправить недельный отчёт: он считает учебные события, повторы, тесты, личные слова, Writing и слабую тему только за последние 7 дней; добавить unit-тест.
- [x] Исправить Smart Reminders: считать незавершённые блоки по фактическому списку заданий урока и показывать их названия; не использовать фиксированное предположение о 8 блоках.
- [x] Добавить безопасный `/whoami` bootstrap: доступен только в личном чате до настройки owner ID; после настройки действует обычный owner-only middleware.
- [x] Owner account сохранён в persistent volume; повторная регистрация не нужна. Остаётся войти в чистой вкладке Chrome с паролем, который знает только владелец.
- [ ] После входа вручную собрать 8 визуальных workflows в n8n и проверить их; не импортировать JSON.
- [x] Добавить защищённый Python endpoint для семи scheduled event типов и SQLite dedupe ledger; добавить миграцию и тесты. Daily Lesson использует существующий защищённый `/internal/daily`.
- [x] Подготовить восемь экспортируемых JSON-шаблонов n8n с расписанием Asia/Tashkent; шаблоны inactive, не содержат секретов и используют только Python API.
- [x] Добавить проверки полноты workflow exports, timezone, inactivity и отсутствия секретов; `pytest -q` — 23 passed.
- [ ] Создать восемь workflows непосредственно в редакторе self-hosted n8n; расписания, безопасный вызов Python, dedupe и E2E пока не проверены.
- [ ] Владелец должен добавить bot token, numeric owner ID и OpenAI API key в Railway Variables, передать исходный XLSX и создать owner password n8n через защищённую веб-форму.
- [ ] Проверить Telegram, Writing API, все 11 функций, восстановление volume и workflow E2E после подключения нужных материалов и credentials.
- [ ] После снятия GitHub billing restriction повторить remote CI и secret scan.

### Блокеры и бюджет

- n8n Cloud `saidaminov.app.n8n.cloud` показывает `Your trial is over`; апгрейд/оплата не выполнялись.
- Railway workspace сейчас Hobby. Usage UI: $0.20 текущего resource usage, $5 included usage, $0.00 текущего счёта. Снимок периода Oct 11–Nov 11, не прогноз.
- По текущей выборке Railway n8n использовал до ~0.874 GB RAM; постоянная стоимость зависит от фактического распределения ресурса и тарификации Railway. Текущий пик превышает ориентир 0.5 GB, среднее выборки недостоверно из-за нулей до запуска.
- n8n сейчас приватен и не имеет публичного домена. Безопасная первичная настройка требует, чтобы владелец создал пароль в защищённой форме; не открывать публичный незащищённый редактор и не вводить пароль вместо владельца.
- GitHub browser попросил включить 2FA; коды не вводились. GitHub Actions отдельно заблокирован billing/spending-limit сообщением.

## План

- [x] Осмотреть проект, инструкции, окружение, секреты и наличие XLSX.
- [x] Создать безопасный каркас, конфигурацию, запуск и deploy-файлы.
- [ ] Довести обучение до полного соответствия: базовые уроки, словарь, SRS, журнал ошибок, тесты, темы и streak реализованы; адаптивный курс зависит от исходной программы, daily quiz пока ограничен 10 общими вопросами.
- [x] Реализовать schema-driven импорт XLSX с валидацией и повторяемым импортом; фактические данные не проверены, так как исходная книга отсутствует.
- [ ] Завершить Telegram UI: owner-only доступ, меню, quiz/SRS/Writing реализованы; UX остальных разделов и Telegram smoke test не завершены.
- [ ] Завершить Writing Examiner: сервис с JSON и ограничениями реализован; автоопределение типа задания/агрегация повторных ошибок и live API test не завершены.
- [ ] Завершить напоминания/weekly report: Python расчёты weekly report и Smart Reminders исправлены; остаются live E2E доставки Telegram и проверка расписания после restart.
- [x] Добавить тесты и выполнить pytest, Ruff, mypy, compileall и сканирование секретов.
- [x] Документировать запуск, Railway, приватность, бюджет, ограничения и требуемые действия владельца.

## Текущее состояние

- Этап 1: завершён. Рабочая папка была пуста, Git отсутствует; Python 3.12.7 доступен.
- Реализованы и локально проверены: Python backend, aiogram handlers, SQLite, owner-only middleware, lessons, SRS, quiz, weekly exam, Writing examiner service, бюджетный guard, XLSX importer, сохранённые напоминания.
- Последний локальный прогон после исправлений отчёта, напоминаний и `/whoami`: 31 тест проходят; Ruff чист по app/tests/migrations; mypy чист по проверенным модулям; compileall чист; сканер не нашёл вероятных hard-coded секретов.
- Alembic initial migration для 12 таблиц добавлена; тест проверил создание схемы и повторный `upgrade head`; `init_db()` применил её к `data/ielts.db`.
- Недостающий XLSX не был сконструирован. Код не содержит проверенных 182 уроков, 1750 слов и готовых материалов Reading/Listening.
- В Railway отсутствуют `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, `OPENAI_API_KEY`; живой Telegram/OpenAI smoke test не запускался. Python и n8n deployment проверены отдельно как `SUCCESS`.
- Остались внешние блокировки для полного acceptance: владелец должен предоставить/настроить Telegram и OpenAI credentials и исходную книгу; создать owner account n8n через защищённую форму. После этого нужно выполнить Telegram/n8n/OpenAI E2E, подтвердить все 182 дня и исходные слова, проверить резервное копирование/восстановление и переход legacy `create_all` БД на миграции.

# Checkpoint — 2026-10-14  (n8n owner access paused)

- The owner replied that they cannot enter the n8n password right now. No further password-reset command, account creation, or login attempt was performed. The clean Chrome sign-in tab remains the next user-dependent step.
- Live Railway snapshot: `ielts-webhook` is `SLEEPING` with its `/data` persistent volume; `ielts-daily-trigger` is `SUCCESS` on `0 19 * * *`; `ielts-n8n` is `SUCCESS` with `ielts-n8n-data` mounted at `/home/node/.n8n`. No staged Railway work exists.
- n8n remains inaccessible to workflow editing without owner authentication. Its one existing `Daily IELTS Lesson` workflow remains inactive and unverified; do not activate it or create duplicate schedules. The Railway daily cron remains the only verified scheduled deployment.
- Local verification was rerun: 32 pytest tests pass, Ruff is clean, secret scan reports no likely hard-coded secrets, and `git diff --check` is clean.
- Fresh live audit at 16:46 UTC rechecked all 3 Railway services and one-hour metrics/logs. n8n's capped sample had a 146-request/minute peak during Chrome editor load, all rows shared one client IP, 5 transient 502s, and continued login 401s. See `RAILWAY_AUDIT.md`; no unexplained multi-source burst was evident in the inspected sample.
- At 16:48 UTC, Railway aggregate request metrics independently confirmed 486 n8n requests / 1h (5xx 1.03%), 930 / 24h (5xx 0.86%), peak bucket 145/min at Chrome page load. Recent deploy logs say n8n 2.43.5 is ready; sign-in still requires owner input. Longer-term spike baseline is not yet available because the deployment is new.
- Remaining: owner sign-in/persistence check; visually build and E2E-check the requested n8n workflows; rotate exposed Telegram token and set required credentials directly in Railway; source workbook import and full live Telegram/OpenAI validation.
