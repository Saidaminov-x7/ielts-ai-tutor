# Gates: IELTS Obsidian integration

OWNS: app/**, migrations/versions/**, tests/**, .env.example, README.md, GATES.md, obsidian-server/**

Scope: Save explicitly requested owner-scoped IELTS content into a private GitHub-backed Obsidian vault, idempotently and safely; host a hardened Obsidian UI behind GitHub OAuth and Railway idle sleep.

- [x] G1: Targeted Obsidian integration and bot behavior tests pass
  CHECK: rtk proxy python -m pytest -p no:cov -p no:anyio -q tests/test_obsidian_integration.py tests/test_bot_handlers.py tests/test_telegram_html.py && echo BOT_TESTS_OK
  EXPECT: BOT_TESTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=915ec584c467864513948d154108fc35d9aebd0a031033c8b995ad31fb53565e; exit=0; EXPECT=matched; output-sha256=4b6c53c02108afe4d200f7940da5bb34953dc6356b7c54f6568d4e18604e3146; output-bytes=115; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G2: Existing project test suite passes
  CHECK: rtk proxy python -m pytest -p no:cov -p no:anyio -q && echo PROJECT_TESTS_OK
  EXPECT: PROJECT_TESTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=ec263c898f4947c99ba49687016e78ed0ad3ad60089a054d8052db8fc7c7dd96; exit=0; EXPECT=matched; output-sha256=c5d6859cf3a862951faac5b11804001e959ed1ca51058a1ab940ab2420e1e8fe; output-bytes=120; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G3: Python source and migrations compile and lint cleanly
  CHECK: rtk proxy python -m compileall -q app tests migrations && rtk proxy ruff check app tests migrations && echo PYTHON_LINT_OK
  EXPECT: PYTHON_LINT_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=686fa7180f0588892a4efa5b7b0130a5f7268538dbde2a828112b30fd6929d29; exit=0; EXPECT=matched; output-sha256=bc3ae9c6c590360c29dca6c355ce86577fd77319f92aa80fc6eafc2901c08da7; output-bytes=35; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G4: Alembic has one merged head
  CHECK: rtk proxy python -m alembic heads && echo ALEMBIC_HEAD_OK
  EXPECT: ALEMBIC_HEAD_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=1d17298cb0109be9fc530d60debe62bb8ec3c39a8af9cc04deec55426a16fded; exit=0; EXPECT=matched; output-sha256=7ede3c04ead464a7c0f3db784da4ed22c318a9eb137b713afb815a718513a17a; output-bytes=42; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G5: Git diff contains no whitespace errors
  CHECK: rtk proxy git diff --check && echo DIFF_OK
  EXPECT: DIFF_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=025dc29ba47fcc593e3a3b76b685a6055a182c9a6afe527fdc77ca20346e737a; exit=0; EXPECT=matched; output-sha256=e92bd6185e84dff0c8254e0909c9c40ca6452d2e1edc62411f7b9029a537e629; output-bytes=359; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G6: Obsidian server container and private-vault initializer build
  MANUAL: Railway built image from commit de6a141 using obsidian-server/Dockerfile; build logs confirm the image push completed. Runtime logs confirm the custom initializer was copied and executed, then correctly reported the missing GITHUB_TOKEN. Local Docker CLI is unavailable.
  EVIDENCE: Railway deployment 544318ff-175d-40f9-8c60-8b608d338ce3 is SLEEPING; its build and deploy logs were read on 2026-10-16.

- [x] G7: Server config tests prove app privacy, OAuth setup, credential safety, and sleep instructions
  CHECK: rtk proxy python -m pytest -p no:cov -q tests/test_obsidian_server_config.py && echo SERVER_TESTS_OK
  EXPECT: SERVER_TESTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=7a21f4e890057296e92fd8e3637b7b8a4e737ba24b3e370c6a6831cb13dcf49c; exit=0; EXPECT=matched; output-sha256=837103a22c2a8675bcf56ab7359b8c08cd9bad8f25bb9ed0cbd2db988084df68; output-bytes=117; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [x] G8: Railway config matches ielts-webhook idle-sleep setting
  MANUAL: Compared live Railway service configs: ielts-webhook, obsidian-app, and obsidian-auth all have deploy.sleepApplication=true. Railway's configurable threshold is not one minute; document the platform's approximately 5–10 minute behavior.
  EVIDENCE: Live Railway config confirms sleepApplication=true on all three services; ielts-webhook and obsidian-app latest deployments both report SLEEPING. The obsidian-auth deployment config also has sleepApplication=true.

- [ ] G9: Obsidian and proxy deployment pass live OAuth and vault sync verification
  MANUAL: Verify app service has no public domain, OAuth2 Proxy blocks non-allowlisted GitHub accounts, allowed account can open the persistent vault, and bot notes plus Obsidian edits synchronize through the private GitHub repository.

- [x] G10: Private vault clone configures the environment credential helper before Git accesses GitHub
  CHECK: rtk proxy python -m pytest -p no:cov -q tests/test_obsidian_server_config.py && echo PRIVATE_CLONE_OK
  EXPECT: PRIVATE_CLONE_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=20f3ccbb4d9563aa5f85ba609a57ae33ce1a0a80dea76d4f4bf791df347907cd; exit=0; EXPECT=matched; output-sha256=bfeb52ac017f8f860fc00e8a2e0a01cded2bf4eeb3955ed54bf3e775bebb8416; output-bytes=118; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\vosil\Desktop\IELTS; path=b11ea96863f8/44 entries

- [ ] G11: Railway cold start serves the authenticated Obsidian desktop and clones the private vault without exposing credentials
  MANUAL: Verify the root page streams the desktop after the cold start, `/config/vault` is a Git checkout of the configured private repo, and runtime logs plus the Git remote contain no token.
