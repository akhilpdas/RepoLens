"""RepoLens — Agentic onboarding assistant for GitHub repos.

Pipeline: Plan → Index → Research → Review → Synthesize
UI: Sidebar (config) + Main panel (answer) + Tabs (evidence, memory, traces)
"""

import json
import time
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from groq import Groq

from tools import TOOL_DEFINITIONS, TOOL_MAP, set_repo
from planner import create_plan
from state import SessionState, StepStatus
from retriever import RepoRetriever
from reviewer import review_answer, revise_answer
from memory import (
    get_profile, update_profile, add_question,
    get_history, get_repo_history, get_memory_context,
)
from tracer import RunTrace, Timer

load_dotenv()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="RepoLens", page_icon="🔍", layout="wide")

# --- Initialize session state ---
if "session" not in st.session_state:
    st.session_state.session = SessionState()
if "trace" not in st.session_state:
    st.session_state.trace = None
if "retriever" not in st.session_state:
    st.session_state.retriever = None
if "last_review" not in st.session_state:
    st.session_state.last_review = None
if "evidence_chunks" not in st.session_state:
    st.session_state.evidence_chunks = ""


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🔍 RepoLens")
    st.caption("Agentic repo onboarding assistant")
    st.markdown("---")

    repo_url = st.text_input(
        "📂 GitHub Repo URL",
        placeholder="https://github.com/owner/repo",
    )

    profile = get_profile()

    level = st.selectbox(
        "👤 Your experience level",
        ["beginner", "intermediate", "advanced"],
        index=["beginner", "intermediate", "advanced"].index(profile.get("skill_level", "intermediate")),
    )

    style = st.selectbox(
        "📝 Explanation style",
        ["concise", "balanced", "detailed"],
        index=["concise", "balanced", "detailed"].index(profile.get("explanation_style", "balanced")),
    )

    # Save preferences
    update_profile(skill_level=level, explanation_style=style)

    st.markdown("---")

    # Preset demo buttons
    st.markdown("**🚀 Quick Actions**")
    preset_q = None
    presets = [
        ("📋 Summarize architecture", "What is the architecture of this project?"),
        ("📖 Onboarding guide", "Generate a complete onboarding guide for this project."),
        ("🔧 Setup steps", "What are the exact steps to set up and run this project?"),
        ("📚 What to read first", "What files should I read first to understand this codebase?"),
        ("🤝 How to contribute", "What would be a good first contribution?"),
    ]
    for label, q in presets:
        if st.button(label, use_container_width=True):
            preset_q = q

    # Show last repo from memory
    if profile.get("last_repo"):
        st.markdown("---")
        st.caption(f"Last explored: `{profile['last_repo']}`")


# ---------------------------------------------------------------------------
# Main panel header
# ---------------------------------------------------------------------------
st.title("🔍 RepoLens")
st.markdown("*Understand any GitHub repo in minutes — powered by AI agents*")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def parse_repo(url: str):
    url = url.rstrip("/")
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


def fetch_readme(owner: str, repo: str):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    resp = requests.get(api_url, headers=headers, timeout=15)
    if resp.status_code == 200:
        return resp.text
    return None


def fetch_repo_tree(owner: str, repo: str) -> list[str]:
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD"
    resp = requests.get(api_url, timeout=15)
    if resp.status_code == 200:
        return [item["path"] for item in resp.json().get("tree", [])]
    return []


# ---------------------------------------------------------------------------
# Researcher: executes a single plan step with tools + RAG context
# ---------------------------------------------------------------------------
RESEARCHER_SYSTEM_PROMPT = """You are the Researcher for RepoLens, a GitHub repo onboarding assistant.

You are executing ONE step of an investigation plan. You have 3 tools:
- list_files(path) — list files/folders at a path (use "" for root)
- read_file(path) — read a file's contents
- search_docs(query) — search for a keyword across the repo

INSTRUCTIONS:
1. Execute the current plan step using the suggested tools.
2. You also have RETRIEVED CHUNKS from the codebase — use them as evidence.
3. Be factual. ALWAYS cite file paths for any claims.
4. Do NOT produce the final user-facing answer — just findings for this step.
5. If a retrieved chunk answers the question, cite it: (source: filename.ext)"""


