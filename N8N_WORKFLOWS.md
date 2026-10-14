# n8n workflow inventory and plan

Проверено 2026-10-14. На этом шаге n8n flows не создавались и не активировались.

## Состояние найденных экземпляров

- Chrome: Railway авторизован в workspace Hobby; n8n homepage открывается.
- n8n MCP: подключён к личному n8n project; найден один workflow `My workflow`, inactive, 0 triggers, без описания.
- Visible credential metadata: `Telegram account` (`telegramApi`) и `Header Auth account` (`httpHeaderAuth`). Значения не запрашивались; назначение и валидность для IELTS неизвестны.
- Cloud UI instance `saidaminov.app.n8n.cloud` показывает `Your trial is over`; платная подписка не оформлялась.
- Railway project `ielts-ai-tutor` имеет два Python-сервиса, n8n там нет.
- По Railway resource pricing постоянные 0.5 GB RAM обходятся примерно в $5/месяц только за RAM; n8n потребит также CPU, storage и network. Footprint не измерен.

## Планируемые workflows

| Workflow | Роль | Python владеет состоянием | Статус |
|---|---|---|---|
| Daily IELTS Lesson | Раз в день запускает отправку плана урока | Да; защищённый идемпотентный `/internal/daily` уже есть | Не подключён |
| Vocabulary Revision | Проверяет due words и просит бот прислать ревизию | Да; отдельного event endpoint нет | Не подключён |
| Daily Mini Test | Доступность теста и уведомление | Да; функция daily quiz есть, event endpoint не создан | Не подключён |
| Smart Reminders | Пинги незавершённых блоков с учётом настроек | Да; полноценный n8n event endpoint не подключён | Не подключён |
| Weekly IELTS Exam | Идемпотентное создание экзамена/уведомление | Да; exam session должна создаваться Python | Не подключён |
| Weekly Progress Report | Уведомление о готовом Python-отчёте | Да; статистика рассчитывается Python | Не подключён |
| Application Health Monitoring | Проверяет `/health`; безопасно сигналит о сбое | Health endpoint есть; admin notification endpoint отсутствует | Не подключён |
| AI Budget Monitoring | Читает агрегированные показатели Python и сигналит при пороге | Budget guard есть; безопасного агрегированного API нет | Не подключён |

## Требования безопасности и интеграции

- Единственный Telegram update receiver: Telegram → Python. Не создавать Telegram Trigger в n8n.
- Передавать только короткие event type/key, без эссе, prompts или Telegram message history.
- Для каждого event нужна server-side idempotency запись в Python DB и service-to-service auth; Railway private networking предпочтительнее публичного внутреннего API.
- Сохранять минимум execution data: не сохранять успешные/ручные runs, включить pruning с коротким сроком и лимитом; n8n execution data не должна содержать эссе или prompts.
- Railway volume и стабильный `N8N_ENCRYPTION_KEY` обязательны. Backup/restore нужно испытать.
- Первичную учётную запись владельца n8n создаёт владелец в защищённой форме. Нельзя публиковать незащищённый editor/setup wizard или вводить пароль вместо пользователя.
- Existing Cloud Telegram credential не экспортировался. Новый credential не настраивать до наличия bot token.

## Необходимое продолжение

1. Безопасно создать self-hosted n8n Community после первичного owner setup; включить Asia/Tashkent и ограничить execution retention.
2. Измерить реальную память/CPU/egress и сверить с согласованным бюджетом ~$5/month; не менять Railway plan.
3. Реализовать недостающие защищённые Python event endpoints и event-key idempotency.
4. Создать восемь workflows, настроить расписания и провести E2E включая повторное выполнение и restart.
