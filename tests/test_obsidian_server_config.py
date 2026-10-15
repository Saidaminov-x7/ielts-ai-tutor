from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "obsidian-server"


def test_obsidian_app_is_hardened_and_private_instructions_are_explicit():
    readme = (SERVER / "README.md").read_text(encoding="utf-8")

    assert "HARDEN_DESKTOP=true" in readme
    assert "disables its terminal, sudo" in readme
    assert "Do not make the\nObsidian service public." in readme
    assert "Contents read/write" in readme


def test_railway_sleep_setting_matches_webhook_with_platform_limit_documented():
    readme = (SERVER / "README.md").read_text(encoding="utf-8")

    assert "sleepApplication` mode" in readme
    assert "one-minute idle" in readme
    assert "roughly five minutes" in readme
    assert "open remote-desktop/WebSocket session may keep" in readme


def test_git_credential_helper_reads_token_from_environment_without_storing_it():
    helper = (SERVER / "git-credential-env").read_text(encoding="utf-8")
    initializer = (SERVER / "init-vault").read_text(encoding="utf-8")

    assert "GITHUB_TOKEN" in helper
    assert "password=%s" in helper
    assert "credential.helper" in initializer
    assert "git clone --single-branch" in initializer
    assert "git remote set-url" not in initializer
    assert "https://x-access-token:" not in initializer
    assert "HARDEN_DESKTOP=true" in readme_content()


def readme_content():
    return (SERVER / "README.md").read_text(encoding="utf-8")


def test_obsidian_container_uses_pinned_base_and_initialization_scripts():
    dockerfile = (SERVER / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.startswith("FROM lscr.io/linuxserver/obsidian:1.14.4\n")
    assert "git-credential-env" in dockerfile
    assert "init-vault" in dockerfile


def test_vault_initializer_rejects_invalid_repo_and_nonempty_non_git_folder():
    initializer = (SERVER / "init-vault").read_text(encoding="utf-8")

    assert "GITHUB_REPO" in initializer
    assert "A-Za-z0-9_.-" in initializer
    assert "non-empty directory has no Git metadata" in initializer
    assert "different origin" in initializer


def test_setup_does_not_contain_tokens_or_public_vault_instruction():
    readme = (SERVER / "README.md").read_text(encoding="utf-8")
    dockerfile = (SERVER / "Dockerfile").read_text(encoding="utf-8")
    helper = (SERVER / "git-credential-env").read_text(encoding="utf-8")

    assert "ghp_" not in readme + dockerfile + helper
    assert "github_pat_" not in readme + dockerfile + helper
    assert "public repository" not in readme.lower()
