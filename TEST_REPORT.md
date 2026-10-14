# IELTS AI Tutor — тестовый отчёт

## Fresh code verification (2026-10-14 22:59 Asia/Tashkent)

- `pytest -q`: **35 passed**, включая проверку сохранения последнего SRS-ответа и регистрации обязательных slash-команд.
- `ruff check app tests scripts migrations`: clean; `mypy app`: no issues; `python -m compileall -q app`: clean.
- `scripts/scan_secrets.py`: no likely hard-coded secrets; `git diff --check`: clean.
- Проверки выполнены на локальном коде. Изменения ещё не развёрнуты в Railway; реальные Telegram/OpenAI/n8n UI E2E остаются заблокированы отсутствующими credentials и входом в n8n.

## Fresh verification (2026-10-14 22:29 Asia/Tashkent)

- Earlier local run: `pytest -q`: **32 passed**. Current run and added coverage are in the checkpoint above.
- Live `GET https://ielts-webhook-production.up.railway.app/health`: HTTP 200. Live `GET https://ielts-n8n-production.up.railway.app/healthz`: HTTP 200.
- Railway environment health: 3 services, 0 with issues, 0 recent failures; n8n online, webhook sleeping, daily trigger ready.
- Traffic snapshot: n8n 930 requests/24h (8 5xx) and 166/last hour (1 5xx); webhook 19/24h (1 5xx); cron no public HTTP requests. This aggregate check does not identify request source; previous bounded log sample correlated the burst with owner's browser session.
- Detailed last-hour n8n HTTP logs: 133 rows, all from one client source; 10 login 401s, one 502, one 403, and one status-0 connection among the rows. No client address or sensitive headers were retained.
- Read-only n8n database metadata: one active owner account, one inactive workflow, zero credentials. No password hash or personal account fields were read. Chrome password autofill is empty, so no login or workflow execution could be tested in this turn.
- Upstream issue #35194 describes a similar optional `license.planName` settings crash, fixed by PR #35281 before deployed n8n 2.43.5. It is not evidence of this instance's current cause; the prior browserId warning and current 401s remain unresolved without a real authenticated browser trace.
- Follow-up Railway runtime logs confirm `browserId check failed` on workflow/settings requests. A fresh isolated Chrome sign-in context now has a new browser ID and no saved password. This may clear a stale browser/session binding; success still requires owner login and has not yet been verified.
- Functional limitations remain: n8n draft has an empty schedule interval; seven required workflows are absent; Telegram/OpenAI credentials are absent by name; real bot delivery and full end-to-end function coverage remain unverified.

## Fresh verification (2026-10-14 21:36 Asia/Tashkent)

- Local: `pytest -q` **32 passed**; `ruff check app tests scripts migrations` clean; `scripts/scan_secrets.py` found no likely hard-coded secrets; `git diff --check` clean.
- n8n UI: Chrome recorded a successful login (HTTP 200), but a later workflow-save request returned 401 and subsequent login attempts returned 401. The visual schedule selection was not saved. A fresh Railway CLI export confirms the only workflow remains inactive with an empty interval; no n8n execution or notification was tested.
- Runtime version is 2.43.5; Railway also logged `browserId check failed` for the earlier session. The public `/rest/settings` response lacks optional license fields, but the matching frontend guard shipped in n8n 2.34, so the response shape is not sufficient to identify a root cause. The user cannot re-enter credentials in the clean isolated context right now.
- Railway n8n last-hour sample: 583 requests, 5 5xx (4 `/rest/push`/`/healthz` reconnect/startup responses), 54 4xx. In 501 detailed log entries all requests came from one client IP; 401s aligned with this browser session. No unexplained client source was found in the sample.
- Current n8n memory: 0.584 GB; 1-hour max 0.663 GB. The Python webhook is `SLEEPING`; the daily trigger remains active on its existing schedule.
- Live Telegram, OpenAI, positive internal event delivery, and all eight n8n end-to-end workflows remain untested because required Python service variables are absent and n8n session authorization is unstable.
- `n8n audit` ran through the service CLI. It flagged the required built-in HTTP Request node as potentially capable of arbitrary host/network requests and noted community-package installation and authenticated public API settings. `N8N_COMMUNITY_PACKAGES_ENABLED=false` deployment reached `SUCCESS`; a repeat audit showed community packages disabled, and `/healthz` returned 200.

