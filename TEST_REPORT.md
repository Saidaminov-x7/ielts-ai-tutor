# IELTS AI Tutor — тестовый отчёт

Дата проверки: 2026-10-14.

## Выполнено

- Локальные `pytest -q`: **19 passed** после исправления запуска контейнера и прав Railway volume.
- `python -m compileall -q app`: пройдено.
- Ruff и mypy: в последней локальной проверке проекта без ошибок (25 исходных файлов по зафиксированному предыдущему прогону).
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
- n8n workflows не запускались: существующий Cloud trial завершён; self-hosted экземпляр и workflows не созданы.
- Полный end-to-end сценарий после рестарта/восстановления volume не запускался; резервное копирование не настроено.

## Текущий критерий

Сборка и HTTP health подтверждены. Доступность бота, отправка сообщений, работа GPT и ежедневный курс не объявляются готовыми до ввода владельцем credentials и исходных учебных материалов.