def execute_step(step, plan, readme, previous_findings, retriever, status_ui):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    # Get RAG context for this step
    rag_context = ""
    if retriever:
        rag_context = retriever.get_context_string(
            f"{plan.question} {step.title} {step.description}", n_results=3
        )

    prev_context = ""
    if previous_findings:
        prev_context = "\n\n".join(
            f"### Step {i+1} findings:\n{f}" for i, f in enumerate(previous_findings)
        )
        prev_context = f"\n\nFindings from previous steps:\n{prev_context}"

    # Get memory context
    memory_ctx = get_memory_context(plan.repo, plan.user_level)

    messages = [
        {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Repository: {plan.repo}\n"
                f"User context: {memory_ctx}\n\n"
                f"README preview:\n```\n{readme[:2000]}\n```\n\n"
                f"Retrieved evidence chunks:\n{rag_context}\n"
                f"{prev_context}\n\n"
                f"---\n"
                f"CURRENT STEP ({step.id}/{len(plan.steps)}): {step.title}\n"
                f"Description: {step.description}\n"
                f"Suggested tools: {', '.join(step.suggested_tools) if step.suggested_tools else 'none (synthesis step)'}\n\n"
                f"Execute this step now. Cite sources for every claim."
            ),
        },
    ]

    tool_calls_log = []

    for _ in range(5):
        call_kwargs = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1500,
        }
        if step.suggested_tools:
            call_kwargs["tools"] = TOOL_DEFINITIONS
            call_kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**call_kwargs)
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content, tool_calls_log

        messages.append(msg)
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            status_ui.update(label=f"Step {step.id}: 🔧 {fn_name}({', '.join(f'{k}={v!r}' for k, v in fn_args.items())})")
            fn = TOOL_MAP.get(fn_name)
            result = fn(**fn_args) if fn else f"Unknown tool: {fn_name}"
            tool_calls_log.append({"step": step.id, "tool": fn_name, "args": fn_args, "result_preview": result[:300]})
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

    messages.append({"role": "user", "content": "Summarize your findings for this step now. Cite file sources."})
    response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.3, max_tokens=1500)
    return response.choices[0].message.content, tool_calls_log


# ---------------------------------------------------------------------------
# Synthesizer
# ---------------------------------------------------------------------------
def synthesize_answer(plan, findings, readme, evidence_chunks, style):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    findings_text = "\n\n".join(f"### Step {i+1}: {plan.steps[i].title}\n{f}" for i, f in enumerate(findings))

    style_instruction = {
        "concise": "Keep the answer brief and to the point. Use bullet points.",
        "balanced": "Provide a well-structured answer with moderate detail.",
        "detailed": "Provide a comprehensive, in-depth answer with examples and explanations.",
    }.get(style, "Provide a well-structured answer.")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are RepoLens, an expert developer onboarding assistant.\n"
                    "Synthesize the investigation findings into a final answer.\n"
                    "RULES:\n"
                    "- ALWAYS cite specific files as evidence: (source: filename)\n"
                    "- Do NOT make claims without evidence from the findings\n"
                    "- Use markdown formatting\n"
                    f"- Style: {style_instruction}\n"
                    f"- Tailor for a **{plan.user_level}** developer."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Repository: {plan.repo}\n"
                    f"Question: {plan.question}\n\n"
                    f"Investigation findings:\n{findings_text}\n\n"
                    f"Supporting evidence chunks:\n{evidence_chunks[:3000]}\n\n"
                    f"Produce the final answer now. Every claim must cite a source file."
                ),
            },
        ],
        temperature=0.3,
        max_tokens=3000,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Main application flow
# ---------------------------------------------------------------------------
QUESTIONS = [
    "What does this repo do?",
    "What files should I read first?",
    "How do I run it?",
    "What is the architecture?",
    "What would be a good first contribution?",
]

