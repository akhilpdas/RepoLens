# RepoLens Workspace

## Project Overview
RepoLens is an agentic onboarding assistant for GitHub repositories. It helps developers understand any public GitHub repo in minutes by generating AI-powered summaries tailored to their experience level.

**Tech Stack**: Streamlit, OpenAI API, LangGraph, ChromaDB

## Quick Start

### Setup
```bash
cd /Users/akhil_das/Documents/RepoLens
source venv/bin/activate
export OPENAI_API_KEY="your-actual-api-key"
streamlit run app.py
```

### Access
- **App URL**: http://localhost:8501
- **API Key**: Add your OpenAI API key to `.env` file

## Project Structure
- `app.py` — Main Streamlit application
- `requirements.txt` — Python dependencies
- `.env` — Environment variables (create from `.env.example`)
- `venv/` — Python virtual environment

## Key Files
- [app.py](app.py) — Streamlit UI and main logic
  - `parse_repo()` — Extract owner/repo from GitHub URL
  - `fetch_readme()` — Fetch README from GitHub API
  - `fetch_repo_tree()` — Get top-level file listing
  - `summarize_repo()` — Call OpenAI for repo summary

## Development Tips

### Running Tests
```bash
source venv/bin/activate
pytest
```

### Environment Variables
Create a `.env` file from `.env.example`:
```
OPENAI_API_KEY=sk-...
```

### Active Dependencies
- **streamlit** ≥1.30.0 — Web UI framework
- **openai** ≥1.12.0 — OpenAI API client
- **langgraph** ≥0.0.40 — Agentic workflows
- **chromadb** ≥0.4.22 — Vector database
- **requests** ≥2.31.0 — HTTP client

## Common Commands
```bash
# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Deactivate venv
deactivate
```

## Notes
- The app requires a valid OpenAI API key to generate summaries
- Without an API key, the app will display the raw README only
- GitHub API calls are rate-limited (60 requests/hour without auth)
