"""GitHub HTTP helper — injects optional GITHUB_TOKEN at every call site.

Without a token, GitHub allows 60 unauthenticated requests/hour.
With a Personal Access Token, that lifts to 5000 req/hr and unlocks private repos.

Usage:
    from gh import gh_get
    resp = gh_get("https://api.github.com/repos/owner/repo/contents/path")
"""

from __future__ import annotations

import os
import requests


def gh_headers(extra: dict | None = None) -> dict:
    """Build GitHub API headers, adding Bearer auth if GITHUB_TOKEN is set."""
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    return headers


def gh_get(url: str, *, headers: dict | None = None, timeout: int = 15, **kwargs) -> requests.Response:
    """GET a GitHub API URL with optional auth header injection.

    Custom Accept headers (e.g. raw README, code-search text-match) merge cleanly
    via the `headers` kwarg.
    """
    return requests.get(url, headers=gh_headers(headers), timeout=timeout, **kwargs)
