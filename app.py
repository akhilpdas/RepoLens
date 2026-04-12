"""RepoLens — Agentic onboarding assistant for GitHub repos."""

import streamlit as st
import requests
import os
from openai import OpenAI

st.set_page_config(page_title="RepoLens", page_icon="🔍", layout="wide")
st.title("🔍 RepoLens")
st.subheader("Understand any GitHub repo in minutes")

# --- Sidebar: user level ---
level = st.sidebar.selectbox(
    "Your experience level",
    ["beginner", "intermediate", "advanced"],
    index=1,
)

# --- Main input ---
repo_url = st.text_input(
    "Paste a public GitHub repo URL",
    placeholder="https://github.com/owner/repo",
)


# --- Helpers ---
def parse_repo(url: str) -> tuple[str, str] | None:
    """Extract owner/repo from a GitHub URL."""
    url = url.rstrip("/")
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


def fetch_readme(owner: str, repo: str) -> str | None:
    """Fetch the README content via GitHub API."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    resp = requests.get(api_url, headers=headers, timeout=15)
    if resp.status_code == 200:
        return resp.text
    return None


def fetch_repo_tree(owner: str, repo: str) -> list[str]:
    """Fetch the top-level file/folder listing."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD"
    resp = requests.get(api_url, timeout=15)
    if resp.status_code == 200:
        return [item["path"] for item in resp.json().get("tree", [])]
    return []


def summarize_repo(readme: str, files: list[str], user_level: str) -> str:
    """Call OpenAI to produce a repo summary."""
    client = OpenAI()

    file_listing = "\n".join(files[:60])  # cap to avoid token blow-up

    prompt = f"""You are RepoLens, an expert at onboarding developers to new codebases.

The user is a **{user_level}** developer. Tailor your language accordingly.

Given the README and file tree of a GitHub repository, produce a structured summary:

1. **What this repo does** — one paragraph.
2. **Key files to read first** — up to 5 files, with a one-line reason each.
3. **How to run it** — step-by-step, extracted from the README.
4. **Architecture overview** — describe the main components/layers.
5. **Good first contribution ideas** — 2-3 suggestions.

---
README:
{readme[:8000]}

---
File tree (top-level):
{file_listing}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1500,
    )
    return response.choices[0].message.content


# --- Run ---
if repo_url:
    parsed = parse_repo(repo_url)
    if not parsed:
        st.error("Please enter a valid GitHub repo URL (https://github.com/owner/repo)")
    else:
        owner, repo = parsed
        with st.spinner(f"Analyzing **{owner}/{repo}**..."):
            readme = fetch_readme(owner, repo)
            files = fetch_repo_tree(owner, repo)

            if not readme:
                st.warning("Could not fetch README. The repo may be private or have no README.")
            else:
                col1, col2 = st.columns([2, 1])
                with col2:
                    st.markdown("**📂 Top-level files**")
                    for f in files[:30]:
                        st.text(f)

                with col1:
                    if "OPENAI_API_KEY" not in os.environ:
                        st.error(
                            "Set your `OPENAI_API_KEY` environment variable to get AI summaries. "
                            "For now, here's the raw README."
                        )
                        st.markdown(readme[:3000])
                    else:
                        summary = summarize_repo(readme, files, level)
                        st.markdown(summary)
