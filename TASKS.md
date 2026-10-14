# IELTS AI Tutor — план и статус

Исходный проект был пустым, Git-репозитория и файла `IELTS_7_5_250_istoriy_26_nedel_182_dnya_PRO.xlsx` нет. Переменные `TELEGRAM_BOT_TOKEN` и `OPENAI_API_KEY` не настроены. Исходные материалы курса не создаются и не подменяются вымышленными.

## Дополнение: n8n, эксплуатация и security status (2026-10-14)

- [x] Проверить открытые Chrome вкладки и подключения: Railway авторизован; n8n Cloud доступен как завершившийся trial; GitHub browser просит включить 2FA.
- [x] Проверить n8n workflows/credentials без чтения секретных значений: один пустой неактивный workflow без триггеров и Telegram/Header Auth credential metadata.
- [x] Проверить Railway проекты, workload, цену, sleep и health endpoint; посторонние проекты не менялись.
- [x] После исправления прав `/data` оба IELTS Railway сервиса успешно развернулись; `/health` вернул HTTP 200.
- [x] Создать `TEST_REPORT.md`, `SECURITY_REPORT.md`, `DEPLOYMENT_REPORT.md`, `N8N_WORKFLOWS.md`.
- [ ] Развернуть и защитить self-hosted n8n Community, затем создать и проверить 8 workflows. Не публиковать n8n до bootstrap владельца и его пароля.
- [ ] Связать workflows с авторизованными внутренними Python-операциями. Сейчас реализован только защищённый идемпотентный daily delivery; остальных event endpoints нет.
- [ ] Владелец должен добавить bot token, numeric owner ID и OpenAI API key в Railway Variables, передать исходный XLSX и создать owner password n8n через защищённую веб-форму.
- [ ] Проверить Telegram, Writing API, все 11 функций, восстановление volume и workflow E2E после подключения нужных материалов и credentials.
- [ ] После снятия GitHub billing restriction повторить remote CI и secret scan.

### Блокеры и бюджет

- n8n Cloud `saidaminov.app.n8n.cloud` показывает `Your trial is over`; апгрейд/оплата не выполнялись.
- Railway workspace сейчас Hobby. Usage UI: $0.20 текущего resource usage, $5 included usage, $0.00 текущего счёта. Снимок периода Oct 11–Nov 11, не прогноз.
- По ставкам Railway постоянно работающий n8n при 0.5 GB RAM обойдётся примерно в $5/месяц только за память, до CPU, storage и egress. Footprint инстанса не измерен.
- Безопасная первичная настройка n8n требует владельца и его пароля. Не создавать публичный незащищённый редактор и не вводить пароль вместо владельца.
- GitHub browser попросил включить 2FA; коды не вводились. GitHub Actions отдельно заблокирован billing/spending-limit сообщением.

## План

- [x] Осмотреть проект, инструкции, окружение, секреты и наличие XLSX.
- [x] Создать безопасный каркас, конфигурацию, запуск и deploy-файлы.
- [ ] Довести обучение до полного соответствия: базовые уроки, словарь, SRS, журнал ошибок, тесты, темы и streak реализованы; адаптивный курс зависит от исходной программы, daily quiz пока ограничен 10 общими вопросами.
- [x] Реализовать schema-driven импорт XLSX с валидацией и повторяемым импортом; фактические данные не проверены, так как исходная книга отсутствует.
- [ ] Завершить Telegram UI: owner-only доступ, меню, quiz/SRS/Writing реализованы; UX остальных разделов и Telegram smoke test не завершены.
- [ ] Завершить Writing Examiner: сервис с JSON и ограничениями реализован; автоопределение типа задания/агрегация повторных ошибок и live API test не завершены.
- [ ] Завершить напоминания/weekly report: расписание сохраняется и восстанавливается; уведомления о SRS/незавершённых блоках и полный недельный срез статистики отсутствуют.
- [x] Добавить тесты и выполнить pytest, Ruff, mypy, compileall и сканирование секретов.
- [x] Документировать запуск, Railway, приватность, бюджет, ограничения и требуемые действия владельца.

## Текущее состояние

- Этап 1: завершён. Рабочая папка была пуста, Git отсутствует; Python 3.12.7 доступен.
- Реализованы и локально проверены: Python backend, aiogram handlers, SQLite, owner-only middleware, lessons, SRS, quiz, weekly exam, Writing examiner service, бюджетный guard, XLSX importer, сохранённые напоминания.
- Последний локальный прогон: 16 тестов проходят; Ruff чист по приложению/тестам/миграциям; mypy чист по 24 модулям приложения; compileall чист; сканер не нашёл секретных шаблонов.
- Alembic initial migration для 12 таблиц добавлена; тест проверил создание схемы и повторный `upgrade head`; `init_db()` применил её к `data/ielts.db`.
- Недостающий XLSX не был сконструирован. Код не содержит проверенных 182 уроков, 1750 слов и готовых материалов Reading/Listening.
- В этой среде отсутствуют `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, `OPENAI_API_KEY`; живой Telegram/OpenAI smoke test и Railway deployment не запускались.
- Исходная книга и ключи — единственные внешние блокировки для импорта/живых интеграций. Перед production требуется проверить модель/актуальные тарифы OpenAI, добавить постоянный том `/data`, настроить владельца, затем пройти Telegram и Writing smoke tests.
- Не завершены до полного production acceptance: интеграционные UI smoke tests; недельная агрегация отчёта; уведомления о SRS/незавершённых блоках; проверенные 182 дня и 1750 слов; процедура перехода legacy `create_all` БД на миграции.
