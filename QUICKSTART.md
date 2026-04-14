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

1. **Paste a GitHub URL** in the sidebar
2. **Select your experience level** (beginner/intermediate/advanced)
3. **Choose explanation style** (concise/balanced/detailed)
4. **Ask a question** — use a preset button or type your own
5. **Watch the pipeline** — Index → Plan → Research → Synthesize → Review
6. **Explore the tabs** — Evidence, Memory, Trace, Details

---

## What Happens Under the Hood

```
Paste GitHub URL
       ↓
📚 INDEX — ChromaDB indexes README, docs, configs, source files
       ↓
📋 PLAN — Planner LLM creates 3-5 investigation steps
       ↓
🔬 RESEARCH — Researcher executes each step with tools (list_files, read_file, search_docs)
       ↓
✍️ SYNTHESIZE — Combines findings into a cited answer
       ↓
🔍 REVIEW — Reviewer checks for accuracy, citations, hallucinations
       ↓
✏️ REVISE — Auto-fixes if quality score < 6/10
       ↓
Display answer + Evidence tab + Memory tab + Trace tab
```

---

## Project Structure

```
RepoLens/
├── app.py              # Main app — UI + pipeline
├── tools.py            # 3 tools: list_files, read_file, search_docs
├── planner.py          # Planner agent
├── retriever.py        # ChromaDB RAG indexing + retrieval
├── reviewer.py         # Reviewer agent + auto-revision
├── memory.py           # SQLite memory (profile + history)
├── state.py            # Dataclasses (Plan, PlanStep, etc.)
├── tracer.py           # Observability (timing + events)
├── evaluator.py        # 10-question benchmark suite
├── requirements.txt    # Dependencies
├── .env                # Your API key (private, gitignored)
└── .env.example        # Template
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
| `GROQ_API_KEY not set` | Check `.env` file exists with your key, restart app |
| `Port 8501 in use` | `streamlit run app.py --server.port 8502` |
| `Could not fetch README` | Repo may be private — use public repos only |
| Rate limit errors | Wait 1 minute, Groq free tier has per-minute limits |

**More help**: See [SETUP.md](SETUP.md) for detailed troubleshooting.

---

## Quick Links

- [Groq Console](https://console.groq.com) — Free API key
- [Full Setup Guide](SETUP.md) — Detailed instructions
- [Architecture Guide](ARCHITECTURE_GUIDE.md) — How it works
- [Contributing](CONTRIBUTING.md) — Help improve RepoLens
