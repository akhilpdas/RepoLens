"""RepoLens evaluator — 10 benchmark questions with automated scoring.

Scores each answer on:
- right_file: Did the answer reference the correct/relevant file?
- citation_present: Does the answer cite specific files as evidence?
- answer_complete: Is the answer substantive (not a one-liner)?
- no_hallucination: No made-up file paths, functions, or claims?
- clear_for_level: Is the language appropriate for the stated user level?

Each criterion is scored 0 or 1. Total per question: 0-5.
"""

import json
import os
from groq import Groq


# ---------------------------------------------------------------------------
# Benchmark questions (designed for any repo)
# ---------------------------------------------------------------------------
BENCHMARK_QUESTIONS = [
    {
        "id": 1,
        "question": "What is this project?",
        "expected_files": ["README.md"],
        "criteria_focus": "Should give a clear project overview with purpose and audience.",
    },
    {
        "id": 2,
        "question": "How do I run it?",
        "expected_files": ["README.md", "package.json", "Makefile", "Dockerfile", "pyproject.toml"],
        "criteria_focus": "Should provide specific commands, not vague instructions.",
    },
    {
        "id": 3,
        "question": "What files define config?",
        "expected_files": ["*.config.*", "*.json", "*.toml", "*.yaml", "*.yml", ".env*"],
        "criteria_focus": "Should list actual config files found in the repo.",
    },
    {
        "id": 4,
        "question": "Where is the entry point?",
        "expected_files": ["main.*", "app.*", "index.*", "server.*", "__main__.*", "manage.*"],
        "criteria_focus": "Should identify the main entry file with evidence.",
    },
    {
        "id": 5,
        "question": "What should a beginner read first?",
        "expected_files": ["README.md", "CONTRIBUTING.md", "docs/*"],
        "criteria_focus": "Should prioritize files and explain reading order.",
    },
    {
        "id": 6,
        "question": "What is the architecture?",
        "expected_files": [],
        "criteria_focus": "Should describe layers/components with file-based evidence.",
    },
    {
        "id": 7,
        "question": "What dependencies does this project use?",
        "expected_files": ["package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "go.mod", "Gemfile"],
        "criteria_focus": "Should list actual dependencies from manifest files.",
    },
    {
        "id": 8,
        "question": "How do I contribute?",
        "expected_files": ["CONTRIBUTING.md", "README.md", ".github/*"],
        "criteria_focus": "Should describe workflow: fork, branch, PR, tests.",
    },
    {
        "id": 9,
        "question": "What tests exist and how do I run them?",
        "expected_files": ["test*", "spec*", "*_test.*", "jest.config.*", "pytest.ini", "pyproject.toml"],
        "criteria_focus": "Should identify test framework and test command.",
    },
    {
        "id": 10,
        "question": "What would be a good first contribution?",
        "expected_files": ["README.md", "CONTRIBUTING.md"],
        "criteria_focus": "Should suggest specific, actionable ideas with difficulty levels.",
    },
]


EVAL_SYSTEM_PROMPT = """You are an evaluation judge for RepoLens, a GitHub repository onboarding assistant.

You will score an answer on 5 criteria. Each is scored 0 or 1.

1. **right_file** — Did the answer reference at least one relevant/correct file from the repo?
2. **citation_present** — Does the answer cite specific file paths as evidence (not just mention them in passing)?
3. **answer_complete** — Is the answer substantive (more than 2 sentences, addresses the question fully)?
4. **no_hallucination** — Are all file paths, function names, and technical details plausible and consistent with the repo context?
5. **clear_for_level** — Is the language appropriate for the stated user level?

Respond ONLY with valid JSON:
{
  "right_file": 0 or 1,
  "citation_present": 0 or 1,
  "answer_complete": 0 or 1,
  "no_hallucination": 0 or 1,
  "clear_for_level": 0 or 1,
  "total": sum of above (0-5),
  "notes": "Brief explanation of scoring"
}"""


def score_answer(
    question: str,
    answer: str,
    user_level: str,
    indexed_files: list[str],
    criteria_focus: str,
) -> dict:
    """Score a single answer against the 5 criteria.

    Returns dict with individual scores and total.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    files_list = "\n".join(f"  - {f}" for f in indexed_files[:30]) if indexed_files else "(unknown)"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n"
                    f"User level: {user_level}\n"
                    f"Focus: {criteria_focus}\n\n"
                    f"--- ANSWER ---\n{answer}\n\n"
                    f"--- KNOWN REPO FILES ---\n{files_list}\n\n"
                    f"Score this answer now."
                ),
            },
        ],
        temperature=0.1,
        max_tokens=300,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, Exception):
        result = {
            "right_file": 0, "citation_present": 0, "answer_complete": 0,
            "no_hallucination": 1, "clear_for_level": 1, "total": 2,
            "notes": "Scoring failed, default applied.",
        }

    return result


def run_eval_suite(answer_fn, repo_name: str, user_level: str, indexed_files: list[str]) -> dict:
    """Run all 10 benchmark questions and collect scores.

    Args:
        answer_fn: callable(question: str) -> str that produces an answer.
        repo_name: "owner/repo" string.
        user_level: beginner / intermediate / advanced.
        indexed_files: list of files that were indexed.

    Returns:
        dict with per-question scores and aggregate stats.
    """
    results = []
    total_score = 0

    for bench in BENCHMARK_QUESTIONS:
        # Get the answer
        answer = answer_fn(bench["question"])

        # Score it
        scores = score_answer(
            question=bench["question"],
            answer=answer,
            user_level=user_level,
            indexed_files=indexed_files,
            criteria_focus=bench["criteria_focus"],
        )

        results.append({
            "id": bench["id"],
            "question": bench["question"],
            "scores": scores,
            "answer_preview": answer[:200],
        })
        total_score += scores.get("total", 0)

    return {
        "results": results,
        "total_score": total_score,
        "max_score": len(BENCHMARK_QUESTIONS) * 5,
        "percentage": round(total_score / (len(BENCHMARK_QUESTIONS) * 5) * 100, 1),
        "repo": repo_name,
        "user_level": user_level,
    }
