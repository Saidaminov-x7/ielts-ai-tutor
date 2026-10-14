# IELTS AI Tutor — тестовый отчёт

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

