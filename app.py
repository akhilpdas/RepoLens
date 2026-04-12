"""RepoLens — Agentic onboarding assistant for GitHub repos."""

import streamlit as st
import requests
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

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
    """Call Groq (Llama) to produce a detailed repo summary."""
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    file_listing = "\n".join(files[:60])

    prompt = f"""You are RepoLens, an expert at onboarding developers to new codebases.

The user is a **{user_level}** developer. Tailor your language accordingly and provide DETAILED explanations.

Given the README and file tree of a GitHub repository, produce a comprehensive structured summary:

## 1. **Project Overview**
Provide a 2-3 paragraph detailed explanation of:
- What this repository does in simple terms
- What problems it solves
- Who would benefit from using it
- Main purpose and goals

## 2. **Tech Stack & Dependencies**
List and briefly explain:
- Primary programming language(s)
- Key frameworks/libraries used
- Database systems (if any)
- External services/APIs (if any)

## 3. **Directory Structure & Key Components**
Explain the organization:
- Main folder structure (what each folder does)
- Key subdirectories and their purposes
- Entry point files

## 4. **Key Files to Read First**
List up to 8 files with detailed reasons (2-3 sentences each):
- Why read this file
- What it does
- When you need it

## 5. **Detailed Setup & Installation Instructions**
Provide step-by-step guide:
- Prerequisites (languages, tools needed)
- Installation steps with commands
- Configuration steps
- How to verify installation worked

## 6. **How to Run & Use**
Detailed usage guide:
- How to start the application
- What to expect when running
- How to use the main features
- Example commands or workflows

## 7. **Architecture Deep Dive**
Explain in detail:
- High-level architecture (main layers/modules)
- How components interact
- Data flow through the system
- Important design patterns used
- Scalability considerations

## 8. **Development Workflow**
For developers who want to contribute:
- Development setup (different from user setup)
- How to run tests
- Coding standards/conventions
- Git workflow for contributions
- Building and deployment process

## 9. **Code Quality & Testing**
Information about:
- Test coverage
- Quality assurance practices
- CI/CD pipelines
- Documentation standards
- Performance considerations

## 10. **Good First Contributions for Beginners**
Suggest 4-5 specific, actionable ideas:
- Feature ideas (with difficulty level)
- Bug fixes
- Documentation improvements
- Testing opportunities
- Each with "Why this helps" explanation

## 11. **Common Gotchas & Troubleshooting**
Share practical knowledge:
- Common mistakes beginners make
- Known issues
- How to debug problems
- Common error messages and solutions

## 12. **Learning Resources & Next Steps**
After understanding the repo, where to go:
- Important documentation to read
- Example projects using this
- Community or discussion forums
- Related projects to learn from

---
README:
{readme[:10000]}

---
File tree (top-level):
{file_listing}

IMPORTANT:
- Be detailed and comprehensive
- Use markdown formatting for clarity
- Include code examples where helpful
- Make it understandable for {user_level} level developers
- Total response should be thorough but readable (2000-3000 words)
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=3000,
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
                    if "GROQ_API_KEY" not in os.environ:
                        st.error(
                            "Set your `GROQ_API_KEY` environment variable to get AI summaries. "
                            "For now, here's the raw README."
                        )
                        st.markdown(readme[:3000])
                    else:
                        try:
                            summary = summarize_repo(readme, files, level)
                            st.markdown(summary)
                        except Exception as e:
                            st.warning(f"⚠️ **API Error**: {e}")
                            st.markdown("**Raw README:**")
                            st.markdown(readme[:3000])
