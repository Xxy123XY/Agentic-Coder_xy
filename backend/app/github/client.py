from github import Github, Auth
from functools import lru_cache
from app.config import get_settings
from app.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def get_github_client() -> Github:
    """Singleton GitHub client — reuses connection across calls."""
    auth = Auth.Token(settings.github_token)
    return Github(auth=auth)


def get_repo(repo_full_name: str):
    """Fetch a repository object by 'owner/name'."""
    client = get_github_client()
    return client.get_repo(repo_full_name)


def get_issue(repo_full_name: str, issue_number: int):
    """Fetch an issue from a repo."""
    repo = get_repo(repo_full_name)
    return repo.get_issue(number=issue_number)