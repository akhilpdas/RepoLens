"""RepoLens LangGraph orchestration.

Defines a ``StateGraph`` that wires the 5-phase pipeline::

    index → plan → research → synthesize → review → (revise → review)? → END

The ``review → revise`` edge is a real conditional edge (no hardcoded ``if``
in ``app.py``). Revision is capped at :data:`REVISION_CAP` = 1 iteration to
prevent loops.

State is a :class:`GraphState` ``TypedDict`` so non-serializable values
(retriever handle, tracer, status callback) can flow through LangGraph
without needing a checkpointer.

Three compiled graphs are exported:

* :func:`build_graph` — full pipeline, used for tests / non-streaming flows.
* :func:`build_pre_synth_graph` — ``index → plan → research`` only. Stops
  before the synthesizer so streaming can render in the Streamlit UI.
* :func:`build_post_synth_graph` — ``review → (revise → review)?`` only.
  Runs after the user approves the streamed draft (HITL gate in ``app.py``).

The split exists so :func:`synthesize_stream` can be consumed by
``st.write_stream`` between the two halves — LangGraph itself doesn't
need to be in the streaming hot path.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional, TypedDict

from groq import Groq
from langgraph.graph import StateGraph, END

from planner import create_plan
from reviewer import review_answer, revise_answer
from retriever import RepoRetriever
from memory import get_memory_context
from state import Plan, StepStatus
from tools import TOOL_DEFINITIONS, TOOL_MAP
from tracer import Timer


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------
class GraphState(TypedDict, total=False):
    # Inputs
    owner: str
    repo: str
    repo_name: str
    question: str
    user_level: str
    style: str
    readme: str

    # Cross-node objects (non-serializable; OK without a checkpointer)
    retriever: Any              # RepoRetriever
    trace: Any                  # RunTrace
    status_cb: Any              # callable(phase: str, label: str) for Streamlit
    force_reindex: bool

    # Produced by nodes
    index_stats: dict
    evidence_chunks: str
    plan: Plan
    findings: list
    tool_calls: list
    final_answer: str
    review_result: dict
    revision_count: int
    error: str


# ---------------------------------------------------------------------------
# Prompts (moved from app.py so app.py becomes pure UI)
# ---------------------------------------------------------------------------
RESEARCHER_SYSTEM_PROMPT = """You are the Researcher for RepoLens, a GitHub repo onboarding assistant.

You are executing ONE step of an investigation plan. You have 3 tools:
- list_files(path) — list files/folders at a path (use "" for root)
- read_file(path) — read a file's contents
- search_docs(query) — search for a keyword across the repo

