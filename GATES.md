# Gates: IELTS Obsidian integration

OWNS: app/**, migrations/versions/**, tests/**, .env.example, README.md, GATES.md

Scope: Save explicitly requested owner-scoped IELTS content into a private GitHub-backed Obsidian vault, idempotently and safely.

- [ ] G1: Targeted Obsidian integration and bot behavior tests pass
  CHECK: python -m pytest -p no:cov -p no:anyio -q tests/test_obsidian_integration.py tests/test_bot_handlers.py tests/test_telegram_html.py
  EXPECT: 100%
  EVIDENCE: pending

- [ ] G2: Existing project test suite passes
  CHECK: python -m pytest -p no:cov -p no:anyio -q
  EXPECT: 100%
  EVIDENCE: pending

- [ ] G3: Python source and migrations compile and lint cleanly
  CHECK: python -m compileall -q app tests migrations; ruff check app tests migrations
  EXPECT: All checks passed!
  EVIDENCE: pending

- [ ] G4: Alembic has one merged head
  CHECK: python -m alembic heads
  EXPECT: obsidian_save_v1 (head)
  EVIDENCE: pending

- [ ] G5: Git diff contains no whitespace errors
  CHECK: git diff --check
  EXPECT: git diff --check
  EVIDENCE: pending
