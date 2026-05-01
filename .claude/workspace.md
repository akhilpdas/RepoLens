# RepoLens Workspace

## Project Overview
RepoLens is an **agentic onboarding assistant for GitHub repositories** — helps developers understand any GitHub repo in minutes by generating AI-powered summaries tailored to their experience level.

**Tech Stack**: Streamlit · Groq (Llama 3.3-70b) · LangGraph · ChromaDB · SQLite · fpdf2

**Current version**: v3.2.0 — multi-repo compare + dark mode shipped. Full feature parity with the original plan.

## Quick Start

### Setup
```bash
cd /Users/akhildas/Documents/RepoLens
source venv/bin/activate
export GROQ_API_KEY="gsk-your-actual-key"
# Optional but recommended for private repos + 5k req/hr:
export GITHUB_TOKEN="ghp-your-token"
streamlit run app.py
```

### Access
- **App URL**: http://localhost:8501
- **API Keys**: Add `GROQ_API_KEY` (and optional `GITHUB_TOKEN`) to `.env`

## Pipeline (LangGraph-orchestrated)

```
index → plan → research → synthesize → [HITL approval] → review → (revise → review)? → END
```

5 specialized agents:
1. **Planner** — converts question → 3-5 step JSON plan
2. **Researcher** — agentic tool-calling loop (list_files, read_file, search_docs)
3. **Synthesizer** — composes streaming final answer
4. **Reviewer** — 1-10 quality score, flags hallucinations
5. **Reviser** — auto-rewrites if score < 6 (capped at 1 iteration)

## Project Structure

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI + HITL stage machine + slot dispatch |
| `graph.py` | LangGraph StateGraph (pre/post-synth subgraphs + streaming) |
| `gh.py` | Auth-aware GitHub HTTP helper |
| `tools.py` | 3 tools: list_files, read_file, search_docs |
| `planner.py`, `reviewer.py` | Planner + Reviewer agents |
| `retriever.py` | Persistent ChromaDB RAG (24h TTL) |
| `memory.py` | SQLite — profile + history + prefs |
| `state.py`, `tracer.py`, `evaluator.py` | Dataclasses, observability, benchmark suite |
| `export.py` | Markdown + PDF export (fpdf2 + DejaVuSans) |
| `theme.py` | Light / Dark / System theme runtime CSS |
| `compare.py` | Multi-repo state namespacing helpers (slot a/b) |
| `assets/` | Theme CSS + DejaVuSans.ttf font |
| `tests/` | 270 unit + integration tests across 12 files |
| `.streamlit/` | Cloud config + secrets template |

## Key Features Available

- 🧩 LangGraph orchestration with conditional revise→review edge
- ⚡ Streaming responses (`st.write_stream`)
- 🧑‍⚖️ Human-in-the-loop approval (Approve / Revise / Discard)
- 🔀 **Multi-repo compare** — toggle in sidebar, run two pipelines side-by-side
- 🎨 **Dark mode** — Light / Dark / System (persisted to SQLite prefs)
- 💾 Persistent ChromaDB cache (per-repo, 24h TTL, schema versioned)
- 🔐 Optional `GITHUB_TOKEN` for private repos + 5k req/hr
- 📤 Markdown + PDF export per answer
- 📈 Eval suite (3-Q quick or full 10-Q)
- ☁️ Streamlit Cloud-ready (secrets fallback)

## Development Tips

### Running Tests
```bash
source venv/bin/activate
pytest tests/ -v       # 270 tests, ~2s
```

### Environment Variables
Create `.env` from `.env.example`:
```
GROQ_API_KEY=gsk-...
GITHUB_TOKEN=ghp-...   # optional
CHROMA_PATH=./.chroma_cache
```

### Active Dependencies
- `streamlit` ≥1.30.0 — Web UI framework
- `groq` — LLM inference (Llama 3.3-70b-versatile)
- `langgraph` ≥0.2.0 — StateGraph orchestration
- `chromadb` ≥0.4.22 — Vector database (persistent)
- `fpdf2` ≥2.7.6 — PDF export with Unicode support
- `requests`, `python-dotenv`

## Common Commands

```bash
# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Run tests
pytest tests/ -v

# Force fresh ChromaDB (or use the sidebar 🔄 Re-index button)
rm -rf .chroma_cache/
```

## Notes
- Requires a valid `GROQ_API_KEY` (free tier — sign up at console.groq.com).
- Without `GITHUB_TOKEN`, GitHub API rate-limits to 60 req/hr (sufficient for small/medium public repos).
- ChromaDB cache is single-process and ephemeral on Streamlit Cloud (re-indexes on cold start).
- Compare-mode is desktop-only (mobile falls back to single column).
