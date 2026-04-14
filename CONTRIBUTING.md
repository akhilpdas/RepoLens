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
├── app.py              # Main app — UI + 5-phase pipeline
├── tools.py            # 3 tools (list_files, read_file, search_docs)
├── planner.py          # Planner agent
├── retriever.py        # ChromaDB RAG
├── reviewer.py         # Reviewer agent
├── memory.py           # SQLite memory
├── state.py            # Dataclasses
├── tracer.py           # Observability
├── evaluator.py        # Benchmark evaluation
├── requirements.txt    # Dependencies
└── .env.example        # Env template
```

### Key Functions

| File | Function | Purpose |
|------|----------|---------|
| `app.py` | `execute_step()` | Runs one plan step with tool calling |
| `app.py` | `synthesize_answer()` | Combines findings into final answer |
| `planner.py` | `create_plan()` | LLM creates investigation plan |
| `retriever.py` | `RepoRetriever.index()` | Indexes repo files into ChromaDB |
| `retriever.py` | `RepoRetriever.query()` | Retrieves relevant chunks |
| `reviewer.py` | `review_answer()` | Quality-checks the answer |
| `reviewer.py` | `revise_answer()` | Fixes issues from review |
| `memory.py` | `get_memory_context()` | Builds personalized prompt context |
| `evaluator.py` | `run_eval_suite()` | Runs all 10 benchmark questions |

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

### High Priority
- [ ] Add unit tests for core functions
- [ ] GitHub auth token support for private repos
- [ ] Persistent ChromaDB (disk-backed instead of in-memory)
- [ ] Streaming responses during pipeline execution

### Medium Priority
- [ ] Export answers as Markdown/PDF
- [ ] LangGraph workflow orchestration
- [ ] Caching layer for frequently requested repos
- [ ] Human-in-the-loop approval button

### Low Priority
- [ ] GitLab/Bitbucket support
- [ ] Dark mode theme
- [ ] Multi-repo comparison
- [ ] Browser extension

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
