# RepoLens Setup Guide

Complete step-by-step guide to get RepoLens running on your machine.

> **See [QUICKSTART.md](QUICKSTART.md) for a faster 5-minute setup.**  
> **v3 (current):** LangGraph orchestration, streaming, persistent cache, HITL approval, exports. [See CHANGELOG](CHANGELOG.md).

---

## Prerequisites

- **Python 3.9+** — Check with `python3 --version`
- **pip** — Python package manager (comes with Python)
- **Git** (optional) — To clone the repository
- **Groq Account** (free) — For API access

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/akhilpdas/RepoLens.git
cd RepoLens
```

Or download ZIP from https://github.com/akhilpdas/RepoLens → Code → Download ZIP

### Step 2: Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `streamlit` — Web UI framework
- `groq` — Groq API client (Llama 3.3-70b)
- `chromadb` — Vector database for RAG retrieval
- `requests` — HTTP library for GitHub API
- `python-dotenv` — Environment variable management

---

## Configuration

### Step 1: Create .env File

```bash
cp .env.example .env
```

### Step 2: Get Groq API Key (Free)

1. Go to https://console.groq.com
2. Sign up (email or OAuth — no credit card needed)
3. Navigate to "API Keys"
4. Click "Create New Secret Key"
5. Copy the key (starts with `gsk_`)

### Step 3: Add Key to .env

```bash
# Edit .env with your editor
GROQ_API_KEY=gsk_paste_your_key_here
```

**Important:**
- Never share your API key
- Never commit `.env` to Git (it's in `.gitignore`)

---

## Running the App

```bash
streamlit run app.py
```

You should see:
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

### Using the App

1. **Paste a GitHub URL** in the sidebar (e.g. `https://github.com/streamlit/streamlit`)
2. **Select experience level** — beginner, intermediate, or advanced
3. **Choose explanation style** — concise, balanced, or detailed
4. **Ask a question** — use a preset button or type your own
5. **Watch the pipeline execute:**
   - 📚 Indexing repo files into ChromaDB
   - 📋 Creating investigation plan
   - 🔬 Researching step by step with tools
   - ✍️ Synthesizing the answer
   - 🔍 Reviewing for quality
6. **Explore the tabs:**
   - 📚 Evidence — retrieved chunks + indexed files
   - 🧠 Memory — your profile + question history
   - 📊 Trace — timing metrics + event log
   - 🔬 Details — plan, findings, tool calls, review

---

## Troubleshooting

### "command not found: python3"
Install Python from https://www.python.org/downloads. Try `python` instead of `python3`.

### "No module named 'venv'"
```bash
# Ubuntu/Debian
sudo apt-get install python3-venv
```

### "ModuleNotFoundError" when running app
Make sure venv is activated:
```bash
source venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

### "GROQ_API_KEY not set"
1. Verify `.env` file exists in project root
2. Check `GROQ_API_KEY=gsk_...` line is present
3. Restart the app after editing `.env`

### "Could not fetch README"
- Repository may be private (only public repos supported)
- No README.md file in the repo
- GitHub API rate limit exceeded (60 req/hour unauthenticated)

### "Port 8501 already in use"
```bash
streamlit run app.py --server.port 8502
```

### Rate limit / API errors
- Groq free tier has per-minute limits — wait 1 minute and retry
- GitHub code search API can be rate-limited — affects `search_docs` tool

---

## Project Structure

```
RepoLens/
├── app.py              # Main app — UI + 5-phase pipeline
├── tools.py            # 3 tools: list_files, read_file, search_docs
├── planner.py          # Planner agent — investigation plans
├── retriever.py        # ChromaDB RAG — indexing + retrieval
├── reviewer.py         # Reviewer agent — quality checks
├── memory.py           # SQLite memory — profile + history
├── state.py            # Dataclasses (Plan, PlanStep, etc.)
├── tracer.py           # Observability (timing + events)
├── evaluator.py        # Benchmark evaluation suite
├── requirements.txt    # Dependencies
├── .env                # Your API key (private)
├── .env.example        # Template
└── .gitignore          # Git ignore rules
```

---

## Next Steps

1. **Try different repos** — paste various public GitHub URLs
2. **Explore the code** — start with `app.py`, then `tools.py` and `planner.py`
3. **Read the architecture** — [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md)
4. **Contribute** — [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Need help?** Open an issue: https://github.com/akhilpdas/RepoLens/issues
