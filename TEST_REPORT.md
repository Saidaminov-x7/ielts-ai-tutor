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
- Railway оба сервиса: последний deployment `SUCCESS`; volume доступен вебхуку; режим sleep включён; cron настроен на `0 19 * * *` UTC.
- Unit tests покрывают owner-only, отказ при неправильном секрете, идемпотентность ежедневной доставки, budget guard, owner filtering и SQL-подобную строку.

## Не выполнено или не подтверждено

- GitHub Actions: jobs `quality` и `secret-scan` не стартовали. GitHub сообщил об ограничении оплаты/лимита расходов. Удалённые проверки не запускались.
- Live Telegram команды и inline-кнопки не проверялись: в Railway нет `TELEGRAM_BOT_TOKEN` и `OWNER_TELEGRAM_ID`.
- Live OpenAI Writing не проверялся: нет `OPENAI_API_KEY`; платных API-вызовов не сделано.
- Ежедневная отправка по настоящему курсу не подтверждена: отсутствует исходный XLSX с программой на 182 дня и словарём.
- n8n workflows не запускались: Cloud trial завершён; self-hosted сервис staged в Railway, но deployment был отклонён автоматическим review. Внутренний Python endpoint готов, но нет live n8n для E2E.
- Полный end-to-end сценарий после рестарта/восстановления volume не запускался; резервное копирование не настроено.

## Текущий критерий

Сборка и HTTP health подтверждены. Доступность бота, отправка сообщений, работа GPT и ежедневный курс не объявляются готовыми до ввода владельцем credentials и исходных учебных материалов.