## Post-deploy smoke checks (2026-10-14 21:30 Asia/Tashkent)

- Railway deployment for exact SHA `7fb241ac28abb0b16f314a0e5dfc1a048a8bed02`: webhook `SUCCESS`; daily-trigger `SUCCESS`.
- Live `GET /health`: HTTP 200 after cold wake.
- Live POST to protected `/internal/scheduled-event` without auth: HTTP 403; unauthorized event rejected.
- n8n visual workflow execution not tested: owner setup succeeded but interactive login currently fails after correcting the sign-in email. The one saved workflow remains inactive and its schedule interval is empty.

## Latest verification (2026-10-14)

- `pytest -q`: **32 passed** (rerun 2026-10-14).
- `ruff check app tests scripts migrations`: clean (rerun 2026-10-14).
- `scripts/scan_secrets.py`: no likely hard-coded secrets found in project text files (rerun 2026-10-14).
- `git diff --check`: clean (rerun 2026-10-14).
- Railway latest-hour traffic: n8n 683 HTTP requests (519 2xx, 117 3xx, 43 4xx, 4 5xx). Every sampled request came from one Chrome IP; peak minute 146 during owner/editor loading. The 75 `/rest/push` status-0 requests, 401 login checks, and three `/rest/push` 502s correspond to the browser session and restarts. No second source or unexplained client traffic was seen. Webhook logged 2 health requests; cron had none and zero idle CPU/RAM.
- n8n owner setup completed. After restart and redeploy, `/rest/settings` returned 200 and `showSetupOnFirstLoad=false`, proving first-owner setup persisted on the volume. Chrome requires a fresh sign-in; password remains user-held.
- n8n `N8N_PROXY_HOPS` corrected from `0` to `1`; follow-up deployment succeeded and no new proxy-trust validation error appeared.
- Latest n8n startup reported **0 draft and 0 published workflows**. The unsaved canvas is not counted as a workflow; none has yet passed an n8n execution test.

## Verification follow-up (2026-10-14 21:20 Asia/Tashkent)

- Owner recovery reset succeeded; a new owner registration then returned HTTP 200. Chrome is now at `/signin`; interactive editor verification awaits the user signing in with the password they just entered.
- The persistent database now reports one inactive workflow, `Daily IELTS Lesson`. Metadata confirms its HTTP Request is `POST` to the private Python `/internal/daily` endpoint, with an environment expression for the auth header and no inline secret value.
- The saved Schedule Trigger has an empty interval object. The workflow is incomplete and untested; do not activate it.
- Current regression checks: pytest 32 passed; Ruff clean; secret scanner found no likely hard-coded secrets; `git diff --check` clean.

Дата проверки: 2026-10-14 (обновлено при добавлении n8n event API).

## Выполнено

- Локальные `python -m pytest -q`: **21 passed**; добавлены проверки n8n event endpoint, секретной авторизации, idempotency и новой Alembic migration.
- `python -m compileall -q app`: пройдено.
- `ruff check app tests migrations`: пройдено.
- `mypy app/scheduler/n8n_events.py --follow-imports=silent`: пройдено без ошибок. Полный `mypy app` на Windows сообщает о 4 POSIX-only вызовах в `container_entrypoint.py` и 3 отсутствующих типовых stub-пакетах APScheduler/openpyxl; новые ошибки event ledger исправлены.
- `scripts/scan_secrets.py`: не нашёл вероятных hard-coded секретов.
- `detect-secrets scan --all-files`: 0 findings, 0 файлов с находками после исключения каталогов локального кэша.
- Production health smoke test: `GET https://ielts-webhook-production.up.railway.app/health` вернул HTTP 200 и `{"status":"ok"}`.
- После push `98088aa` оба Python сервиса получили Railway `SUCCESS`; live POST `/internal/scheduled-event` с неверным секретом вернул 403. Валидный event не отправлялся, поскольку Telegram owner credentials отсутствуют.
- Исторический снимок проверки Python-сервисов: deployment `SUCCESS`; volume доступен webhook; Python sleep включён; cron настроен на `0 19 * * *` UTC.
- Unit tests покрывают owner-only, отказ при неправильном секрете, идемпотентность ежедневной доставки, budget guard, owner filtering и SQL-подобную строку.

