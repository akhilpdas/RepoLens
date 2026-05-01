# Contributing to RepoLens

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and inclusive. We welcome contributions from everyone, regardless of experience level.

---

## How to Contribute

### Reporting Bugs

1. **Search existing issues** — check if it's already reported
2. **Create a new issue** with:
   - Clear title: "Bug: [description]"
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (OS, Python version)

### Suggesting Features

1. **Create a feature request** with:
   - Clear title: "Feature: [description]"
   - Problem it solves
   - Proposed solution

### Submitting Pull Requests

**Important:** All PRs require review before merging. The `main` branch is protected.

#### Setup

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/RepoLens.git
cd RepoLens
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=gsk_your_key" > .env
git checkout -b feature/my-feature
```

#### Make Changes

1. **Keep commits atomic** — one feature/fix per commit
2. **Follow code style** — PEP 8, type hints, docstrings
3. **Test locally** — `streamlit run app.py` with different repos and questions
4. **Verify imports** — `python3 -c "import ast; ast.parse(open('your_file.py').read())"`

#### Submit

```bash
git push origin feature/my-feature
# Create PR on GitHub
```

---

## Project Structure

```
RepoLens/
├── app.py              # Main Streamlit app — UI + HITL stage machine
├── graph.py            # LangGraph StateGraph orchestration
├── gh.py               # GitHub auth-aware HTTP helper
├── tools.py            # 3 tools (list_files, read_file, search_docs)
├── planner.py          # Planner agent
├── retriever.py        # Persistent ChromaDB RAG (24h TTL cache)
├── reviewer.py         # Reviewer agent + revision
├── memory.py           # SQLite-backed user profile + history
├── state.py            # Structured state classes
├── tracer.py           # Observability (timing + event log)
├── evaluator.py        # 10-question benchmark suite
├── export.py           # MD + PDF export (fpdf2 + DejaVuSans)
├── requirements.txt    # Dependencies
├── .env.example        # Env template
└── .streamlit/         # Streamlit Cloud config + secrets
```

### Key Functions & Classes

| Module | Symbol | Purpose |
|--------|--------|---------|
| `graph.py` | `build_pre_synth_graph()` | Index→Plan→Research subgraph |
| `graph.py` | `build_post_synth_graph()` | Review→(Revise)? subgraph |
| `graph.py` | `synthesize_stream()` | Streaming answer generator |
| `graph.py` | `route_after_review()` | Conditional revise edge logic |
| `planner.py` | `create_plan()` | LLM creates investigation plan |
| `retriever.py` | `RepoRetriever.index()` | Indexes repo, caches to disk |
| `retriever.py` | `RepoRetriever.query()` | Retrieves relevant chunks |
| `retriever.py` | `RepoRetriever.is_fresh()` | TTL + schema version check |
| `reviewer.py` | `review_answer()` | Quality-checks answer (score 1-10) |
| `reviewer.py` | `revise_answer()` | Auto-fixes low-quality answers |
| `evaluator.py` | `run_eval_suite()` | Runs 10 benchmark questions |
| `export.py` | `to_markdown()` | Exports answer + metadata to MD |
| `export.py` | `to_pdf()` | Exports answer + metadata to PDF |
| `gh.py` | `gh_get()` | GitHub API call w/ optional token |
| `memory.py` | `add_question()` | Persists Q&A to SQLite |
| `memory.py` | `get_profile()` / `update_profile()` | User prefs (skill level, style) |
| `app.py` | `_reset_pipeline_state()` | Clears draft/stage on new question |

---

## Code Standards

- **PEP 8** style
- **Type hints** for function signatures
- **Docstrings** for public functions
- **Max line length**: 120 characters
- **Python 3.9 compatible** — use `from __future__ import annotations` for type unions

### Commit Messages

```
feat: add markdown export functionality
fix: handle repos without README gracefully
docs: update setup guide for Windows
refactor: extract tool dispatch into separate function
test: add benchmark for private repo handling
```

---

## Areas for Contribution

### v3 Features (Shipped)
- [x] LangGraph workflow orchestration
- [x] GitHub auth token support (private repos + 5000 req/hr)
- [x] Persistent ChromaDB (disk-backed, 24h TTL, schema versioning)
- [x] Streaming responses (progressively render synthesis)
- [x] Human-in-the-loop approval gate (Approve/Revise/Discard)
- [x] Export answers as Markdown/PDF (fpdf2 + DejaVuSans)
- [x] Evaluator suite wiring (3-Q subset or full 10-Q)
- [x] Streamlit Cloud deploy config
- [x] Comprehensive unit + integration test suite (270 tests across 12 files)
- [x] Dark mode theme (light / dark / system, persisted across sessions)
- [x] Multi-repo side-by-side comparison (independent approval gates per slot)

### Future (v4+)
- [ ] GitLab / Bitbucket support (beyond GitHub)
- [ ] Browser extension for inline documentation
- [ ] Compare summary — automatic diff/contrast synthesis between two repos
- [ ] Memory + Trace tabs accessible from compare mode
- [ ] Mobile-responsive compare layout
- [ ] CI/CD integration with GitHub Actions (run pytest on every PR)

---

## Pull Request Review Process

1. **Automated checks** — verify Python syntax
2. **Code review** — maintainer reviews for quality
3. **Testing** — tested with different repos and questions
4. **Approval** — maintainer approves and merges

---

## Getting Help

- **Questions?** Open a discussion: https://github.com/akhilpdas/RepoLens/discussions
- **Bug?** Open an issue: https://github.com/akhilpdas/RepoLens/issues
- **Architecture question?** Read [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md)

---

**Thank you for contributing to RepoLens!**

By contributing, you agree that your contributions will be licensed under the MIT License.
