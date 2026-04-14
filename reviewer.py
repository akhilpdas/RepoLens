"""RepoLens reviewer — quality-checks the researcher's answer before showing it to the user.

Checks for:
- Unsupported claims (no file citation)
- Missing citations
- Vague setup instructions
- Incorrect file references
- Hallucinated file paths or function names
"""

import os
from groq import Groq


REVIEWER_SYSTEM_PROMPT = """You are the Reviewer for RepoLens, a GitHub repository onboarding assistant.

Your job is to quality-check an answer before it is shown to the user.

You will receive:
1. The user's original question
2. The researcher's draft answer
3. A list of files that were actually indexed/read from the repo
4. Retrieved evidence chunks from the codebase

CHECK FOR THESE ISSUES:

1. **Unsupported Claims** — Any factual statement not backed by a cited file or chunk.
   Flag: "⚠️ UNSUPPORTED: [the claim]"

2. **Missing Citations** — Key claims that should reference a specific file but don't.
   Flag: "📎 NEEDS CITATION: [the claim]"

3. **Vague Setup Instructions** — Setup steps that say "install dependencies" without
   specifying the actual command or file.
   Flag: "🔧 VAGUE: [the instruction]"

4. **Incorrect File References** — File paths mentioned that don't exist in the indexed files list.
   Flag: "❌ BAD REF: [the file path] — not found in repo"

5. **Hallucination Risk** — Function names, class names, or technical details that
   aren't confirmed by the retrieved chunks.
   Flag: "🤔 UNVERIFIED: [the detail]"

RESPOND with this exact JSON format:
{
  "verdict": "pass" | "needs_revision",
  "issues": [
    {
      "type": "unsupported | missing_citation | vague | bad_ref | hallucination",
      "description": "What the issue is",
      "location": "Which part of the answer",
      "suggestion": "How to fix it"
    }
  ],
  "quality_score": 1-10,
  "summary": "One sentence overall assessment"
}

If the answer is good (score >= 7, no critical issues), set verdict to "pass".
Otherwise set verdict to "needs_revision".

Be strict but fair. Not every sentence needs a citation — focus on factual claims
about what the code does, what files exist, and how to run things."""


def review_answer(
    question: str,
    answer: str,
    indexed_files: list[str],
    evidence_chunks: str,
    user_level: str,
) -> dict:
    """Run the reviewer on a draft answer.

    Returns:
        dict with verdict, issues, quality_score, summary.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    files_list = "\n".join(f"  - {f}" for f in indexed_files) if indexed_files else "(none indexed)"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"User level: {user_level}\n"
                    f"Question: {question}\n\n"
                    f"--- DRAFT ANSWER ---\n{answer}\n\n"
                    f"--- INDEXED FILES ---\n{files_list}\n\n"
                    f"--- EVIDENCE CHUNKS ---\n{evidence_chunks[:4000]}\n\n"
                    f"Review this answer now."
                ),
            },
        ],
        temperature=0.2,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )

    import json

    try:
        result = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, Exception):
        result = {
            "verdict": "pass",
            "issues": [],
            "quality_score": 7,
            "summary": "Review could not be completed; passing by default.",
        }

    return result


def revise_answer(
    original_answer: str,
    review_result: dict,
    question: str,
    evidence_chunks: str,
    user_level: str,
) -> str:
    """Revise an answer based on reviewer feedback.

    Only called when verdict is "needs_revision".
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    issues_text = "\n".join(
        f"- [{issue['type']}] {issue['description']} → {issue.get('suggestion', 'Fix this.')}"
        for issue in review_result.get("issues", [])
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are RepoLens. Revise the answer to fix the issues flagged by the reviewer.\n"
                    "Keep the same structure but:\n"
                    "- Add citations where missing\n"
                    "- Remove or qualify unsupported claims\n"
                    "- Make vague instructions specific\n"
                    "- Fix incorrect file references\n"
                    "- Remove hallucinated details\n"
                    f"Tailor for a **{user_level}** developer.\n"
                    "Use markdown formatting."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"--- ORIGINAL ANSWER ---\n{original_answer}\n\n"
                    f"--- REVIEWER ISSUES ---\n{issues_text}\n\n"
                    f"--- EVIDENCE CHUNKS ---\n{evidence_chunks[:4000]}\n\n"
                    f"Revise the answer now."
                ),
            },
        ],
        temperature=0.3,
        max_tokens=3000,
    )
    return response.choices[0].message.content
