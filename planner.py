"""RepoLens planner — converts a user question into a structured investigation plan."""

import json
import os
from groq import Groq
from state import Plan, PlanStep


PLANNER_SYSTEM_PROMPT = """You are the Planner for RepoLens, a GitHub repository onboarding assistant.

Your job: take the user's question about a repository and produce a structured investigation plan.

You have 3 tools available for investigating:
- list_files(path) — list files/folders at a path in the repo
- read_file(path) — read a specific file's contents
- search_docs(query) — search for a keyword across the repo

RULES:
1. Produce 3-5 steps. Keep it focused — avoid redundant steps.
2. Each step should be a clear, atomic action with a specific goal.
3. Order: structure first → read key files → search for specifics → synthesize.
4. Suggest which tool(s) would be useful for each step.
5. Always start by understanding the project structure (list_files at root).
6. Always end with a synthesis step (no tools) that produces the final answer.
7. Do NOT add generic steps like "review findings" — the synthesis step handles that.
8. Tailor the plan to the question: a "how to run" question needs different steps than "what is the architecture".

Respond ONLY with valid JSON in this exact format:
{
  "steps": [
    {
      "title": "Short title",
      "description": "What to do and why",
      "suggested_tools": ["list_files", "read_file"]
    }
  ]
}

Do NOT include any text outside the JSON block."""


def create_plan(question: str, repo_name: str, user_level: str, readme_preview: str) -> Plan:
    """Call the LLM to generate a structured plan for answering the question.

    Args:
        question: The user's question about the repo.
        repo_name: "owner/repo" string.
        user_level: beginner / intermediate / advanced.
        readme_preview: First ~2000 chars of README for context.

    Returns:
        A Plan object with ordered PlanSteps.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    user_prompt = f"""Repository: {repo_name}
User level: {user_level}
Question: "{question}"

README preview (first 2000 chars):
{readme_preview[:2000]}

Create an investigation plan to answer this question thoroughly."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: create a sensible default plan
        data = {
            "steps": [
                {
                    "title": "Explore project structure",
                    "description": "List root files and directories to understand the layout.",
                    "suggested_tools": ["list_files"],
                },
                {
                    "title": "Read documentation",
                    "description": "Read the README and any docs files for context.",
                    "suggested_tools": ["read_file"],
                },
                {
                    "title": "Investigate key source files",
                    "description": "Read main entry points and core modules.",
                    "suggested_tools": ["list_files", "read_file"],
                },
                {
                    "title": "Synthesize findings",
                    "description": "Combine all gathered information into a final answer.",
                    "suggested_tools": [],
                },
            ]
        }

    steps = []
    for i, step_data in enumerate(data.get("steps", []), start=1):
        steps.append(
            PlanStep(
                id=i,
                title=step_data.get("title", f"Step {i}"),
                description=step_data.get("description", ""),
                suggested_tools=step_data.get("suggested_tools", []),
            )
        )

    return Plan(
        question=question,
        repo=repo_name,
        user_level=user_level,
        steps=steps,
    )
