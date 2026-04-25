# Changelog

All notable changes to RepoLens will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Multi-repo side-by-side comparison

---

## [3.0.0] - 2026-04-25

Major release: completes the originally planned scope. Pipeline is now LangGraph-orchestrated with disk-backed RAG, streaming answers, human approval, and exportable reports.

### Added

#### LangGraph orchestration (`graph.py`)
- Replaced inline 5-phase block in `app.py` with a real `StateGraph` (`GraphState` TypedDict).
- Conditional `revise → review` edge (capped at 1 iteration when quality score < 6).
- Two compiled subgraphs (`build_pre_synth_graph`, `build_post_synth_graph`) so streaming synthesis can run between them.

#### GitHub auth token (`gh.py`)
- Central `gh_get` / `gh_headers` helper used by `retriever.py`, `tools.py`, `app.py`.
- Optional `GITHUB_TOKEN` env var lifts rate limit from 60 → 5,000 req/hr and unlocks private repos.
- Soft fallback — works without a token on public repos.

#### Persistent ChromaDB cache (`retriever.py`)
- Switched from `EphemeralClient` to `PersistentClient` rooted at `./.chroma_cache` (configurable via `CHROMA_PATH`).
- 24-hour freshness TTL + `SCHEMA_VERSION` invalidation.
- "🔄 Re-index repo" sidebar button forces a rebuild.

#### Streaming answers
- `synthesize_stream` generator wired to `st.write_stream`; tokens render progressively.
- Non-streaming `synthesize_answer_blocking` retained for the eval suite.

#### Evaluator wiring
- `run_eval_suite` now exposed via a sidebar button + 📈 Eval tab.
- Default 3-question quick run; opt-in **Full suite (10 Q)** checkbox.
- `limit` and `progress_callback` params added to `evaluator.run_eval_suite`.

#### Markdown + PDF export (`export.py`)
- `to_markdown` and `to_pdf` produce downloadable reports with citations.
- PDF uses `fpdf2`; bundled `assets/DejaVuSans.ttf` enables full Unicode support.
- Graceful fallback to core Helvetica + latin-1 sanitization if the font isn't bundled.

#### Human-in-the-loop approval
- Stage machine in `app.py` (`input → running → approval → user_revise → approved → done`).
- Three actions per draft: ✅ Approve, ✏️ Request revision (free-text feedback), 🗑️ Discard.
- `add_question(...)` and `RunTrace.finalize()` only fire on approval — discarded drafts leave no trace.

#### Streamlit Cloud deploy
- `.streamlit/config.toml` + `.streamlit/secrets.toml.example`.
- App falls back from `os.environ` to `st.secrets` automatically.
- README "Deploy on Streamlit Cloud" section.

### Changed
- `requirements.txt` adds `langgraph>=0.2.0` and `fpdf2>=2.7.6`.
- `.gitignore` adds `.chroma_cache/`, `repolens_memory.db`, `assets/DejaVuSans.ttf`.
- `.env.example` documents `GITHUB_TOKEN` and `CHROMA_PATH`.
- README: updated architecture/features/roadmap to reflect shipped scope.

### Removed
- Inline `RESEARCHER_SYSTEM_PROMPT`, `execute_step`, `synthesize_answer` from `app.py` (moved into `graph.py`).

### Fixed
- `retriever.py`: dropped `hnsw:space` from the freshness-stamp `collection.modify(...)` call — newer ChromaDB (≥1.x) rejects modifying the distance function after creation.
- `export.py`: PDF rendering now resets X to the left margin before every `multi_cell`. Without this, a bullet immediately following a paragraph (no blank line between) raised "Not enough horizontal space to render a single character" on fpdf2 ≥2.8.

---

## [2.0.0] - 2026-04-14

### Added — Days 4-10

#### Day 4: RAG Retrieval (`retriever.py`)
- ChromaDB in-memory vector store for repo file indexing
- Selective indexing: README, docs/, configs, package manifests, entry-point source files
- Text chunking (800 chars, 200 overlap) with cosine similarity retrieval
- `RepoRetriever` class with `index()` and `query()` methods
- `get_context_string()` for prompt injection of evidence chunks

