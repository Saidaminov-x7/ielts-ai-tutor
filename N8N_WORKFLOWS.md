# n8n workflow inventory and plan

## Fresh live inventory (2026-10-14 22:29 Asia/Tashkent)

- Railway n8n is online on persistent volume `/home/node/.n8n`; HTTPS `/healthz` returned 200. SQLite contains one inactive `Daily IELTS Lesson` workflow and no credential records.
- Owner record exists and is enabled. Chrome password autofill is empty; do not reset/re-register. Visual editor operations require the owner to enter the password manually.
- The similar public-settings `planName` crash reported upstream was fixed before deployed version 2.43.5 (PR #35281), so the current auth/session failure needs fresh browser evidence and is not attributed to that older bug.
- Railway recorded `browserId check failed` on workflow/settings endpoints. A clean isolated sign-in tab is prepared to remove the stale browser binding; it still requires the owner to sign in before visual workflow edits can continue.
- `Daily IELTS Lesson` is incomplete: its Schedule Trigger has no interval. Keep Railway `ielts-daily-trigger` at `0 19 * * *` UTC until the replacement workflow is saved and passes delivery/deduplication tests.
- The other seven requested workflows are not created. No workflow execution or notification was verified. Live Telegram/OpenAI testing is blocked pending credential rotation/configuration.

## Fresh live checkpoint (2026-10-14 21:36 Asia/Tashkent)

- The Railway n8n login succeeded once (HTTP 200) and the editor loaded. A later workflow save failed with HTTP 401, and subsequent login attempts returned 401. Because the successful login is recorded, do not assume the password itself is the only problem; diagnose session/cookie/proxy behavior before another reset.
- Runtime version is 2.43.5. The public settings response lacks optional license fields, but n8n merged a frontend guard for that shape in release 2.34; there is not enough evidence to blame the response shape. Railway did log `browserId check failed` on the earlier session. The user cannot currently re-enter credentials in the clean isolated context, so do not reset the existing owner.
- The visual editor opened `Daily IELTS Lesson`; 19:00 was selected in the Schedule Trigger, but the session expired before the save was accepted. A fresh CLI export from the persistent Railway database confirms no change: one inactive workflow, interval `[{}]`, no executions. No workflows were activated or created beyond that saved draft.
- The workflow's HTTP node still uses the internal webhook URL and a `DAILY_JOB_SECRET` expression (the secret value was never exported or printed). Keep the existing Railway cron enabled to avoid losing daily delivery.
- The API log sample contains only one client IP among 501 detailed rows, with the observed 401/502 requests corresponding to this browser/editor activity and push/health reconnects. No unexpected outside source was observed in that sample.
- Blockers: stable owner session; missing Telegram/OpenAI owner credentials for live delivery; course workbook absent. The Python service has no Telegram token, owner Telegram ID, or OpenAI API key by variable name.
- `n8n audit` reports the HTTP Request node as an official risky node because it can make arbitrary requests; it is required for private Python event calls and remains editable only through authenticated n8n. Audit also found community-node installation enabled and the authenticated public API enabled. Deployment `0bd24930-58c6-4322-a9ab-c734b0769b23` is now `SUCCESS`; repeat audit confirms community-package installation is disabled.

## Post-recovery checkpoint (2026-10-14 21:30 Asia/Tashkent)

- Owner setup succeeded, but interactive sign-in still returns 401 after using the registered email. The user must manually re-enter the owner password; no more attempts/resets until then.
- One stored workflow only: `Daily IELTS Lesson`, inactive. Its HTTP Request targets Python's private `/internal/daily` endpoint and uses an env expression for `DAILY_JOB_SECRET`. The Schedule Trigger interval is empty; configure it before any test or activation.
- No Telegram/OpenAI credentials are present in n8n, and there are no saved credential rows. Seven workflows are not yet created. Do not disable the separate Railway cron before replacement is verified.

## Live state (2026-10-14 21:20 Asia/Tashkent)

- Read-only inspection of Railway's persistent SQLite database found one inactive `Daily IELTS Lesson` workflow: Schedule Trigger and HTTP Request nodes. It survived `n8n user-management:reset`.
- Its `X-Daily-Job-Secret` header uses an expression referencing `DAILY_JOB_SECRET`; no literal secret was stored in the header. No n8n credential rows exist.
- The owner setup returned HTTP 200; Chrome is now on `/signin`, awaiting the user to sign in. The workflow has not been end-to-end tested and is not active. Its Schedule Trigger has an empty interval and needs configuration in the editor.
- Seven other workflows remain uncreated. Do not disable the existing Railway cron until the replacement has passed authenticated-call, deduplication, persistence, and delivery checks.

## Live instance checkpoint (2026-10-14)

- The Railway instance is reachable over HTTPS but currently shows `/setup`; owner setup must be completed once more after the database path was aligned to the persistent volume. The user must enter their own password in Chrome. Then restart n8n and confirm the login/session persists before building workflows.
- Persistence is now configured and verified in Railway UI: volume mount `/home/node/.n8n`, `N8N_USER_FOLDER=/home/node`, `RAILWAY_RUN_UID=0`.
- No IELTS workflows are currently created in this Railway instance. Build eight workflows directly in the visual editor as requested; do not import the local JSON exports. Use the exports only as implementation notes.
- After owner setup, create and verify each schedule, protected Python call, deduplication behavior, and final notification outcome. Keep workflows inactive until the user credentials needed for notifications are present and tests pass.

Runtime update (2026-10-14): Railway self-hosted n8n is reachable at `https://ielts-n8n-production.up.railway.app` over HTTPS. Chrome currently shows `/setup`. Railway's persistent volume is mounted at `/home/node/.n8n`; `N8N_USER_FOLDER=/home/node` is explicit after the owner setup did not survive an earlier redeploy. The user requested building workflows directly in the n8n editor; do not import the local JSON exports. The n8n MCP connection is a separate expired-trial Cloud instance and must not be used for this Railway project.

Проверено 2026-10-14. Self-hosted n8n Community развернут отдельным Railway сервисом; восемь локальных workflow exports не импортировались. Сейчас в n8n нет созданных IELTS workflows.

## Состояние найденных экземпляров

- Chrome: Railway авторизован в workspace Hobby; n8n homepage открывается.
- n8n MCP: подключён к личному n8n project; найден один workflow `My workflow`, inactive, 0 triggers, без описания.
- Visible credential metadata: `Telegram account` (`telegramApi`) и `Header Auth account` (`httpHeaderAuth`). Значения не запрашивались; назначение и валидность для IELTS неизвестны.
- Cloud UI instance `saidaminov.app.n8n.cloud` показывает `Your trial is over`; платная подписка не оформлялась.
- n8n Cloud `saidaminov.app.n8n.cloud` показывает завершившийся trial и в self-hosted архитектуре не используется.
- Railway service `ielts-n8n` использует Docker image `n8nio/n8n:latest` и persistent volume 1 GB на `/home/node/.n8n`, регион `sfo`, HTTPS-домен, `ALWAYS` restart и выключенный sleep. Deployment `25ca0939-dd90-435b-bb29-8d93a1028cb2` имеет `SUCCESS`; n8n 2.43.5 слушает порт 5678. `N8N_USER_FOLDER=/home/node` задан явно, а `DAILY_JOB_SECRET` в n8n задан как Railway reference на сервис webhook; plaintext не читался.
- Первый запуск завершился `EACCES` при записи `/home/node/.n8n/config`, потому что Railway монтирует volume от root, а образ n8n по умолчанию работает как non-root. Добавлен Railway variable `RAILWAY_RUN_UID=0` согласно Railway volumes docs; новый deployment стартовал без этой ошибки. Это увеличивает привилегии процесса внутри контейнера.
- В Railway Variables настроены ключ шифрования credentials, `Asia/Tashkent`, отключённая диагностика, execution pruning и UID volume runtime. Значения секретов не помещены в Git или этот документ.
- Startup log подтвердил готовность редактора. В логах есть предупреждение, что Python task runner не доступен в image; IELTS workflows используют HTTP Request nodes и не нуждаются в Python runner.
- Короткий предварительный Railway metrics snapshot сразу после запуска: RAM current около 60 MB, max около 147 MB; выборка содержит нули до успешного запуска, поэтому её нельзя считать устойчивым средним. Снять свежую метрику после 10 минут стабильной работы.

## Планируемые workflows

| Workflow | Роль | Python владеет состоянием | Статус |
|---|---|---|---|
| Daily IELTS Lesson | Раз в день запускает отправку плана урока | Да; защищённый идемпотентный `/internal/daily` уже есть | Визуально создать в n8n после owner setup |
| Vocabulary Revision | Проверяет due words и просит бот прислать ревизию | Python endpoint `vocabulary_revision` читает SQLite и отправляет сообщение | Визуально создать в n8n после owner setup |
| Daily Mini Test | Напоминает о тесте `/test` | Python endpoint `daily_mini_test` | Визуально создать в n8n после owner setup |
| Smart Reminders | Пинги незавершённых блоков с учётом настроек | Python endpoint `smart_reminders`; проверяет quiet mode и настройки | Визуально создать в n8n после owner setup |
| Weekly IELTS Exam | Напоминает о недельном учебном экзамене | Python endpoint `weekly_ielts_exam`; сессию создаёт существующий Telegram flow после выбора экзамена | Визуально создать в n8n после owner setup |
| Weekly Progress Report | Отправляет готовую Python статистику | Python endpoint `weekly_progress_report` | Визуально создать в n8n после owner setup |
| Application Health Monitoring | Проверяет `/health`; при проблеме — безопасное уведомление | Health endpoint и Python event handler | Визуально создать в n8n после owner setup |
| AI Budget Monitoring | Сигнал при приближении к лимиту | Python endpoint `ai_budget_monitoring` смотрит SQLite usage и порог 80%, без вызова OpenAI | Визуально создать в n8n после owner setup |

## Целевая схема workflows для ручной сборки в редакторе

Пользователь просит собрать workflow nodes непосредственно в n8n; локальные JSON в `n8n/workflows/` не загружать. Все расписания используют `Asia/Tashkent`. Daily Lesson вызывает `/internal/daily`; остальные передают только `event_type` и дату в `/internal/scheduled-event`. Оба endpoint защищены `X-Daily-Job-Secret`, который передаётся как `={{ $env.DAILY_JOB_SECRET }}`; сам секрет закреплён за n8n Railway reference variable и не хранится в схеме. Private URL: `http://ielts-webhook.railway.internal:8080`. При включении daily workflow отключить прежний Railway cron, чтобы избежать избыточного ежедневного вызова.

Локальная проверка схемы: `scripts/generate_n8n_workflows.py`; `tests/test_n8n_workflow_exports.py` — 2 passed. Health схема исправлена на ежедневный health-check в 03:00 Tashkent; при ошибке уведомление отправляет Python, отдельный Telegram node не нужен. Реальные nodes не созданы: editor сейчас показывает `/setup`.

Python endpoint `POST /internal/scheduled-event` защищён `X-Daily-Job-Secret`. Тело содержит только `event_type` и `event_date`; событие дедуплицируется в `scheduled_events` по типу/дате. Тексты, ответы и учебная история не передаются в n8n. `/internal/daily` остаётся отдельной, уже защищённой операцией ежедневного урока.

Python event API развернут в commit `98088aa`; Railway webhook и cron deployment получили `SUCCESS`. Live `/health` вернул 200, неправильный event secret — 403. Положительная Telegram доставка не проверена, так как bot token и owner ID не настроены.

## Требования безопасности и интеграции

- Единственный Telegram update receiver: Telegram → Python. Не создавать Telegram Trigger в n8n.
- Передавать только короткие event type/key, без эссе, prompts или Telegram message history.
- Использовать Railway private networking к `ielts-webhook.railway.internal:8080`; секрет брать из Railway reference variable, не записывать plaintext в workflow.
- Для каждого event сохраняется server-side idempotency запись в Python DB. Уникальный ключ формируется из типа события и даты.
- Сохранять минимум execution data: не сохранять успешные/ручные runs, включить pruning с коротким сроком и лимитом; n8n execution data не должна содержать эссе или prompts.
- Railway volume и стабильный `N8N_ENCRYPTION_KEY` обязательны. Backup/restore нужно испытать.
- Первичную учётную запись владельца n8n создаёт владелец в защищённой форме. Нельзя публиковать незащищённый editor/setup wizard или вводить пароль вместо пользователя.
- Existing Cloud Telegram credential не экспортировался. Новый credential не настраивать до наличия bot token.

## Необходимое продолжение

1. Владелец повторно создаёт owner account на открытой HTTPS странице `/setup`; не вводить пароль за него. После этого проверить, что новый login сохраняется после рестарта.
2. После 10 минут стабильной работы измерить RAM/CPU/egress и сверить расходы с бюджетом; не менять Railway plan.
3. После owner setup вручную собрать восемь workflows в UI, назначить расписания, проверить авторизованный вызов Python и дедупликацию. Только после успешного E2E отключить прежний Railway daily cron.

## Повторная runtime проверка (2026-10-14 14:49 UTC)

n8n и Python Online, cron Ready. `/healthz` внутри n8n и Python private `/health` по адресу `ielts-webhook.railway.internal:8080` дали HTTP 200. Метрики n8n (окно 1 час, 61 samples): RAM 0.452 GB current / 0.874 GB max; CPU 0.0017 current / 0.1745 max. Окно содержит время до старта сервиса, поэтому среднее 0.077 GB и min 0 не отражают steady state. Owner setup и импорт шаблонов пока не выполнены; workflows оставлены выключенными.

## Обновлённая логика расписаний

Python формирует `weekly_progress_report` из фактических активностей за последние 7 дней: завершённые дни, личные слова, повторы, тесты, последнюю Writing оценку и слабую тему. `smart_reminders` перечисляет оставшиеся задания по тому же каталогу `TASKS`, что использует экран урока, и пропускает уведомление, если все блоки завершены. Unit-тесты покрывают границы недельного окна и оба сценария напоминания. Live доставка и импорт workflow ещё ожидают owner bootstrap и credentials.
# Latest checkpoint — 2026-10-14

The owner said they cannot enter the password right now. No additional reset or registration was attempted. Railway currently reports n8n deployment `0bd24930-58c6-4322-a9ab-c734b0769b23` as `SUCCESS`, with the 1 GB `ielts-n8n-data` volume mounted at `/home/node/.n8n`. This confirms service health and persistent-volume configuration, not successful owner login or database persistence.

The existing `Daily IELTS Lesson` workflow remains inactive. Its configured schedule was not saved, it has no verified execution, and it must not be activated while the Railway `ielts-daily-trigger` cron (`0 19 * * *`) remains in place. The requested eight workflows have not been fully built or E2E tested. Continue only after owner authentication works in the editor; build them visually as requested, then test deduplication and notification results before considering any change to the existing cron.
