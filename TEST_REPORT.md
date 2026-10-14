# IELTS AI Tutor — тестовый отчёт

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