STRICT RULES:
1. Execute the current plan step using the suggested tools.
2. You also have RETRIEVED CHUNKS from the codebase — prefer these over guessing.
3. NEVER state something as fact unless you have file-based evidence.
4. If you don't know, say "Not found in indexed files" — do NOT guess.
5. ALWAYS cite file paths for any claims using format: (source: filename.ext)
6. If a retrieved chunk answers the question, cite it directly.
7. Keep findings concise — 3-8 bullet points per step, not paragraphs.
8. Do NOT produce the final user-facing answer — just findings for this step."""


SYNTHESIZER_SYSTEM_PROMPT_TEMPLATE = (
    "You are RepoLens, an expert developer onboarding assistant.\n"
    "Synthesize the investigation findings into a final answer.\n\n"
    "STRICT RULES:\n"
    "- NEVER answer without evidence. Every factual claim MUST cite a file: (source: filename)\n"
    "- Prefer information from retrieved chunks and read files over general knowledge\n"
    "- If evidence is missing for a topic, say 'Not found in the codebase' rather than guessing\n"
    "- For setup instructions: include exact commands, file names, and prerequisites\n"
    "- Keep answers focused — avoid filler paragraphs. Use bullet points and headers\n"
    "- Do NOT repeat the question back. Start with the answer directly\n"
    "- Use markdown formatting with clear section headers\n"
    "- Style: {style_instruction}\n"
    "- Tailor for a **{user_level}** developer.\n"
    "- For beginners: explain jargon, add context\n"
    "- For advanced: skip basics, focus on architecture and internals"
)

STYLE_INSTRUCTIONS = {
    "concise": "Keep the answer brief and to the point. Use bullet points.",
    "balanced": "Provide a well-structured answer with moderate detail.",
    "detailed": "Provide a comprehensive, in-depth answer with examples and explanations.",
}


def _client() -> Groq:
    return Groq(api_key=os.environ["GROQ_API_KEY"])


def _emit(state: GraphState, phase: str, label: str) -> None:
    cb = state.get("status_cb")
    if cb:
        try:
            cb(phase, label)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Node: index (RAG)
# ---------------------------------------------------------------------------
def node_index(state: GraphState) -> GraphState:
    _emit(state, "index", "📚 Indexing repo for retrieval...")
    trace = state.get("trace")
    retriever: RepoRetriever = state.get("retriever") or RepoRetriever(state["owner"], state["repo"])

    with Timer() as t:
        try:
            stats = retriever.index(
                status_callback=lambda msg: _emit(state, "index", f"📚 {msg}"),
                force=state.get("force_reindex", False),
            )
            if trace:
                trace.files_indexed = stats.get("files_indexed", 0)
        except TypeError:
            # Pre-Phase-3 retriever has no `force` kwarg
            stats = retriever.index(status_callback=lambda msg: _emit(state, "index", f"📚 {msg}"))
            if trace:
                trace.files_indexed = stats.get("files_indexed", 0)
        except Exception as e:
            stats = {"files_indexed": 0, "chunks_created": 0, "files": []}
            if trace:
                trace.add_event("index", f"Indexing failed: {e}", 0, error=str(e))
    if trace:
        trace.add_event(
            "index",
            f"Indexed {stats.get('files_indexed', 0)} files, {stats.get('chunks_created', 0)} chunks",
            t.elapsed_ms,
        )

    # Pre-fetch evidence for the question (used by synthesizer + research)
    evidence = ""
    try:
        evidence = retriever.get_context_string(state["question"], n_results=5)
    except Exception:
        evidence = ""
    if trace:
        trace.chunks_retrieved = min(5, getattr(retriever, "chunk_count", 0))

    _emit(state, "index", f"📚 Indexed {stats.get('files_indexed', 0)} files ({stats.get('chunks_created', 0)} chunks)")

    return {
        **state,
        "retriever": retriever,
        "index_stats": stats,
        "evidence_chunks": evidence,
    }


# ---------------------------------------------------------------------------
# Node: plan
# ---------------------------------------------------------------------------
def node_plan(state: GraphState) -> GraphState:
    _emit(state, "plan", "📋 Creating investigation plan...")
    trace = state.get("trace")

    with Timer() as t:
        try:
            plan = create_plan(
                question=state["question"],
                repo_name=state["repo_name"],
                user_level=state["user_level"],
                readme_preview=state.get("readme", ""),
            )
            if trace:
                trace.add_event("plan", f"Created {len(plan.steps)}-step plan", t.elapsed_ms)
        except Exception as e:
            if trace:
                trace.add_event("plan", f"Failed: {e}", t.elapsed_ms, error=str(e))
            return {**state, "error": f"Planning failed: {e}", "plan": None}

    _emit(state, "plan", f"📋 Plan ready — {len(plan.steps)} steps")
    return {**state, "plan": plan}


# ---------------------------------------------------------------------------
# Node: research
# ---------------------------------------------------------------------------
def _execute_step(step, plan, readme, previous_findings, retriever, status_cb_label):
    """Execute a single research step (moved from app.py). Returns (finding, tool_calls_log)."""
    client = _client()

    rag_context = ""
    if retriever:
        try:
            rag_context = retriever.get_context_string(
                f"{plan.question} {step.title} {step.description}", n_results=3
            )
        except Exception:
            rag_context = ""

    prev_context = ""
    if previous_findings:
        prev_context = "\n\n".join(
            f"### Step {i+1} findings:\n{f}" for i, f in enumerate(previous_findings)
        )
        prev_context = f"\n\nFindings from previous steps:\n{prev_context}"

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
            if status_cb_label:
                status_cb_label(
                    f"Step {step.id}: 🔧 {fn_name}({', '.join(f'{k}={v!r}' for k, v in fn_args.items())})"
                )
            fn = TOOL_MAP.get(fn_name)
            result = fn(**fn_args) if fn else f"Unknown tool: {fn_name}"
            tool_calls_log.append({
                "step": step.id, "tool": fn_name, "args": fn_args,
                "result_preview": result[:300],
            })
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

    messages.append({"role": "user", "content": "Summarize your findings for this step now. Cite file sources."})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=1500,
    )
    return response.choices[0].message.content, tool_calls_log


def node_research(state: GraphState) -> GraphState:
    plan = state.get("plan")
    if not plan:
        return state

    trace = state.get("trace")
    retriever = state.get("retriever")
    readme = state.get("readme", "")

    findings: list[str] = []
    all_tool_calls: list[dict] = []

    _emit(state, "research", "🔬 Researching...")

    for step in plan.steps:
        step.status = StepStatus.RUNNING
        _emit(state, "research", f"Step {step.id}/{len(plan.steps)}: {step.title}")

        # Status callback for tool-call labels
        def _label_cb(label: str, _state=state):
            _emit(_state, "research", label)

        with Timer() as t:
            try:
                finding, step_tools = _execute_step(step, plan, readme, findings, retriever, _label_cb)
                findings.append(finding)
                all_tool_calls.extend(step_tools)
                step.status = StepStatus.DONE
                step.result_summary = (finding or "")[:200]
            except Exception as e:
                findings.append(f"(Step failed: {e})")
                step.status = StepStatus.SKIPPED
                if trace:
                    trace.add_event("research", f"Step {step.id} failed", t.elapsed_ms, step=step.id, error=str(e))
        if trace:
            trace.add_event(
                "research", f"Step {step.id}: {step.title}",
                t.elapsed_ms, step=step.id, detail=step.result_summary,
            )

    if trace:
        trace.tool_calls_count = len(all_tool_calls)

    _emit(state, "research", "🔬 Research complete!")
    return {**state, "findings": findings, "tool_calls": all_tool_calls}


# ---------------------------------------------------------------------------
# Node: synthesize (blocking variant; Phase 4 adds streaming)
# ---------------------------------------------------------------------------
def synthesize_messages(plan: Plan, findings: list, readme: str, evidence_chunks: str, style: str, user_level: str):
    """Build the chat messages used by both blocking and streaming synthesis."""
    findings_text = "\n\n".join(
        f"### Step {i+1}: {plan.steps[i].title}\n{f}" for i, f in enumerate(findings)
    )
    style_instruction = STYLE_INSTRUCTIONS.get(style, "Provide a well-structured answer.")
    sys_prompt = SYNTHESIZER_SYSTEM_PROMPT_TEMPLATE.format(
        style_instruction=style_instruction, user_level=user_level,
    )
    user_prompt = (
        f"Repository: {plan.repo}\n"
        f"Question: {plan.question}\n\n"
        f"Investigation findings:\n{findings_text}\n\n"
        f"Supporting evidence chunks:\n{evidence_chunks[:3000]}\n\n"
        f"Produce the final answer now. Every claim must cite a source file."
    )
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]


def synthesize_answer_blocking(plan, findings, readme, evidence_chunks, style, user_level):
    """Blocking synthesis (used by graph node when not streaming)."""
    client = _client()
    messages = synthesize_messages(plan, findings, readme, evidence_chunks, style, user_level)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=3000,
    )
    return response.choices[0].message.content


def synthesize_stream(plan, findings, readme, evidence_chunks, style, user_level):
    """Streaming synthesis generator (used in Phase 4 with st.write_stream)."""
    client = _client()
    messages = synthesize_messages(plan, findings, readme, evidence_chunks, style, user_level)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=3000,
        stream=True,
    )
    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def node_synthesize(state: GraphState) -> GraphState:
    _emit(state, "synthesis", "✍️ Writing answer...")
    trace = state.get("trace")
    plan = state.get("plan")

    with Timer() as t:
        try:
            answer = synthesize_answer_blocking(
                plan,
                state.get("findings", []),
                state.get("readme", ""),
                state.get("evidence_chunks", ""),
                state.get("style", "balanced"),
                state.get("user_level", "intermediate"),
            )
            if trace:
                trace.add_event("synthesis", "Answer synthesized", t.elapsed_ms)
        except Exception as e:
            answer = "\n\n---\n\n".join(state.get("findings", []))
            if trace:
                trace.add_event("synthesis", f"Failed: {e}", t.elapsed_ms, error=str(e))

    if trace:
        trace.final_answer_length = len(answer)
    _emit(state, "synthesis", "✍️ Answer ready!")
    return {**state, "final_answer": answer}


# ---------------------------------------------------------------------------
# Node: review
# ---------------------------------------------------------------------------
def node_review(state: GraphState) -> GraphState:
    _emit(state, "review", "🔍 Reviewing answer quality...")
    trace = state.get("trace")
    retriever = state.get("retriever")

    with Timer() as t:
        try:
            result = review_answer(
                question=state["question"],
                answer=state.get("final_answer", ""),
                indexed_files=getattr(retriever, "indexed_files", []) if retriever else [],
                evidence_chunks=state.get("evidence_chunks", ""),
                user_level=state.get("user_level", "intermediate"),
            )
            if trace:
                trace.quality_score = result.get("quality_score", 0)
                trace.review_verdict = result.get("verdict", "unknown")
                trace.add_event(
                    "review",
                    f"Verdict: {result.get('verdict')} (score: {result.get('quality_score', '?')})",
                    t.elapsed_ms,
                )
        except Exception as e:
            result = {
                "verdict": "pass", "issues": [], "quality_score": 7,
                "summary": f"Review failed: {e}",
            }
            if trace:
                trace.add_event("review", f"Failed: {e}", t.elapsed_ms, error=str(e))

    _emit(state, "review", f"🔍 Review: {result.get('verdict')} (score: {result.get('quality_score', '?')}/10)")
    return {**state, "review_result": result}


# ---------------------------------------------------------------------------
# Node: revise
# ---------------------------------------------------------------------------
def node_revise(state: GraphState) -> GraphState:
    _emit(state, "revision", "✏️ Revising answer based on review...")
    trace = state.get("trace")

    with Timer() as t:
        try:
            revised = revise_answer(
                state.get("final_answer", ""),
                state.get("review_result", {}),
                state["question"],
                state.get("evidence_chunks", ""),
                state.get("user_level", "intermediate"),
            )
            if trace:
                trace.add_event("revision", "Answer revised", t.elapsed_ms)
        except Exception as e:
            revised = state.get("final_answer", "")
            if trace:
                trace.add_event("revision", f"Failed: {e}", t.elapsed_ms, error=str(e))

    _emit(state, "revision", "✏️ Answer revised!")
    return {
        **state,
        "final_answer": revised,
        "revision_count": state.get("revision_count", 0) + 1,
    }


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------
REVISION_CAP = 1


def route_after_review(state: GraphState) -> str:
    rr = state.get("review_result", {}) or {}
    if (
        rr.get("verdict") == "needs_revision"
        and rr.get("quality_score", 10) < 6
        and state.get("revision_count", 0) < REVISION_CAP
    ):
        return "revise"
    return END


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------
def build_graph():
    """Full pipeline: index → plan → research → synthesize → review → (revise → review)? → END."""
    g = StateGraph(GraphState)
    g.add_node("index", node_index)
    g.add_node("plan", node_plan)
    g.add_node("research", node_research)
    g.add_node("synthesize", node_synthesize)
    g.add_node("review", node_review)
    g.add_node("revise", node_revise)

    g.set_entry_point("index")
    g.add_edge("index", "plan")
    g.add_edge("plan", "research")
    g.add_edge("research", "synthesize")
    g.add_edge("synthesize", "review")
    g.add_conditional_edges("review", route_after_review, {"revise": "revise", END: END})
    g.add_edge("revise", "review")
    return g.compile()


def build_pre_synth_graph():
    """Phase 4 split: index → plan → research → END (then app.py streams synth)."""
    g = StateGraph(GraphState)
    g.add_node("index", node_index)
    g.add_node("plan", node_plan)
    g.add_node("research", node_research)
    g.set_entry_point("index")
    g.add_edge("index", "plan")
    g.add_edge("plan", "research")
    g.add_edge("research", END)
    return g.compile()


def build_post_synth_graph():
    """Phase 4 split: review → (revise → review)? → END.

    Caller must populate `final_answer` in state before invoking.
    """
    g = StateGraph(GraphState)
    g.add_node("review", node_review)
    g.add_node("revise", node_revise)
    g.set_entry_point("review")
    g.add_conditional_edges("review", route_after_review, {"revise": "revise", END: END})
    g.add_edge("revise", "review")
    return g.compile()
