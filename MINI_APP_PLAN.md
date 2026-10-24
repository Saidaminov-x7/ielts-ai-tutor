# IELTS Mini App implementation plan

## Audit result and scope

The initial audit used all ten requested roles (orchestrator, architect, frontend, backend, UX, QA, security, DevOps, reviewer, product analyst). All ten completed read-only inspections; no audit agent modified files or ran tests. The repository has no Mini App, browser API, or frontend toolchain. The current product is an aiohttp/aiogram bot using SQLAlchemy and SQLite. The local database inspected during the audit has zero course days and vocabulary rows; the source course workbook is absent.

Keep the configured single-owner model, existing SQLite database, Telegram bot, learning services, and Railway service. Add a React/TypeScript single-page app built into static assets and served by the existing aiohttp process on the same HTTPS origin. All API identity comes from a fresh, server-verified Telegram `initData` signature and must match `OWNER_TELEGRAM_ID`. Do not accept a client-supplied owner ID or score. Keep course-dependent sections explicit about missing imported materials; do not fabricate the 182-day program, Reading, or Listening content. Writing AI remains opt-in and budget-guarded.

## Implementation sequence

1. Add the Mini App API/auth contract and focused backend tests using existing domain services and models. Preserve existing bot and scheduled routes. No schema migration unless implementation proves one necessary.
2. Add the React/TypeScript responsive shell and real screens against the API: dashboard, lesson/task state, one-question-at-a-time quiz, vocabulary review, progress/errors, Writing, and notifications settings. Render unavailable-content and empty-data states honestly.
3. Build the frontend into the existing Python image and serve same-origin static assets. Extend CI with frontend type/build checks and image smoke checks where supported.
4. Run the requested Python/API/auth/persistence/frontend/browser/mobile checks locally. Independently review security and code changes, fix findings, and rerun relevant checks.
5. Report local readiness separately from Telegram, OpenAI, and Railway production verification. Do not deploy or issue paid AI calls.

## Acceptance gates

- Valid, fresh signed `initData` for the configured owner succeeds. Missing, malformed, tampered, stale, and non-owner credentials fail. Every API endpoint applies the same authenticated identity.
- API routes reuse existing domain services and scope every persisted record/session to the authenticated owner. Objective grading occurs server-side; duplicate submission does not create duplicate results.
- Existing webhook, `/health`, scheduled-event authentication, and SQLite persistence remain intact.
- Dashboard, lesson, test, vocabulary, progress/errors, Writing, and settings use persisted data. Missing course content, missing AI credentials, empty data, and network failures have truthful states.
- Quiz is a single in-app session with one visible question at a time, answer navigation, submission, result, and saved state.
- React app builds and runs locally from the Python service; responsive behavior is checked at mobile and desktop viewports.
- Telegram live integration, Railway deployment, and paid OpenAI API are **NOT TESTED** unless separate authorized credentials are provided.

## Known pre-existing work and review findings

Do not overwrite the existing dirty edits in `app/bot/handlers.py`, `app/learning/daily_tests.py`, `app/learning/lessons.py`, `app/learning/weekly_exams.py`, `tests/test_bot_handlers.py`, or `tests/test_learning.py`. The initial reviewer noted that the existing `WEEKLY_QUESTIONS` bank is not used, contains a potentially ambiguous passive-voice item, and contains an unidiomatic "Only few" answer. Reconcile these against the active diff before touching those files.

The security audit also found an existing `/internal/daily` vocabulary query that does not filter owner-specific rows. Fix it using the owner-or-shared policy after confirming against the current source, and cover it with a regression test.
