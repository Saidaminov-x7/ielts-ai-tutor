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
- Self-hosted n8n Community `ielts-n8n` развернут в том же проекте как Docker image `n8nio/n8n:latest`, production region `sfo`, 1 GB volume `/home/node/.n8n`, private/unexposed service, `ALWAYS` restart, sleep disabled. Успешный deployment: `ee398c7c-d463-4949-b709-6209ce206e17`; runtime reports n8n 2.43.5 and successful migrations.
- Первоначальный запуск показал `EACCES` на volume; Railway variable `RAILWAY_RUN_UID=0` исправил доступ согласно Railway volume permissions guidance. Перезапуск успешен, публичный домен не создавался.
- Короткий metrics snapshot после старта: RAM current ~60 MB, max ~147 MB; среднее и min искажены предыдущими нулевыми интервалами до запуска. Это не 10-минутный steady-state замер. Выборка ещё не достаточна для точной оценки месячной стоимости.
- В Railway проекте размещён только предназначенный IELTS n8n сервис; другие проекты и службы не менялись.

## Данные и работа приложения

- SQLite хранится на persistent volume; при старте entrypoint чинит владельца `/data` и сбрасывает привилегии процесса до `appuser`.
- Daily trigger и sleep-конфигурация работают на уровне инфраструктуры, но ежедневная Telegram-доставка блокирована отсутствующими bot token/owner ID и неимпортированным XLSX.
- `OPENAI_API_KEY` не настроен, поэтому Writing Examiner не прошёл live API smoke test.
- Railway resource ставки: $10/GB RAM-месяц, $20/vCPU-месяц, $0.15/GB volume-месяц. Постоянные 0.5 GB RAM дают около $5/месяц только за память; фактическое потребление и стоимость n8n ещё не измерены.
- n8n Cloud `saidaminov.app.n8n.cloud` показывает `Your trial is over`; апгрейд не оформлялся.
- Python integration commit `98088aa` запушен в `main`; Railway webhook deployment `b19a6de1-f992-49bf-9fbc-f90a94ae9fe6` и daily trigger `33860a39-2663-4a93-9e67-0b6a48ada079` получили `SUCCESS` на этом SHA.
- Live smoke: `/health` вернул HTTP 200; POST `/internal/scheduled-event` с неверным внутренним секретом вернул HTTP 403. Валидный production event не отправлялся.
- Первичный n8n deployment упал из-за volume permission `EACCES`; UI Railway использован для подтверждённого пользователем применения настроек и повторного запуска. После добавления `RAILWAY_RUN_UID=0` deployment `ee398c7c-d463-4949-b709-6209ce206e17` получил `SUCCESS`, n8n 2.43.5 завершил миграции и слушает порт 5678.
- На 2026-10-14 14:42 UTC короткий metrics snapshot после запуска: RAM current 0.060 GB, max 0.147 GB. Усреднение за час содержит интервалы до deployment, поэтому точное устойчивое среднее ещё не установлено; собрать не менее 10 минут свежих метрик.
- Публичного домена нет; owner bootstrap, workflow import и credentials остаются невыполненными. Секретные значения не читались и не помещались в отчёт.
- В репозитории созданы восемь неактивных JSON-экспортов workflows в `n8n/workflows/`; тесты шаблонов проходят вместе с приложением (`pytest -q`: 23 passed), `scripts/scan_secrets.py` не обнаружил вероятных секретов. Шаблоны пока не импортированы в Railway n8n.
- Получен живой 24-часовой snapshot памяти Python webhook: average 0.0047 GB, max 0.2524 GB, current 0.2313 GB; это не метрика n8n. Для ежедневного trigger все метрики были нулевыми в срезе. Фактическая память n8n измерима только после его deployment.

## Следующие действия

1. Владелец добавляет три отсутствующие переменные бота/OpenAI в Railway Variables и передаёт исходную книгу курса.
2. Безопасно завершить первичную настройку self-hosted n8n (создание owner password в n8n UI); до этого не выдавать публичный домен.
3. Измерить расход n8n и сверить прогноз с лимитом ~$5/month без изменения Railway тарифа.
4. Настроить проверенное резервное копирование и тест восстановления persistent volume.
5. Повторить live Telegram/OpenAI smoke tests и E2E workflow tests после конфигурации.
