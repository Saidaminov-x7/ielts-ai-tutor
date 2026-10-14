# IELTS AI Tutor — security report

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
- Self-hosted n8n подготовлен staged, но не развернут; deployment blocked by Railway automatic review. Публичный домен не создавался до ручного owner setup.
- Workflow должен передавать только event type и дату через private networking; не передавать в n8n эссе, сообщения или промпты. Secret хранить как n8n credential, не включать его в workflow JSON.
- Логи Railway и ограничение webhook payload не доказывают отсутствие всех утечек. Внешний penetration test и проверка логов n8n не проводились.

## Вывод

На текущем снимке в tracked project files не найдено секретов. Критических подтверждённых утечек не обнаружено. Остаются блокеры конфигурации, GitHub remote scanning, резервного копирования и n8n bootstrap; абсолютное отсутствие утечек не гарантируется.
