# IELTS AI Tutor — security report

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
