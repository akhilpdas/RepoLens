# RepoLens 🔍

An agentic onboarding assistant for any GitHub repo. Paste a public repo URL and get a structured summary tailored to your experience level.

## Features

- Fetches README and file tree from any public GitHub repo
- Generates structured summaries: what it does, key files, how to run, architecture, first contributions
- Adapts to beginner / intermediate / advanced developers
- Built with Streamlit + OpenAI

## Quick Start

```bash
# Clone
git clone https://github.com/akhilpdas/RepoLens.git
cd RepoLens

# Install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set your API key
export OPENAI_API_KEY="your-key-here"

# Run
streamlit run app.py
```

## Stack

- **Python** — core language
- **Streamlit** — UI
- **OpenAI API** — model + tool calling
- **LangGraph** — workflow orchestration (coming soon)
- **ChromaDB** — retrieval (coming soon)
- **SQLite** — memory (coming soon)

## Roadmap

- [ ] Multi-agent workflow (planner → researcher → reviewer)
- [ ] RAG over docs with ChromaDB
- [ ] Persistent memory with SQLite
- [ ] Question answering beyond summaries
- [ ] Evaluation benchmarks
- [ ] Observability / tracing
