# IELTS AI Tutor — deployment report

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
- В Railway проекте нет n8n-сервиса. Другие проекты и службы не менялись.

## Данные и работа приложения

- SQLite хранится на persistent volume; при старте entrypoint чинит владельца `/data` и сбрасывает привилегии процесса до `appuser`.
- Daily trigger и sleep-конфигурация работают на уровне инфраструктуры, но ежедневная Telegram-доставка блокирована отсутствующими bot token/owner ID и неимпортированным XLSX.
- `OPENAI_API_KEY` не настроен, поэтому Writing Examiner не прошёл live API smoke test.
- Railway resource ставки: $10/GB RAM-месяц, $20/vCPU-месяц, $0.15/GB volume-месяц. Постоянные 0.5 GB RAM дают около $5/месяц только за память; фактическое потребление и стоимость n8n ещё не измерены.
- n8n Cloud `saidaminov.app.n8n.cloud` показывает `Your trial is over`; апгрейд не оформлялся.

## Следующие действия

1. Владелец добавляет три отсутствующие переменные бота/OpenAI в Railway Variables и передаёт исходную книгу курса.
2. Безопасно завершить первичную настройку self-hosted n8n (создание owner password в n8n UI); до этого не выдавать публичный домен.
3. Измерить расход n8n и сверить прогноз с лимитом ~$5/month без изменения Railway тарифа.
4. Настроить проверенное резервное копирование и тест восстановления persistent volume.
5. Повторить live Telegram/OpenAI smoke tests и E2E workflow tests после конфигурации.