#### Day 5: Reviewer Agent (`reviewer.py`)
- Multi-agent pattern: Planner → Researcher → Reviewer
- Reviewer checks: unsupported claims, missing citations, vague instructions, bad file refs, hallucinations
- JSON-structured review with verdict (pass/needs_revision) and quality score (1-10)
- Auto-revision via `revise_answer()` when quality score < 6

#### Day 6: Memory (`memory.py`)
- SQLite-backed persistent storage
- User profile: skill_level, explanation_style, last_repo
- Question history (last 20 entries) with answer previews and quality scores
- `get_memory_context()` for prompt personalization

#### Day 7: UI Overhaul (`app.py`)
- Sidebar: repo URL, experience level, explanation style, 5 preset demo buttons, current plan display
- Main panel: quality badge + final answer
- 4 tabs: Evidence (chunks + indexed files), Memory (profile + history), Trace (timing + event log), Details (plan + findings + tool calls + review JSON)
- Landing page with feature descriptions when no URL is entered

#### Day 8: Tracing & Evaluation (`tracer.py`, `evaluator.py`)
- `RunTrace` with per-phase timing, tool call counts, quality scores, error tracking
- `Timer` context manager for timing operations
- 10-question benchmark suite with 5-criteria scoring
- Criteria: right_file, citation_present, answer_complete, no_hallucination, clear_for_level

#### Day 9: Prompt Polish
- Researcher: strict evidence-only rules, concise bullet-point findings
- Synthesizer: mandatory file citations, no filler, level-aware language
- Planner: focused 3-5 steps, question-specific plans
- Reviewer: stricter scoring guidelines with score band descriptions

#### Day 10: Portfolio Packaging
- Complete README rewrite with architecture diagram, pipeline table, evaluation criteria
- MIT LICENSE file
- Updated all documentation files

### Changed
- `app.py` rewritten from single-prompt to 5-phase pipeline (Index → Plan → Research → Synthesize → Review)
- `requirements.txt` cleaned to minimal direct dependencies
- All Python files made compatible with Python 3.9 (`from __future__ import annotations`)

---

## [1.1.0] - 2026-04-13

### Added — Days 2-3

#### Day 2: Tool Calling (`tools.py`)
- 3 custom tools: `list_files(path)`, `read_file(path)`, `search_docs(query)`
- Agentic tool-calling loop — model decides which tools to call
- Tool definitions in OpenAI/Groq function-calling JSON format
- Evidence-based system prompt
- Question UI with 5 quick-pick buttons + custom input
- Transparency: expandable "Tool calls made" panel

#### Day 3: Planning (`planner.py`, `state.py`)
- Planner LLM that converts questions into 3-6 step investigation plans
- Structured state: `Plan`, `PlanStep`, `SessionState`, `StepStatus`
- 3-phase pipeline: Plan → Research → Synthesize
- Step-by-step execution with previous findings as context

### Changed
- `app.py` refactored from one-shot prompt to agentic tool-calling loop
- Switched from OpenAI to Groq (Llama 3.3-70b) for free-tier API access
- Switched from Google Gemini to Groq after Gemini quota exhaustion

---

## [1.0.0] - 2026-04-12

### Added — Day 1
- Initial release of RepoLens
- Streamlit web interface with sidebar and multi-column layout
- GitHub API integration for README and file tree fetching
- AI-powered repo summarization (single prompt)
- Experience-level tailored explanations (beginner, intermediate, advanced)
- Environment variable configuration with `.env` support
- Error handling and fallback display of raw README

### Technical Details
- Built with Python 3.9+
- Streamlit for UI
- Groq API client with Llama 3.3-70b
- GitHub REST API (no auth required for public repos)

---

## Contributors

- **Akhil P Das** (@akhilpdas) — Creator and maintainer

---

**Last Updated**: 2026-04-25
**Current Version**: 3.0.0
**Status**: Active Development
