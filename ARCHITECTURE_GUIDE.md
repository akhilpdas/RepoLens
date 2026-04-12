# RepoLens - Complete Architecture & Implementation Guide 📐

A detailed technical guide explaining how RepoLens works, what each part does, and how everything connects together.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Tech Stack Explained](#tech-stack-explained)
3. [Data Flow](#data-flow)
4. [Code Components](#code-components)
5. [Implementation Details](#implementation-details)
6. [API Integrations](#api-integrations)
7. [Error Handling](#error-handling)
8. [Performance Optimization](#performance-optimization)

---

## System Architecture

### High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                       │
│                    (Streamlit Web App)                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ - Sidebar (Experience Level Selection)                 │  │
│  │ - Input Field (GitHub URL)                             │  │
│  │ - Display Area (Summary Results)                        │  │
│  │ - File Browser (Right Column)                          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ User Action: Paste URL
                       │
┌──────────────────────▼───────────────────────────────────────┐
│              APPLICATION LOGIC LAYER (Python)                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ parse_repo()      → Extract owner/repo from URL       │  │
│  │ fetch_readme()    → Get README content                │  │
│  │ fetch_repo_tree() → Get file structure                │  │
│  │ summarize_repo()  → Generate AI summary               │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
┌────────▼──────────┐      ┌─────────▼──────────┐
│  GITHUB API       │      │   GROQ API         │
│  ┌──────────────┐ │      │  ┌──────────────┐  │
│  │Get README    │ │      │  │Send Prompt   │  │
│  │Get File Tree │ │      │  │Receive Text  │  │
│  │Public Repos  │ │      │  │Llama 3.3-70b │  │
│  └──────────────┘ │      │  └──────────────┘  │
└───────────────────┘      └────────────────────┘
```

### Component Interactions

```
┌─────────────────────────────────────────────────────────────┐
│                   REQUEST (GitHub URL)                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ PARSE_REPO()   │  Extract owner & repo
        └────────┬───────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌──────────────┐      ┌──────────────────┐
│ FETCH_README │      │ FETCH_REPO_TREE  │
│ GitHub API   │      │ GitHub API       │
└──────┬───────┘      └────────┬─────────┘
       │                       │
       │ Returns README Text   │ Returns File List
       │                       │
       └───────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ SUMMARIZE_REPO()     │
        │ - Build Prompt       │
        │ - Include README     │
        │ - Include Files      │
        │ - Tailor to Level    │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ GROQ API CALL        │
        │ Llama 3.3-70b AI     │
        │ Processes Input      │
        │ Generates Summary    │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ AI RESPONSE          │
        │ Detailed Summary     │
        │ (2000+ words)        │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ DISPLAY ON WEBPAGE   │
        │ Formatted Markdown   │
        │ Multiple Sections    │
        └──────────────────────┘
```

---

## Tech Stack Explained

### 1. Frontend Layer: Streamlit 🎨

**What It Does:**
- Creates the web interface
- Handles user interactions
- Displays results beautifully
- No HTML/CSS/JavaScript needed!

**How It Works:**

```python
# Simple Streamlit Code
import streamlit as st

# This creates a title on the webpage
st.title("🔍 RepoLens")

# This creates a selection dropdown
level = st.sidebar.selectbox("Your level", ["beginner", "advanced"])

# This creates an input field
repo_url = st.text_input("Paste URL")

# This creates a loading spinner
with st.spinner("Analyzing..."):
    # Long process here
    pass

# This displays the result
st.markdown(summary_text)
```

**Why Streamlit?**
```
Traditional Web Development:
├─ Frontend: HTML + CSS + JavaScript
├─ Backend: Python/Node/Java
├─ Database: SQL/NoSQL
├─ Deployment: Complex setup
└─ Time: Weeks to months

Streamlit:
├─ Just Python
├─ Everything handled
├─ Beautiful by default
├─ Deployment: 1 command
└─ Time: Days to hours
```

### 2. Backend Language: Python 🐍

**Why Python?**
- Easy to read and learn
- Great libraries for everything
- Perfect for AI/ML applications
- Strong community support

**Key Python Features Used:**

```python
# String manipulation
repo_url.rstrip("/")  # Remove trailing slash

# List processing
files = [item["path"] for item in tree]  # List comprehension

# Dictionaries (JSON-like)
headers = {"Accept": "application/vnd.github.v3.raw"}

# Try-except (error handling)
try:
    response = requests.get(url)
except Exception as e:
    print(f"Error: {e}")

# Type hints (better code)
def fetch_readme(owner: str, repo: str) -> str | None:
    pass

# F-strings (modern string formatting)
message = f"Repo: {owner}/{repo}"
```

### 3. External APIs

#### A. GitHub REST API 📚

**Purpose:** Get repository information

**What You Can Get:**
```
✅ README content (raw text)
✅ File/folder structure
✅ Commit history
✅ Issue information
✅ Pull request details
✅ User information
✅ Repository statistics
```

**How RepoLens Uses It:**

```python
# Get README
response = requests.get(
    f"https://api.github.com/repos/{owner}/{repo}/readme",
    headers={"Accept": "application/vnd.github.v3.raw"}
)
readme_text = response.text  # Get as plain text

# Get File Tree
response = requests.get(
    f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD"
)
tree_data = response.json()  # Get as JSON
files = [item["path"] for item in tree_data["tree"]]
```

**Why This Works:**
```
No Authentication Required ✅
- GitHub allows 60 requests/hour for public repos without API key
- Perfect for public repositories
- No account needed to use API

Public Data Only ✅
- We only access publicly available information
- No private data access
- Same data you'd see on GitHub website

Instant & Lightweight ✅
- Much faster than cloning repo
- Don't need to download entire codebase
- Just metadata and README
```

#### B. Groq API 🚀

**Purpose:** AI-powered text generation and analysis

**What It Does:**
```
INPUT:
- Your GitHub repository README
- File structure
- List of files
- User experience level

PROCESSING:
- Reads and understands the content
- Analyzes structure and purpose
- Organizes information logically
- Generates human-friendly explanations

OUTPUT:
- Detailed summary (2000+ words)
- Multiple sections with info
- Tailored to experience level
- Well-formatted markdown
```

**Technical Details:**

```python
# Initialize Groq client
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Create chat message
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",  # The AI model
    messages=[
        {"role": "user", "content": prompt}
    ],
    temperature=0.3,      # Low = precise, High = creative
    max_tokens=3000       # Maximum response length
)

# Extract response
summary = response.choices[0].message.content
```

**Why Groq Instead of OpenAI?**

| Feature | Groq | OpenAI |
|---------|------|--------|
| Cost | 🟢 FREE | 🔴 Paid (~$0.05-0.15/request) |
| Daily Limit | 🟢 Unlimited | 🔴 500 requests/month (free tier) |
| Credit Card | 🟢 Not needed | 🔴 Required |
| Speed | 🟢 Super fast | 🟡 Slower |
| AI Quality | 🟢 Llama 3.3-70b | 🟢 GPT-4/3.5 |
| Setup | 🟢 2 minutes | 🔴 Account + billing |

---

## Data Flow

### Step-by-Step Data Journey

```
┌─────────────────────────────────────────────────┐
│ STEP 1: USER INPUT                              │
├─────────────────────────────────────────────────┤
│ URL: https://github.com/anthropics/claude-code  │
│ Level: "beginner"                               │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│ STEP 2: PARSE & VALIDATE                        │
├─────────────────────────────────────────────────┤
│ Extract:                                        │
│ - owner: "anthropics"                           │
│ - repo: "claude-code"                           │
│ Validate:                                       │
│ - Check format: ✅ Valid                        │
│ - Check length: ✅ Valid                        │
└──────────────┬──────────────────────────────────┘
               │
               ├─────────────────────────┐
               │                         │
               ▼                         ▼
        ┌──────────────┐         ┌──────────────┐
        │ GITHUB API   │         │ GITHUB API   │
        │ Call #1      │         │ Call #2      │
        │ GET README   │         │ GET TREE     │
        └──────┬───────┘         └────────┬─────┘
               │ Response:               │ Response:
               │ README text             │ JSON with files
               │ (8000 chars)            │ (60 top-level items)
               │                         │
               └────────────┬────────────┘
                            │
                            ▼
        ┌─────────────────────────────────┐
        │ STEP 3: PREPARE AI PROMPT       │
        ├─────────────────────────────────┤
        │ Build comprehensive instruction:│
        │ 1. Role: Code expert            │
        │ 2. Task: Summarize repo         │
        │ 3. Include README               │
        │ 4. Include file list            │
        │ 5. Tailor to "beginner"         │
        │ 6. Request 12 sections          │
        │ 7. Max 3000 tokens output       │
        └──────────────┬───────────────────┘
                       │
                       ▼
        ┌──────────────────────────┐
        │ STEP 4: GROQ API CALL    │
        ├──────────────────────────┤
        │ Model: llama-3.3-70b     │
        │ Temp: 0.3 (precise)      │
        │ Max Tokens: 3000         │
        └──────────────┬───────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ STEP 5: AI PROCESSING        │
        ├──────────────────────────────┤
        │ Llama 3.3-70b AI analyzes:   │
        │ - README content             │
        │ - File structure             │
        │ - Technologies used          │
        │ - Architecture               │
        │ - Key components             │
        │ - Learning path              │
        │ (This takes 2-5 seconds)     │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ STEP 6: AI GENERATES OUTPUT  │
        ├──────────────────────────────┤
        │ Creates structured response: │
        │ 1. Project Overview          │
        │ 2. Tech Stack                │
        │ 3. Directory Structure        │
        │ 4. Key Files (8 files)        │
        │ 5. Setup Instructions        │
        │ 6. How to Run                │
        │ 7. Architecture Deep Dive    │
        │ 8. Development Workflow      │
        │ 9. Code Quality              │
        │ 10. First Contributions      │
        │ 11. Troubleshooting          │
        │ 12. Learning Resources       │
        │ (Total: 2000-3000 words)     │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ STEP 7: RETURN TO APP        │
        ├──────────────────────────────┤
        │ Response format: Markdown    │
        │ With sections, code blocks   │
        │ Formatted for web display    │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ STEP 8: DISPLAY TO USER      │
        ├──────────────────────────────┤
        │ Left column:                 │
        │ - Formatted markdown summary │
        │ - Easy to read               │
        │ - Multiple sections          │
        │ - Code examples (if included)│
        │                              │
        │ Right column:                │
        │ - File structure preview     │
        │ - Top 30 files/folders       │
        └──────────────────────────────┘
```

---

## Code Components

### Component 1: URL Parser

```python
def parse_repo(url: str) -> tuple[str, str] | None:
    """
    Purpose: Extract GitHub owner and repo name from URL
    
    Input: "https://github.com/anthropics/claude-code"
    Output: ("anthropics", "claude-code")
    """
    
    # Step 1: Remove trailing slash
    url = url.rstrip("/")
    # Result: "https://github.com/anthropics/claude-code"
    
    # Step 2: Remove GitHub domain
    parts = url.replace("https://github.com/", "").split("/")
    # Result: ["anthropics", "claude-code"]
    
    # Step 3: Validate we have at least 2 parts
    if len(parts) >= 2:
        return parts[0], parts[1]  # Return owner, repo
    return None  # Invalid URL format
```

**Error Handling:**
```
✅ Handles URLs with trailing slashes
✅ Removes https:// prefix
✅ Splits correctly
✅ Returns None if invalid format
```

### Component 2: README Fetcher

```python
def fetch_readme(owner: str, repo: str) -> str | None:
    """
    Purpose: Download README from GitHub API
    
    Input: owner="anthropics", repo="claude-code"
    Output: Full README text or None
    """
    
    # Step 1: Build GitHub API URL
    api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    
    # Step 2: Set proper headers
    headers = {"Accept": "application/vnd.github.v3.raw"}
    # This header tells GitHub to return raw text, not JSON
    
    # Step 3: Make HTTP request
    resp = requests.get(api_url, headers=headers, timeout=15)
    
    # Step 4: Check if successful
    if resp.status_code == 200:
        return resp.text  # Return the README content
    return None  # Return None if failed
```

**Status Codes:**
```
200: Success ✅
404: Not found (no README or repo doesn't exist) ❌
403: Rate limited ⏳
500: Server error ❌
```

### Component 3: File Tree Fetcher

```python
def fetch_repo_tree(owner: str, repo: str) -> list[str]:
    """
    Purpose: Get list of files and folders in repo
    
    Input: owner="anthropics", repo="claude-code"
    Output: ["app.py", "README.md", "src/", ...]
    """
    
    # Step 1: Build API URL for git tree
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD"
    # "HEAD" means current main branch
    
    # Step 2: Make request and parse JSON
    resp = requests.get(api_url, timeout=15)
    
    if resp.status_code == 200:
        # Step 3: Extract file paths from JSON
        tree_data = resp.json()  # Convert JSON string to Python dict
        file_list = [item["path"] for item in tree_data.get("tree", [])]
        return file_list
    
    return []  # Return empty list if failed
```

**JSON Response Example:**
```json
{
  "tree": [
    {"path": "app.py", "type": "blob"},
    {"path": "README.md", "type": "blob"},
    {"path": "src", "type": "tree"},
    {"path": "tests", "type": "tree"}
  ]
}
```

### Component 4: AI Summarizer

```python
def summarize_repo(readme: str, files: list[str], user_level: str) -> str:
    """
    Purpose: Use Groq AI to create comprehensive summary
    
    Inputs:
    - readme: Full README text
    - files: List of filenames
    - user_level: "beginner", "intermediate", or "advanced"
    
    Output: Detailed summary (2000-3000 words)
    """
    
    # Step 1: Initialize Groq client
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    
    # Step 2: Prepare file listing (only first 60 to save tokens)
    file_listing = "\n".join(files[:60])
    
    # Step 3: Build detailed prompt (the key to good AI output!)
    prompt = f"""You are RepoLens, an expert...
    [Detailed instructions in markdown format]
    
    README:
    {readme[:10000]}  # First 10,000 characters
    
    Files:
    {file_listing}
    """
    
    # Step 4: Call Groq API
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,      # Lower = more factual/precise
        max_tokens=3000       # Allow 3000 tokens (about 2000 words)
    )
    
    # Step 5: Extract and return the summary
    return response.choices[0].message.content
```

**Prompt Engineering (The Secret Sauce!):**

```
❌ Bad Prompt:
"Summarize this repo"

✅ Good Prompt:
"You are an expert developer. Here's a README and file list.
Please provide a comprehensive 12-section guide covering:
1. Overview (3 paragraphs)
2. Tech stack (with explanations)
3. Directory structure
4. Key files with reasons (8 files)
... [continues for all sections]

Tailor to a {user_level} developer. Use markdown formatting.
Be detailed and thorough."
```

---

## Implementation Details

### 1. Virtual Environment

```bash
# Why use virtual environment?
# Each project can have its own Python packages
# Don't mix dependencies from different projects

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Isolation Benefits:**
```
Project A: Needs numpy 1.20
Project B: Needs numpy 1.24
→ With venv: Both can coexist!
→ Without venv: Conflict! Error!
```

### 2. Environment Variables

```python
# Bad Practice ❌
api_key = "gsk_1234567890abcdef"  # Exposed in code!

# Good Practice ✅
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file
api_key = os.environ["GROQ_API_KEY"]  # Get from environment
```

**Why .env File?**
```
✅ Keeps secrets out of code
✅ Different values per machine
✅ Added to .gitignore (not committed to GitHub)
✅ Easy to change without editing code
✅ Professional practice
```

### 3. Error Handling

```python
try:
    response = requests.get(url, timeout=15)
    if response.status_code == 200:
        return response.text
    else:
        return None  # Handle error gracefully
except requests.exceptions.Timeout:
    st.warning("Request timed out (>15 seconds)")
except Exception as e:
    st.error(f"Unexpected error: {e}")
```

**Timeout Protection:**
```
timeout=15
- If API takes longer than 15 seconds, stop waiting
- Prevent hanging forever
- User gets quick feedback
```

### 4. Session Caching

```python
# Streamlit feature: Caching results
@st.cache_data
def fetch_readme(owner, repo):
    # This function result is cached
    # If called again with same args, return cached result
    # No API call needed = Faster!
```

---

## API Integrations

### GitHub API Rate Limits

```
Public Access (No Auth):
- 60 requests per hour
- Per IP address
- Perfect for public repos

RepoLens uses 2 requests:
1. GET /repos/owner/repo/readme
2. GET /repos/owner/repo/git/trees/HEAD

So you can use RepoLens 30 times per hour
```

### Groq API Features

```
Free Tier:
✅ Unlimited API calls (no daily limit!)
✅ No credit card required
✅ Fast inference
✅ Llama 3.3-70b model access
✅ Production-ready

Rate Limits:
- Check Groq documentation
- Typically 30+ requests/minute
- Sufficient for most use cases
```

---

## Error Handling

### Common Errors & Solutions

```python
# Error 1: API Key Not Set
if "GROQ_API_KEY" not in os.environ:
    st.error("Set GROQ_API_KEY environment variable")
    st.stop()  # Stop execution

# Error 2: Invalid URL
parsed = parse_repo(repo_url)
if not parsed:
    st.error("Invalid GitHub URL format")
    st.stop()

# Error 3: Repo Not Found
readme = fetch_readme(owner, repo)
if not readme:
    st.warning("Could not find README (repo might be private)")
    # Show alternative: just the file list

# Error 4: API Failure
try:
    summary = summarize_repo(readme, files, level)
except Exception as e:
    st.warning(f"Could not generate summary: {e}")
    st.markdown("Here's the raw README instead:")
    st.markdown(readme[:3000])
```

---

## Performance Optimization

### Current Optimizations

```python
# 1. Limit README size
readme[:8000]  # Only use first 8000 characters
# Why? Saves API tokens (= faster + cheaper)

# 2. Limit files
file_listing = "\n".join(files[:60])
# Why? Don't overwhelm AI with info

# 3. Temperature setting
temperature=0.3  # Lower = more predictable
# Why? Faster inference + consistent results

# 4. Caching with Streamlit
@st.cache_data
# Reusing recent results = instant display
```

### Future Optimizations

```
Possible improvements:
- Cache summaries in database
- Batch process multiple repos
- Implement streaming responses
- Use smaller models for small repos
- Load balancing between APIs
```

---

## Summary

### What We Built:

```
┌─────────────────────────────────────────────────────┐
│                  REPOLENS                           │
├─────────────────────────────────────────────────────┤
│ Frontend: Streamlit (web interface)                 │
│ Backend: Python (logic)                             │
│ API 1: GitHub (fetch repo data)                     │
│ API 2: Groq (AI summarization)                      │
│ Database: None (stateless)                          │
│ Deployment: Any Python-capable server               │
└─────────────────────────────────────────────────────┘
```

### Key Achievements:

✅ **Fully functional app** (5 components working together)  
✅ **Easy to understand** (beginner-friendly code)  
✅ **Free to use** (no paid APIs)  
✅ **Fast** (2-5 seconds per summary)  
✅ **Detailed results** (12 sections, 2000+ words)  
✅ **Error handling** (graceful failures)  
✅ **Professional quality** (production-ready)  

---

**Now you understand every part of RepoLens!** 🎉
