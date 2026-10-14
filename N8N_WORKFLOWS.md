# n8n workflow inventory and plan

Проверено 2026-10-14. n8n Community для Railway подготовлен отдельным сервисом, но пока не запущен. В репозитории подготовлены восемь inactive workflow exports в `n8n/workflows/`; они ещё не импортированы в живой экземпляр.

## Состояние найденных экземпляров

- Chrome: Railway авторизован в workspace Hobby; n8n homepage открывается.
- n8n MCP: подключён к личному n8n project; найден один workflow `My workflow`, inactive, 0 triggers, без описания.
- Visible credential metadata: `Telegram account` (`telegramApi`) и `Header Auth account` (`httpHeaderAuth`). Значения не запрашивались; назначение и валидность для IELTS неизвестны.
- Cloud UI instance `saidaminov.app.n8n.cloud` показывает `Your trial is over`; платная подписка не оформлялась.
- n8n Cloud `saidaminov.app.n8n.cloud` показывает завершившийся trial и в self-hosted архитектуре не используется.
- Для Railway подготовлен staged сервис `ielts-n8n` из Docker image `n8nio/n8n:latest` и отдельный persistent volume 1 GB на `/home/node/.n8n`. Сервис размещается в `sfo` рядом с Python webhook, без публичного домена, с `ALWAYS` restart и выключенным sleep.
- В staged variables настроены ключ шифрования credentials, `Asia/Tashkent`, отключённая диагностика, и pruning execution данных. Значения секретов не помещены в Git или этот документ.
- Railway отклонил попытку применить staged deployment: ответ инструмента — `Cancelled — the user did not approve this action`. Сервис и том остаются staged и не потребляют ресурсы; живого n8n процесса пока нет.
- После запуска измерить метрики Railway (memory current/average/max, CPU, network) не менее 10 минут; до этого фактическое потребление памяти неизвестно. 0.5 GB в прежней оценке — тарифное допущение, а не замер.

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

JSON-шаблоны созданы в `n8n/workflows/`. Расписания используют timezone `Asia/Tashkent`; каждый шаблон выключен по умолчанию и не содержит секретов или фиктивного credential ID. Ежедневный урок вызывает `/internal/daily`; остальные события передают `event_type` и локальную дату в `/internal/scheduled-event`. Для защиты после owner setup нужно создать Header Auth credential `IELTS Internal API` с заголовком `X-Daily-Job-Secret` и выбрать его в HTTP Request nodes. Затем проверить точное Railway private DNS имя из n8n service; шаблоны ожидают `ielts-webhook.railway.internal:8080`. После активации Daily IELTS Lesson нужно отключить прежний Railway cron `ielts-daily-trigger`, иначе будут повторные уведомления.

Генератор: `scripts/generate_n8n_workflows.py`; проверки exports: `tests/test_n8n_workflow_exports.py`. Health workflow выполняет запрос каждые 30 минут и может разбудить Python service. При полном сетевом отказе отправка уведомления через сам недоступный Python сервис невозможна; отдельный канал админ-оповещений пока не настроен.

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

1. Применить staged сервис n8n Community после успешного одобрения deployment; затем создать owner account в защищённом UI до публикации редактора.
2. После запуска измерить RAM/CPU/egress минимум 10 минут и сверить расходы с бюджетом ~$5/month; не менять Railway plan.
3. Создать восемь workflows, настроить расписания и провести E2E включая повторное выполнение и restart.
