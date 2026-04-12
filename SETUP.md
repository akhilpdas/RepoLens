# RepoLens Setup Guide 🚀

Complete step-by-step guide to get RepoLens running on your machine.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the App](#running-the-app)
5. [Troubleshooting](#troubleshooting)
6. [Next Steps](#next-steps)

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** — Check with `python --version` or `python3 --version`
- **pip** — Python package manager (usually comes with Python)
- **Git** (optional but recommended) — To clone the repository
- **Groq Account** (free) — For API access

### Verify Python Installation

```bash
# Check Python version
python --version

# Check pip is installed
pip --version
```

If you don't have Python, download it from [python.org](https://www.python.org/downloads)

---

## Installation

### Step 1: Clone the Repository

**Option A: Using Git (Recommended)**

```bash
git clone https://github.com/akhil13algo/RepoLens.git
cd RepoLens
```

**Option B: Download ZIP**

1. Go to https://github.com/akhil13algo/RepoLens
2. Click "Code" → "Download ZIP"
3. Unzip and open folder in terminal

### Step 2: Create Virtual Environment

A virtual environment isolates project dependencies from your system Python.

**On macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (Command Prompt):**

```cmd
python -m venv venv
venv\Scripts\activate
```

**On Windows (PowerShell):**

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

✅ **You should see `(venv)` in your terminal prompt**

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `streamlit` — Web UI framework
- `groq` — Groq API client
- `requests` — HTTP library
- `python-dotenv` — Environment variable management
- All other dependencies listed in requirements.txt

⏱️ This may take 2-5 minutes on first install.

---

## Configuration

### Step 1: Create Environment File

```bash
# Copy the example file
cp .env.example .env
```

On Windows (Command Prompt):
```cmd
copy .env.example .env
```

### Step 2: Get Groq API Key

1. **Sign Up**: Go to https://console.groq.com
2. **Create Account**: Use email or OAuth
3. **Navigate to API Keys**: Click on your profile → "API Keys"
4. **Create New Key**: Click "Create New Secret Key"
5. **Copy Key**: Copy the key starting with `gsk_`

### Step 3: Add API Key to .env

Edit `.env` file with your text editor:

```env
GROQ_API_KEY=gsk_paste_your_key_here
```

**⚠️ Important**: 
- Never share your API key
- Never commit `.env` to Git (it's in `.gitignore`)
- Keep it private

### Verify Configuration

```bash
# This should print your API key (don't share output)
echo $GROQ_API_KEY
```

---

## Running the App

### Start Streamlit

Make sure virtual environment is activated, then run:

```bash
streamlit run app.py
```

You should see:

```
Collecting usage statistics. To deactivate, set browser.gatherUsageStats to false.

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

### Access the App

Open your browser and go to: **http://localhost:8501**

### Using the App

1. **Select Experience Level** — Choose from beginner, intermediate, or advanced in the sidebar
2. **Paste Repo URL** — Enter a public GitHub repo URL
   - Example: `https://github.com/anthropics/claude-code`
3. **View Summary** — AI-generated summary appears on the left, file structure on the right

### Stop the App

Press `Ctrl + C` in the terminal to stop the server.

---

## Troubleshooting

### Issue: "Command not found: python3"

**Solution**: 
- Make sure Python is installed: https://www.python.org/downloads
- Try `python` instead of `python3`
- On Windows, use `python --version`

### Issue: "No module named 'venv'"

**Solution**: Install venv package
```bash
# Ubuntu/Debian
sudo apt-get install python3-venv

# macOS (should be built-in)
python3 -m venv venv
```

### Issue: "Permission denied" when activating venv

**Solution**: Fix permissions
```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

### Issue: "ModuleNotFoundError" when running app

**Solution**: Make sure virtual environment is activated
```bash
# Check for (venv) in prompt
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Then install dependencies
pip install -r requirements.txt
```

### Issue: "GROQ_API_KEY not set"

**Solution**: 
1. Verify `.env` file exists in project root
2. Check `GROQ_API_KEY=` line is present
3. Restart the app after editing `.env`
4. Or set as environment variable:
   ```bash
   export GROQ_API_KEY="gsk_your_key_here"
   streamlit run app.py
   ```

### Issue: "Could not fetch README"

**Possible causes**:
- Repository is private (use public repos only)
- No README.md file in the repo
- Invalid GitHub URL
- GitHub API rate limit exceeded (60 req/hour for public access)

**Solution**: Try a different public repository

### Issue: "Port 8501 already in use"

**Solution**: Use a different port
```bash
streamlit run app.py --server.port 8502
```

Or kill the existing process:
```bash
# macOS/Linux
lsof -ti:8501 | xargs kill -9

# Windows
netstat -ano | findstr :8501
taskkill /PID <PID> /F
```

### Issue: "API Error" or "Quota Exceeded"

**Solution**: 
- Wait a few minutes
- Check Groq console: https://console.groq.com
- Ensure you have free tier access
- Try again

---

## Next Steps

### 1. Explore the Code

- **[app.py](app.py)** — Main application logic
- **[.claude/workspace.md](.claude/workspace.md)** — Project structure

### 2. Customize

Edit `app.py` to:
- Change model (`llama-3.3-70b-versatile`)
- Adjust summary format
- Add new features

### 3. Deploy

Host it online (free options):
- **Streamlit Cloud** — https://share.streamlit.io
- **Heroku** — https://www.heroku.com (paid for always-on)
- **Replit** — https://replit.com
- **Railway** — https://railway.app

See [README.md](README.md#deployment) for deployment guides.

### 4. Contribute

Found a bug? Have an idea? 
- Open an issue: https://github.com/akhil13algo/RepoLens/issues
- Submit a PR: https://github.com/akhil13algo/RepoLens/pulls

---

## Need Help?

- 📖 **Streamlit Docs**: https://docs.streamlit.io
- 🚀 **Groq API Docs**: https://console.groq.com/docs
- 🐙 **GitHub Issues**: https://github.com/akhil13algo/RepoLens/issues
- 💬 **GitHub Discussions**: https://github.com/akhil13algo/RepoLens/discussions

---

**Congratulations! 🎉 You're all set to use RepoLens!**

If you encounter any issues, check the troubleshooting section or open an issue on GitHub.