if repo_url:
    parsed = parse_repo(repo_url)
    if not parsed:
        st.error("Please enter a valid GitHub repo URL (https://github.com/owner/repo)")
    elif "GROQ_API_KEY" not in os.environ:
        st.error("Set your `GROQ_API_KEY` environment variable.")
    else:
        owner, repo = parsed
        repo_name = f"{owner}/{repo}"
        set_repo(owner, repo)
        update_profile(last_repo=repo_name)

        readme = fetch_readme(owner, repo)
        files = fetch_repo_tree(owner, repo)

        if not readme:
            st.warning("Could not fetch README. The repo may be private or have no README.")
        else:
            # --- Question input ---
            st.markdown("**Ask a question about this repo:**")
            q_cols = st.columns(3)
            selected_q = None
            for idx, q in enumerate(QUESTIONS):
                if q_cols[idx % 3].button(q, key=f"q_{idx}"):
                    selected_q = q

            custom_q = st.text_input("Or type your own:", placeholder="e.g. How does authentication work?")
            question = preset_q or custom_q or selected_q

            if question:
                trace = RunTrace(repo=repo_name, question=question, user_level=level)

                # ===== PHASE 0: INDEX (RAG) =====
                with st.status("📚 Indexing repo for retrieval...", expanded=False) as idx_status:
                    with Timer() as t:
                        retriever = RepoRetriever(owner, repo)
                        try:
                            index_stats = retriever.index(
                                status_callback=lambda msg: idx_status.update(label=f"📚 {msg}")
                            )
                            trace.files_indexed = index_stats["files_indexed"]
                        except Exception as e:
                            index_stats = {"files_indexed": 0, "chunks_created": 0, "files": []}
                            trace.add_event("index", f"Indexing failed: {e}", 0, error=str(e))
                    trace.add_event("index", f"Indexed {index_stats['files_indexed']} files, {index_stats['chunks_created']} chunks", t.elapsed_ms)
                    idx_status.update(label=f"📚 Indexed {index_stats['files_indexed']} files ({index_stats['chunks_created']} chunks)", state="complete")

                st.session_state.retriever = retriever

                # Get RAG evidence for the question
                evidence_chunks = retriever.get_context_string(question, n_results=5)
                st.session_state.evidence_chunks = evidence_chunks
                trace.chunks_retrieved = min(5, retriever.chunk_count)

                # ===== PHASE 1: PLAN =====
                with st.status("📋 Creating investigation plan...", expanded=True) as plan_status:
                    with Timer() as t:
                        try:
                            plan = create_plan(question=question, repo_name=repo_name, user_level=level, readme_preview=readme)
                        except Exception as e:
                            st.error(f"Planning failed: {e}")
                            plan = None
                            trace.add_event("plan", f"Failed: {e}", t.elapsed_ms, error=str(e))
                    if plan:
                        trace.add_event("plan", f"Created {len(plan.steps)}-step plan", t.elapsed_ms)
                        plan_status.update(label=f"📋 Plan ready — {len(plan.steps)} steps", state="complete")

                if plan:
                    # Show plan in sidebar
                    with st.sidebar:
                        st.markdown("---")
                        st.markdown("**📋 Current Plan**")
                        for step in plan.steps:
                            st.caption(f"{step.id}. {step.title}")

                    # ===== PHASE 2: RESEARCH =====
                    findings = []
                    all_tool_calls = []

                    with st.status("🔬 Researching...", expanded=True) as research_status:
                        for step in plan.steps:
                            step.status = StepStatus.RUNNING
                            research_status.update(label=f"Step {step.id}/{len(plan.steps)}: {step.title}")
                            with Timer() as t:
                                try:
                                    finding, step_tools = execute_step(step, plan, readme, findings, retriever, research_status)
                                    findings.append(finding)
                                    all_tool_calls.extend(step_tools)
                                    step.status = StepStatus.DONE
                                    step.result_summary = finding[:200]
                                except Exception as e:
                                    findings.append(f"(Step failed: {e})")
                                    step.status = StepStatus.SKIPPED
                                    trace.add_event("research", f"Step {step.id} failed", t.elapsed_ms, step=step.id, error=str(e))
                            trace.add_event("research", f"Step {step.id}: {step.title}", t.elapsed_ms, step=step.id, detail=step.result_summary)
                        research_status.update(label="🔬 Research complete!", state="complete")

                    trace.tool_calls_count = len(all_tool_calls)

                    # ===== PHASE 3: SYNTHESIS =====
                    with st.status("✍️ Writing answer...", expanded=False) as synth_status:
                        with Timer() as t:
                            try:
                                final_answer = synthesize_answer(plan, findings, readme, evidence_chunks, style)
                            except Exception as e:
                                st.error(f"Synthesis failed: {e}")
                                final_answer = "\n\n---\n\n".join(findings)
                                trace.add_event("synthesis", f"Failed: {e}", t.elapsed_ms, error=str(e))
                        trace.add_event("synthesis", "Answer synthesized", t.elapsed_ms)
                        synth_status.update(label="✍️ Answer ready!", state="complete")

                    trace.final_answer_length = len(final_answer)

                    # ===== PHASE 4: REVIEW =====
                    with st.status("🔍 Reviewing answer quality...", expanded=False) as review_status:
                        with Timer() as t:
                            try:
                                review_result = review_answer(
                                    question=question,
                                    answer=final_answer,
                                    indexed_files=retriever.indexed_files,
                                    evidence_chunks=evidence_chunks,
                                    user_level=level,
                                )
                                trace.quality_score = review_result.get("quality_score", 0)
                                trace.review_verdict = review_result.get("verdict", "unknown")
                            except Exception as e:
                                review_result = {"verdict": "pass", "issues": [], "quality_score": 7, "summary": f"Review failed: {e}"}
                                trace.add_event("review", f"Failed: {e}", t.elapsed_ms, error=str(e))
                        trace.add_event("review", f"Verdict: {review_result['verdict']} (score: {review_result.get('quality_score', '?')})", t.elapsed_ms)
                        review_status.update(label=f"🔍 Review: {review_result['verdict']} (score: {review_result.get('quality_score', '?')}/10)", state="complete")

                    st.session_state.last_review = review_result

                    # Revise if needed
                    if review_result.get("verdict") == "needs_revision" and review_result.get("quality_score", 10) < 6:
                        with st.status("✏️ Revising answer based on review...", expanded=False) as rev_status:
                            with Timer() as t:
                                try:
                                    final_answer = revise_answer(final_answer, review_result, question, evidence_chunks, level)
                                except Exception as e:
                                    trace.add_event("revision", f"Failed: {e}", t.elapsed_ms, error=str(e))
                            trace.add_event("revision", "Answer revised", t.elapsed_ms)
                            rev_status.update(label="✏️ Answer revised!", state="complete")

                    # Finalize trace
                    trace.finalize()
                    st.session_state.trace = trace

                    # Save to memory
                    add_question(
                        repo=repo_name,
                        question=question,
                        user_level=level,
                        answer_preview=final_answer[:500],
                        quality_score=review_result.get("quality_score", 0),
                    )

                    # ===== DISPLAY =====
                    st.markdown("---")

                    # Quality badge
                    score = review_result.get("quality_score", 0)
                    if score >= 8:
                        st.success(f"✅ Quality Score: {score}/10 — {review_result.get('summary', '')}")
                    elif score >= 5:
                        st.warning(f"⚠️ Quality Score: {score}/10 — {review_result.get('summary', '')}")
                    else:
                        st.error(f"❌ Quality Score: {score}/10 — {review_result.get('summary', '')}")

                    # Main answer
                    st.markdown(final_answer)

                    # ===== TABS =====
                    st.markdown("---")
                    tab1, tab2, tab3, tab4 = st.tabs(["📚 Evidence", "🧠 Memory", "📊 Trace", "🔬 Details"])

                    with tab1:
                        st.markdown("### Retrieved Evidence Chunks")
                        if evidence_chunks:
                            st.markdown(evidence_chunks)
                        else:
                            st.info("No chunks retrieved.")

                        st.markdown("### Indexed Files")
                        if retriever.indexed_files:
                            for f in retriever.indexed_files:
                                st.text(f"📄 {f}")
                        st.caption(f"Total: {len(retriever.indexed_files)} files, {retriever.chunk_count} chunks")

                    with tab2:
                        st.markdown("### User Profile")
                        prof = get_profile()
                        st.json(prof)

                        st.markdown("### Question History")
                        history = get_history(10)
                        if history:
                            for h in history:
                                with st.expander(f"❓ {h['question'][:60]}... ({h['repo']})"):
                                    st.caption(f"Level: {h['user_level']} | Score: {h['quality_score']} | {h['asked_at'][:16]}")
                                    st.text(h["answer_preview"])
                        else:
                            st.info("No history yet.")

                    with tab3:
                        st.markdown("### Run Trace")
                        if trace:
                            summary = trace.summary()
                            col_a, col_b, col_c = st.columns(3)
                            col_a.metric("Total Time", summary["total_time"])
                            col_b.metric("Tool Calls", summary["tool_calls"])
                            col_c.metric("Quality", f"{summary['quality_score']}/10")

                            st.markdown("#### Phase Timing")
                            for phase, t_val in summary["phase_times"].items():
                                st.text(f"  {phase}: {t_val}")

                            st.markdown("#### Event Log")
                            for line in trace.event_log():
                                st.text(line)

                            if summary["errors"]:
                                st.markdown("#### Errors")
                                for err in summary["errors"]:
                                    st.error(err)

                    with tab4:
                        st.markdown("### Investigation Plan")
                        for step in plan.steps:
                            icon = "✅" if step.status == StepStatus.DONE else "⏭️" if step.status == StepStatus.SKIPPED else "⏳"
                            st.markdown(f"**{icon} Step {step.id}: {step.title}**")
                            st.caption(step.description)

                        st.markdown("### Step Findings")
                        for i, (step, finding) in enumerate(zip(plan.steps, findings)):
                            with st.expander(f"Step {step.id}: {step.title}"):
                                st.markdown(finding)

                        if all_tool_calls:
                            st.markdown("### Tool Calls")
                            for call in all_tool_calls:
                                st.markdown(f"**Step {call['step']}** → `{call['tool']}({call['args']})`")
                                st.code(call["result_preview"][:200], language="text")

                        st.markdown("### Review Details")
                        if review_result:
                            st.json(review_result)

else:
    # Landing page when no URL is entered
    st.info("👆 Paste a public GitHub repo URL in the sidebar to get started!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📋 Plan")
        st.caption("AI creates an investigation plan tailored to your question")
    with col2:
        st.markdown("### 🔬 Research")
        st.caption("Agent explores the repo using tools and RAG retrieval")
    with col3:
        st.markdown("### ✅ Review")
        st.caption("Reviewer checks for accuracy, citations, and clarity")
