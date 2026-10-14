# IELTS AI Tutor — security report

## Fresh security checkpoint (2026-10-14 22:29 Asia/Tashkent)

- Local secret scan found no likely hard-coded secrets in project text files. This does not cover Git history, Railway variable values, browser storage, or prior chat content.
- Railway service descriptions exposed variable names only. The webhook service still lacks `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, and `OPENAI_API_KEY`. Values were not read. The previously exposed Telegram token must be revoked before enabling delivery.
- Read-only n8n metadata confirms one active owner account and zero stored n8n credential rows. Password/hash, email, and encryption-key values were not read.
- n8n is owner-authenticated, has a persistent volume, and is served over HTTPS. Public health endpoints returned 200; private/internal auth and live event delivery were not tested in this turn.
- Railway aggregate traffic for the last 24 hours: n8n 930 (8 5xx), webhook 19 (1 5xx); no unknown client source can be inferred from aggregate counts alone. The previous detailed log sample tied the browser burst to one client, but this remains a bounded observation, not a guarantee.
- Latest detailed n8n HTTP logs cover one hour and 133 rows from one client source; paths are mainly `/healthz`, `/rest/login`, and `/rest/settings`. The sample does not show a separate high-volume client; no IP address or secret header was copied into the report.
- Chrome's isolated sign-in form had no password autofill. No login was attempted, no account reset was repeated, and no credential was exposed. Workflow security review remains pending until visual editor access returns.
- The upstream n8n public-settings `planName` crash was fixed before 2.43.5 (PR #35281); it should not be claimed as the cause here. Diagnosing the remaining 401/browserId session issue needs a user-entered login and browser console/network evidence; no auth bypass was applied.
- Railway runtime logs do confirm browser-ID validation failures on settings and workflow requests. A separate isolated Chrome context is prepared with fresh site storage; it does not expose or alter account credentials and does not affect n8n's persistent database.

## Fresh security/runtime checkpoint (2026-10-14 21:36 Asia/Tashkent)

- Source scan rerun: no likely hard-coded secrets; `git diff --check` clean. This does not inspect Git history, browser storage, prior chat content, or unseen Railway variables.
- Railway `describe_service` was used to read variable names only. The webhook service does not have variable names `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, or `OPENAI_API_KEY`; values of existing secrets were not read.
- The exposed Telegram token must be revoked and replaced before any live delivery test; no token was used in this run. Live OpenAI/Telegram tests are unavailable until owner credentials are added directly in Railway.
- n8n remains protected by owner sign-in. A successful HTTP 200 login was followed by an editor-save 401 and subsequent login 401s. This is an unresolved session/authentication issue; no auth reset was repeated and no workflow was activated.
- In the latest bounded request sample, all 501 detailed n8n HTTP log entries used one client IP; 401s and transient push/health 502s aligned with the browser/editor session. This is not proof against future or unobserved traffic.
- The built-in `n8n audit` command completed. It flagged the workflow's HTTP Request node as an official risky node because that node can make arbitrary requests; this workflow uses it only for the private Python endpoint. It reported community packages enabled despite no package use; `N8N_COMMUNITY_PACKAGES_ENABLED=false` is deployed and a repeat audit confirms it is disabled. It also reports the authenticated public API enabled, which remains a configuration item to review. No credential-value finding was printed.
- n8n login remains unresolved: a prior successful login was followed by a workflow-save 401, and Railway logged `browserId check failed`. The deployed version is 2.43.5; a current upstream fix for absent optional license settings was released in 2.34, so the response omission alone is not treated as the root cause. No additional owner reset or browser-id security bypass was applied.

## Latest checks (2026-10-14)

- `scripts/scan_secrets.py` found no likely hard-coded secrets in project text files. `git diff --check` is clean. This is a source scan, not proof that no secret was ever exposed in chat, browser history, Railway logs, or Git history.
- Railway variable values were not read through the connector. The UI exposed only the two non-secret persistence settings needed for diagnosis: `N8N_USER_FOLDER=/home/node` and `RAILWAY_RUN_UID=0`. Secret values remain unreported.
- n8n is protected by owner setup, but the owner is currently absent from the active database (`/setup`; `/rest/login` 401). Complete owner setup and verify persistence before creating workflows.
- Current Railway request logs show two transient n8n `/rest/push` 502s during restart and one webhook cold-start 502. They contain no token values in the reviewed entries. No sustained request burst was observed.
- Telegram token was previously exposed in the work context; owner plans to rotate it. Do not use or repeat the old token. Telegram and OpenAI live calls remain blocked until replacement credentials are entered directly into Railway Variables.

