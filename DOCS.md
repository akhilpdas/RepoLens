# RepoLens Documentation Index

Welcome to RepoLens! This file helps you navigate all the documentation.

---

## Getting Started

| Need | Document | Time |
|------|----------|------|
| Just run it | [QUICKSTART.md](QUICKSTART.md) | 5 min |
| Detailed setup | [SETUP.md](SETUP.md) | 10 min |
| Understand the project | [README.md](README.md) | 10 min |

---

## Documentation Map

### User Documentation

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](QUICKSTART.md) | Get running in 5 minutes |
| [SETUP.md](SETUP.md) | Detailed installation + troubleshooting |
| [README.md](README.md) | Project overview, architecture, features |

### Developer Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) | Technical deep-dive: pipeline, agents, RAG, memory |
| [DETAILED_EXPLANATION.md](DETAILED_EXPLANATION.md) | Comprehensive how-it-works guide |
| [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md) | Everything explained in simple terms |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute code |
| [CHANGELOG.md](CHANGELOG.md) | Version history (Days 1-10) |

### Source Files

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit app — UI + 5-phase pipeline |
| `tools.py` | 3 tools: list_files, read_file, search_docs |
| `planner.py` | Planner agent — creates investigation plans |
| `retriever.py` | ChromaDB RAG — indexing + retrieval |
| `reviewer.py` | Reviewer agent — quality checks + auto-revision |
| `memory.py` | SQLite memory — user profile + question history |
| `state.py` | Dataclasses: Plan, PlanStep, SessionState |
| `tracer.py` | Observability: timing, events, metrics |
| `evaluator.py` | 10-question benchmark evaluation suite |

### Configuration

| File | Purpose |
|------|---------|
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Git ignore rules |
| `LICENSE` | MIT License |

---

## Quick Navigation by Task

### "I want to install and run RepoLens"
1. [QUICKSTART.md](QUICKSTART.md)
2. If stuck: [SETUP.md](SETUP.md) troubleshooting section

### "I want to understand how it works"
1. [README.md](README.md) — Architecture overview
2. [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) — Technical deep-dive
3. [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md) — Simple explanations

### "I want to contribute"
1. [CONTRIBUTING.md](CONTRIBUTING.md) — Guidelines
2. [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) — Understand the codebase

### "I want to evaluate/benchmark"
1. [README.md](README.md) — Evaluation section
2. `evaluator.py` — 10 benchmark questions + scoring

### "I'm stuck / have errors"
1. [SETUP.md](SETUP.md) — Troubleshooting
2. [QUICKSTART.md](QUICKSTART.md) — Quick fixes table
3. Open an issue: https://github.com/akhilpdas/RepoLens/issues

---

## External Links

| Resource | URL |
|----------|-----|
| Groq Console (API key) | https://console.groq.com |
| Groq API Docs | https://console.groq.com/docs |
| GitHub API Docs | https://docs.github.com/en/rest |
| Streamlit Docs | https://docs.streamlit.io |
| ChromaDB Docs | https://docs.trychroma.com |
| Report Bugs | https://github.com/akhilpdas/RepoLens/issues |

---

**Last Updated**: 2026-04-14
**Version**: 2.0.0
