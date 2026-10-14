# n8n workflow inventory and plan

Проверено 2026-10-14. Self-hosted n8n Community развернут отдельным Railway сервисом; восемь inactive workflow exports в `n8n/workflows/` ещё не импортированы.

## Состояние найденных экземпляров

- Chrome: Railway авторизован в workspace Hobby; n8n homepage открывается.
- n8n MCP: подключён к личному n8n project; найден один workflow `My workflow`, inactive, 0 triggers, без описания.
- Visible credential metadata: `Telegram account` (`telegramApi`) и `Header Auth account` (`httpHeaderAuth`). Значения не запрашивались; назначение и валидность для IELTS неизвестны.
- Cloud UI instance `saidaminov.app.n8n.cloud` показывает `Your trial is over`; платная подписка не оформлялась.
- n8n Cloud `saidaminov.app.n8n.cloud` показывает завершившийся trial и в self-hosted архитектуре не используется.
- Railway service `ielts-n8n` использует Docker image `n8nio/n8n:latest` и persistent volume 1 GB на `/home/node/.n8n`, регион `sfo`, без публичного домена, `ALWAYS` restart и выключенный sleep. Deployment `ee398c7c-d463-4949-b709-6209ce206e17` имеет `SUCCESS`; n8n 2.43.5 завершил миграции и слушает порт 5678.
- Первый запуск завершился `EACCES` при записи `/home/node/.n8n/config`, потому что Railway монтирует volume от root, а образ n8n по умолчанию работает как non-root. Добавлен Railway variable `RAILWAY_RUN_UID=0` согласно Railway volumes docs; новый deployment стартовал без этой ошибки. Это увеличивает привилегии процесса внутри контейнера.
- В Railway Variables настроены ключ шифрования credentials, `Asia/Tashkent`, отключённая диагностика, execution pruning и UID volume runtime. Значения секретов не помещены в Git или этот документ.
- Startup log подтвердил готовность редактора; публичный домен не создавался, editor остаётся private. В логах есть предупреждение, что Python task runner не доступен в image; текущие workflow exports используют HTTP Request nodes и не нуждаются в Python runner.
- Короткий предварительный Railway metrics snapshot сразу после запуска: RAM current около 60 MB, max около 147 MB; выборка содержит нули до успешного запуска, поэтому её нельзя считать устойчивым средним. Снять свежую метрику после 10 минут стабильной работы.

## Планируемые workflows

| Workflow | Роль | Python владеет состоянием | Статус |
|---|---|---|---|
| Daily IELTS Lesson | Раз в день запускает отправку плана урока | Да; защищённый идемпотентный `/internal/daily` уже есть | JSON подготовлен, не импортирован |
| Vocabulary Revision | Проверяет due words и просит бот прислать ревизию | Python endpoint `vocabulary_revision` читает SQLite и отправляет сообщение | JSON подготовлен, не импортирован |
| Daily Mini Test | Напоминает о тесте `/test` | Python endpoint `daily_mini_test` | JSON подготовлен, не импортирован |
| Smart Reminders | Пинги незавершённых блоков с учётом настроек | Python endpoint `smart_reminders`; проверяет quiet mode и настройки | JSON подготовлен, не импортирован |
| Weekly IELTS Exam | Напоминает о недельном учебном экзамене | Python endpoint `weekly_ielts_exam`; сессию создаёт существующий Telegram flow после выбора экзамена | JSON подготовлен, не импортирован |
| Weekly Progress Report | Отправляет готовую Python статистику | Python endpoint `weekly_progress_report` | JSON подготовлен, не импортирован |
| Application Health Monitoring | Проверяет `/health`; при проблеме — безопасное уведомление | Health endpoint и минимальное сообщение `application_health_monitoring`; нужен error path в workflow | JSON подготовлен, не импортирован |
| AI Budget Monitoring | Сигнал при приближении к лимиту | Python endpoint `ai_budget_monitoring` смотрит SQLite usage и порог 80%, без вызова OpenAI | JSON подготовлен, не импортирован |

## Файлы для импорта

JSON-шаблоны созданы в `n8n/workflows/`. Расписания используют timezone `Asia/Tashkent`; каждый шаблон выключен по умолчанию и не содержит секретов или фиктивного credential ID. Ежедневный урок вызывает `/internal/daily`; остальные события передают `event_type` и локальную дату в `/internal/scheduled-event`. Для защиты после owner setup нужно создать Header Auth credential `IELTS Internal API` с заголовком `X-Daily-Job-Secret` и выбрать его в HTTP Request nodes. Затем проверить точное Railway private DNS имя из n8n service; шаблоны ожидают `ielts-webhook.railway.internal:8080`. После активации Daily IELTS Lesson нужно отключить прежний Railway cron `ielts-daily-trigger`, иначе будут повторные уведомления. Health workflow использует отдельную Telegram credential и owner chat ID; сообщение содержит только нейтральный health alert, чтобы сработать даже при полном падении Python.

Генератор: `scripts/generate_n8n_workflows.py`; проверки exports: `tests/test_n8n_workflow_exports.py`. Health workflow выполняет запрос каждые 30 минут, до трёх раз повторяет health-check при cold start, затем отправляет общий admin alert через отдельный зашифрованный Telegram credential. Он может разбудить Python service. Для активации потребуется выбрать Telegram credential и указать chat ID владельца.

Python endpoint `POST /internal/scheduled-event` защищён `X-Daily-Job-Secret`. Тело содержит только `event_type` и `event_date`; событие дедуплицируется в `scheduled_events` по типу/дате. Тексты, ответы и учебная история не передаются в n8n. `/internal/daily` остаётся отдельной, уже защищённой операцией ежедневного урока.

Python event API развернут в commit `98088aa`; Railway webhook и cron deployment получили `SUCCESS`. Live `/health` вернул 200, неправильный event secret — 403. Положительная Telegram доставка не проверена, так как bot token и owner ID не настроены.

## Требования безопасности и интеграции

- Единственный Telegram update receiver: Telegram → Python. Не создавать Telegram Trigger в n8n.
- Передавать только короткие event type/key, без эссе, prompts или Telegram message history.
- Использовать Railway private networking к `ielts-webhook.railway.internal:8080`; для вызова endpoint нужен секрет в n8n credentials, не в workflow JSON.
- Для каждого event сохраняется server-side idempotency запись в Python DB. Уникальный ключ формируется из типа события и даты.
- Сохранять минимум execution data: не сохранять успешные/ручные runs, включить pruning с коротким сроком и лимитом; n8n execution data не должна содержать эссе или prompts.
- Railway volume и стабильный `N8N_ENCRYPTION_KEY` обязательны. Backup/restore нужно испытать.
- Первичную учётную запись владельца n8n создаёт владелец в защищённой форме. Нельзя публиковать незащищённый editor/setup wizard или вводить пароль вместо пользователя.
- Existing Cloud Telegram credential не экспортировался. Новый credential не настраивать до наличия bot token.

## Необходимое продолжение

1. Дать владельцу создать owner account в защищённой форме; до этого оставить n8n без публичного домена.
2. После 10 минут стабильной работы измерить RAM/CPU/egress и сверить расходы с бюджетом; не менять Railway plan.
3. Импортировать восемь workflows, настроить credentials и расписания, отключить прежний ежедневный Railway cron после включения workflow; провести E2E включая повторы и restart.
