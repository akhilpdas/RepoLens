# RepoLens - Everything You Need to Know

A comprehensive guide explaining the current RepoLens system in detail: what it does, how every component works, and why each design decision was made.

---

## Table of Contents

1. [What is RepoLens?](#what-is-repolens)
2. [What Problem Does It Solve?](#what-problem-does-it-solve)
3. [Technology Stack](#technology-stack)
4. [System Architecture Overview](#system-architecture-overview)
5. [The 5-Phase Pipeline](#the-5-phase-pipeline)
6. [Module-by-Module Breakdown](#module-by-module-breakdown)
7. [Multi-Agent Design](#multi-agent-design)
8. [RAG: Retrieval-Augmented Generation](#rag-retrieval-augmented-generation)
9. [Memory System](#memory-system)
10. [Tracing and Observability](#tracing-and-observability)
11. [Evaluation Framework](#evaluation-framework)
12. [The User Interface](#the-user-interface)
13. [Data Flow: End to End](#data-flow-end-to-end)
14. [Conditions and Limitations](#conditions-and-limitations)

---

## What is RepoLens?

RepoLens is an **agentic GitHub repository onboarding assistant**. You give it a public GitHub repo URL and ask it any question about that repo. It does not guess or generate a generic answer from its training data — it actively investigates: it reads the actual files, searches the codebase, and retrieves relevant chunks before writing an answer. A separate Reviewer agent then checks that answer for quality before you see it.

### What It Does vs. What It Does Not Do

RepoLens is not a simple "summarize the README" tool. Each question triggers a multi-phase pipeline:

- A Planner agent breaks the question into a structured investigation plan
- A Researcher agent executes that plan step-by-step, calling tools against the live GitHub API
- ChromaDB semantic search retrieves the most relevant code and documentation chunks
- A Synthesizer writes the final answer grounded in the retrieved evidence
- A Reviewer checks for hallucinations, missing citations, and vague instructions
- If the answer scores below 6/10, it is automatically revised

Every factual claim in the output must cite a source file. The system refuses to guess.

### Real-World Analogy

```
Traditional approach (paste README into ChatGPT):
- Gets a generic summary based on what the README says
- Hallucinates file names and commands it has never seen
- Cannot look inside source files or configs
- Cannot search the codebase

RepoLens agentic approach:
- Reads the actual files via GitHub API
- Searches for specific concepts across the whole repo
- RAG retrieval finds the most relevant passages
- Reviewer catches any claims that lack evidence
```

---

## What Problem Does It Solve?

### The Code Comprehension Problem

When you encounter an unfamiliar repository, you face several problems simultaneously:

- The README may be incomplete or outdated
- The file structure alone does not explain how components connect
- Config files, build scripts, and package manifests are scattered
- Setup instructions vary in quality and specificity
- You do not know which files matter most

RepoLens solves this by acting as an automated investigator. It knows which files to prioritize (README, package manifests, Dockerfiles, docs/ folders, entry-point source files), indexes them into a searchable vector store, and then uses that knowledge base to answer questions with evidence.

### The Hallucination Problem

General-purpose LLMs frequently hallucinate when asked about specific codebases because they have no access to the actual files. They generate plausible-sounding but wrong file names, function names, and commands. RepoLens addresses this with two mechanisms:

1. **RAG grounding**: Every researcher prompt is seeded with real chunks retrieved from the actual indexed files
2. **Reviewer gate**: A dedicated Reviewer agent checks every answer for unsupported claims, bad file references, and hallucinated technical details before the answer reaches the user

---

## Technology Stack

### Layer 1: User Interface — Streamlit

Streamlit is a Python framework that converts Python scripts into interactive web applications without requiring HTML, CSS, or JavaScript. RepoLens uses Streamlit's `st.status` widgets to show live pipeline progress, `st.tabs` to organize output into panels, and `st.session_state` to carry state across interactions.

Key Streamlit features used:
- `st.status` — collapsible live-updating status blocks for each pipeline phase
- `st.tabs` — organizes Evidence, Memory, Trace, and Details panels below the answer
- `st.session_state` — holds the `SessionState`, `RunTrace`, `RepoRetriever`, and review result between renders
- `st.sidebar` — houses repo URL input, experience level selector, explanation style selector, and preset question buttons

### Layer 2: LLM Inference — Groq + Llama 3.3-70b

All LLM calls go through the Groq API using the `llama-3.3-70b-versatile` model. Groq runs this model on custom LPU hardware, delivering inference in approximately 2-5 seconds per call.

The model is used with **function calling** (also called tool use). The Researcher agent receives a list of tool definitions in JSON Schema format and the model responds with structured tool-call requests that the application dispatches to the real GitHub API.

```python
# From app.py — tool-augmented researcher call
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
```

The Planner and Reviewer use `response_format={"type": "json_object"}` to force structured JSON output, which is then parsed into `Plan`/`PlanStep` and review result dictionaries.

### Layer 3: Vector Search — ChromaDB

ChromaDB is an open-source embedded vector database. RepoLens uses it to index chunked file contents and retrieve the most semantically similar passages for a given question. It runs in-process (no server required) using `chromadb.Client()` with anonymous telemetry disabled.

Each collection uses cosine similarity (`hnsw:space: cosine`). Documents are indexed as plain text; ChromaDB uses its built-in embedding model to vectorize them. Chunks are sized at 800 characters with 200-character overlap to preserve context across boundaries.

### Layer 4: Persistent Memory — SQLite

User preferences and question history are stored in `repolens_memory.db` using Python's built-in `sqlite3` module with WAL journal mode for write performance. Two tables are maintained: `user_profile` (one row, stores skill level, explanation style, last repo) and `question_history` (rolling window of 20 most recent questions with answer previews and quality scores).

### Layer 5: Data Access — GitHub REST API

All repository content is fetched live from the GitHub REST API with no authentication required for public repos. Three endpoints are used:

```
GET /repos/{owner}/{repo}/readme
    Accept: application/vnd.github.v3.raw
    → Returns raw README text

GET /repos/{owner}/{repo}/git/trees/HEAD?recursive=1
    → Returns full file tree (all paths and types)

GET /repos/{owner}/{repo}/contents/{path}
    → Returns file metadata + base64-encoded content

GET /search/code?q={query}+repo:{owner}/{repo}
    → Returns matching file paths with text fragments
```

The unauthenticated rate limit is 60 requests/hour for most endpoints and 10 requests/minute for code search.

---

## System Architecture Overview

```
User Input (URL + Question)
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│                         app.py                                  │
│                   (Orchestrator / UI)                           │
└──────────┬────────────────────────────────────────────────────┘
           │
           │  Phase 0
           ▼
┌──────────────────────┐    GitHub API (git/trees, contents)
│    retriever.py      │◄──────────────────────────────────────┐
│  RepoRetriever       │                                        │
│  (ChromaDB indexing) │                                        │
└──────────┬───────────┘                                        │
           │ indexed chunks                                      │
           │  Phase 1                                            │
           ▼                                                     │
┌──────────────────────┐                                        │
│    planner.py        │                                        │
│  Planner Agent       │◄─── Groq LLM (JSON mode)              │
│  (Plan + PlanSteps)  │                                        │
└──────────┬───────────┘                                        │
           │ Plan object                                         │
           │  Phase 2                                            │
           ▼                                                     │
┌──────────────────────┐    tools.py                            │
│  Researcher Agent    │◄── list_files()  ──────────────────────┤
│  (in app.py:         │◄── read_file()   ──────────────────────┤
│   execute_step())    │◄── search_docs() ──────────────────────┘
│  + RAG chunks        │◄── retriever.get_context_string()
└──────────┬───────────┘
           │ step findings[]
           │  Phase 3
           ▼
┌──────────────────────┐
│  Synthesizer Agent   │◄─── Groq LLM
│  (in app.py:         │
│  synthesize_answer() │
└──────────┬───────────┘
           │ draft answer
           │  Phase 4
           ▼
┌──────────────────────┐
│    reviewer.py       │◄─── Groq LLM (JSON mode)
│  Reviewer Agent      │
│  + optional revision │
└──────────┬───────────┘
           │ final answer + quality score
           ▼
┌──────────────────────────────────────────────────────────────┐
│   Streamlit UI                                                │
│   Main: answer + quality badge                               │
│   Tab 1: Evidence chunks + indexed files                     │
│   Tab 2: Memory (user profile + question history)            │
│   Tab 3: Trace (phase timings, tool calls, event log)        │
│   Tab 4: Details (plan steps, findings, tool calls, review)  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐    ┌──────────────────────┐
│    memory.py         │    │    tracer.py          │
│  SQLite persistence  │    │  RunTrace + Timer     │
└──────────────────────┘    └──────────────────────┘
```

---

## The 5-Phase Pipeline

Every question goes through exactly five phases in sequence. Each phase has a live `st.status` widget showing its progress.

### Phase 0: Index

**What:** The `RepoRetriever` fetches the repo's full file tree recursively from GitHub, selects which files to index based on a priority ruleset, downloads each selected file's content, splits it into overlapping 800-character chunks, and loads all chunks into a fresh ChromaDB in-memory collection.

**File selection rules (from retriever.py):**

```python
CONFIG_PATTERNS = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod", "Gemfile", "pom.xml", "build.gradle",
    "Makefile", "Dockerfile", "docker-compose.yml",
    ".env.example", "requirements.txt", "tsconfig.json", ...
}
DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}
SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb"}
MAX_DOC_FILES = 10
MAX_SOURCE_FILES = 5  # entry points only: main, app, index, server, cli, manage
```

README files (any variant) and all config/manifest files are always indexed. Doc files are capped at 10. Source files are capped at 5, and only entry-point names (main, app, index, server, cli, manage) or top-level files qualify.

**Output:** `index_stats` dict with `files_indexed`, `chunks_created`, and `files` list. These stats are recorded in the `RunTrace`.

**Why this phase first:** RAG context is injected into both the Researcher and Synthesizer prompts. Indexing must complete before any LLM calls.

### Phase 1: Plan

**What:** The Planner agent receives the user's question, the repo name, the user level, and the first 2000 characters of the README. It calls the Groq LLM in JSON mode and receives back a structured list of 3-5 investigation steps.

**Planner system prompt excerpt (from planner.py):**

```
You are the Planner for RepoLens...
RULES:
1. Produce 3-5 steps. Keep it focused — avoid redundant steps.
2. Each step should be a clear, atomic action with a specific goal.
3. Order: structure first → read key files → search for specifics → synthesize.
4. Suggest which tool(s) would be useful for each step.
5. Always start by understanding the project structure (list_files at root).
6. Always end with a synthesis step (no tools).
```

The JSON response is parsed into a `Plan` object containing a list of `PlanStep` dataclasses, each with `id`, `title`, `description`, `suggested_tools`, and a `status` field (PENDING/RUNNING/DONE/SKIPPED).

**Fallback:** If JSON parsing fails, a sensible four-step default plan is used (explore structure, read docs, investigate source, synthesize).

### Phase 2: Research

**What:** The Researcher agent (implemented as `execute_step()` in `app.py`) executes each `PlanStep` in order. For each step:

1. RAG context is retrieved from ChromaDB for the combined question + step title + step description query
2. Previous step findings are appended as context
3. Memory context (user level, explanation style, past questions about this repo) is injected
4. The LLM is called with the three tool definitions if the step has `suggested_tools`
5. If the model returns tool calls, the application dispatches them to the real GitHub API and feeds results back as `role: tool` messages
6. This loop runs up to 5 iterations per step until the model produces a text response (no more tool calls)

**Tool dispatch loop (from app.py):**

```python
for _ in range(5):
    response = client.chat.completions.create(**call_kwargs)
    msg = response.choices[0].message

    if not msg.tool_calls:
        return msg.content, tool_calls_log  # step complete

    messages.append(msg)
    for tool_call in msg.tool_calls:
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)
        fn = TOOL_MAP.get(fn_name)
        result = fn(**fn_args) if fn else f"Unknown tool: {fn_name}"
        tool_calls_log.append({"step": step.id, "tool": fn_name, "args": fn_args, ...})
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
```

All tool calls are logged for display in the Details tab. The Researcher is instructed to cite file paths for every claim using the format `(source: filename.ext)` and to never state facts it cannot back with file evidence.

### Phase 3: Synthesize

**What:** The Synthesizer agent (`synthesize_answer()`) receives the complete list of step findings, the README, and the top 5 RAG evidence chunks. It writes the final user-facing answer in markdown.

The Synthesizer's style instruction is driven by the user's explanation style preference:

```python
style_instruction = {
    "concise": "Keep the answer brief and to the point. Use bullet points.",
    "balanced": "Provide a well-structured answer with moderate detail.",
    "detailed": "Provide a comprehensive, in-depth answer with examples and explanations.",
}.get(style, "Provide a well-structured answer.")
```

The user level (beginner/intermediate/advanced) is also passed: beginners get jargon explained, advanced users get architecture and internals focus.

**Key constraint:** The Synthesizer system prompt contains `NEVER answer without evidence. Every factual claim MUST cite a file: (source: filename)`. If evidence is missing for a topic, the answer must say "Not found in the codebase" rather than guessing.

### Phase 4: Review and Revise

**What:** The Reviewer agent (`review_answer()` in `reviewer.py`) quality-checks the Synthesizer's output. It receives the original question, the draft answer, the list of indexed files, and the evidence chunks. It returns a JSON object with:

- `verdict`: `"pass"` or `"needs_revision"`
- `issues`: list of flagged problems (type, description, location, suggestion)
- `quality_score`: integer 1-10
- `summary`: one-sentence overall assessment

**What the Reviewer checks:**

| Issue Type | Flag | Example |
|---|---|---|
| Unsupported Claims | `UNSUPPORTED` | Factual statement with no file citation |
| Missing Citations | `NEEDS CITATION` | Key claim without a source file |
| Vague Instructions | `VAGUE` | "Install dependencies" without the actual command |
| Bad File References | `BAD REF` | Path that does not appear in the indexed files list |
| Hallucination Risk | `UNVERIFIED` | Function name not confirmed by any chunk |

**Scoring thresholds:**
- 9-10: Excellent — no issues, well-cited, complete
- 7-8: Good — minor issues only; verdict is "pass"
- 5-6: Acceptable — vague sections or unsupported claims; verdict depends
- 1-4: Poor — verdict is "needs_revision"

**Automatic revision:** If `verdict == "needs_revision"` and `quality_score < 6`, the `revise_answer()` function is called. It receives the original answer, the reviewer issues list, the question, and the evidence chunks, and rewrites the answer to fix the flagged problems. The revision is shown to the user instead of the original.

The quality score is displayed as a badge above the answer (green for 8+, yellow for 5-7, red below 5) and is saved to question history.

---

## Module-by-Module Breakdown

### app.py — Orchestrator and UI

The central file. Owns the Streamlit page, the full pipeline execution loop, the `execute_step()` Researcher function, and the `synthesize_answer()` Synthesizer function. Imports from all other modules. Also contains the `parse_repo()` and `fetch_readme()` / `fetch_repo_tree()` helpers.

Key responsibilities:
- Initialize `st.session_state` with `SessionState`, `RunTrace`, `RepoRetriever`, and review result
- Read sidebar preferences and update user profile via `memory.py`
- Execute phases 0-4 in sequence with `st.status` wrappers
- Dispatch tool calls returned by the LLM in the research loop
- Display the final answer, quality badge, and all four tabs

### tools.py — GitHub Tool Implementations

Defines the three tools the Researcher can call, both as Python functions and as JSON Schema tool definitions for the Groq function-calling API.

**`list_files(path: str) -> str`**

Calls `GET /repos/{owner}/{repo}/contents/{path}`. Returns a formatted directory listing with `📁` / `📄` icons sorted directories-first. Used to explore the project structure.

**`read_file(path: str) -> str`**

Calls `GET /repos/{owner}/{repo}/contents/{path}`. Base64-decodes the response and returns up to 8,000 characters. Used to inspect source files, configs, and documentation.

**`search_docs(query: str) -> str`**

Calls the GitHub code search API: `GET /search/code?q={query}+repo:{owner}/{repo}`. Returns up to 10 matching file paths with a 120-character text fragment each. Used to find where a concept or function is defined.

The global `_owner` and `_repo` variables are set via `set_repo(owner, repo)` at the start of each analysis session. `TOOL_DEFINITIONS` is the list of JSON Schema objects passed to the Groq API. `TOOL_MAP` maps function name strings to callables for dispatch.

### planner.py — Planner Agent

Single public function: `create_plan(question, repo_name, user_level, readme_preview) -> Plan`.

Calls the Groq LLM in JSON mode with `temperature=0.2` (low for deterministic plans) and `max_tokens=800`. Parses the JSON into `Plan` and `PlanStep` dataclass instances. The fallback default plan handles JSON parsing failures gracefully.

### retriever.py — RAG Module

`RepoRetriever` class manages a per-session ChromaDB collection.

**`index(status_callback) -> dict`**: Fetches the recursive file tree, selects files using `_select_files_to_index()`, downloads each file via `_fetch_file_content()`, splits into chunks with `_chunk_text(chunk_size=800, overlap=200)`, and batch-adds to ChromaDB in groups of 100 (ChromaDB's batch limit). Returns stats.

**`query(question, n_results) -> list[dict]`**: Calls `collection.query(query_texts=[question])`. Returns list of dicts with `content`, `source`, `chunk_index`, and `distance`.

**`get_context_string(question, n_results) -> str`**: Formats query results into a labeled string for prompt injection:

```
[Chunk 1] Source: README.md (chunk #0)
<content>

---

[Chunk 2] Source: setup.py (chunk #1)
<content>
```

### reviewer.py — Reviewer Agent

Two public functions:

**`review_answer(...) -> dict`**: Sends the answer, indexed file list, and evidence chunks to the Groq LLM in JSON mode with `temperature=0.2`. Returns the verdict, issues list, quality score, and summary.

**`revise_answer(...) -> str`**: Called only when `verdict == "needs_revision"` and score < 6. Formats the reviewer issues as a numbered list and instructs the LLM to rewrite the answer fixing each issue while keeping the same structure.

### memory.py — SQLite Persistence

All database operations go through `_get_connection()`, which creates the two tables if they do not exist and ensures the single `user_profile` row exists (using `INSERT OR IGNORE`). WAL journal mode is enabled for concurrent read performance.

**`get_profile() -> dict`**: Reads the single user_profile row.

**`update_profile(skill_level, explanation_style, last_repo)`**: Partial updates — only provided fields are changed.

**`add_question(repo, question, user_level, answer_preview, quality_score)`**: Inserts a history row and immediately prunes to 20 most recent.

**`get_memory_context(repo, user_level) -> str`**: Builds a formatted string combining user level, explanation style preference, previously explored repo, and up to 3 past questions about the current repo. This string is injected into every Researcher prompt to personalize the investigation.

### state.py — Data Structures

Pure dataclasses with no external dependencies.

**`StepStatus`**: Enum with PENDING, RUNNING, DONE, SKIPPED.

**`PlanStep`**: `id`, `title`, `description`, `suggested_tools: list[str]`, `status: StepStatus`, `result_summary: str`.

**`Plan`**: `question`, `repo`, `user_level`, `steps: list[PlanStep]`. Properties: `is_complete`, `current_step`, `progress` (done/total tuple).

**`SessionState`**: Top-level container holding `owner`, `repo`, `user_level`, `readme`, `plan`, `tool_calls_log`, `final_answer`.

### tracer.py — Observability

**`TraceEvent`**: Dataclass with `phase`, `step`, `action`, `duration_ms`, `detail`, `error`, `timestamp`.

**`RunTrace`**: One per question. Collects `TraceEvent` instances via `add_event()`. Aggregates phase times in `summary()`. Produces a human-readable event log via `event_log()`. Also tracks `files_indexed`, `chunks_retrieved`, `tool_calls_count`, `final_answer_length`, `quality_score`, `review_verdict`.

**`Timer`**: Context manager that records elapsed milliseconds. Used with `with Timer() as t:` blocks wrapping each phase.

### evaluator.py — Benchmark Evaluation

Not run during normal operation. Provides a standalone eval suite for measuring system quality.

**`BENCHMARK_QUESTIONS`**: 10 pre-defined questions designed to be answerable against any repo (e.g. "What is this project?", "How do I run it?", "Where is the entry point?", "What tests exist?").

**`score_answer(...) -> dict`**: Scores one answer on 5 binary criteria (0 or 1 each):
- `right_file`: Referenced at least one relevant file
- `citation_present`: Cited specific file paths as evidence
- `answer_complete`: Substantive, not a one-liner
- `no_hallucination`: No implausible file paths or technical details
- `clear_for_level`: Language appropriate for stated user level

Maximum score per question: 5. Maximum across the full suite: 50.

**`run_eval_suite(answer_fn, repo_name, user_level, indexed_files) -> dict`**: Calls `answer_fn(question)` for each benchmark question, scores the result, and returns per-question scores plus aggregate stats including percentage.

---

## Multi-Agent Design

RepoLens uses four specialized agents, each with a distinct role, system prompt, and output format. They are not running concurrently — they execute in pipeline order, each consuming the output of the previous.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PLANNER    │────▶│  RESEARCHER  │────▶│ SYNTHESIZER  │────▶│   REVIEWER   │
│              │     │              │     │              │     │              │
│ Input:       │     │ Input:       │     │ Input:       │     │ Input:       │
│ - question   │     │ - plan step  │     │ - all        │     │ - question   │
│ - user level │     │ - RAG chunks │     │   findings   │     │ - answer     │
│ - README     │     │ - memory ctx │     │ - RAG chunks │     │ - indexed    │
│              │     │ - prev steps │     │ - user level │     │   files      │
│ Output:      │     │              │     │ - style      │     │ - evidence   │
│ Plan (JSON)  │     │ Output:      │     │              │     │              │
│              │     │ Findings     │     │ Output:      │     │ Output:      │
│ LLM mode:    │     │ (markdown    │     │ Final answer │     │ Verdict,     │
│ JSON         │     │  + citations)│     │ (markdown)   │     │ Score (JSON) │
│ temp=0.2     │     │ temp=0.3     │     │ temp=0.3     │     │ temp=0.2     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

**Why separate agents instead of one big prompt?**

- The Planner needs to reason about *what* to investigate, which is a different cognitive task from actually investigating
- The Researcher needs tool access and iterative tool loops — unsuitable for a single-shot prompt
- The Synthesizer can work at a higher level, combining already-gathered evidence
- The Reviewer benefits from having no stake in the answer — it reads the answer cold and applies strict criteria
- Each agent uses the minimum context needed, keeping token usage efficient

**Agent separation in the codebase:**

The Planner lives entirely in `planner.py`. The Researcher and Synthesizer are functions in `app.py` (`execute_step()` and `synthesize_answer()`). The Reviewer lives in `reviewer.py`. This reflects their different purposes: the Planner and Reviewer are stateless utilities; the Researcher and Synthesizer are tightly coupled to the orchestration loop in `app.py`.

---

## RAG: Retrieval-Augmented Generation

RAG solves the context window problem. A large repository may have hundreds of files and thousands of lines. You cannot fit all of that into a single LLM prompt. Instead, RepoLens indexes the most important files, then retrieves only the most relevant passages for each specific question.

### Chunking Strategy

```python
def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap  # 600 characters advance per step
    return [c.strip() for c in chunks if c.strip()]
```

The 200-character overlap ensures that sentences and code blocks that span a chunk boundary appear in both adjacent chunks. This prevents answers from missing information that straddles a cut point.

### Embedding and Similarity

ChromaDB uses its default embedding model (sentence-transformers under the hood) to vectorize each chunk when it is added, and to vectorize the query at retrieval time. Cosine similarity is used (`hnsw:space: cosine`), which measures the angle between vectors rather than their magnitude — better suited for semantic similarity than Euclidean distance.

### Retrieval Injection Points

RAG context is injected at two points:

1. **Researcher prompts** — `retriever.get_context_string(question + step_title + step_description, n_results=3)` — 3 chunks per step, combined with step-specific keywords for better targeting
2. **Synthesizer prompts** — `retriever.get_context_string(question, n_results=5)` — 5 broader chunks for the final answer

The formatted string labels each chunk with its source file and chunk index:

```
[Chunk 1] Source: requirements.txt (chunk #0)
streamlit>=1.32
groq>=0.5
chromadb>=0.4
...

---

[Chunk 2] Source: README.md (chunk #2)
## Installation
pip install -r requirements.txt
...
```

### Why Not Index Everything?

Two reasons. First, GitHub API rate limits. Fetching every file in a large repo would exhaust the 60 request/hour unauthenticated limit. Second, noise reduction. Source files outside the entry points (utility modules, test fixtures, generated code) add noise to retrieval results without improving answer quality. The file selection heuristic focuses on the files that are most likely to answer onboarding questions: documentation, package manifests, and entry points.

---

## Memory System

RepoLens remembers the user across sessions using SQLite. The database file is `repolens_memory.db` in the project directory.

### Schema

```sql
CREATE TABLE user_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- enforces single row
    skill_level TEXT DEFAULT 'intermediate',
    explanation_style TEXT DEFAULT 'balanced',
    last_repo TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);

CREATE TABLE question_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo TEXT NOT NULL,
    question TEXT NOT NULL,
    user_level TEXT NOT NULL,
    answer_preview TEXT DEFAULT '',   -- first 500 chars of answer
    quality_score INTEGER DEFAULT 0,
    asked_at TEXT NOT NULL
);
```

### How Memory Affects Answers

At the start of each Researcher step, `get_memory_context(repo, user_level)` builds a context string:

```
User skill level: beginner
Explanation style preference: detailed
Previously explored: tensorflow/tensorflow
Previous questions about this repo:
  - "What is this project?" (level: beginner, score: 9)
  - "How do I run it?" (level: beginner, score: 8)
```

This is injected into the Researcher's user prompt. The effect is that the LLM knows the user is a beginner, prefers detailed explanations, and has already asked basic questions — so it can calibrate the depth and vocabulary of its findings accordingly.

### Memory in the UI

The sidebar shows the last explored repo name from the profile. The Memory tab shows the full profile as JSON and the 10 most recent questions as expandable cards with level, quality score, timestamp, and answer preview.

---

## Tracing and Observability

Every run produces a `RunTrace` that records the full execution history.

### What Is Tracked

```python
@dataclass
class RunTrace:
    repo: str
    question: str
    user_level: str
    started_at: str
    events: list[TraceEvent]       # all phase events
    total_duration_ms: float
    quality_score: int             # from Reviewer
    review_verdict: str            # "pass" or "needs_revision"
    chunks_retrieved: int          # RAG chunks used
    files_indexed: int             # files in ChromaDB
    tool_calls_count: int          # total tool calls across all steps
    final_answer_length: int       # character count
```

Each `TraceEvent` records the phase name, step number, action description, duration in milliseconds, optional detail, and optional error.

### What the Trace Tab Shows

Three metrics displayed as columns:
- Total time (sum of all phase durations in seconds)
- Tool calls (total across all research steps)
- Quality score (from Reviewer, out of 10)

Phase timing breakdown: each unique phase name (index, plan, research, synthesis, review, revision) with its cumulative duration.

Event log: one line per event, showing phase, step number if applicable, action, and duration. Errors are highlighted.

### How Timing Works

```python
with Timer() as t:
    plan = create_plan(...)
trace.add_event("plan", f"Created {len(plan.steps)}-step plan", t.elapsed_ms)
```

The `Timer` context manager records wall-clock time in milliseconds. It is wrapped around each phase call and the elapsed time is passed directly to `add_event()`.

---

## Evaluation Framework

`evaluator.py` provides a standalone benchmark for measuring overall system quality. It is not invoked during normal usage — it is run separately to evaluate how well the full pipeline performs.

### The 10 Benchmark Questions

| ID | Question | Key Files Expected |
|---|---|---|
| 1 | What is this project? | README.md |
| 2 | How do I run it? | README.md, Makefile, Dockerfile, package.json |
| 3 | What files define config? | *.config.*, *.json, *.toml, *.yaml |
| 4 | Where is the entry point? | main.*, app.*, index.*, server.* |
| 5 | What should a beginner read first? | README.md, CONTRIBUTING.md, docs/* |
| 6 | What is the architecture? | (any file-based evidence) |
| 7 | What dependencies does this project use? | requirements.txt, package.json, go.mod |
| 8 | How do I contribute? | CONTRIBUTING.md, .github/* |
| 9 | What tests exist and how do I run them? | test*, pytest.ini, jest.config.* |
| 10 | What would be a good first contribution? | CONTRIBUTING.md, README.md |

### The 5 Scoring Criteria

Each criterion is scored 0 or 1 per question. Maximum: 50 points across the full suite.

| Criterion | What It Checks |
|---|---|
| `right_file` | Answer references at least one relevant file |
| `citation_present` | Specific file paths are cited as evidence |
| `answer_complete` | Substantive answer, more than 2 sentences |
| `no_hallucination` | All technical details are plausible and consistent |
| `clear_for_level` | Language is appropriate for the stated user level |

`run_eval_suite()` takes an `answer_fn` callable so it can be plugged into any version of the pipeline, making it useful for regression testing when the prompts or architecture change.

---

## The User Interface

### Sidebar

The sidebar is always visible. It contains:
- Repo URL text input
- Experience level selector (beginner / intermediate / advanced) — pre-populated from SQLite memory
- Explanation style selector (concise / balanced / detailed) — pre-populated from SQLite memory
- Five preset question buttons (Summarize architecture, Onboarding guide, Setup steps, What to read first, How to contribute)
- Current plan steps (shown after planning completes)
- Last explored repo name (from memory)

Any change to level or style immediately calls `update_profile()` to persist it.

### Main Panel

Before a URL is entered: a landing page with three columns describing the Plan, Research, and Review phases.

After a question is submitted:
1. Four `st.status` blocks show live progress for each phase (Index, Plan, Research, Synthesize, Review, and optionally Revision)
2. A quality badge displays the Reviewer's score and summary
3. The final answer renders as formatted markdown
4. Four tabs appear below the answer

### Tab 1: Evidence

Shows the raw RAG chunks retrieved for the question, labeled by source file and chunk index. Also lists all indexed files with a count of total files and chunks. This makes the system's sources fully transparent.

### Tab 2: Memory

Shows the full `user_profile` as JSON and the 10 most recent questions as expandable cards. Each card shows the repo, user level, quality score, timestamp, and first 500 characters of the answer.

### Tab 3: Trace

Shows the three key metrics (total time, tool calls, quality score), per-phase timing breakdown, and the full event log. Any errors from any phase are shown in red at the bottom.

### Tab 4: Details

Shows the full investigation plan with step status icons, the per-step findings in expandable sections, the complete tool call log with arguments and result previews, and the full Reviewer JSON output including the issues list.

---

## Data Flow: End to End

This section traces a single question through the entire system.

**Input:** `https://github.com/pallets/flask` + question: `"How do I run it?"` + level: `beginner`

```
1. app.py: parse_repo() → owner="pallets", repo="flask"
   tools.set_repo("pallets", "flask")
   memory.update_profile(last_repo="pallets/flask")
   fetch_readme() → raw README text
   fetch_repo_tree() → list of all file paths

2. Phase 0 — Index:
   retriever = RepoRetriever("pallets", "flask")
   retriever.index():
     _fetch_tree_recursive() → 150+ file paths
     _select_files_to_index() → selects:
       README.rst, CHANGES.rst, pyproject.toml, setup.cfg,
       Makefile, docs/installation.rst, docs/quickstart.rst,
       src/flask/app.py (entry point), src/flask/__main__.py
     For each file: _fetch_file_content() → base64 decode
     _chunk_text(content, 800, 200) → chunks
     collection.add(documents, metadatas, ids)
   → 9 files indexed, ~40 chunks created

3. Phase 1 — Plan:
   evidence_chunks = retriever.get_context_string("How do I run it?", n_results=5)
   planner.create_plan(question="How do I run it?", repo_name="pallets/flask",
                       user_level="beginner", readme_preview=readme[:2000])
   → Groq LLM returns JSON:
   {
     "steps": [
       {"title": "Explore project structure", "suggested_tools": ["list_files"]},
       {"title": "Read README for setup instructions", "suggested_tools": ["read_file"]},
       {"title": "Check pyproject.toml for install commands", "suggested_tools": ["read_file"]},
       {"title": "Synthesize run instructions", "suggested_tools": []}
     ]
   }
   → Plan with 4 PlanSteps

4. Phase 2 — Research (4 steps):
   Step 1: execute_step()
     RAG: get_context_string("How do I run it? Explore project structure list_files", n_results=3)
     memory_ctx: "User skill level: beginner\nExplanation style: balanced"
     LLM call with tools → model calls list_files(path="")
     tools.list_files("") → "📁 docs\n📁 src\n📄 README.rst\n📄 pyproject.toml..."
     model receives tool result → produces findings text with citations

   Step 2: execute_step()
     RAG: get_context_string("How do I run it? Read README for setup instructions read_file", n_results=3)
     prev findings from step 1 appended
     LLM call with tools → model calls read_file(path="README.rst")
     tools.read_file("README.rst") → first 8000 chars of README
     model produces findings: "Flask can be run with flask run (source: README.rst)"

   Step 3: execute_step()
     LLM calls read_file(path="pyproject.toml")
     → "dependencies = ['werkzeug', 'jinja2', ...]"
     findings: "Install with pip install flask (source: pyproject.toml)"

   Step 4: synthesis step (no tools)
     LLM summarizes all findings into structured bullet points

5. Phase 3 — Synthesize:
   synthesize_answer(plan, findings=[...4 items...], readme, evidence_chunks, style="balanced")
   → Final answer in markdown:
   "## Running Flask
   Install: `pip install flask` (source: pyproject.toml)
   Create app.py: ...
   Run: `flask run` (source: README.rst)
   ..."

6. Phase 4 — Review:
   reviewer.review_answer(question, final_answer, indexed_files, evidence_chunks, user_level="beginner")
   → {verdict: "pass", quality_score: 9, issues: [], summary: "Well-cited setup instructions"}
   score >= 8 → green badge, no revision needed

7. Finalize:
   trace.finalize()
   memory.add_question(repo="pallets/flask", question="How do I run it?",
                       user_level="beginner", answer_preview=..., quality_score=9)

8. Display:
   Green badge: "Quality Score: 9/10 — Well-cited setup instructions"
   st.markdown(final_answer)
   Tabs: Evidence (9 indexed files, 40 chunks, 5 retrieved)
         Memory (profile + history)
         Trace (total ~18s, 3 tool calls)
         Details (plan, findings, tool calls, review JSON)
```

---

## Conditions and Limitations

### Works When:
- The repository is public (no authentication required)
- The repo has at least a README file
- `GROQ_API_KEY` is set in the environment (via `.env` or shell)
- GitHub API rate limit has not been exhausted (60 requests/hour unauthenticated)

### Limitations:
- **Private repos** are not supported. The GitHub API returns 404 for private repos without authentication. Adding GitHub token support would require an additional env variable and passing a Bearer token header.
- **Code search rate limit**: `search_docs` uses the GitHub code search API which is limited to 10 requests/minute unauthenticated. Heavy use of the `search_docs` tool in a single session will trigger rate limit errors, which the Researcher handles gracefully by continuing with remaining tools and RAG context.
- **Very large files**: `read_file()` truncates files at 8,000 characters. Large source files will have their tail content missing in tool outputs, though their chunks may still be in the RAG index.
- **No persistent vector index**: ChromaDB is instantiated in-memory and rebuilt fresh for every question. Repeated questions about the same repo re-index from scratch. This is intentional for simplicity but adds 5-15 seconds to each run depending on repo size.
- **Context window**: Researcher prompts can grow large with many tool iterations plus RAG chunks. The 5-iteration limit per step and the 1,500 token response cap keep this bounded.
- **Evaluation suite** (`evaluator.py`) is not integrated into the UI — it must be run as a standalone script, and it will make many LLM calls (10 questions × multiple agents each).

### Configuration Required:
```
# .env file in project root
GROQ_API_KEY=your_groq_api_key_here
```

Groq API keys are free at console.groq.com. No credit card is required for the free tier.
