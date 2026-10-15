# Gates: IELTS Obsidian integration

OWNS: app/**, migrations/versions/**, tests/**, .env.example, README.md, GATES.md, obsidian-server/**

Scope: Save explicitly requested owner-scoped IELTS content into a private GitHub-backed Obsidian vault, idempotently and safely; host a hardened Obsidian UI behind GitHub OAuth and Railway idle sleep.

- [x] G1: Targeted Obsidian integration and bot behavior tests pass
  CHECK: python -m pytest -p no:cov -p no:anyio -q tests/test_obsidian_integration.py tests/test_bot_handlers.py tests/test_telegram_html.py && echo BOT_TESTS_OK
  EXPECT: BOT_TESTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=63276d78d530367a7cc58a83525c6e6433da995cc477ef3afcb923b98f965e52; exit=0; EXPECT=matched; output-sha256=152f0c6c889a42feb8e073a956caef35bf761996a3d02765bb4b060464dec0fa; output-bytes=116; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G2: Existing project test suite passes
  CHECK: python -m pytest -p no:cov -p no:anyio -q && echo PROJECT_TESTS_OK
  EXPECT: PROJECT_TESTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=65539f1751ae587652189fcb6c6a6ab8842a5b88db34c98d2294fbcad491728b; exit=0; EXPECT=matched; output-sha256=01107c4c259ec3edac0f68e712917dbe716127c0fd98a4bc13897146cdbcfbcc; output-bytes=130; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G3: Python source and migrations compile and lint cleanly
  CHECK: python -m compileall -q app tests migrations && ruff check app tests migrations && echo PYTHON_LINT_OK
  EXPECT: PYTHON_LINT_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=5f5dc1b553ad2140e2e27e16ef014381b8b055228cbbfc09277f8ea65839d599; exit=0; EXPECT=matched; output-sha256=bc3ae9c6c590360c29dca6c355ce86577fd77319f92aa80fc6eafc2901c08da7; output-bytes=35; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G4: Alembic has one merged head
  CHECK: python -m alembic heads && echo ALEMBIC_HEAD_OK
  EXPECT: ALEMBIC_HEAD_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=b3c70c812a889ae26d56a8320788eb51807157015870b60838e05c05abe47a8b; exit=0; EXPECT=matched; output-sha256=7ede3c04ead464a7c0f3db784da4ed22c318a9eb137b713afb815a718513a17a; output-bytes=42; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G5: Git diff contains no whitespace errors
  CHECK: git diff --check && echo DIFF_OK
  EXPECT: DIFF_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=f918581ef9ffed94279c159a4dc17a13f9a3c6b13065c0e61108b00a56b14539; exit=0; EXPECT=matched; output-sha256=d2cbb4415c6313f98858ae9e65a747f3dd87b23fedb344b4c17d82eefaa5557a; output-bytes=111; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [ ] G6: Obsidian server container and private-vault initializer build
  CHECK: docker build -q -f obsidian-server/Dockerfile -t ielts-obsidian-server-check . && echo OBSIDIAN_IMAGE_BUILT
  EXPECT: OBSIDIAN_IMAGE_BUILT
  EVIDENCE: pending

- [x] G7: Server config tests prove app privacy, OAuth setup, credential safety, and sleep instructions
  CHECK: python -m pytest -p no:cov -q tests/test_obsidian_server_config.py && echo SERVER_TESTS_OK
  EXPECT: SERVER_TESTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=56e8558f6870919d21364db049569ce4d1dc4818461658d3bca0c7569cb6b45d; exit=0; EXPECT=matched; output-sha256=fa18a63b02bb386c6074eb77341341b8ae21759c35b6f286be6c9bc462db638b; output-bytes=117; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G8: Railway config matches ielts-webhook idle-sleep setting
  MANUAL: Compared Railway service configs: ielts-webhook has deploy.sleepApplication=true and is currently SLEEPING; staged obsidian-app and obsidian-auth both have sleepApplication=true for their first deployment. Railway's configurable threshold is not one minute; document the platform's approximately 5–10 minute behavior.

- [ ] G9: Obsidian and proxy deployment pass live OAuth and vault sync verification
  MANUAL: Verify app service has no public domain, OAuth2 Proxy blocks non-allowlisted GitHub accounts, allowed account can open the persistent vault, and bot notes plus Obsidian edits synchronize through the private GitHub repository.
