"""RepoLens — Agentic onboarding assistant for GitHub repos."""

import json
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from groq import Groq

from tools import TOOL_DEFINITIONS, TOOL_MAP, set_repo

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


# ---------------------------------------------------------------------------
# Agentic tool-calling loop
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are RepoLens, an expert developer onboarding assistant.

You have 3 tools to explore GitHub repositories:
- list_files(path) — list files/folders at a path (use "" for root)
- read_file(path) — read a file's contents
- search_docs(query) — search for a keyword across the repo

WORKFLOW:
1. Start by listing the root directory to understand the project structure.
2. Read key files (README, main entry points, configs) to gather evidence.
3. Search for specific terms if the user's question requires it.
4. Only after gathering enough evidence, produce your final answer.

Always base your answers on actual file contents you've read — never guess.
Cite the files you read as evidence."""


def run_agent(user_question: str, readme: str, user_level: str, status) -> str:
    """Run the tool-calling agent loop.

    The model decides which tools to call, we execute them, feed results
    back, and repeat until the model produces a final text answer.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"The user is a **{user_level}** developer.\n\n"
                f"Here is the repo README for initial context:\n"
                f"```\n{readme[:6000]}\n```\n\n"
                f"User question: {user_question}"
            ),
        },
    ]

    max_iterations = 8  # safety cap
    tool_calls_log = []  # track for display

    for i in range(max_iterations):
        status.update(label=f"Thinking... (step {i + 1})")

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=3000,
        )

        msg = response.choices[0].message

        # If no tool calls, we have the final answer
        if not msg.tool_calls:
            return msg.content, tool_calls_log

        # Process each tool call
        messages.append(msg)  # add assistant message with tool_calls

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            status.update(label=f"🔧 Calling {fn_name}({', '.join(f'{k}={v!r}' for k, v in fn_args.items())})")

            # Execute the tool
            fn = TOOL_MAP.get(fn_name)
            if fn:
                result = fn(**fn_args)
            else:
                result = f"Unknown tool: {fn_name}"

            tool_calls_log.append({
                "tool": fn_name,
                "args": fn_args,
                "result_preview": result[:200],
            })

            # Feed result back to the model
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    # If we hit the cap, ask model to wrap up
    messages.append({
        "role": "user",
        "content": "Please provide your final answer now based on what you've gathered.",
    })
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=3000,
    )
    return response.choices[0].message.content, tool_calls_log


# ---------------------------------------------------------------------------
# Default question options
# ---------------------------------------------------------------------------
QUESTIONS = [
    "What does this repo do?",
    "What files should I read first?",
    "How do I run it?",
    "What is the architecture?",
    "What would be a good first contribution?",
]


# --- Run ---
if repo_url:
    parsed = parse_repo(repo_url)
    if not parsed:
        st.error("Please enter a valid GitHub repo URL (https://github.com/owner/repo)")
    elif "GROQ_API_KEY" not in os.environ:
        st.error("Set your `GROQ_API_KEY` environment variable to get AI summaries.")
    else:
        owner, repo = parsed
        set_repo(owner, repo)  # configure tools for this repo

        # Fetch baseline data
        readme = fetch_readme(owner, repo)
        files = fetch_repo_tree(owner, repo)

        if not readme:
            st.warning("Could not fetch README. The repo may be private or have no README.")
        else:
            # Layout
            col1, col2 = st.columns([2, 1])

            with col2:
                st.markdown("**📂 Top-level files**")
                for f in files[:30]:
                    st.text(f)

            with col1:
                # Quick-pick buttons
                st.markdown("**Ask a question about this repo:**")
                selected_q = None
                button_cols = st.columns(3)
                for idx, q in enumerate(QUESTIONS):
                    if button_cols[idx % 3].button(q, key=f"q_{idx}"):
                        selected_q = q

                # Or type your own
                custom_q = st.text_input(
                    "Or type your own question:",
                    placeholder="e.g. How does authentication work?",
                )

                question = custom_q if custom_q else selected_q

                if question:
                    with st.status(f"Analyzing **{owner}/{repo}**...", expanded=True) as status:
                        try:
                            answer, tool_log = run_agent(question, readme, level, status)
                            status.update(label="Done!", state="complete")
                        except Exception as e:
                            st.error(f"Error: {e}")
                            answer, tool_log = None, []

                    if answer:
                        st.markdown("---")
                        st.markdown(answer)

                        # Show tool calls in expander
                        if tool_log:
                            with st.expander(f"🔧 Tool calls made ({len(tool_log)})"):
                                for call in tool_log:
                                    st.markdown(f"**{call['tool']}**({call['args']})")
                                    st.code(call["result_preview"], language="text")
