# IELTS AI Tutor — план и статус

Исходный проект был пустым, Git-репозитория и файла `IELTS_7_5_250_istoriy_26_nedel_182_dnya_PRO.xlsx` нет. Переменные `TELEGRAM_BOT_TOKEN` и `OPENAI_API_KEY` не настроены. Исходные материалы курса не создаются и не подменяются вымышленными.

## Дополнение: n8n, эксплуатация и security status (2026-10-14)

- [x] Проверить открытые Chrome вкладки и подключения: Railway авторизован; n8n Cloud доступен как завершившийся trial; GitHub browser просит включить 2FA.
- [x] Проверить n8n workflows/credentials без чтения секретных значений: один пустой неактивный workflow без триггеров и Telegram/Header Auth credential metadata.
- [x] Проверить Railway проекты, workload, цену, sleep и health endpoint; посторонние проекты не менялись.
- [x] После исправления прав `/data` оба IELTS Railway сервиса успешно развернулись; `/health` вернул HTTP 200.
- [x] Создать `TEST_REPORT.md`, `SECURITY_REPORT.md`, `DEPLOYMENT_REPORT.md`, `N8N_WORKFLOWS.md`.
- [x] Развернуть отдельный Railway сервис self-hosted n8n Community и persistent volume 1 GB; private networking, `ALWAYS` restart, sleep off, timezone Asia/Tashkent, encryption key и execution pruning настроены.
- [x] Исправить права Railway volume через `RAILWAY_RUN_UID=0` после подтверждённого `EACCES`; повторный deployment `ee398c7c-d463-4949-b709-6209ce206e17` получил `SUCCESS`, миграции завершились, editor слушает `0.0.0.0:5678`.
- [x] Снять текущие метрики Railway после запуска: n8n RAM current ~452 MB, max ~874 MB за выборку 1 час; среднее ~77 MB искажено нулями до запуска, поэтому для оценки постоянной нагрузки использовать нельзя. CPU current ~0.0017, max ~0.1745.
- [x] Проверить Railway private networking из n8n: `ielts-webhook.railway.internal:8080/health` вернул HTTP 200; n8n `/healthz` также HTTP 200.
- [x] Исправить недельный отчёт: он считает учебные события, повторы, тесты, личные слова, Writing и слабую тему только за последние 7 дней; добавить unit-тест.
- [x] Исправить Smart Reminders: считать незавершённые блоки по фактическому списку заданий урока и показывать их названия; не использовать фиксированное предположение о 8 блоках.
- [x] Добавить безопасный `/whoami` bootstrap: доступен только в личном чате до настройки owner ID; после настройки действует обычный owner-only middleware.
- [ ] Создать owner account n8n в защищённой форме. Не публиковать публичный редактор до bootstrap владельца.
- [ ] Завершить owner bootstrap и защитить self-hosted n8n Community, затем создать и проверить 8 workflows.
- [x] Добавить защищённый Python endpoint для семи scheduled event типов и SQLite dedupe ledger; добавить миграцию и тесты. Daily Lesson использует существующий защищённый `/internal/daily`.
- [x] Подготовить восемь экспортируемых JSON-шаблонов n8n с расписанием Asia/Tashkent; шаблоны inactive, не содержат секретов и используют только Python API.
- [x] Добавить проверки полноты workflow exports, timezone, inactivity и отсутствия секретов; `pytest -q` — 23 passed.
- [ ] Создать восемь workflows на self-hosted n8n, настроить internal credential, расписания и E2E после owner bootstrap.
- [ ] Владелец должен добавить bot token, numeric owner ID и OpenAI API key в Railway Variables, передать исходный XLSX и создать owner password n8n через защищённую веб-форму.
- [ ] Проверить Telegram, Writing API, все 11 функций, восстановление volume и workflow E2E после подключения нужных материалов и credentials.
- [ ] После снятия GitHub billing restriction повторить remote CI и secret scan.

### Блокеры и бюджет

- n8n Cloud `saidaminov.app.n8n.cloud` показывает `Your trial is over`; апгрейд/оплата не выполнялись.
- Railway workspace сейчас Hobby. Usage UI: $0.20 текущего resource usage, $5 included usage, $0.00 текущего счёта. Снимок периода Oct 11–Nov 11, не прогноз.
- По текущей выборке Railway n8n использовал до ~0.874 GB RAM; постоянная стоимость зависит от фактического распределения ресурса и тарификации Railway. Текущий пик превышает ориентир 0.5 GB, среднее выборки недостоверно из-за нулей до запуска.
- n8n сейчас приватен и не имеет публичного домена. Безопасная первичная настройка требует, чтобы владелец создал пароль в защищённой форме; не открывать публичный незащищённый редактор и не вводить пароль вместо владельца.
- GitHub browser попросил включить 2FA; коды не вводились. GitHub Actions отдельно заблокирован billing/spending-limit сообщением.

## План

- [x] Осмотреть проект, инструкции, окружение, секреты и наличие XLSX.
- [x] Создать безопасный каркас, конфигурацию, запуск и deploy-файлы.
- [ ] Довести обучение до полного соответствия: базовые уроки, словарь, SRS, журнал ошибок, тесты, темы и streak реализованы; адаптивный курс зависит от исходной программы, daily quiz пока ограничен 10 общими вопросами.
- [x] Реализовать schema-driven импорт XLSX с валидацией и повторяемым импортом; фактические данные не проверены, так как исходная книга отсутствует.
- [ ] Завершить Telegram UI: owner-only доступ, меню, quiz/SRS/Writing реализованы; UX остальных разделов и Telegram smoke test не завершены.
- [ ] Завершить Writing Examiner: сервис с JSON и ограничениями реализован; автоопределение типа задания/агрегация повторных ошибок и live API test не завершены.
- [ ] Завершить напоминания/weekly report: Python расчёты weekly report и Smart Reminders исправлены; остаются live E2E доставки Telegram и проверка расписания после restart.
- [x] Добавить тесты и выполнить pytest, Ruff, mypy, compileall и сканирование секретов.
- [x] Документировать запуск, Railway, приватность, бюджет, ограничения и требуемые действия владельца.

## Текущее состояние

- Этап 1: завершён. Рабочая папка была пуста, Git отсутствует; Python 3.12.7 доступен.
- Реализованы и локально проверены: Python backend, aiogram handlers, SQLite, owner-only middleware, lessons, SRS, quiz, weekly exam, Writing examiner service, бюджетный guard, XLSX importer, сохранённые напоминания.
- Последний локальный прогон после исправлений отчёта, напоминаний и `/whoami`: 31 тест проходят; Ruff чист по app/tests/migrations; mypy чист по проверенным модулям; compileall чист; сканер не нашёл вероятных hard-coded секретов.
- Alembic initial migration для 12 таблиц добавлена; тест проверил создание схемы и повторный `upgrade head`; `init_db()` применил её к `data/ielts.db`.
- Недостающий XLSX не был сконструирован. Код не содержит проверенных 182 уроков, 1750 слов и готовых материалов Reading/Listening.
- В Railway отсутствуют `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, `OPENAI_API_KEY`; живой Telegram/OpenAI smoke test не запускался. Python и n8n deployment проверены отдельно как `SUCCESS`.
- Остались внешние блокировки для полного acceptance: владелец должен предоставить/настроить Telegram и OpenAI credentials и исходную книгу; создать owner account n8n через защищённую форму. После этого нужно выполнить Telegram/n8n/OpenAI E2E, подтвердить все 182 дня и исходные слова, проверить резервное копирование/восстановление и переход legacy `create_all` БД на миграции.

