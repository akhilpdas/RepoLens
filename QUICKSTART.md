# Quick Start Guide

Get RepoLens running in 5 minutes!

## TL;DR (For Experienced Developers)

```bash
git clone https://github.com/akhilpdas/RepoLens.git
cd RepoLens
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=gsk_your_key_here" > .env
streamlit run app.py
# Open http://localhost:8501
```

Get a free Groq key: https://console.groq.com/keys (2 min signup)

---

## Step-by-Step

### 1. Prerequisites
- Python 3.9+
- Free Groq account

### 2. Clone
```bash
git clone https://github.com/akhilpdas/RepoLens.git
cd RepoLens
```

### 3. Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Get API Key
1. Go to https://console.groq.com
2. Sign up (free)
3. Click "API Keys" → "Create New Secret Key"
4. Copy the key (starts with `gsk_`)

### 6. Configure
```bash
cp .env.example .env
# Edit .env and paste your key
```

### 7. Run
```bash
streamlit run app.py
```

Browser opens at **http://localhost:8501**

---

## Usage

1. **Paste a GitHub URL** in the sidebar (public or private if you set `GITHUB_TOKEN`)
2. **Select your experience level** (beginner/intermediate/advanced)
3. **Choose explanation style** (concise/balanced/detailed)
4. **Ask a question** — use a preset button or type your own
5. **Streaming synthesis** — watch the answer render token-by-token
6. **Approve or revise** — review the draft, approve to save, or request changes
7. **Explore the tabs** — Evidence, Memory, Trace, Details, Eval
8. **Export** — download as Markdown or PDF

---

## What Happens Under the Hood

```
Paste GitHub URL
       ↓
    ┌──────────────────────────────────┐
    │  PRE-SYNTH SUBGRAPH              │
    │  ─────────────────────────────── │
📚  INDEX — ChromaDB (persistent cache, 24h TTL)
📋  PLAN — Planner LLM creates 3-5 investigation steps
🔬  RESEARCH — Researcher executes steps with tools
    └──────────────────────────────────┘
       ↓
✍️  STREAMING SYNTHESIS — tokens render progressively
       ↓
    🧑‍⚖️  HUMAN APPROVAL GATE
       ├─ ✅ Approve → continue
       ├─ ✏️ Request revision → call LLM to fix
       └─ 🗑️ Discard → nothing saved
       ↓
    ┌──────────────────────────────────┐
    │  POST-SYNTH SUBGRAPH             │
    │  ──────────────────────────────  │
🔍  REVIEW — Checks accuracy (score 1-10)
✏️  REVISE — Auto-fixes if score < 6 (capped 1x)
    └──────────────────────────────────┘
       ↓
💾 PERSIST — Add to memory, finalize trace
       ↓
📤 EXPORT — Download as MD or PDF (DejaVu Unicode)
       ↓
📊 TABS — Evidence, Memory, Trace, Details, Eval
```

---

## Project Structure

```
RepoLens/
├── app.py                 # Main Streamlit UI + HITL stage machine
├── graph.py               # LangGraph StateGraph orchestration
├── gh.py                  # GitHub auth-aware HTTP helper
├── tools.py               # 3 tools: list_files, read_file, search_docs
├── planner.py             # Planner agent
├── retriever.py           # Persistent ChromaDB RAG (24h TTL)
├── reviewer.py            # Reviewer agent + auto-revision
├── memory.py              # SQLite memory (profile + history)
├── state.py               # Dataclasses (Plan, PlanStep, etc.)
├── tracer.py              # Observability (timing + events)
├── evaluator.py           # 10-question benchmark suite
├── export.py              # MD + PDF export (fpdf2 + DejaVuSans)
├── theme.py               # Light / Dark / System theme CSS injection
├── compare.py             # Multi-repo state-namespacing helpers
├── assets/                # Theme CSS + DejaVuSans.ttf
├── tests/                 # 270-test unit + integration suite
├── requirements.txt       # Dependencies
├── .env                   # Your API keys (private, gitignored)
├── .env.example           # Template
└── .streamlit/            # Streamlit Cloud config + secrets
```

---

## Example Repos to Try

```
https://github.com/anthropics/claude-code
https://github.com/streamlit/streamlit
https://github.com/langchain-ai/langgraph
https://github.com/chroma-core/chroma
https://github.com/groq/groq-python
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `command not found: python3` | Install Python from python.org |
| `ModuleNotFoundError` | Activate venv, then `pip install -r requirements.txt` |
| `GROQ_API_KEY not set` | Check `.env` file has your key, restart app |
| `Port 8501 in use` | `streamlit run app.py --server.port 8502` |
| `Could not fetch README (404)` | Repo is private — add `GITHUB_TOKEN` to `.env` or use public repos |
| Rate limit errors (GitHub) | Set `GITHUB_TOKEN` to lift limit from 60 → 5000 req/hr |
| Rate limit errors (Groq) | Groq free tier has per-minute limits, wait 1 min and retry |
| PDF export fails | DejaVu font may be missing; unicode fallback (Helvetica + latin-1) will be used |

**More help**: See [SETUP.md](SETUP.md) for detailed troubleshooting.

---

## Quick Links

- [Groq Console](https://console.groq.com) — Free API key
- [Full Setup Guide](SETUP.md) — Detailed instructions
- [Architecture Guide](ARCHITECTURE_GUIDE.md) — How it works
- [Contributing](CONTRIBUTING.md) — Help improve RepoLens
