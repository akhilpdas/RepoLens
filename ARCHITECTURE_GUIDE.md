# RepoLens - Complete Architecture & Implementation Guide

A detailed technical guide explaining how RepoLens works, what each part does, and how everything connects together.

---

## Table of Contents

1. [What RepoLens Does](#what-repolens-does)
2. [System Architecture](#system-architecture)
3. [Tech Stack Explained](#tech-stack-explained)
4. [The 5-Phase Pipeline](#the-5-phase-pipeline)
5. [Multi-Agent Roles](#multi-agent-roles)
6. [Code Components](#code-components)
7. [Data Flow](#data-flow)
8. [API Integrations](#api-integrations)
9. [Error Handling](#error-handling)
10. [Performance Notes](#performance-notes)

---

## What RepoLens Does

RepoLens is an **agentic GitHub repository onboarding assistant**. You paste a public GitHub URL and ask a question like "What is the architecture?" or "How do I run this?". RepoLens does not just summarize the README — it runs a multi-step investigation using AI agents:

1. It **indexes** the repo's key files into a local vector database (RAG).
2. A **Planner** agent creates a 3–5 step investigation plan for your specific question.
3. A **Researcher** agent executes each step, using real tools to read files and search the codebase.
4. A **Synthesizer** agent writes the final answer from all gathered evidence.
5. A **Reviewer** agent checks the answer for hallucinations, missing citations, and vague instructions. If the score is low, the answer is automatically revised.

Every factual claim in the answer is backed by a cited file from the actual repo.

---

## System Architecture

### High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                         │
│                        (Streamlit Web App)                           │
│                                                                      │
│  Sidebar:                      Main Panel:                           │
│  ┌────────────────────────┐   ┌──────────────────────────────────┐  │
│  │ - GitHub Repo URL      │   │ - Question buttons (5 presets)   │  │
│  │ - Experience Level     │   │ - Custom question text input     │  │
│  │ - Explanation Style    │   │ - Quality score badge            │  │
│  │ - Quick Action presets │   │ - Final answer (markdown)        │  │
│  │ - Current Plan display │   │ - 4 Tabs: Evidence, Memory,      │  │
│  │ - Last repo explored   │   │          Trace, Details          │  │
│  └────────────────────────┘   └──────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ User submits question
                                       │
┌──────────────────────────────────────▼──────────────────────────────┐
│                      PIPELINE ORCHESTRATOR (app.py)                 │
│                                                                      │
│  Phase 0: INDEX  →  Phase 1: PLAN  →  Phase 2: RESEARCH             │
│                                                                      │
│  Phase 3: SYNTHESIZE  →  Phase 4: REVIEW / (REVISE)                 │
└──────────┬───────────────────┬───────────────────┬──────────────────┘
           │                   │                   │
    ┌──────▼──────┐   ┌────────▼───────┐   ┌───────▼──────────┐
    │  retriever  │   │  planner.py    │   │  reviewer.py     │
    │  (ChromaDB  │   │  (Planner LLM) │   │  (Reviewer LLM)  │
    │   RAG)      │   └────────────────┘   └──────────────────┘
    └─────────────┘
           │
    ┌──────▼──────┐   ┌────────────────┐   ┌──────────────────┐
    │  tools.py   │   │  memory.py     │   │  tracer.py       │
    │  (3 GitHub  │   │  (SQLite user  │   │  (per-run        │
    │   tools)    │   │   memory)      │   │   observability) │
    └─────────────┘   └────────────────┘   └──────────────────┘
           │
    ┌──────▼──────────────────┐
    │        EXTERNAL APIs     │
    │  ┌───────────────────┐  │
    │  │ GitHub REST API   │  │
    │  │ - list_files      │  │
    │  │ - read_file       │  │
    │  │ - search_docs     │  │
    │  └───────────────────┘  │
    │  ┌───────────────────┐  │
    │  │   Groq API        │  │
    │  │ llama-3.3-70b-    │  │
    │  │ versatile         │  │
    │  └───────────────────┘  │
    └─────────────────────────┘
```

### File Map

```
RepoLens/
├── app.py           — Main Streamlit app; orchestrates the 5-phase pipeline
├── tools.py         — 3 callable tools for the Researcher (list_files, read_file, search_docs)
├── planner.py       — Planner LLM: converts a question into a 3–5 step JSON plan
├── retriever.py     — RAG module: indexes repo files into ChromaDB, serves context chunks
├── reviewer.py      — Reviewer LLM: quality-checks answers, returns verdict + score 1–10
├── memory.py        — SQLite-backed persistent memory (user profile + question history)
├── state.py         — Dataclasses: PlanStep, Plan, SessionState; StepStatus enum
├── tracer.py        — Observability: TraceEvent, RunTrace, Timer context manager
├── evaluator.py     — 10 benchmark questions scored on 5 criteria for offline evals
└── requirements.txt — streamlit, groq, chromadb, langgraph, requests, python-dotenv
```

---

## Tech Stack Explained

### 1. Frontend: Streamlit

Streamlit turns Python scripts into interactive web apps — no HTML, CSS, or JavaScript needed.

```python
# Everything in the sidebar
with st.sidebar:
    repo_url = st.text_input("GitHub Repo URL")
    level = st.selectbox("Experience level", ["beginner", "intermediate", "advanced"])
    style = st.selectbox("Explanation style", ["concise", "balanced", "detailed"])

# Tabbed results panel
tab1, tab2, tab3, tab4 = st.tabs(["Evidence", "Memory", "Trace", "Details"])
```

The four result tabs show:
- **Evidence** — the raw ChromaDB chunks that were retrieved and which files were indexed
- **Memory** — your stored user profile and the last 10 questions you asked
- **Trace** — per-phase timing, tool call count, quality score, and the full event log
- **Details** — the investigation plan, per-step findings, tool call log, and full reviewer JSON

### 2. Backend: Python

Python is used for all application logic. Key features used throughout the codebase:

```python
# Dataclasses for structured state (state.py)
@dataclass
class PlanStep:
    id: int
    title: str
    description: str
    suggested_tools: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING

# Enums for step status
class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"

# Context managers for timing (tracer.py)
with Timer() as t:
    finding = execute_step(step, ...)
trace.add_event("research", f"Step {step.id}", t.elapsed_ms)
```

### 3. LLM: Groq with Llama 3.3-70b-versatile

All four agent roles (Planner, Researcher, Synthesizer, Reviewer) call the same Groq API endpoint with different system prompts.

```python
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0.2,       # Low = consistent, deterministic output
    max_tokens=800,        # Planner: compact JSON plan
    response_format={"type": "json_object"},  # Forced JSON for Planner/Reviewer
)
```

The Researcher uses **function/tool calling** — Groq sends tool call requests back, the app executes the Python function, and feeds the result back into the conversation:

```python
# Groq sends back a tool_call; the app dispatches it
for tool_call in msg.tool_calls:
    fn_name = tool_call.function.name         # e.g. "read_file"
    fn_args = json.loads(tool_call.function.arguments)
    fn = TOOL_MAP.get(fn_name)
    result = fn(**fn_args)                    # Executes the real GitHub API call
    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
```

### 4. RAG: ChromaDB (in-memory)

ChromaDB stores text chunks as vectors and answers similarity queries ("which chunks are most relevant to this question?"). It runs entirely in memory — no external database needed.

```python
# Create a collection per repo
self.client = chromadb.Client(Settings(anonymized_telemetry=False))
self.collection = self.client.create_collection(
    name=collection_name,
    metadata={"hnsw:space": "cosine"},   # Cosine similarity distance
)

# Add chunks
self.collection.add(documents=[...], metadatas=[...], ids=[...])

# Query at inference time
results = self.collection.query(query_texts=[question], n_results=5)
```

### 5. Memory: SQLite

SQLite stores two tables in `repolens_memory.db`:
- `user_profile` — one row: skill_level, explanation_style, last_repo
- `question_history` — up to 20 most recent questions with repo, user_level, answer_preview, quality_score

```python
# Builds a plain-text context string injected into every Researcher prompt
def get_memory_context(repo: str, user_level: str) -> str:
    # Returns something like:
    # "User skill level: beginner
    #  Explanation style preference: detailed
    #  Previous questions about this repo:
    #    - "How do I run it?" (level: beginner, score: 8)"
```

---

## The 5-Phase Pipeline

Every time you submit a question, `app.py` runs five phases in sequence:

```
Phase 0: INDEX
  └─ RepoRetriever fetches the recursive file tree from GitHub
  └─ Selects files: README, docs/, config manifests, entry-point source files
  └─ Chunks each file at 800 chars with 200-char overlap
  └─ Stores all chunks in a fresh ChromaDB collection

Phase 1: PLAN
  └─ Planner LLM receives: question, repo name, user level, README preview
  └─ Returns a JSON array of 3–5 PlanStep objects
  └─ Each step has: title, description, suggested_tools

Phase 2: RESEARCH
  └─ For each step in the plan:
      └─ RAG: retrieve top-3 relevant chunks for (question + step title)
      └─ Researcher LLM executes the step using tools (up to 5 rounds per step)
      └─ Tool calls hit the real GitHub API and return file contents / search results
      └─ Step findings are accumulated for the next step

Phase 3: SYNTHESIZE
  └─ Synthesizer LLM receives all step findings + top-5 RAG chunks
  └─ Writes the final markdown answer, respecting explanation style and user level
  └─ Every factual claim must cite a source file

Phase 4: REVIEW (+ optional REVISE)
  └─ Reviewer LLM checks the draft answer against indexed files and evidence chunks
  └─ Returns: verdict ("pass" | "needs_revision"), issues list, quality_score 1–10
  └─ If score < 6 and verdict == "needs_revision": Reviser LLM rewrites the answer
  └─ Final answer and score are saved to SQLite memory
```

### Pipeline Phase Diagram

```
User Question
     │
     ▼
┌─────────┐
│  INDEX  │ ← GitHub API (recursive tree) → ChromaDB chunks
└────┬────┘
     │
     ▼
┌─────────┐
│  PLAN   │ ← Groq (json_object mode) → Plan(steps=[PlanStep, ...])
└────┬────┘
     │
     ▼
┌──────────┐
│ RESEARCH │ ← For each step:
│          │     RAG chunks (ChromaDB) ──────────────────────┐
│          │     Groq tool calling loop (up to 5 rounds)     │
│          │     → list_files / read_file / search_docs      │
│          │     → step findings (bullet points + citations) │
└────┬─────┘
     │ all findings + RAG evidence
     ▼
┌───────────┐
│ SYNTHESIZE│ ← Groq → final markdown answer
└─────┬─────┘
      │
      ▼
┌────────┐
│ REVIEW │ ← Groq (json_object mode) → {verdict, issues, quality_score}
│        │   score < 6 → REVISE → Groq → revised answer
└────────┘
      │
      ▼
Display answer + quality badge + 4 tabs
Save to SQLite memory
```

---

## Multi-Agent Roles

RepoLens uses four distinct agent roles. Each has its own system prompt, temperature, and token budget.

### Planner Agent (`planner.py`)

**Job:** Convert the user's question into a focused investigation plan.

**Temperature:** 0.2 (highly deterministic — we want consistent JSON structure)
**Max tokens:** 800
**Output format:** Forced JSON object

```python
# System prompt excerpt
"""
RULES:
1. Produce 3-5 steps. Keep it focused — avoid redundant steps.
3. Order: structure first → read key files → search for specifics → synthesize.
5. Always start by understanding the project structure (list_files at root).
6. Always end with a synthesis step (no tools).
"""
```

Example plan output for "What is the architecture?":
```json
{
  "steps": [
    {"title": "Explore root structure", "suggested_tools": ["list_files"]},
    {"title": "Read README", "suggested_tools": ["read_file"]},
    {"title": "Read main entry files", "suggested_tools": ["read_file"]},
    {"title": "Search for config patterns", "suggested_tools": ["search_docs"]},
    {"title": "Synthesize architecture findings", "suggested_tools": []}
  ]
}
```

### Researcher Agent (`app.py → execute_step`)

**Job:** Execute one plan step at a time using tools and RAG context.

**Temperature:** 0.3
**Max tokens:** 1500 per step
**Tool calling:** Up to 5 rounds per step before forcing a summary

The Researcher receives:
- The step's title, description, and suggested tools
- The top-3 RAG chunks for this step's topic
- All findings from previous steps (running context)
- Memory context (user level, explanation style, past questions)

```python
# Strict rules baked into system prompt
"""
3. NEVER state something as fact unless you have file-based evidence.
4. If you don't know, say "Not found in indexed files" — do NOT guess.
5. ALWAYS cite file paths for any claims using format: (source: filename.ext)
7. Keep findings concise — 3-8 bullet points per step, not paragraphs.
"""
```

### Synthesizer Agent (`app.py → synthesize_answer`)

**Job:** Write the final user-facing answer from all step findings.

**Temperature:** 0.3
**Max tokens:** 3000

The Synthesizer adapts its output based on:
- `explanation_style`: "concise" (bullets), "balanced" (structured), "detailed" (comprehensive)
- `user_level`: beginners get jargon explained; advanced users get architecture focus

### Reviewer Agent (`reviewer.py`)

**Job:** Quality-check the draft answer before it reaches the user.

**Temperature:** 0.2 (strict and consistent judgement)
**Max tokens:** 1000
**Output format:** Forced JSON object

The Reviewer flags five issue types:
| Flag | Meaning |
|------|---------|
| `unsupported` | Factual claim with no cited file |
| `missing_citation` | Claim that should cite a file but doesn't |
| `vague` | Setup instruction without an exact command |
| `bad_ref` | File path cited that doesn't exist in the indexed files |
| `hallucination` | Function/class name not confirmed by evidence chunks |

**Scoring:**
- 9–10: Excellent, well-cited, no issues
- 7–8: Good with minor gaps
- 5–6: Acceptable but has vague or unsupported sections
- 1–4: Poor — hallucinations, missing evidence, or off-topic

If `verdict == "needs_revision"` and `quality_score < 6`, the Reviser (`revise_answer`) is called to rewrite the answer with the issues fixed.

---

## Code Components

### `tools.py` — The 3 GitHub Tools

The tools are plain Python functions registered in `TOOL_DEFINITIONS` (Groq's function-calling format) and `TOOL_MAP` (name → callable).

```python
# Tool 1: list_files
def list_files(path: str = "") -> str:
    # Calls GitHub Contents API: /repos/owner/repo/contents/{path}
    # Returns newline-separated entries with 📁 / 📄 icons

# Tool 2: read_file
def read_file(path: str) -> str:
    # Calls GitHub Contents API for a single file
    # Decodes base64 content, truncates to 8000 chars

# Tool 3: search_docs
def search_docs(query: str) -> str:
    # Calls GitHub Code Search API scoped to the current repo
    # Returns up to 10 matching file paths with text fragments
```

The tools operate on a shared module-level `_owner`/`_repo` state set by `set_repo(owner, repo)` in `app.py` before each run.

### `retriever.py` — ChromaDB RAG

**What gets indexed:**

```
Always indexed:
  - README* (any README variant)
  - Config/manifest files: package.json, requirements.txt, pyproject.toml,
    Dockerfile, docker-compose.yml, Makefile, .env.example, etc.

Up to 10 docs/:
  - Files in docs/ or doc/ with extensions .md, .rst, .txt, .adoc

Top-level docs:
  - Any .md/.rst/.txt at the repo root

Up to 5 entry-point source files:
  - .py/.js/.ts/.go/.rs/.java/.rb files named main, app, index, server,
    cli, __main__, manage, or at the root level
```

**Chunking strategy:**
```python
def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
    # Splits text into 800-character chunks with 200-character overlap
    # Overlap ensures important context at chunk boundaries is not lost
```

Each chunk is stored with metadata: `source` (file path), `chunk_index`, `repo`.

**At query time:**
```python
retriever.get_context_string(question, n_results=5)
# Returns formatted string:
# [Chunk 1] Source: README.md (chunk #0)
# ... (up to 500 chars of content) ...
# ---
# [Chunk 2] Source: app.py (chunk #2)
# ...
```

### `planner.py` — Plan Creation

```python
def create_plan(question, repo_name, user_level, readme_preview) -> Plan:
    # Calls Groq with json_object response_format
    # Parses JSON into Plan(steps=[PlanStep(...), ...])
    # Falls back to a hardcoded 4-step plan if JSON parsing fails
```

### `reviewer.py` — Review and Revision

```python
def review_answer(question, answer, indexed_files, evidence_chunks, user_level) -> dict:
    # Returns: {"verdict": "pass"|"needs_revision", "issues": [...], "quality_score": 1-10, "summary": "..."}

def revise_answer(original_answer, review_result, question, evidence_chunks, user_level) -> str:
    # Only called when score < 6
    # Tells the LLM to fix each flagged issue and return an improved answer
```

### `memory.py` — SQLite Persistence

```python
# Two tables in repolens_memory.db:

# user_profile (single row, id=1)
# skill_level | explanation_style | last_repo | updated_at

# question_history (up to 20 rows, trimmed by asked_at)
# repo | question | user_level | answer_preview | quality_score | asked_at

# Key functions:
get_profile()                          # Returns dict with user preferences
update_profile(skill_level, style, last_repo)
add_question(repo, question, ...)      # Inserts and trims to 20 rows
get_memory_context(repo, user_level)   # Returns plain-text string for prompt injection
```

### `state.py` — Dataclasses

```python
class StepStatus(str, Enum):
    PENDING | RUNNING | DONE | SKIPPED

@dataclass
class PlanStep:
    id: int
    title: str
    description: str
    suggested_tools: list[str]
    status: StepStatus        # Updated live during research phase
    result_summary: str       # First 200 chars of step findings

@dataclass
class Plan:
    question, repo, user_level, steps, created_at
    # Properties: is_complete, current_step, progress (done/total)

@dataclass
class SessionState:
    owner, repo, user_level, readme, plan, tool_calls_log, final_answer
```

### `tracer.py` — Observability

```python
# Timer: context manager that measures elapsed milliseconds
with Timer() as t:
    result = do_something()
# t.elapsed_ms is available after the block

# RunTrace: accumulates events per run
trace = RunTrace(repo=repo_name, question=question, user_level=level)
trace.add_event("research", f"Step {step.id}: {step.title}", t.elapsed_ms, step=step.id)
trace.finalize()          # Sums all event durations into total_duration_ms

# summary() returns a dict with total_time, phase_times, tool_calls, quality_score, errors
# event_log() returns a list of human-readable strings for the Trace tab
```

### `evaluator.py` — Benchmark Eval Suite

```python
BENCHMARK_QUESTIONS = [
    # 10 questions designed to work for any repo:
    # "What is this project?", "How do I run it?", "What files define config?",
    # "Where is the entry point?", "What should a beginner read first?",
    # "What is the architecture?", "What dependencies does this project use?",
    # "How do I contribute?", "What tests exist?", "What is a good first contribution?"
]

# Each answer is scored 0 or 1 on 5 criteria:
# right_file, citation_present, answer_complete, no_hallucination, clear_for_level

# run_eval_suite(answer_fn, repo_name, user_level, indexed_files)
# → Returns per-question scores and an aggregate percentage
```

---

## Data Flow

### Complete Request Walkthrough

```
INPUT: repo_url="https://github.com/owner/repo", question="What is the architecture?", level="beginner"
                                │
              ┌─────────────────▼──────────────────┐
              │ parse_repo() → owner="owner",       │
              │                repo="repo"          │
              │ set_repo(owner, repo)               │
              │ fetch_readme() → readme text        │
              │ fetch_repo_tree() → file list       │
              └─────────────────┬──────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │ PHASE 0: INDEX                      │
              │ RepoRetriever.index()               │
              │   → GitHub recursive tree API       │
              │   → _select_files_to_index()        │
              │   → _chunk_text(800 chars, 200 ovlp)│
              │   → ChromaDB.add(chunks, metadata)  │
              │ Output: N files, M chunks indexed   │
              └─────────────────┬──────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │ PHASE 1: PLAN                       │
              │ create_plan(question, repo, level,  │
              │             readme[:2000])          │
              │   → Groq (temp=0.2, json_object)    │
              │   → Parse JSON → Plan(steps=[...])  │
              │ Output: Plan with 3–5 PlanSteps     │
              └─────────────────┬──────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │ PHASE 2: RESEARCH                   │
              │ For each PlanStep:                  │
              │   1. RAG query (top-3 chunks)       │
              │   2. execute_step(step, plan, ...)  │
              │      → Groq tool-calling loop       │
              │      → list_files / read_file /     │
              │        search_docs → GitHub API     │
              │      → findings (bullet citations)  │
              │   3. Append to findings[]           │
              │ Output: findings[0..N-1]            │
              └─────────────────┬──────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │ PHASE 3: SYNTHESIZE                 │
              │ synthesize_answer(plan, findings,   │
              │   readme, evidence_chunks, style)   │
              │   → Groq (temp=0.3, max_tokens=3000)│
              │   → Markdown answer with citations  │
              │ Output: final_answer (string)       │
              └─────────────────┬──────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │ PHASE 4: REVIEW                     │
              │ review_answer(question, final_answer│
              │   indexed_files, evidence_chunks,   │
              │   user_level)                       │
              │   → Groq (temp=0.2, json_object)    │
              │   → {verdict, issues, score, summary}│
              │                                     │
              │ If score < 6 and needs_revision:    │
              │   revise_answer(answer, review, ...) │
              │   → Groq → revised final_answer     │
              └─────────────────┬──────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │ DISPLAY                             │
              │ Quality badge (green/yellow/red)    │
              │ st.markdown(final_answer)           │
              │ 4 tabs: Evidence / Memory /         │
              │          Trace / Details            │
              └─────────────────┬──────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │ PERSIST                             │
              │ add_question(repo, question,        │
              │   user_level, answer_preview, score)│
              │   → SQLite question_history         │
              │ trace.finalize() → st.session_state │
              └────────────────────────────────────┘
```

---

## API Integrations

### GitHub REST API

RepoLens uses four GitHub API endpoints, all on public repos without authentication:

| Endpoint | Used by | Purpose |
|----------|---------|---------|
| `GET /repos/{owner}/{repo}/readme` | `app.py` | Fetch README text |
| `GET /repos/{owner}/{repo}/git/trees/HEAD` | `app.py` | Get shallow file list |
| `GET /repos/{owner}/{repo}/git/trees/HEAD?recursive=1` | `retriever.py` | Full recursive tree for indexing |
| `GET /repos/{owner}/{repo}/contents/{path}` | `tools.py` | Read a file or list a directory |
| `GET /search/code?q={query}+repo:{owner}/{repo}` | `tools.py` | Full-text search across the repo |

**Rate limits (unauthenticated):**
- Standard endpoints: 60 requests/hour per IP
- Code search: 10 requests/minute per IP (most likely to be rate-limited)

### Groq API

All LLM calls go to the same model: `llama-3.3-70b-versatile`.

| Agent | Temperature | Max Tokens | Response Format |
|-------|------------|------------|----------------|
| Planner | 0.2 | 800 | `json_object` |
| Researcher | 0.3 | 1500 | text (with tool calling) |
| Synthesizer | 0.3 | 3000 | text (markdown) |
| Reviewer | 0.2 | 1000 | `json_object` |
| Reviser | 0.3 | 3000 | text (markdown) |
| Evaluator | 0.1 | 300 | `json_object` |

**Why Groq?**

| Feature | Groq | OpenAI |
|---------|------|--------|
| Cost | Free tier | Paid (~$0.05–0.15/request) |
| Credit card | Not needed | Required |
| Speed | Very fast (hardware inference) | Slower |
| Model | Llama 3.3-70b-versatile | GPT-4 / GPT-3.5 |
| Function calling | Supported | Supported |

---

## Error Handling

Every phase is wrapped in a try/except so that a failure in one phase degrades gracefully rather than crashing the whole run:

```python
# Phase 1: PLAN — fallback to hardcoded 4-step plan
try:
    plan = create_plan(...)
except Exception as e:
    st.error(f"Planning failed: {e}")
    plan = None

# Phase 2: RESEARCH — failed steps are marked SKIPPED, not fatal
try:
    finding, step_tools = execute_step(step, ...)
    step.status = StepStatus.DONE
except Exception as e:
    findings.append(f"(Step failed: {e})")
    step.status = StepStatus.SKIPPED

# Phase 3: SYNTHESIS — fallback to raw findings joined together
try:
    final_answer = synthesize_answer(...)
except Exception as e:
    final_answer = "\n\n---\n\n".join(findings)

# Phase 4: REVIEW — fallback passes the answer through with score=7
try:
    review_result = review_answer(...)
except Exception as e:
    review_result = {"verdict": "pass", "quality_score": 7, ...}
```

Errors are also recorded in the `RunTrace` and appear in the Trace tab under "Errors".

---

## Performance Notes

### What makes it fast
- **Groq's inference hardware** — responses come back in 1–3 seconds
- **ChromaDB in-memory** — no disk I/O for vector search
- **Selective indexing** — only README, configs, docs, and up to 5 entry-point source files are indexed (not the entire codebase)
- **Chunked batching** — ChromaDB has a batch size limit; chunks are added in batches of 100

### Token budgets
- README fed to Planner and Researcher: `readme[:2000]`
- Evidence chunks fed to Synthesizer: `evidence_chunks[:3000]`
- Evidence chunks fed to Reviewer: `evidence_chunks[:4000]`
- Tool results are truncated: file reads cap at 8000 chars; search snippets at 120 chars

### Known limitations
- **Rate limits** — GitHub's unauthenticated code search (10 req/min) can slow the Research phase for repos with many steps that use `search_docs`
- **In-memory RAG** — ChromaDB collection is recreated fresh on every question; indexing the same repo twice does duplicate API calls
- **Private repos** — all GitHub API calls are unauthenticated and only work on public repositories
- **Large repos** — the recursive tree fetch and file indexing will be slower for repos with thousands of files, though file selection caps the actual reads

---

**Now you understand every part of RepoLens — from the moment you paste a URL to the final quality-checked answer displayed in the app.**
