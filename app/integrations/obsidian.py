"""GitHub-backed Markdown writer for a private Obsidian vault."""

import logging
import re
from datetime import UTC, datetime
from urllib.parse import quote

import aiohttp

from app.config import Settings

logger = logging.getLogger(__name__)
GITHUB_API = "https://api.github.com"
_SAFE_COMPONENT = re.compile(r"[^\w .()-]+", re.UNICODE)


class ObsidianNotConfigured(Exception):
    pass


class ObsidianAPIError(Exception):
    pass


class _GitHubNotFound(ObsidianAPIError):
    pass


def safe_component(value: str, *, fallback: str = "note", limit: int = 80) -> str:
    value = _SAFE_COMPONENT.sub("_", value.strip()).strip(" ._")
    value = re.sub(r"\s+", " ", value)[:limit].rstrip(" .")
    return value or fallback


def safe_root(value: str) -> str:
    parts = [safe_component(part, fallback="") for part in value.replace("\\", "/").split("/")]
    parts = [part for part in parts if part and part not in {".", ".."}]
    if not parts:
        return "IELTS Tutor"
    return "/".join(parts)


def yaml_string(value: str) -> str:
    # JSON string literals are valid YAML scalars and safely quote arbitrary text.
    import json

    return json.dumps(value, ensure_ascii=False)


def render_note(title: str, category: str, owner_id: int, body: str) -> str:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    return (
        "---\n"
        f"title: {yaml_string(title)}\n"
        f"category: {yaml_string(category)}\n"
        f"telegram_user_id: {owner_id}\n"
        f"created_at: {yaml_string(now)}\n"
        "source: IELTS Tutor\n"
        "---\n\n"
        f"# {title.replace(chr(10), ' ')}\n\n"
        f"{body.strip()}\n"
    )


def note_path(root: str, category: str, title: str, update_id: int) -> str:
    if update_id < 0:
        raise ValueError("Telegram update id must be non-negative")
    return (
        f"{safe_root(root)}/{safe_root(category)}/"
        f"{safe_component(title)}-{update_id}.md"
    )


class GitHubVault:
    def __init__(self, settings: Settings, *, timeout_seconds: float = 10.0):
        self.settings = settings
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    def _configuration(self) -> tuple[str, str, str, str]:
        token = self.settings.github_token.get_secret_value() if self.settings.github_token else ""
        repo = (self.settings.github_repo or "").strip()
        if not token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ObsidianNotConfigured
        return token, repo, self.settings.github_branch, safe_root(self.settings.github_notes_path)

    async def _request(self, method: str, url: str, token: str, **kwargs) -> dict:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ielts-tutor-obsidian-integration",
        }
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as client:
                async with client.request(method, url, headers=headers, **kwargs) as response:
                    if response.status >= 400:
                        if response.status == 404:
                            raise _GitHubNotFound
                        logger.warning(
                            "GitHub vault request failed with status %d", response.status
                        )
                        raise ObsidianAPIError
                    return await response.json() if response.content_length != 0 else {}
        except (aiohttp.ClientError, TimeoutError) as exc:
            logger.warning("GitHub vault request failed (%s)", type(exc).__name__)
            raise ObsidianAPIError from None

    async def check(self) -> str:
        token, repo, branch, root = self._configuration()
        data = await self._request(
            "GET", f"{GITHUB_API}/repos/{repo}/branches/{quote(branch, safe='')}", token
        )
        sha = data.get("commit", {}).get("sha")
        if not sha:
            raise ObsidianAPIError
        return f"{repo}@{branch}:{root}"

    async def write(self, path: str, content: str) -> None:
        token, repo, branch, root = self._configuration()
        normalized = path.replace("\\", "/").lstrip("/")
        if not normalized.startswith(f"{root}/") or ".." in normalized.split("/"):
            raise ValueError("Note path must stay inside the configured vault folder")
        import base64

        url = f"{GITHUB_API}/repos/{repo}/contents/{quote(normalized, safe='/')}"
        existing: dict = {}
        try:
            existing = await self._request("GET", url, token, params={"ref": branch})
        except _GitHubNotFound:
            # 404 is the normal create path for a new note.
            existing = {}
        body = {
            "message": "Save IELTS Tutor note",
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if existing.get("sha"):
            body["sha"] = existing["sha"]
        await self._request("PUT", url, token, json=body)
