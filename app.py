"""RepoLens — Agentic onboarding assistant for GitHub repos.

Pipeline (orchestrated by LangGraph in graph.py):
    Index → Plan → Research → Synthesize → [HITL APPROVAL] → Review → (Revise → Review)? → END

UI: Sidebar (config) + Main panel (answer) + Tabs (evidence, memory, traces).

Supports single-repo mode (slot=None) and compare mode (slot="a"/"b") via
the keyer pattern in compare.py.
"""

import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from tools import set_repo
from gh import gh_get
from state import SessionState, StepStatus
from memory import (
    get_profile, update_profile, add_question,
    get_history, get_pref, set_pref,
)
from tracer import RunTrace, Timer
from graph import (
    build_pre_synth_graph, build_post_synth_graph,
    synthesize_stream, synthesize_answer_blocking,
)
from evaluator import run_eval_suite
from export import to_markdown, to_pdf
from reviewer import revise_answer
from compare import (
    PIPELINE_KEYS, SLOTS,
    ss_get, ss_set, ss_pop,
    reset_slot, reset_all_slots,
    slot_label, widget_key,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Streamlit Cloud secrets fallback (Phase 8.2)
# ---------------------------------------------------------------------------
for _key in ("GROQ_API_KEY", "GITHUB_TOKEN"):
    if _key not in os.environ:
        try:
            if hasattr(st, "secrets") and _key in st.secrets:
                os.environ[_key] = st.secrets[_key]
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="RepoLens", page_icon="🔍", layout="wide")

# ---------------------------------------------------------------------------
# Theme (light / dark / system) — runtime CSS injection
# ---------------------------------------------------------------------------
from theme import THEME_CHOICES, DEFAULT_THEME, apply_theme, resolve_choice

if "theme_choice" not in st.session_state:
    st.session_state["theme_choice"] = resolve_choice(get_pref("theme", default=DEFAULT_THEME))

apply_theme()


# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
def _ensure_session_defaults(slot=None):
    """Ensure pipeline keys exist for a given slot."""
    defaults = {
        "session": None,
        "trace": None,
        "retriever": None,
        "last_review": None,
        "evidence_chunks": "",
        "stage": "input",
        "active_question": None,
        "draft": None,
        "final_state": None,
    }
    for base, default in defaults.items():
        if ss_get(st.session_state, base, slot=slot, default="__MISSING__") == "__MISSING__":
            ss_set(st.session_state, base, default, slot=slot)
    if ss_get(st.session_state, "session", slot=slot) is None:
        ss_set(st.session_state, "session", SessionState(), slot=slot)


_ensure_session_defaults(slot=None)
_ensure_session_defaults(slot="a")
_ensure_session_defaults(slot="b")

if "pre_synth_graph" not in st.session_state:
    st.session_state.pre_synth_graph = build_pre_synth_graph()
