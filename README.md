# 🔍 RepoLens

**An agentic AI onboarding assistant for any GitHub repository.**

Paste a public GitHub repo URL → get a comprehensive, evidence-based analysis powered by a multi-agent pipeline with planning, retrieval, review, and memory.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3--70b-green.svg)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What It Does

RepoLens takes any public GitHub repository URL and answers questions about it — using actual file contents as evidence, not guesses.

**Example questions you can ask:**
- *"What does this repo do?"*
- *"How do I run it?"*
- *"What is the architecture?"*
- *"What files should I read first?"*
- *"What would be a good first contribution?"*

The AI agent **autonomously explores** the repo: listing directories, reading files, searching code — then produces answers with citations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI                            │
│  Sidebar: URL, level, style, presets    Main: answer + tabs │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │  📚 INDEX  │ │  📋 PLAN   │ │  🧠 MEMORY │
   │ ChromaDB   │ │ Planner LLM│ │  SQLite    │
   │ RAG chunks │ │ 3-5 steps  │ │ profile +  │
   │ README,    │ │ per question│ │ history    │
   │ docs,      │ └─────┬──────┘ └─────┬──────┘
   │ configs,   │       │              │
   │ source     │       ▼              │
   └─────┬──────┘ ┌────────────┐       │
         │        │ 🔬 RESEARCH│◄──────┘
         │        │ Researcher │
         ├───────►│ LLM + Tools│
         │        │ list_files │
         │        │ read_file  │
         │        │ search_docs│
         │        └─────┬──────┘
         │              │
         │              ▼
         │        ┌────────────┐
         │        │ ✍️ SYNTHESIZE│
         ├───────►│ Combines    │
         │        │ findings +  │
         │        │ evidence    │
         │        └─────┬──────┘
         │              │
         │              ▼
         │        ┌────────────┐
         └───────►│ 🔍 REVIEW  │
                  │ Checks for:│
                  │ - citations│
                  │ - accuracy │
                  │ - clarity  │
                  │ - halluc.  │
                  └─────┬──────┘
                        │
                  ┌─────▼──────┐
                  │ ✏️ REVISE   │ (if score < 6)
                  │ Fix issues │
                  └────────────┘
```

### Pipeline Phases

| Phase | Module | What It Does |
|-------|--------|--------------|
| **Index** | `retriever.py` | Indexes README, docs, configs, manifests, select source files into ChromaDB |
| **Plan** | `planner.py` | LLM creates a 3-5 step investigation plan tailored to the question |
| **Research** | `app.py` | Researcher LLM executes each step using tools + RAG evidence |
| **Synthesize** | `app.py` | Combines all findings into a coherent, cited answer |
| **Review** | `reviewer.py` | Quality-checks for unsupported claims, bad refs, hallucinations |
| **Revise** | `reviewer.py` | Auto-revises if quality score < 6/10 |

### Multi-Agent Roles

| Role | Responsibility |
|------|----------------|
| **Planner** | Breaks question into atomic investigation steps |
| **Researcher** | Executes steps using tools, gathers evidence |
| **Synthesizer** | Combines findings into a user-facing answer |
| **Reviewer** | Quality gate — catches errors before showing to user |

---

## Key Features

- 🔧 **Agentic tool calling** — Model autonomously calls `list_files`, `read_file`, `search_docs`
- 📚 **RAG retrieval** — ChromaDB indexes repo files; every answer cites retrieved chunks
- 📋 **Structured planning** — LLM creates investigation plans before researching
- 🔍 **Quality review** — Reviewer agent checks for hallucinations, missing citations, vague instructions
- 🧠 **Persistent memory** — SQLite stores user profile, preferences, and question history
- 📊 **Observability** — Full trace with per-phase timing, tool call counts, quality scores
- 📈 **Evaluation** — 10-question benchmark suite with 5-criteria scoring
- 🎯 **Experience-level tailoring** — Beginner/intermediate/advanced answers
- 📝 **Explanation styles** — Concise, balanced, or detailed
- 💬 **Interactive Q&A** — Quick-pick buttons + custom questions

---

## Quick Start

```bash
# Clone
git clone https://github.com/akhilpdas/RepoLens.git
cd RepoLens

