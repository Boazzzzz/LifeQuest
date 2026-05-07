from datetime import date
from pydantic import BaseModel

from app.core.config import settings


class GitHubDailyPythonActivity(BaseModel):
    commits: int = 0
    repositories: list[str] = []


class GitHubAdapter:
    async def get_daily_python_activity(self, target_date: date) -> GitHubDailyPythonActivity:
        if not settings.github_enabled:
            return GitHubDailyPythonActivity()

        # First real implementation should use the GitHub Events or GraphQL API.
        # It stays inert for now so Learning Core works without a token.
        return GitHubDailyPythonActivity()