if "post_synth_graph" not in st.session_state:
    st.session_state.post_synth_graph = build_post_synth_graph()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🔍 RepoLens")
    st.caption("Agentic repo onboarding assistant")

    _theme_prev = st.session_state.get("theme_choice", DEFAULT_THEME)
    _theme_idx = THEME_CHOICES.index(_theme_prev) if _theme_prev in THEME_CHOICES else 2
    theme_choice = st.radio(
        "🎨 Theme",
        THEME_CHOICES,
        index=_theme_idx,
        horizontal=True,
        key="theme_choice",
    )
    if theme_choice != _theme_prev:
        try:
            set_pref("theme", theme_choice)
        except Exception:
            pass
        st.rerun()

    st.markdown("---")

    # Compare-mode toggle
    compare_mode = st.toggle(
        "🔀 Compare two repos",
        key="compare_mode",
        help="Run the pipeline on two repos side-by-side to compare them.",
    )

    repo_url = st.text_input(
        "📂 GitHub Repo URL" if not compare_mode else "📂 Repo A URL",
        placeholder="https://github.com/owner/repo",
        key="repo_url_a",
    )
    repo_url_b = ""
    if compare_mode:
        repo_url_b = st.text_input(
            "📂 Repo B URL",
            placeholder="https://github.com/owner/repo",
            key="repo_url_b",
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

    update_profile(skill_level=level, explanation_style=style)

    st.markdown("---")

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

    st.markdown("---")

    if compare_mode:
        ri_cols = st.columns(2)
        if ri_cols[0].button("🔄 Re-index A", use_container_width=True):
            ss_set(st.session_state, "force_reindex", True, slot="a")
        if ri_cols[1].button("🔄 Re-index B", use_container_width=True):
            ss_set(st.session_state, "force_reindex", True, slot="b")
    else:
        if st.button("🔄 Re-index repo", use_container_width=True,
                     help="Force a fresh ChromaDB build (otherwise cached for 24h)."):
            ss_set(st.session_state, "force_reindex", True, slot=None)

    if st.button("🆕 New question", use_container_width=True,
                 help="Reset the current draft / finalized answer."):
        reset_all_slots(st.session_state)
        st.rerun()

    # ----- Eval suite (single-repo only) -----
    st.markdown("**🧪 Evaluation**")
    if compare_mode:
        st.caption("ℹ️ Disable Compare mode to run the eval suite.")
    else:
        full_suite = st.checkbox("Full suite (10 Q)", value=False,
                                 help="Default runs 3 questions; full suite runs all 10.")
        if st.button("Run Eval Suite", use_container_width=True, disabled=not repo_url,
                     help="Evaluate this repo against the benchmark questions."):
            st.session_state.run_eval = "full" if full_suite else "subset"

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
    """Extract owner/repo from a GitHub URL."""
    url = url.rstrip("/")
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


def fetch_readme(owner: str, repo: str):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    resp = gh_get(api_url, headers={"Accept": "application/vnd.github.v3.raw"}, timeout=15)
    if resp.status_code == 200:
        return resp.text
    return None


def fetch_repo_tree(owner: str, repo: str):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD"
    resp = gh_get(api_url, timeout=15)
    if resp.status_code == 200:
        return [item["path"] for item in resp.json().get("tree", [])]
    return []


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


# Landing page when no URL is entered
if not repo_url:
    st.info("👆 Paste a public GitHub repo URL in the sidebar to get started!")
    if compare_mode:
        st.caption("Compare mode is on — paste two URLs to compare them side-by-side.")
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
    st.stop()

if compare_mode and not repo_url_b:
    st.info("Compare mode is on — paste a second GitHub repo URL in the sidebar to begin.")
    st.stop()

if "GROQ_API_KEY" not in os.environ:
    st.error("Set your `GROQ_API_KEY` environment variable.")
    st.stop()


def parse_or_stop(url: str, label: str = "repo"):
    parsed = parse_repo(url)
    if not parsed:
        st.error(f"Please enter a valid GitHub URL for {label} (https://github.com/owner/repo)")
        st.stop()
    return parsed


# ---------------------------------------------------------------------------
# Shared question input — presented above the columns in compare mode
# ---------------------------------------------------------------------------
def render_question_input(slot=None):
    """Render the question input. Returns (active_question_or_None, just_kicked_off)."""
    # Show input only when this slot is in input or done state
    stg = ss_get(st.session_state, "stage", slot=slot, default="input")
    if stg not in ("input", "done"):
        return ss_get(st.session_state, "active_question", slot=slot), False

    label_prefix = slot_label(slot)
    st.markdown(f"**{label_prefix}Ask a question about this repo:**")
    q_cols = st.columns(3)
    selected_q = None
    for idx, q in enumerate(QUESTIONS):
        if q_cols[idx % 3].button(q, key=widget_key(f"q_{idx}", slot)):
            selected_q = q
    custom_q = st.text_input(
        "Or type your own:",
        placeholder="e.g. How does authentication work?",
        key=widget_key("custom_q", slot),
    )
    new_question = preset_q or custom_q or selected_q

    just_kicked = False
    if new_question and (
        stg == "input" or new_question != ss_get(st.session_state, "active_question", slot=slot)
    ):
        ss_set(st.session_state, "active_question", new_question, slot=slot)
        ss_set(st.session_state, "stage", "running", slot=slot)
        ss_set(st.session_state, "draft", None, slot=slot)
        ss_set(st.session_state, "final_state", None, slot=slot)
        just_kicked = True
    return new_question, just_kicked


def shared_question_for_compare():
    """In compare mode, render a single question input above both columns,
    syncing it into both slots' active_question."""
    # Display only if at least one slot is at input/done
    stg_a = ss_get(st.session_state, "stage", slot="a", default="input")
    stg_b = ss_get(st.session_state, "stage", slot="b", default="input")
    if stg_a not in ("input", "done") and stg_b not in ("input", "done"):
        return

    st.markdown("**Ask the same question to both repos:**")
    q_cols = st.columns(3)
    selected_q = None
    for idx, q in enumerate(QUESTIONS):
        if q_cols[idx % 3].button(q, key=widget_key(f"q_{idx}", "shared")):
            selected_q = q
    custom_q = st.text_input(
        "Or type your own:",
        placeholder="e.g. How does authentication work?",
        key="custom_q_shared",
    )
    new_question = preset_q or custom_q or selected_q
    if not new_question:
        return

    triggered = False
    for s in ("a", "b"):
        cur = ss_get(st.session_state, "active_question", slot=s)
        stg = ss_get(st.session_state, "stage", slot=s, default="input")
        if stg in ("input", "done") and (new_question != cur):
            ss_set(st.session_state, "active_question", new_question, slot=s)
            ss_set(st.session_state, "stage", "running", slot=s)
            ss_set(st.session_state, "draft", None, slot=s)
            ss_set(st.session_state, "final_state", None, slot=s)
            triggered = True
    if triggered:
        st.rerun()


# ---------------------------------------------------------------------------
# The pipeline — runs for a single slot
# ---------------------------------------------------------------------------
def run_pipeline_for_slot(slot, owner, repo, repo_name, readme):
    """Execute the stage machine for one slot.

    Reads/writes session state via ss_get/ss_set with the given slot.
    In single-repo mode pass slot=None (canonical keys preserved).
    """
    set_repo(owner, repo)

    stage = ss_get(st.session_state, "stage", slot=slot, default="input")
    active_q = ss_get(st.session_state, "active_question", slot=slot)

    # =========================================================================
    # STAGE: running — pre_synth + streaming synthesis → approval
    # =========================================================================
    if stage == "running" and active_q:
        question = active_q
        trace = RunTrace(repo=repo_name, question=question, user_level=level)

        status_box = st.status("🚀 Starting RepoLens pipeline...", expanded=True)
        phase_labels = {
            "index": "📚", "plan": "📋", "research": "🔬",
            "synthesis": "✍️", "review": "🔍", "revision": "✏️",
        }

        def status_cb(phase: str, label: str):
            icon = phase_labels.get(phase, "•")
            status_box.update(label=f"{icon} {label}" if not label.startswith(icon) else label)

        initial_state = {
            "owner": owner, "repo": repo, "repo_name": repo_name,
            "question": question, "user_level": level, "style": style,
            "readme": readme, "trace": trace, "status_cb": status_cb,
            "force_reindex": ss_pop(st.session_state, "force_reindex", slot=slot, default=False),
            "findings": [], "tool_calls": [], "revision_count": 0,
        }

        try:
            pre_state = st.session_state.pre_synth_graph.invoke(
                initial_state, config={"recursion_limit": 25},
            )
        except Exception as e:
            st.error(f"Pipeline failed before synthesis: {e}")
            reset_slot(st.session_state, slot=slot)
            return

        status_box.update(label="✍️ Streaming answer...", state="running")

        plan_obj = pre_state.get("plan")
        final_answer = ""
        if plan_obj:
            st.markdown("### 📝 Draft Answer")
            with Timer() as _synth_t:
                try:
                    final_answer = st.write_stream(
                        synthesize_stream(
                            plan_obj,
                            pre_state.get("findings", []),
                            pre_state.get("readme", ""),
                            pre_state.get("evidence_chunks", ""),
                            style, level,
                        )
                    )
                except Exception as e:
                    st.error(f"Streaming synthesis failed: {e}")
                    final_answer = "\n\n---\n\n".join(pre_state.get("findings", []))
                    trace.add_event("synthesis", f"Failed: {e}", _synth_t.elapsed_ms, error=str(e))
            trace.add_event("synthesis", "Answer streamed", _synth_t.elapsed_ms)
            trace.final_answer_length = len(final_answer or "")

        status_box.update(label="📝 Draft ready — awaiting your approval", state="complete")

        ss_set(st.session_state, "draft", {
            "question": question,
            "final_answer": final_answer,
            "pre_state": pre_state,
            "trace": trace,
            "owner": owner, "repo": repo, "repo_name": repo_name,
            "user_level": level, "style": style, "readme": readme,
        }, slot=slot)
        ss_set(st.session_state, "retriever", pre_state.get("retriever"), slot=slot)
        ss_set(st.session_state, "evidence_chunks", pre_state.get("evidence_chunks", ""), slot=slot)
        ss_set(st.session_state, "stage", "approval", slot=slot)
        st.rerun()

    # =========================================================================
    # STAGE: approval / user_revise
    # =========================================================================
    if stage in ("approval", "user_revise"):
        draft = ss_get(st.session_state, "draft", slot=slot)
        if not draft:
            return

        st.markdown("### 📝 Draft Answer — review before saving")
        st.caption(f"**Question:** {draft['question']}")
        st.markdown(draft["final_answer"])
        st.markdown("---")

        if stage == "approval":
            st.markdown("**Approve this answer?**")
            c1, c2, c3 = st.columns(3)
            if c1.button("✅ Approve", type="primary", use_container_width=True,
                         key=widget_key("btn_approve", slot)):
                ss_set(st.session_state, "stage", "approved", slot=slot)
                st.rerun()
            if c2.button("✏️ Request revision", use_container_width=True,
                         key=widget_key("btn_revise", slot)):
                ss_set(st.session_state, "stage", "user_revise", slot=slot)
                st.rerun()
            if c3.button("🗑️ Discard", use_container_width=True,
                         help="Throw away this draft. Nothing is saved.",
                         key=widget_key("btn_discard", slot)):
                reset_slot(st.session_state, slot=slot)
                st.rerun()
        else:
            st.markdown("**What should change?**")
            fb = st.text_area(
                "Describe the issue or what you'd like the answer to address:",
                key=widget_key("revise_feedback_input", slot),
                placeholder="e.g. The setup section is too vague.",
                height=120,
            )
            c1, c2 = st.columns(2)
            if c1.button("Apply revision", type="primary", disabled=not fb.strip(),
                         use_container_width=True,
                         key=widget_key("btn_apply_revise", slot)):
                with st.spinner("Revising answer based on your feedback..."):
                    try:
                        new_ans = revise_answer(
                            draft["final_answer"],
                            {"issues": [{
                                "type": "user_request",
                                "description": fb,
                                "suggestion": fb,
                            }]},
                            draft["question"],
                            draft["pre_state"].get("evidence_chunks", ""),
                            draft["user_level"],
                        )
                        draft["final_answer"] = new_ans
                        ss_set(st.session_state, "draft", draft, slot=slot)
                        if draft.get("trace"):
                            draft["trace"].add_event("revision", "User-requested revision applied", 0)
                        ss_set(st.session_state, "stage", "approval", slot=slot)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Revision failed: {e}")
            if c2.button("Cancel", use_container_width=True,
                         key=widget_key("btn_revise_cancel", slot)):
                ss_set(st.session_state, "stage", "approval", slot=slot)
                st.rerun()
        return

    # =========================================================================
    # STAGE: approved — post_synth_graph, persist, advance to done
    # =========================================================================
    if stage == "approved":
        draft = ss_get(st.session_state, "draft", slot=slot)
        if not draft:
            return
        pre_state = draft["pre_state"]
        final_answer = draft["final_answer"]
        trace = draft["trace"]

        status_box = st.status("🔍 Reviewing & finalizing...", expanded=True)
        phase_labels = {"review": "🔍", "revision": "✏️"}

        def status_cb_post(phase: str, label: str):
            icon = phase_labels.get(phase, "•")
            status_box.update(label=f"{icon} {label}" if not label.startswith(icon) else label)

        try:
            final_state = st.session_state.post_synth_graph.invoke(
                {**pre_state, "final_answer": final_answer, "status_cb": status_cb_post,
                 "trace": trace},
                config={"recursion_limit": 10},
            )
        except Exception as e:
            st.error(f"Review failed: {e}")
            final_state = {**pre_state, "final_answer": final_answer,
                           "review_result": {"quality_score": 0, "summary": f"Review failed: {e}"}}

        status_box.update(label="✅ Pipeline complete!", state="complete")

        review_result = final_state.get("review_result", {}) or {}
        final_answer = final_state.get("final_answer", final_answer)

        add_question(
            repo=repo_name,
            question=draft["question"],
            user_level=level,
            answer_preview=final_answer[:500],
            quality_score=review_result.get("quality_score", 0),
        )
        if trace:
            trace.finalize()
            ss_set(st.session_state, "trace", trace, slot=slot)

        ss_set(st.session_state, "final_state", final_state, slot=slot)
        ss_set(st.session_state, "stage", "done", slot=slot)
        st.rerun()

    # =========================================================================
    # STAGE: done — render finalized result
    # =========================================================================
    if stage == "done":
        final_state = ss_get(st.session_state, "final_state", slot=slot)
        draft = ss_get(st.session_state, "draft", slot=slot)
        if not (final_state and draft):
            return
        trace = draft.get("trace") or ss_get(st.session_state, "trace", slot=slot)
        question = draft["question"]

        plan = final_state.get("plan")
        findings = final_state.get("findings", []) or []
        all_tool_calls = final_state.get("tool_calls", []) or []
        final_answer = final_state.get("final_answer", "") or ""
        review_result = final_state.get("review_result", {}) or {}
        evidence_chunks = final_state.get("evidence_chunks", "") or ""
        retriever = final_state.get("retriever") or ss_get(st.session_state, "retriever", slot=slot)

        if not plan:
            st.error("Planning phase failed — no plan was created.")
            return

        # Show plan in sidebar (single-repo only — too cluttered with two)
        if slot is None:
            with st.sidebar:
                st.markdown("---")
                st.markdown("**📋 Current Plan**")
                for step in plan.steps:
                    st.caption(f"{step.id}. {step.title}")

        st.markdown(f"### ✅ {slot_label(slot)}Saved Answer")
        st.caption(f"**Question:** {question}")
        st.markdown(final_answer)
        st.markdown("---")

        score = review_result.get("quality_score", 0)
        summary = review_result.get("summary", "")
        if score >= 8:
            st.success(f"✅ Quality Score: {score}/10 — {summary}")
        elif score >= 5:
            st.warning(f"⚠️ Quality Score: {score}/10 — {summary}")
        else:
            st.error(f"❌ Quality Score: {score}/10 — {summary}")

        if final_state.get("revision_count", 0) > 0:
            st.caption("✏️ Auto-revised once based on reviewer feedback.")

        # ----- Export buttons -----
        dl_score = review_result.get("quality_score", "?")
        md_blob = to_markdown(
            repo_name=repo_name,
            question=question,
            user_level=level,
            style=style,
            quality_score=dl_score,
            answer=final_answer,
            indexed_files=getattr(retriever, "indexed_files", []) if retriever else [],
        )
        safe_slug = f"{owner}_{repo}".replace("/", "_")
        dl_cols = st.columns(2)
        dl_cols[0].download_button(
            "⬇️ Markdown", md_blob,
            file_name=f"repolens_{safe_slug}.md",
            mime="text/markdown", use_container_width=True,
            key=widget_key("dl_md", slot),
        )
        try:
            pdf_bytes = to_pdf(
                repo_name=repo_name, question=question, user_level=level,
                quality_score=dl_score, answer=final_answer,
            )
            dl_cols[1].download_button(
                "⬇️ PDF", pdf_bytes,
                file_name=f"repolens_{safe_slug}.pdf",
                mime="application/pdf", use_container_width=True,
                key=widget_key("dl_pdf", slot),
            )
        except Exception as e:
            dl_cols[1].caption(f"PDF unavailable: {e}")

        # ===== TABS =====
        st.markdown("---")
        if slot is None:
            tab1, tab2, tab3, tab4, tab5 = st.tabs(
                ["📚 Evidence", "🧠 Memory", "📊 Trace", "🔬 Details", "📈 Eval"]
            )
        else:
            tab1, tab4 = st.tabs(["📚 Evidence", "🔬 Details"])
            tab2 = tab3 = tab5 = None

        with tab1:
            st.markdown("### Retrieved Evidence Chunks")
            if evidence_chunks:
                st.markdown(evidence_chunks)
            else:
                st.info("No chunks retrieved.")

            st.markdown("### Indexed Files")
            if retriever and retriever.indexed_files:
                for f in retriever.indexed_files:
                    st.text(f"📄 {f}")
                st.caption(f"Total: {len(retriever.indexed_files)} files, {retriever.chunk_count} chunks")

        if tab2 is not None:
            with tab2:
                st.markdown("### User Profile")
                st.json(get_profile())
                st.markdown("### Question History")
                history = get_history(10)
                if history:
                    for h in history:
                        with st.expander(f"❓ {h['question'][:60]}... ({h['repo']})"):
                            st.caption(f"Level: {h['user_level']} | Score: {h['quality_score']} | {h['asked_at'][:16]}")
                            st.text(h["answer_preview"])
                else:
                    st.info("No history yet.")

        if tab3 is not None:
            with tab3:
                st.markdown("### Run Trace")
                if trace:
                    tsumm = trace.summary()
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Total Time", tsumm["total_time"])
                    col_b.metric("Tool Calls", tsumm["tool_calls"])
                    col_c.metric("Quality", f"{tsumm['quality_score']}/10")

                    st.markdown("#### Phase Timing")
                    for phase, t_val in tsumm["phase_times"].items():
                        st.text(f"  {phase}: {t_val}")

                    st.markdown("#### Event Log")
                    for line in trace.event_log():
                        st.text(line)

                    if tsumm["errors"]:
                        st.markdown("#### Errors")
                        for err in tsumm["errors"]:
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

        if tab5 is not None:
            with tab5:
                _render_eval_tab(owner, repo, repo_name, readme, retriever)


def _render_eval_tab(owner, repo, repo_name, readme, retriever):
    """Render the eval suite tab — single-repo mode only."""
    st.markdown("### 🧪 Evaluation Suite")
    st.caption(
        "Benchmarks the assistant against 10 standard onboarding questions, "
        "scoring each on 5 criteria (right_file, citation_present, answer_complete, "
        "no_hallucination, clear_for_level)."
    )
    eval_mode = st.session_state.pop("run_eval", None)

    if eval_mode and retriever:
        limit = None if eval_mode == "full" else 3
        eval_status = st.status(
            f"Running eval ({eval_mode}: "
            f"{limit or 10} questions)...", expanded=True
        )

        def _eval_progress(idx, total, q):
            eval_status.update(label=f"Eval {idx}/{total}: {q[:50]}")

        def _eval_answer_fn(q: str) -> str:
            eval_init = {
                "owner": owner, "repo": repo, "repo_name": repo_name,
                "question": q, "user_level": level, "style": style,
                "readme": readme, "trace": None, "status_cb": None,
                "force_reindex": False, "retriever": retriever,
                "findings": [], "tool_calls": [], "revision_count": 0,
            }
            pre = st.session_state.pre_synth_graph.invoke(
                eval_init, config={"recursion_limit": 25}
            )
            return synthesize_answer_blocking(
                pre.get("plan"), pre.get("findings", []),
                pre.get("readme", ""), pre.get("evidence_chunks", ""),
                style, level,
            )

        try:
            eval_result = run_eval_suite(
                answer_fn=_eval_answer_fn,
                repo_name=repo_name, user_level=level,
                indexed_files=retriever.indexed_files,
                limit=limit, progress_callback=_eval_progress,
            )
            eval_status.update(
                label=f"✅ Eval complete: {eval_result['percentage']}%",
                state="complete",
            )
            st.session_state.last_eval = eval_result
        except Exception as e:
            eval_status.update(label=f"❌ Eval failed: {e}", state="error")
            st.session_state.last_eval = None

    last_eval = st.session_state.get("last_eval")
    if last_eval:
        cols = st.columns(3)
        cols[0].metric("Score", f"{last_eval['percentage']}%")
        cols[1].metric("Total", f"{last_eval['total_score']}/{last_eval['max_score']}")
        cols[2].metric("Questions", last_eval.get("questions_run", "?"))

        for r in last_eval["results"]:
            with st.expander(
                f"Q{r['id']}: {r['question']} — {r['scores'].get('total', 0)}/5"
            ):
                st.json(r["scores"])
                st.caption("Answer preview:")
                st.text(r["answer_preview"])
    else:
        st.info(
            "Click **Run Eval Suite** in the sidebar to score this repo against "
            "the benchmark questions."
        )


# ---------------------------------------------------------------------------
# Entry point dispatch
# ---------------------------------------------------------------------------
if compare_mode:
    owner_a, repo_a = parse_or_stop(repo_url, "Repo A")
    owner_b, repo_b = parse_or_stop(repo_url_b, "Repo B")
    repo_name_a = f"{owner_a}/{repo_a}"
    repo_name_b = f"{owner_b}/{repo_b}"
    update_profile(last_repo=repo_name_a)

    readme_a = fetch_readme(owner_a, repo_a)
    readme_b = fetch_readme(owner_b, repo_b)
    if not readme_a:
        st.warning(f"Could not fetch README for {repo_name_a}.")
        st.stop()
    if not readme_b:
        st.warning(f"Could not fetch README for {repo_name_b}.")
        st.stop()

    shared_question_for_compare()

    col_a, col_b = st.columns(2, gap="medium")
    with col_a:
        st.markdown(f"### 🅰️ `{repo_name_a}`")
        run_pipeline_for_slot("a", owner_a, repo_a, repo_name_a, readme_a)
    with col_b:
        st.markdown(f"### 🅱️ `{repo_name_b}`")
        run_pipeline_for_slot("b", owner_b, repo_b, repo_name_b, readme_b)

else:
    owner, repo = parse_or_stop(repo_url)
    repo_name = f"{owner}/{repo}"
    update_profile(last_repo=repo_name)

    readme = fetch_readme(owner, repo)
    if not readme:
        st.warning("Could not fetch README. The repo may be private or have no README.")
        st.stop()

    new_q, just_kicked = render_question_input(slot=None)
    if just_kicked:
        st.rerun()

    run_pipeline_for_slot(None, owner, repo, repo_name, readme)
