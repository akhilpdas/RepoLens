"""RepoLens tools — functions the model can call to explore a GitHub repo."""

import requests
import base64

# ---------------------------------------------------------------------------
# GitHub helpers (shared state set per-session)
# ---------------------------------------------------------------------------
_owner: str = ""
_repo: str = ""


def set_repo(owner: str, repo: str) -> None:
    """Configure which repo the tools operate on."""
    global _owner, _repo
    _owner = owner
    _repo = repo


# ---------------------------------------------------------------------------
# Tool 1: list_files
# ---------------------------------------------------------------------------
def list_files(path: str = "") -> str:
    """List files and folders at a given path inside the repo.

    Args:
        path: directory path relative to repo root. Use "" for root.

    Returns:
        Newline-separated list of entries with type indicators (📁 / 📄).
    """
    api_url = f"https://api.github.com/repos/{_owner}/{_repo}/contents/{path}"
    resp = requests.get(api_url, timeout=15)
    if resp.status_code != 200:
        return f"Error: could not list path '{path}' (HTTP {resp.status_code})"

    items = resp.json()
    if not isinstance(items, list):
        return f"'{path}' is a file, not a directory."

    lines = []
    for item in sorted(items, key=lambda x: (x["type"] != "dir", x["name"])):
        icon = "📁" if item["type"] == "dir" else "📄"
        lines.append(f"{icon} {item['path']}")
    return "\n".join(lines) if lines else "(empty directory)"


# ---------------------------------------------------------------------------
# Tool 2: read_file
# ---------------------------------------------------------------------------
def read_file(path: str) -> str:
    """Read the contents of a single file from the repo.

    Args:
        path: file path relative to repo root (e.g. "src/main.py").

    Returns:
        The file contents (truncated to ~8 000 chars for large files).
    """
    api_url = f"https://api.github.com/repos/{_owner}/{_repo}/contents/{path}"
    resp = requests.get(api_url, timeout=15)
    if resp.status_code != 200:
        return f"Error: could not read '{path}' (HTTP {resp.status_code})"

    data = resp.json()
    if data.get("type") != "file":
        return f"'{path}' is not a file."

    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error decoding '{path}': {e}"

    if len(content) > 8000:
        content = content[:8000] + "\n\n... (truncated)"
    return content


# ---------------------------------------------------------------------------
# Tool 3: search_docs
# ---------------------------------------------------------------------------
def search_docs(query: str) -> str:
    """Search for a keyword or phrase across the repo's code and docs.

    Uses the GitHub code-search API scoped to this repo.

    Args:
        query: the search term (e.g. "database", "setup instructions").

    Returns:
        Up to 10 matching file paths with a one-line text fragment each.
    """
    search_url = "https://api.github.com/search/code"
    params = {"q": f"{query} repo:{_owner}/{_repo}", "per_page": 10}
    headers = {"Accept": "application/vnd.github.v3.text-match+json"}
    resp = requests.get(search_url, params=params, headers=headers, timeout=15)

    if resp.status_code != 200:
        return f"Search error (HTTP {resp.status_code}). GitHub code search may be rate-limited; try again shortly."

    items = resp.json().get("items", [])
    if not items:
        return f"No results found for '{query}'."

    lines = []
    for item in items:
        path = item["path"]
        # pull first text-match fragment if available
        fragments = item.get("text_matches", [])
        snippet = fragments[0]["fragment"][:120] if fragments else ""
        lines.append(f"📄 {path}\n   ...{snippet}...")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool definitions for the Groq / OpenAI function-calling format
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files and directories at a given path inside the repository. "
                "Use path='' for the repo root. Useful for understanding project structure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to repo root. Use empty string for root.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a specific file from the repository. "
                "Useful for inspecting source code, configs, or documentation files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to repo root (e.g. 'src/main.py').",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": (
                "Search for a keyword or phrase across all files in the repository. "
                "Returns matching file paths with text snippets. Useful for finding "
                "where a concept, function, or configuration is defined."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term or phrase to look for in the codebase.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]

# Map function names → callables
TOOL_MAP = {
    "list_files": list_files,
    "read_file": read_file,
    "search_docs": search_docs,
}