Дата: 2026-10-14. Это ограниченная проверка текущего кода и настроек, не независимый внешний аудит.

## Проверенные меры

- GitHub repository `Saidaminov-x7/ielts-ai-tutor` приватный.
- Локальные `scripts/scan_secrets.py` и `detect-secrets` завершились без находок. GitHub Actions gitleaks не исполнялся: GitHub не выделил runners из-за billing/spending-limit состояния.
- Telegram webhook требует секретный header; владелец ограничивается middleware по Telegram user ID.
- Внутренний daily endpoint сверяет отдельный случайный секрет в constant-time и защищён уникальной записью на владельца/день.
- Новый `POST /internal/scheduled-event` использует тот же длинный внутренний Railway secret с constant-time compare; принимает только whitelist event type и дату, а не произвольный текст/Telegram ID. События получают уникальный `event_type:event_date` key в SQLite.
- Пользовательский ввод для Writing ограничен по размеру; тесты проверяют структурирование prompt, budget guard, owner filtering и SQL-подобную строку.
- Railway Variables используются для service secrets; секретные значения не читались через Railway, не помещались в файлы/отчёты/вывод.
- n8n MCP вернул только имена/типы двух credentials; их значения не читались. Существующих workflows с активными триггерами не найдено.
- n8n интерфейс показывает завершённый Cloud trial. Не выполнялись upgrade или передача пользовательских данных этому экземпляру.

## Риски и незакрытые пункты

- `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, `OPENAI_API_KEY` отсутствуют в конфигурации IELTS Railway. До их ввода бот остаётся в setup mode; Telegram webhook не активирован.
- GitHub Actions и удалённый secret scan остаются непроверенными, поскольку jobs не стартовали. Повторить после устранения GitHub billing restriction.
- У Railway persistent volume нет проверенной резервной копии и теста восстановления.
- n8n Cloud instance имеет существующие Telegram/Header Auth credentials, но их срок действия, sharing scopes, encryption-at-rest и владелец неизвестны. Значения не экспортировались.
- Self-hosted n8n Community развернут private/unexposed, постоянный volume и encryption key заданы. После `EACCES` на volume добавлен `RAILWAY_RUN_UID=0`, что запускает весь контейнерный процесс с UID 0; это рабочая настройка Railway, но повышает привилегии внутри контейнера. Публичный домен не создавался до owner bootstrap.
- Workflow должен передавать только event type и дату через private networking; не передавать в n8n эссе, сообщения или промпты. Secret хранить как n8n credential, не включать его в workflow JSON.
- Логи Railway и ограничение webhook payload не доказывают отсутствие всех утечек. Внешний penetration test и проверка логов n8n не проводились.

## Вывод

На текущем снимке в tracked project files не найдено секретов. Критических подтверждённых утечек не обнаружено. Остаются блокеры конфигурации, GitHub remote scanning, резервного копирования и n8n bootstrap; абсолютное отсутствие утечек не гарантируется.

## Повторная runtime проверка (2026-10-14 14:49 UTC)

Все три Railway сервиса имеют `SUCCESS`; environment показывает 0 активных warnings/criticals и 0 недавних падений. Два health запроса (n8n локальный и Python по Railway private networking) вернули HTTP 200. Метрики за 1 час включают период до запуска n8n: RAM current 0.452 GB, max 0.874 GB, среднее 0.077 GB (не использовать как steady-state). Текущий пик отражает заметное потребление памяти; нужно продолжить мониторинг, бюджет по этому короткому окну не подтверждён.

## Проверка Telegram HTML-экранирования (2026-10-14)

- Экранируются строки из учебных данных, словаря, журнала ошибок и модели перед отправкой в Telegram с глобальным HTML parse mode.
- Добавлен regression-тест со строками, похожими на HTML/script; результат проверен с Telegram-safe escaped markup.
- Полный прогон после изменений: 31 тест passed; Ruff чист; mypy проверенных модулей чист; compileall и секрет-скан пройдены.
# Latest checkpoint — 2026-10-14

- The owner cannot enter the n8n password at this time. No password was read or copied, and no further reset or login attempt was made. The n8n editor remains protected by authentication.
- Current Railway configuration lists a stable n8n data volume at `/home/node/.n8n`, and the latest n8n deployment is `SUCCESS`. This does not prove owner login or successful recovery after restart.
- Current environment snapshot lists names only; no variable values were read. The webhook service still lacks `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, and `OPENAI_API_KEY`. The previously exposed Telegram token must be revoked and replaced before any live delivery.
- Prior source scan and bounded log review are limited checks; they do not prove absence of exposure in Git history, browser state, or uninspected logs. No full security-audit claim is made.
