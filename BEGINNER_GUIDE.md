# RepoLens - Complete Beginner's Guide

Welcome! This guide explains **everything about RepoLens** in simple terms that anyone can understand — even if you have never built an AI application before.

---

## Table of Contents

1. [What is RepoLens?](#what-is-repolens)
2. [Why Would You Use It?](#why-would-you-use-it)
3. [Technology Stack (Each Tool Explained Simply)](#technology-stack)
4. [How Does It Work? (The 5-Phase Pipeline)](#how-does-it-work)
5. [The 4 Agents Explained](#the-4-agents-explained)
6. [The 3 Tools Explained](#the-3-tools-explained)
7. [The User Interface](#the-user-interface)
8. [Memory: How RepoLens Remembers You](#memory-how-repolens-remembers-you)
9. [Data Flow (Step-by-Step with Diagrams)](#data-flow)
10. [Key Files and What They Do](#key-files-and-what-they-do)
11. [Key Conditions and Features](#key-conditions-and-features)
12. [Use Cases](#use-cases)
13. [Common Questions](#common-questions)

---

## What is RepoLens?

### Simple Explanation

**RepoLens is an AI agent that investigates GitHub repositories and answers your questions about them.**

Think of it this way:
- You give it a GitHub project link and ask a question
- It sends a team of AI agents to investigate the codebase
- Each agent has a specific job: plan, research, write, or review
- You get a well-cited, accurate answer tailored to your skill level

### How is this different from just asking ChatGPT?

A regular AI chatbot guesses based on general knowledge. RepoLens actually reads the real files in the real repository and **only states things it can prove with evidence**. Every factual claim in the answer is backed by a cited file from the repo.

### Real-World Analogy

Imagine you hire a small consulting team to explain a codebase to you:

1. **Project Manager (Planner)** — reads your question, looks at the README, writes a custom investigation plan
2. **Researcher** — follows the plan, opens actual files, searches for specific things, takes notes
3. **Report Writer (Synthesizer)** — turns all the research notes into a clear, readable answer
4. **Quality Reviewer** — reads the answer and checks that every claim is backed by real evidence

**That is exactly what RepoLens does, using AI for each role.**

---

## Why Would You Use It?

### Scenario 1: You Want to Learn a New Project
```
WITHOUT RepoLens: Spend 3 hours reading README, browsing files, trying to understand
WITH RepoLens:    Ask "What is the architecture?" — get a cited answer in ~30 seconds
```

### Scenario 2: You Are New to a Team
```
Your manager says: "We use this project for data processing"
WITHOUT RepoLens: Spend days reading code, asking colleagues questions
WITH RepoLens:    Ask "Generate a complete onboarding guide" — get step-by-step guide
```

### Scenario 3: You Want to Contribute to Open Source
```
WITHOUT RepoLens: Browse issues, try to understand the codebase, feel lost
WITH RepoLens:    Ask "What would be a good first contribution?" — get specific ideas
```

### When to Use RepoLens
- Learning a new codebase quickly
- Onboarding to a new team project
- Exploring open-source projects before contributing
- Understanding someone else's code
- Getting exact setup/run instructions from the actual files
- Finding the architecture of a large project

---

## Technology Stack

Here is every technology RepoLens uses, explained simply:

---

### 1. Python
**What is it?** A programming language — like English sentences that a computer can execute.

**Why use it?** Easy to read, excellent support for AI, and great for web apps.

**In RepoLens:** Every single file (`app.py`, `tools.py`, `planner.py`, etc.) is Python.

---

### 2. Streamlit
**What is it?** A library that turns Python code into a web application automatically.

**The problem it solves:**
```
OLD WAY to build a web page:
  - Learn HTML (page structure)
  - Learn CSS (styling)
  - Learn JavaScript (interactivity)
  - Set up a server
  --> Takes months to learn

WITH STREAMLIT:
  - Write Python
  - It becomes a web page
  --> Takes days to learn
```

**In RepoLens:** Creates the entire UI — the sidebar, the tabs, the buttons, the answer display. All at http://localhost:8501.

---

### 3. Groq API with Llama 3.3-70b
**What is it?** A service that gives you access to a very powerful AI language model — for free.

**What is Llama 3.3-70b?** An open-source AI model with 70 billion parameters. Think of "parameters" as the number of learned connections in the AI's brain. 70 billion is a large, capable model.

**Why Groq and not OpenAI?**
```
OpenAI (GPT-4):
  - Costs money per request
  - Requires credit card
  - Can get expensive fast

Groq (Llama 3.3-70b):
  - Completely free tier
  - No credit card needed
  - Very fast inference speed
```

**In RepoLens:** Every AI agent (Planner, Researcher, Synthesizer, Reviewer) uses Groq to think and generate output.

---

### 4. ChromaDB
**What is it?** A special type of database called a "vector database" that understands meaning.

**How a regular database works:**
```
Search for "database"
→ Finds files containing the exact word "database"
```

**How ChromaDB works:**
```
Search for "database"
→ Finds files about databases, data storage, SQL, persistence...
→ Understands meaning, not just exact text matches
```

**In RepoLens:** Used to store chunks of repo files during the Index phase. When you ask a question, ChromaDB finds the most relevant text chunks from the codebase to give to the AI agents as evidence.

This technique is called **RAG (Retrieval-Augmented Generation)** — giving the AI real evidence before asking it to write an answer.

---

### 5. GitHub API
**What is it?** A way to ask GitHub programmatically: "Give me the files from this repository."

**In RepoLens:** Used to:
- Fetch the README file
- Get the full list of all files and folders
- Read individual file contents (via the tools)
- Search for keywords across the codebase

No downloading or cloning required — it all happens over HTTPS in seconds.

---

### 6. SQLite
**What is it?** A lightweight database that lives in a single file on your computer.

**In RepoLens:** Stores your user profile (preferred skill level, explanation style) and your question history across sessions. The database file is `repolens_memory.db` in the project folder. Every question you ask is saved so the app can personalise future answers.

---

## How Does It Work?

RepoLens runs a **5-phase pipeline** every time you ask a question. Here is each phase:

```
  YOUR QUESTION
       |
       v
+------+-------+
| Phase 0:     |
| INDEX        |   <-- Read files from GitHub, store them in ChromaDB
| (RAG)        |
+------+-------+
       |
       v
+------+-------+
| Phase 1:     |
| PLAN         |   <-- Planner agent creates a custom investigation plan
|              |
+------+-------+
       |
       v
+------+-------+
| Phase 2:     |
| RESEARCH     |   <-- Researcher agent executes each step using tools
|              |
+------+-------+
       |
       v
+------+-------+
| Phase 3:     |
| SYNTHESIZE   |   <-- Synthesizer agent writes the final answer
|              |
+------+-------+
       |
       v
+------+-------+
| Phase 4:     |
| REVIEW /     |   <-- Reviewer agent checks quality; revises if score < 6
| REVISE       |
+------+-------+
       |
       v
  YOUR ANSWER
  (with quality score)
```

---

### Phase 0: Index (RAG)

**What happens:**
1. The `RepoRetriever` fetches the full file tree from GitHub
2. It selects which files are worth indexing: README, config files (`requirements.txt`, `package.json`, `Dockerfile`, etc.), docs folder, and top-level source files
3. Each file is split into overlapping **chunks** of ~800 characters
4. All chunks are stored in ChromaDB with metadata (source file, chunk number)
5. When you ask a question, ChromaDB finds the 5 most relevant chunks as evidence

**Why this matters:** The AI agents get real, cited evidence from the actual codebase — not general knowledge. This prevents hallucination.

**Files involved:** `retriever.py`

---

### Phase 1: Plan

**What happens:**
1. The Planner agent receives your question, the repo name, your skill level, and the first 2000 characters of the README
2. It generates a JSON plan with 3 to 5 investigation steps
3. Each step has: a title, a description of what to do, and which tools to use

**Example plan for "How do I run this project?":**
```
Step 1: Explore root structure        [tools: list_files]
Step 2: Read the README               [tools: read_file]
Step 3: Find setup/config files       [tools: read_file, search_docs]
Step 4: Check for Makefile/scripts    [tools: list_files, read_file]
Step 5: Synthesize setup instructions [no tools — write the answer]
```

**Files involved:** `planner.py`, `state.py`

---

### Phase 2: Research

**What happens:**
1. The Researcher agent executes each plan step one by one
2. For each step, it receives: the plan step description, the README preview, the ChromaDB evidence chunks, and findings from previous steps
3. It calls tools (list_files, read_file, search_docs) to gather real evidence
4. It produces a set of findings for that step (bullet points with file citations)
5. Findings accumulate — each step builds on the previous ones

**The Researcher follows strict rules:**
- Every factual claim must cite a file: `(source: filename.ext)`
- If something is not found in the files, it says "Not found" — it does not guess
- Keeps findings concise: 3 to 8 bullet points per step

**Files involved:** `app.py` (the `execute_step` function), `tools.py`

---

### Phase 3: Synthesize

**What happens:**
1. The Synthesizer receives all step findings plus the top evidence chunks
2. It writes the final, user-facing answer in clean markdown
3. It applies your style preference: concise (bullet points), balanced, or detailed
4. It tailors the language for your experience level (beginner gets jargon explained; advanced gets the technical internals)

**Files involved:** `app.py` (the `synthesize_answer` function)

---

### Phase 4: Review and Revise

**What happens:**
1. The Reviewer agent reads the draft answer
2. It checks for specific quality problems:
   - Unsupported claims (no file cited)
   - Missing citations on key facts
   - Vague setup instructions ("install dependencies" with no actual command)
   - File paths that do not exist in the repo
   - Hallucinated function or class names not confirmed by evidence
3. It assigns a **quality score from 1 to 10** and a verdict: `pass` or `needs_revision`
4. If the score is below 6 and verdict is `needs_revision`, the answer is automatically revised
5. The final quality score is displayed as a badge above the answer

**Scoring guide:**
```
9-10: Excellent — well-cited, complete, no issues
7-8:  Good — minor issues (one or two missing citations)
5-6:  Acceptable — some vague sections or unsupported claims
1-4:  Poor — hallucinations, missing evidence, off-topic
```

**Files involved:** `reviewer.py`

---

## The 4 Agents Explained

An "agent" in this context is an AI model call with a specific system prompt (a set of instructions) that gives it a focused role. All 4 agents use the same underlying model (Groq / Llama 3.3-70b) but behave very differently because their instructions are different.

---

### Agent 1: Planner
- **Lives in:** `planner.py`
- **Job:** Turn your question into a structured JSON investigation plan
- **Input:** Your question + repo name + user level + README preview
- **Output:** A `Plan` object with 3–5 `PlanStep` objects
- **Personality:** Methodical, organized, never produces the answer itself — only the roadmap

---

### Agent 2: Researcher
- **Lives in:** `app.py` (the `execute_step` function)
- **Job:** Execute one plan step at a time using tools and RAG evidence
- **Input:** One plan step + evidence chunks + previous findings
- **Output:** Bullet-point findings with file citations for that step
- **Personality:** Evidence-focused detective — never states a fact without a source

---

### Agent 3: Synthesizer
- **Lives in:** `app.py` (the `synthesize_answer` function)
- **Job:** Combine all research findings into a polished, readable answer
- **Input:** All step findings + evidence chunks + user style preference + skill level
- **Output:** Final markdown answer with section headers
- **Personality:** Clear communicator — adapts writing style to beginner/intermediate/advanced

---

### Agent 4: Reviewer
- **Lives in:** `reviewer.py`
- **Job:** Quality-check the answer before the user sees it; optionally trigger revision
- **Input:** Draft answer + list of indexed files + evidence chunks
- **Output:** JSON with verdict, issues list, quality score, and summary
- **Personality:** Strict editor — flags hallucinations, missing citations, and vague instructions

---

## The 3 Tools Explained

Tools are Python functions that the Researcher agent can call during its investigation. The agent decides which tools to use and when — this is called **tool use** or **function calling**.

---

### Tool 1: list_files(path)
**What it does:** Lists all files and folders at a given path inside the repo.

```
Example call:    list_files("")
Example result:
  📁 src/
  📁 tests/
  📄 README.md
  📄 requirements.txt
  📄 app.py
```

**When the agent uses it:** At the start of any investigation to understand the project structure; also to look inside specific folders.

---

### Tool 2: read_file(path)
**What it does:** Fetches and returns the full text content of a specific file (up to ~8000 characters).

```
Example call:    read_file("requirements.txt")
Example result:
  streamlit==1.32.0
  groq==0.4.2
  chromadb==0.4.22
  ...
```

**When the agent uses it:** To read configuration files, check exact dependency versions, inspect source code, or read documentation files.

---

### Tool 3: search_docs(query)
**What it does:** Searches for a keyword or phrase across all files in the repo using the GitHub code-search API. Returns up to 10 matching file paths with text snippets.

```
Example call:    search_docs("database connection")
Example result:
  📄 src/db.py
     ...conn = sqlite3.connect(DB_PATH)...
  📄 config/settings.py
     ...DATABASE_URL = os.environ.get("DB_URL")...
```

**When the agent uses it:** To find where a specific concept, function, or configuration lives without having to read every file.

---

**Files involved:** `tools.py`

---

## The User Interface

The UI is built with Streamlit and has two main areas: the sidebar and the main panel.

---

### Sidebar Controls

| Control | What it does |
|---|---|
| GitHub Repo URL | The repository you want to explore |
| Experience Level | beginner / intermediate / advanced — affects how answers are written |
| Explanation Style | concise / balanced / detailed — affects answer length and format |
| Quick Action buttons | 5 preset questions (summarize, onboarding guide, setup, what to read, how to contribute) |
| Last explored | Shows the last repo you used (loaded from memory) |

Your experience level and style preference are **saved to SQLite memory** and pre-filled the next time you open the app.

---

### Main Panel

When you enter a URL, the main panel shows:
- 5 one-click question buttons for common questions
- A text input for custom questions
- Live progress indicators for each pipeline phase as it runs
- A quality score badge (green/yellow/red) above the final answer
- The final answer in formatted markdown

---

### The 4 Tabs

After an answer is generated, four tabs appear below it:

| Tab | What it shows |
|---|---|
| Evidence | The raw ChromaDB chunks retrieved for the question; list of all indexed files |
| Memory | Your stored user profile (JSON); your last 10 questions with scores and previews |
| Trace | Total run time, tool call count, quality score; per-phase timing; full event log |
| Details | The investigation plan with step statuses; per-step research findings; all tool calls with results; full reviewer JSON output |

---

## Memory: How RepoLens Remembers You

RepoLens uses **SQLite** (a file-based database) to remember things between sessions. The database file is `repolens_memory.db` in the project folder.

### What is stored

**User Profile table** — one row, always updated:
```
skill_level        → "beginner" / "intermediate" / "advanced"
explanation_style  → "concise" / "balanced" / "detailed"
last_repo          → last GitHub repo you explored
updated_at         → timestamp of last update
```

**Question History table** — up to 20 most recent rows:
```
repo            → which repo the question was about
question        → the exact question asked
user_level      → what level you were set to
answer_preview  → first 500 chars of the answer
quality_score   → the reviewer's score (1–10)
asked_at        → timestamp
```

### How memory is used during a run

When the Researcher agent investigates a step, it receives a **memory context string** injected into its prompt. This string tells it:
- Your current skill level
- Your preferred explanation style
- The last repo you explored (if different)
- The last 3 questions you asked about this specific repo

This means if you asked "What is the architecture?" earlier, and now ask "How do I run it?", the agent knows the context of your session.

**Files involved:** `memory.py`

---

## Data Flow

Here is the complete journey from your question to your answer:

```
You type a question and paste a GitHub URL
              |
              v
     app.py parses the URL
     → extracts owner and repo name
     → calls set_repo() in tools.py to configure the tools
     → fetches README text and file tree from GitHub API
              |
              v
+--------------------------+
|  PHASE 0: INDEX          |
|  retriever.py            |
|                          |
|  1. Fetch full file tree |
|  2. Select files to index|
|     (README, configs,    |
|      docs, entry points) |
|  3. Fetch each file      |
|  4. Split into 800-char  |
|     overlapping chunks   |
|  5. Store in ChromaDB    |
|  6. Query top 5 chunks   |
|     for your question    |
+-----------+--------------+
            |
            v
+--------------------------+
|  PHASE 1: PLAN           |
|  planner.py              |
|                          |
|  LLM call with:          |
|  - Your question         |
|  - Repo name             |
|  - User level            |
|  - README preview        |
|                          |
|  Returns JSON plan       |
|  (3-5 PlanStep objects)  |
+-----------+--------------+
            |
            v
+--------------------------+
|  PHASE 2: RESEARCH       |
|  app.py: execute_step()  |
|                          |
|  For each plan step:     |
|  - LLM decides which     |
|    tools to call         |
|  - Calls list_files,     |
|    read_file, or         |
|    search_docs           |
|  - Tool results feed     |
|    back to LLM           |
|  - LLM writes findings   |
|    (with file citations) |
+-----------+--------------+
            |
            v
+--------------------------+
|  PHASE 3: SYNTHESIZE     |
|  app.py: synthesize()    |
|                          |
|  LLM receives:           |
|  - All step findings     |
|  - Evidence chunks       |
|  - Style preference      |
|  - User level            |
|                          |
|  Writes final answer     |
|  in markdown             |
+-----------+--------------+
            |
            v
+--------------------------+
|  PHASE 4: REVIEW/REVISE  |
|  reviewer.py             |
|                          |
|  LLM checks answer for:  |
|  - Missing citations     |
|  - Vague instructions    |
|  - Bad file references   |
|  - Hallucinations        |
|                          |
|  Assigns score 1-10      |
|  If score < 6: revise    |
+-----------+--------------+
            |
            v
   Answer displayed with quality badge
   Question saved to SQLite memory
   Trace recorded for the Trace tab
```

---

## Key Files and What They Do

```
RepoLens/
|
+-- app.py              Main application. Runs the Streamlit UI, orchestrates
|                       all 5 pipeline phases, contains the Researcher and
|                       Synthesizer agent logic.
|
+-- tools.py            The 3 tools (list_files, read_file, search_docs) that
|                       the Researcher can call. Also contains the tool
|                       definitions in OpenAI function-calling JSON format.
|
+-- planner.py          The Planner agent. Calls Groq to generate a structured
|                       JSON investigation plan from a question.
|
+-- retriever.py        The RAG module. Fetches files from GitHub, splits them
|                       into chunks, stores them in ChromaDB, and retrieves
|                       the most relevant chunks for a query.
|
+-- reviewer.py         The Reviewer agent. Checks answer quality, assigns a
|                       score, and can revise the answer if quality is low.
|
+-- memory.py           SQLite persistence. Stores user profile and question
|                       history. Builds memory context strings for agents.
|
+-- state.py            Data classes: PlanStep, Plan, SessionState, StepStatus.
|                       These are the structured objects that flow through the
|                       pipeline.
|
+-- tracer.py           Observability. Records timing, tool calls, quality
|                       scores, and errors for each run. Displayed in the
|                       Trace tab.
|
+-- evaluator.py        (Evaluation utilities — used for testing and scoring
|                       the pipeline's performance.)
|
+-- requirements.txt    All Python libraries required to run the app.
+-- .env                Your secret API key (GROQ_API_KEY). Never commit this.
+-- repolens_memory.db  SQLite database file (auto-created on first run).
```

---

### Key Functions Reference

#### `parse_repo(url)` — in app.py
```
Input:   "https://github.com/django/django"
Process: Split URL, extract owner and repo
Output:  ("django", "django")
```

#### `fetch_readme(owner, repo)` — in app.py
```
Input:   owner="django", repo="django"
Process: GitHub API call to /repos/{owner}/{repo}/readme
Output:  Full README text, or None if not found
```

#### `fetch_repo_tree(owner, repo)` — in app.py
```
Input:   owner="django", repo="django"
Process: GitHub API call to get file tree
Output:  ["README.rst", "setup.py", "django/", ...]
```

#### `execute_step(step, plan, readme, previous_findings, retriever, status_ui)` — in app.py
```
Input:   One PlanStep, context from previous steps, RAG retriever
Process: Calls Groq with tool use enabled; loops up to 5 tool calls per step
Output:  String of findings (bullet points with citations) + list of tool calls made
```

#### `synthesize_answer(plan, findings, readme, evidence_chunks, style)` — in app.py
```
Input:   All research findings, evidence chunks, style preference
Process: Single Groq call with structured system prompt
Output:  Final markdown answer string
```

#### `create_plan(question, repo_name, user_level, readme_preview)` — in planner.py
```
Input:   Question and context
Process: Groq call with JSON response format enforced
Output:  Plan object containing PlanStep objects
```

#### `RepoRetriever.index(status_callback)` — in retriever.py
```
Input:   Owner/repo already set in __init__
Process: Fetch tree → select files → fetch contents → chunk → store in ChromaDB
Output:  Dict with files_indexed count and chunks_created count
```

#### `review_answer(question, answer, indexed_files, evidence_chunks, user_level)` — in reviewer.py
```
Input:   Draft answer and all context
Process: Groq call with JSON response format enforced
Output:  Dict: {verdict, issues[], quality_score, summary}
```

#### `get_memory_context(repo, user_level)` — in memory.py
```
Input:   Current repo and user level
Process: Query SQLite for profile + last 3 questions about this repo
Output:  Formatted string injected into agent prompts
```

---

## Key Conditions and Features

### When RepoLens Works
- The repo is publicly accessible on GitHub
- A valid GitHub URL is provided (`https://github.com/owner/repo`)
- `GROQ_API_KEY` is set in your `.env` file
- GitHub and Groq APIs are reachable

### When It Has Limitations
- **Private repos:** The GitHub API calls will fail — RepoLens only supports public repositories
- **No README:** The planner will have less context; it falls back to a default plan
- **GitHub rate limiting:** The `search_docs` tool may get a 403 error if you make many requests in quick succession; the error is shown to the agent which adjusts its approach
- **Very large repos:** The retriever indexes a limited set of files (up to 10 doc files and 5 source files) to avoid taking too long

### Features

**Core pipeline:**
- 5-phase agentic pipeline: Index, Plan, Research, Synthesize, Review/Revise
- RAG (ChromaDB) for evidence-grounded answers
- Tool use: the Researcher calls real GitHub APIs mid-investigation
- Automatic answer revision if quality score is below 6

**Personalisation:**
- Experience level adapts answer language (beginner gets jargon explained)
- Explanation style adapts answer length and format
- SQLite memory persists preferences across sessions
- Past questions feed into agent context for personalised answers

**Transparency:**
- Every factual claim in the answer cites a source file
- Quality score badge (1–10) shown above every answer
- Evidence tab shows the exact chunks used
- Trace tab shows per-phase timing and all events
- Details tab shows the full investigation plan, per-step findings, and all tool calls

**Safety:**
- API key stored in `.env`, never in source code
- GitHub fetch timeout set to 15 seconds
- ChromaDB chunk size limits (8000 chars per file read, 500 chars per chunk preview)
- Pipeline phases catch exceptions individually — one failure does not crash the whole run

---

## Use Cases

### Use Case 1: Onboarding to a New Job
```
Situation: First week at a new company. Your manager points to a large codebase.
Question:  "Generate a complete onboarding guide for this project."
Result:    Step-by-step guide citing the actual setup files, the real entry
           points, and the actual folder structure — not generic advice.
```

### Use Case 2: Evaluating an Open Source Library
```
Situation: You found a library that might solve your problem. Is it right for you?
Question:  "What is the architecture of this project?"
Result:    Architectural overview with source citations — lets you judge
           complexity and fit without reading thousands of lines of code.
```

### Use Case 3: Finding Where to Start Contributing
```
Situation: You want to contribute to open source but don't know where to start.
Question:  "What would be a good first contribution?"
Result:    Specific suggestions based on the actual state of the codebase:
           tests that are missing, docs that are thin, utilities that could
           be extended — all backed by file evidence.
```

### Use Case 4: Understanding Setup and Dependencies
```
Situation: You need to run a project locally but the README is vague.
Question:  "What are the exact steps to set up and run this project?"
Result:    Exact commands from the actual requirements.txt, Makefile,
           or setup script — not generic "install dependencies" advice.
```

### Use Case 5: Pre-Code-Review Understanding
```
Situation: Assigned to review a PR in an unfamiliar part of the codebase.
Question:  "What files should I read first to understand this codebase?"
Result:    Prioritised reading list based on which files are entry points,
           which are most important, and what they depend on.
```

---

## Common Questions

### Q: Does it work with any GitHub repo?
A: Yes, any public GitHub repository. Private repos are not supported because the GitHub API calls require authentication that RepoLens does not handle.

### Q: How long does it take?
A: Typically 20 to 60 seconds depending on repo size, number of plan steps, and Groq API response speed. The indexing phase (fetching and chunking files) is usually the longest part.

### Q: Can it be wrong?
A: Yes, but it is designed to minimise this. The Researcher cites file sources for every claim, and the Reviewer checks for unsupported claims and hallucinations. The quality score tells you how confident the system is in its answer. A score of 8 or above is generally reliable. A score below 6 triggers automatic revision.

### Q: What files does it actually read?
A: The retriever always indexes: README variants, common config/manifest files (requirements.txt, package.json, Dockerfile, etc.), files in docs/ folders, and top-level source entry points (files named main, app, index, server, etc.). This gives broad coverage without reading the entire repo.

### Q: Is my data safe?
A: The app only sends data that is already publicly available — README content, file names, and file contents from public GitHub repos. Your Groq API key is stored locally in `.env` and is never sent anywhere except to Groq's API.

### Q: How much does it cost to run?
A: The Groq API is free to use. The GitHub API is free for public repos (with rate limits). The only cost is your time to set it up.

### Q: How do I change how the answer is written?
A: Use the "Experience Level" and "Explanation Style" dropdowns in the sidebar. Your preferences are saved automatically to the local SQLite database and used in every future session.

### Q: Where is my question history stored?
A: In `repolens_memory.db` in the project folder. It is a local SQLite file. Nothing is sent to a server. The last 20 questions are kept.

---

## Summary

### What You Have Learned:
- RepoLens is a **multi-agent AI pipeline** that investigates GitHub repos
- It has **5 phases**: Index (RAG), Plan, Research, Synthesize, Review/Revise
- It has **4 agents**: Planner, Researcher, Synthesizer, Reviewer — each with a focused role
- It has **3 tools**: list_files, read_file, search_docs — real GitHub API calls
- It uses **ChromaDB** so answers are grounded in real codebase evidence
- It uses **SQLite memory** to remember your preferences and question history
- It uses **Groq (Llama 3.3-70b)** — completely free
- Every answer includes **file citations** and a **quality score**

### Key Takeaways:
1. RepoLens does not guess — it reads the actual files and cites its sources
2. The pipeline is transparent — you can see every step, every tool call, and every piece of evidence in the tabs
3. The Reviewer catches mistakes before you see the answer
4. Your preferences and history persist across sessions
5. It works with any public GitHub repository

---

If you have more questions, check `README.md` for setup instructions or `SETUP.md` for environment configuration.