# Install
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure (get free key from https://console.groq.com/keys)
echo 'GROQ_API_KEY=gsk_your_key_here' > .env

# Run
streamlit run app.py
```

Open **http://localhost:8501**, paste a repo URL, and ask a question.

---

## Project Structure

```
RepoLens/
├── app.py              # Main Streamlit app — UI + research/synthesis pipeline
├── tools.py            # 3 tools: list_files, read_file, search_docs
├── planner.py          # Planner agent — creates investigation plans
├── retriever.py        # RAG module — ChromaDB indexing + retrieval
├── reviewer.py         # Reviewer agent — quality checks + revision
├── memory.py           # SQLite-backed persistent user memory
├── state.py            # Structured state: Plan, PlanStep, SessionState
├── tracer.py           # Lightweight observability — timing + event log
├── evaluator.py        # 10-question benchmark evaluation suite
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── .gitignore          # Git ignore rules
```

---

## Tools

The model decides which tools to call based on the question:

| Tool | Function | Example |
|------|----------|---------|
| `list_files(path)` | Lists files/folders at any repo path | `list_files("src")` |
| `read_file(path)` | Reads actual file contents (up to 8KB) | `read_file("package.json")` |
| `search_docs(query)` | Searches code across the entire repo | `search_docs("database config")` |

---

## RAG: What Gets Indexed

RepoLens selectively indexes (not the entire repo):

| Category | Files | Max |
|----------|-------|-----|
| README | Any `README*` file | All |
| Documentation | `docs/` and `doc/` folders (.md, .rst, .txt) | 10 files |
| Config | package.json, pyproject.toml, Dockerfile, Makefile, etc. | All |
| Manifests | requirements.txt, Cargo.toml, go.mod, Gemfile, etc. | All |
| Source | Entry-point files (main.py, app.js, index.ts, etc.) | 5 files |

Chunks: 800 chars with 200 char overlap → stored in ChromaDB with cosine similarity.

---

## Evaluation

10 benchmark questions scored on 5 criteria (0-1 each):

| Criterion | What It Checks |
|-----------|---------------|
| `right_file` | Did the answer reference a correct/relevant file? |
| `citation_present` | Does the answer cite specific file paths as evidence? |
| `answer_complete` | Is the answer substantive (not a one-liner)? |
| `no_hallucination` | No made-up file paths, functions, or claims? |
| `clear_for_level` | Is the language appropriate for the user's level? |

**Max score: 50** (10 questions × 5 criteria)

### Benchmark Questions

1. What is this project?
2. How do I run it?
3. What files define config?
4. Where is the entry point?
5. What should a beginner read first?
6. What is the architecture?
7. What dependencies does this project use?
8. How do I contribute?
9. What tests exist and how do I run them?
10. What would be a good first contribution?

---

## Sample Output

For any repo, RepoLens produces answers like:

> **How do I run it?**
>
> 1. Install dependencies: `pip install -r requirements.txt` *(source: requirements.txt)*
> 2. Set up environment: `cp .env.example .env` and add your API key *(source: .env.example)*
> 3. Run the app: `streamlit run app.py` *(source: README.md)*
>
> **Quality Score: 9/10** ✅

---

## UI Layout

| Area | Content |
|------|---------|
| **Sidebar** | Repo URL, experience level, explanation style, preset buttons, current plan |
| **Main Panel** | Quality badge + final answer |
| **📚 Evidence tab** | Retrieved chunks + indexed files list |
| **🧠 Memory tab** | User profile + question history |
| **📊 Trace tab** | Timing metrics, tool call counts, event log |
| **🔬 Details tab** | Investigation plan, step findings, tool calls, review JSON |

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI | Streamlit | Web interface |
| LLM | Groq (Llama 3.3-70b) | Planning, research, synthesis, review |
| RAG | ChromaDB | Vector storage + retrieval |
| Memory | SQLite | User profile + question history |
| Tools | GitHub REST API | File listing, reading, code search |
| Orchestration | Custom Python | Multi-agent pipeline |
| Tracing | Custom Python | Observability + timing |

---

## Limitations

- **Public repos only** — private repos require GitHub auth (not yet implemented)
- **GitHub API rate limits** — 60 requests/hour unauthenticated; `search_docs` is the heaviest consumer
- **No streaming** — answers appear after full pipeline completes
- **Groq rate limits** — free tier has per-minute limits; large repos may hit them
- **Selective indexing** — only key files are indexed, not the full codebase
- **No persistent vector store** — ChromaDB is in-memory, re-indexes each session
- **Single repo per session** — no cross-repo analysis

---

## Roadmap

- [ ] GitHub auth token for private repos + higher rate limits
- [ ] LangGraph-based workflow orchestration
- [ ] Persistent ChromaDB storage (disk-backed)
- [ ] Streaming responses
- [ ] Export answers as Markdown/PDF
- [ ] Human-in-the-loop approval step
- [ ] Multi-repo comparison
- [ ] Deploy to Streamlit Cloud

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and test locally
4. Submit a PR — all PRs require review before merging

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

**Built by [@akhilpdas](https://github.com/akhilpdas)** | Powered by Groq + ChromaDB + Streamlit
