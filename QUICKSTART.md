# Quick Start Guide ⚡

Get RepoLens running in 5 minutes!

## TL;DR (For Experienced Developers)

```bash
# Clone & setup
git clone https://github.com/akhil13algo/RepoLens.git
cd RepoLens
python3 -m venv venv && source venv/bin/activate

# Install & configure
pip install -r requirements.txt
echo "GROQ_API_KEY=gsk_your_key_here" > .env

# Get Groq key: https://console.groq.com (free, 2 min signup)

# Run
streamlit run app.py

# Open browser: http://localhost:8501
```

---

## Step-by-Step (For Everyone)

### 1. Prerequisites ✅

- Python 3.10+ installed
- Free Groq account (2 minutes to setup)

### 2. Clone Repository (1 min)

```bash
git clone https://github.com/akhil13algo/RepoLens.git
cd RepoLens
```

### 3. Setup Virtual Environment (30 sec)

```bash
# Create venv
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows
```

### 4. Install Dependencies (2 min)

```bash
pip install -r requirements.txt
```

### 5. Get API Key (2 min)

1. Go to https://console.groq.com
2. Sign up (email or OAuth)
3. Click "API Keys"
4. Create new key
5. Copy the key (starts with `gsk_`)

### 6. Configure App (30 sec)

```bash
# Copy template
cp .env.example .env

# Edit .env and paste your key
nano .env  # or use your favorite editor
```

Should look like:
```env
GROQ_API_KEY=gsk_paste_your_key_here_xxxxxxxxxxx
```

### 7. Run App (immediate)

```bash
streamlit run app.py
```

Browser opens automatically at **http://localhost:8501** ✅

---

## Usage (2 min)

1. **Select Level** → Pick from sidebar (beginner/intermediate/advanced)
2. **Paste URL** → Enter a GitHub repo URL
   - Example: `https://github.com/anthropics/claude-code`
3. **View Results** → Summary appears instantly!

---

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "command not found: python3" | Install Python from python.org |
| "venv not found" | Use `python -m venv venv` (not python3) |
| "(venv) not in prompt" | Run `source venv/bin/activate` again |
| "ModuleNotFoundError" | Activate venv, then `pip install -r requirements.txt` |
| "GROQ_API_KEY not set" | Restart app after editing `.env` |
| "Port 8501 in use" | Use `streamlit run app.py --server.port 8502` |
| "Could not fetch README" | Try a different public GitHub repo |

**Still stuck?** See [SETUP.md](SETUP.md) for detailed help.

---

## What's Happening

```
You paste GitHub URL
         ↓
App extracts owner/repo
         ↓
Fetches README + file list from GitHub API (free, no auth)
         ↓
Sends to Groq API with your prompt
         ↓
Groq's Llama 3.3-70b AI generates summary
         ↓
Results displayed in app!
```

**All free** 🎉

---

## Common Commands

```bash
# Stop the app
Ctrl + C

# Rerun the app
streamlit run app.py

# Use different port
streamlit run app.py --server.port 8502

# Deactivate venv
deactivate

# Reactivate venv
source venv/bin/activate

# Check installed packages
pip list

# Update dependencies
pip install -r requirements.txt --upgrade
```

---

## Environment Variables

Only 1 required:

```env
GROQ_API_KEY=gsk_your_api_key_here
```

Optional (for future features):
```env
OPENAI_API_KEY=sk_...
GEMINI_API_KEY=...
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

## File Structure

```
RepoLens/
├── app.py                    ← Main app to run
├── requirements.txt          ← Dependencies
├── .env                      ← Your config (private)
├── .env.example              ← Template
├── README.md                 ← Full documentation
├── SETUP.md                  ← Detailed setup guide
├── QUICKSTART.md             ← This file
├── CONTRIBUTING.md           ← How to contribute
├── CHANGELOG.md              ← Version history
└── venv/                     ← Virtual env (ignore)
```

---

## Next Steps

1. **Use the app** — Try a few repos
2. **Explore code** — Check [app.py](app.py) to see how it works
3. **Customize** — Edit prompts or add features
4. **Deploy** — Put it online at streamlit.io (free)
5. **Contribute** — See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Quick Links

- 🚀 [Groq API](https://console.groq.com) — Get free API key
- 📖 [Full Setup Guide](SETUP.md) — Detailed instructions
- 💡 [How to Contribute](CONTRIBUTING.md) — Help improve RepoLens
- 🐛 [Report Issues](https://github.com/akhil13algo/RepoLens/issues) — Found a bug?
- 📝 [Main Docs](README.md) — Complete documentation

---

## That's It! 🎉

You're ready to understand any GitHub repo in seconds.

Enjoy RepoLens! ✨
