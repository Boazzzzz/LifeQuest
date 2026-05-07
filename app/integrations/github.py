import logging
from datetime import date, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubIntegrationError(RuntimeError):
    pass


class GitHubStatus(BaseModel):
    enabled: bool
    connected: bool
    username: str | None = None
    api_version: str
    rate_limit_remaining: int | None = None
    error: str | None = None


class GitHubDailyPythonActivity(BaseModel):
    enabled: bool = False
    connected: bool = False
    commits: int = 0
    python_commits: int = 0
    repositories: list[str] = Field(default_factory=list)
    python_files: list[str] = Field(default_factory=list)
    commit_messages: list[str] = Field(default_factory=list)
    error: str | None = None


class GitHubAdapter:
    def __init__(
        self,
        enabled: bool | None = None,
        token: str | None = None,
        username: str | None = None,
        api_version: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.enabled = settings.github_enabled if enabled is None else enabled
        self.token = token if token is not None else settings.github_token
        self.username = username if username is not None else settings.github_username
        self.api_version = api_version or settings.github_api_version
        self.timeout_seconds = timeout_seconds or settings.github_timeout_seconds
        self.base_url = "https://api.github.com"

    async def check_status(self) -> GitHubStatus:
        if not self.enabled:
            return GitHubStatus(
                enabled=False,
                connected=False,
                username=self.username,
                api_version=self.api_version,
            )

        if not self.username:
            return GitHubStatus(
                enabled=True,
                connected=False,
                api_version=self.api_version,
                error="GITHUB_USERNAME is required",
            )

        try:
            response = await self._request("GET", f"/users/{self.username}")
            remaining = self._rate_limit_remaining(response)
            return GitHubStatus(
                enabled=True,
                connected=True,
                username=self.username,
                api_version=self.api_version,
                rate_limit_remaining=remaining,
            )
        except GitHubIntegrationError as error:
            logger.warning("GitHub status check failed: %s", error)
            return GitHubStatus(
                enabled=True,
                connected=False,
                username=self.username,
                api_version=self.api_version,
                error=str(error),
            )

    async def get_daily_python_activity(self, target_date: date) -> GitHubDailyPythonActivity:
        if not self.enabled:
            return GitHubDailyPythonActivity(enabled=False)

        if not self.username:
            return GitHubDailyPythonActivity(enabled=True, connected=False, error="GITHUB_USERNAME is required")

        try:
            events = await self._list_user_events()
            push_events = self._filter_push_events_for_date(events, target_date)
            commits = self._extract_commits(push_events)
            python_files_by_sha = await self._find_python_files_for_commits(commits)
            python_shas = {sha for sha, files in python_files_by_sha.items() if files}

            repositories = sorted({commit["repo"] for commit in commits})
            python_files = sorted({file for files in python_files_by_sha.values() for file in files})
            messages = [str(commit["message"]) for commit in commits if commit.get("message")]

            return GitHubDailyPythonActivity(
                enabled=True,
                connected=True,
                commits=len(commits),
                python_commits=len(python_shas),
                repositories=repositories,
                python_files=python_files,
                commit_messages=messages[:20],
            )
        except GitHubIntegrationError as error:
            logger.warning("GitHub daily activity unavailable: %s", error)
            return GitHubDailyPythonActivity(enabled=True, connected=False, error=str(error))

    async def _list_user_events(self) -> list[dict[str, Any]]:
        response = await self._request("GET", f"/users/{self.username}/events", params={"per_page": 100})
        data = response.json()
        if not isinstance(data, list):
            raise GitHubIntegrationError("Unexpected GitHub events response shape")
        return [event for event in data if isinstance(event, dict)]

    async def _find_python_files_for_commits(self, commits: list[dict[str, str]]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for commit in commits[:30]:
            repo = commit["repo"]
            sha = commit["sha"]
            try:
                response = await self._request("GET", f"/repos/{repo}/commits/{sha}")
            except GitHubIntegrationError as error:
                logger.info("Skipping GitHub commit detail for %s/%s: %s", repo, sha, error)
                result[sha] = []
                continue

            data = response.json()
            files = data.get("files", []) if isinstance(data, dict) else []
            python_files = [
                str(file["filename"])
                for file in files
                if isinstance(file, dict) and str(file.get("filename", "")).endswith(".py")
            ]
            result[sha] = python_files
        return result

    async def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version,
            "User-Agent": "LifeQuest",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.request(method, f"{self.base_url}{path}", headers=headers, params=params)
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as error:
            raise GitHubIntegrationError(
                f"GitHub API returned {error.response.status_code}: {error.response.text[:200]}"
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            raise GitHubIntegrationError(str(error)) from error

    def _filter_push_events_for_date(self, events: list[dict[str, Any]], target_date: date) -> list[dict[str, Any]]:
        return [
            event
            for event in events
            if event.get("type") == "PushEvent" and self._event_local_date(event.get("created_at")) == target_date
        ]

    def _extract_commits(self, push_events: list[dict[str, Any]]) -> list[dict[str, str]]:
        commits_by_key: dict[tuple[str, str], dict[str, str]] = {}
        for event in push_events:
            repo = event.get("repo", {}).get("name")
            payload = event.get("payload", {})
            if not repo or not isinstance(payload, dict):
                continue

            for commit in payload.get("commits", []):
                if not isinstance(commit, dict) or not commit.get("sha"):
                    continue
                sha = str(commit["sha"])
                commits_by_key[(str(repo), sha)] = {
                    "repo": str(repo),
                    "sha": sha,
                    "message": str(commit.get("message") or ""),
                }
        return list(commits_by_key.values())

    def _event_local_date(self, created_at: Any) -> date | None:
        if not created_at:
            return None

        try:
            created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        except ValueError:
            return None

        local_timezone = datetime.now().astimezone().tzinfo
        return created.astimezone(local_timezone).date()

    def _rate_limit_remaining(self, response: httpx.Response) -> int | None:
        raw_value = response.headers.get("x-ratelimit-remaining")
        if raw_value is None:
            return None
        try:
            return int(raw_value)
        except ValueError:
            return None