## Не выполнено или не подтверждено

- GitHub Actions: jobs `quality` и `secret-scan` не стартовали. GitHub сообщил об ограничении оплаты/лимита расходов. Удалённые проверки не запускались.
- Live Telegram команды и inline-кнопки не проверялись: в Railway нет `TELEGRAM_BOT_TOKEN` и `OWNER_TELEGRAM_ID`.
- Live OpenAI Writing не проверялся: нет `OPENAI_API_KEY`; платных API-вызовов не сделано.
- Ежедневная отправка по настоящему курсу не подтверждена: отсутствует исходный XLSX с программой на 182 дня и словарём.
- На первом снимке self-hosted n8n ещё не был развернут. На текущем снимке n8n Community работает на Railway, но workflow exports не импортированы, owner account не создан; live n8n workflow E2E не выполнен.
- Полный end-to-end сценарий после рестарта/восстановления volume не запускался; резервное копирование не настроено.

## Текущий критерий

Сборка и HTTP health подтверждены. Доступность бота, отправка сообщений, работа GPT и ежедневный курс не объявляются готовыми до ввода владельцем credentials и исходных учебных материалов.
# Проверка workflow exports (2026-10-14)

- Сгенерированы восемь JSON workflow templates; все `active=false`, timezone `Asia/Tashkent`, включено отсутствие сохранения execution payloads в экспортных settings.
- Автотесты проверяют наличие всех восьми файлов, обращения к ожидаемым Python маршрутам, отсутствие Telegram/OpenAI ключевых шаблонов и незаписанный секрет header.
- Прогон после добавления тестов exports: `python -m pytest -q` — 23 passed.
- Импорт, owner credential, расписания в реальном n8n и E2E уведомления не проверены: Railway deployment остаётся staged, owner account и bot credentials отсутствуют.

## Повторная проверка и weekly logic (2026-10-14)

- `python -m pytest -q`: **26 passed**. Добавлены тесты расчёта недельного отчёта из реальных событий только за последние 7 дней и Smart Reminders для точного набора завершённых/незавершённых блоков.
- `ruff check app tests migrations`: чисто.
- `mypy app/scheduler/n8n_events.py app/learning/reports.py --follow-imports=silent`: без ошибок.
- `python -m compileall -q app`: пройдено.
- `scripts/scan_secrets.py`: вероятных hard-coded секретов не найдено; `git diff --check`: чисто.
- После последнего кода deployment не проверялся до push; live Telegram доставка и n8n workflow E2E остаются непроверенными из-за отсутствующих owner credentials и bootstrap.


## Telegram owner bootstrap (2026-10-14)

- Добавлена команда `/whoami` для безопасного получения собственного Telegram ID, если bot token уже настроен, но owner ID ещё неизвестен.
- До owner setup middleware пропускает только `/whoami` в личном чате; учебные команды и группы закрыты. После настройки owner ID эта команда тоже проходит обычную проверку владельца.
- Добавлено три unit-теста: bootstrap в личном чате, блокировка группы и отсутствие обхода заданного owner ID.
- Полный повторный прогон после этого изменения: `pytest -q` — **29 passed**; Ruff чист по `app/tests/migrations`; mypy проверенных модулей без ошибок; compileall и secret scan пройдены; `git diff --check` чист.


## Telegram rendering security

Непроверенные строки из импортированного курса, личного словаря, журнала ошибок и OpenAI feedback экранируются перед отправкой с HTML parse mode aiogram. Regression-тест проверяет, что разметка/теги превращаются в текст, а не в HTML.
# Latest regression/security check (2026-10-14 21:20 Asia/Tashkent)

- `rtk pytest -q`: 32 passed.
- `rtk ruff check app tests scripts migrations`: clean.
- `rtk python scripts/scan_secrets.py`: no likely hard-coded secrets found in project text files.
- `rtk git diff --check`: clean.
- n8n live metadata: one inactive, incomplete `Daily IELTS Lesson` workflow. It has not been executed; these local tests do not verify n8n or Telegram delivery.

