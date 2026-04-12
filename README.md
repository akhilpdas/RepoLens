# RepoLens 🔍

An agentic onboarding assistant for any GitHub repository. Simply paste a public repo URL and get a structured, AI-powered summary tailored to your experience level (beginner, intermediate, or advanced).

Perfect for quickly understanding new codebases, exploring open-source projects, or onboarding new team members.

## ✨ Features

- 📂 **Fetches repo metadata** — Pulls README and file tree from any public GitHub repository
- 🤖 **AI-powered summaries** — Generates structured insights using Groq (Llama 3.3-70b)
- 👥 **Experience-level tailored** — Adapts explanations for beginner, intermediate, or advanced developers
- 🚀 **Fast & free** — No API quota limits on the free Groq tier
- 💾 **View file structure** — See top-level files and directories at a glance
- 🎨 **Clean UI** — Built with Streamlit for a smooth user experience

## 📋 What You Get

For any repo, RepoLens generates:

1. **What this repo does** — One-paragraph summary
2. **Key files to read first** — Up to 5 files with explanations
3. **How to run it** — Step-by-step instructions extracted from README
4. **Architecture overview** — Main components and layers
5. **Good first contribution ideas** — 2-3 beginner-friendly tasks

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **UI Framework** | Streamlit 1.56.0 |
| **AI Model** | Groq (Llama 3.3-70b) |
| **API Client** | Groq Python SDK 1.1.2 |
| **GitHub Integration** | GitHub REST API |
| **Environment** | Python 3.13, pip |
| **Additional** | LangGraph, ChromaDB, OpenAI SDK |

## 📦 Prerequisites

- **Python** 3.10 or higher
- **pip** (Python package manager)
- **Groq API Key** (free at [console.groq.com](https://console.groq.com))
- **Git** (optional, for cloning)
- **Internet connection** (to fetch repos and call APIs)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/akhil13algo/RepoLens.git
cd RepoLens
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Groq API Key

1. Sign up for free at [console.groq.com](https://console.groq.com)
2. Generate an API key from your dashboard
3. Copy the key (starts with `gsk_`)

### 5. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:

```env
GROQ_API_KEY=gsk_your_actual_key_here
```

Or set it as an environment variable:

```bash
export GROQ_API_KEY="gsk_your_actual_key_here"
```

### 6. Run the App

```bash
streamlit run app.py
```

The app will open in your browser at **http://localhost:8501** 🎉

## 📖 Usage

1. **Select your experience level** in the sidebar (beginner, intermediate, advanced)
2. **Paste a GitHub repo URL** in the input field
   - Example: `https://github.com/anthropics/claude-code`
   - Must be a public repository
3. **View the results**:
   - Left column: AI-generated summary
   - Right column: File structure preview

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ Yes | Your Groq API key (get it free at [console.groq.com](https://console.groq.com)) |

### Streamlit Config (Optional)

Create `~/.streamlit/config.toml` for custom settings:

```toml
[client]
showErrorDetails = true

[logger]
level = "info"

[server]
headless = true
port = 8501
```

## 📁 Project Structure

```
RepoLens/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies (pip freeze)
├── .env.example          # Environment variables template
├── .env                  # Environment variables (local, gitignored)
├── README.md             # This file
├── venv/                 # Virtual environment (gitignored)
└── .claude/              # Claude Code workspace config
    ├── workspace.md      # Project workspace documentation
    └── settings.local.json # Claude Code permissions
```

## 🔍 How It Works

1. **URL Parsing** — Extracts owner/repo from GitHub URL
2. **Metadata Fetching** — Calls GitHub REST API to get README and file tree
3. **AI Summary** — Sends README + file list to Groq (Llama 3.3-70b)
4. **Formatting** — Displays structured summary with Streamlit

### API Calls Made

- **GitHub API**: No auth required for public repos
- **Groq API**: Free tier (no daily quota limits)

## 🆓 Free Tier Limits

**Groq Free Tier**:
- ✅ Unlimited API calls
- ✅ No daily quota
- ✅ No credit card required
- ⚠️ Rate limit: Check Groq docs for per-minute limits

**GitHub API** (unauthenticated):
- ✅ 60 requests per hour
- ✅ No auth token needed for public repos

## 🐛 Troubleshooting

### "GROQ_API_KEY not set"

**Solution**: Add your API key to `.env`:

```bash
echo "GROQ_API_KEY=gsk_your_key_here" > .env
```

Or set environment variable:

```bash
export GROQ_API_KEY="gsk_your_key_here"
```

### "Could not fetch README"

**Possible causes**:
- Repository doesn't exist or is private
- No README.md file in the repo
- GitHub API rate limit exceeded

**Solution**: Try a different public repository

### "API Error / Quota Exceeded"

**Solution**: Wait a few minutes or check your Groq account at [console.groq.com](https://console.groq.com)

### Port 8501 Already in Use

```bash
# Kill existing Streamlit process
pkill -f "streamlit run"

# Or use a different port
streamlit run app.py --server.port 8502
```

## 🚀 Deployment

### Streamlit Cloud (Recommended)

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app" → Select your repo
4. Add `GROQ_API_KEY` in Secrets section
5. Deploy! 🎉

### Docker

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .
COPY .env .

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:

```bash
docker build -t repolens .
docker run -p 8501:8501 -e GROQ_API_KEY="your_key" repolens
```

## 🛣️ Roadmap

- [ ] Multi-agent workflow (planner → researcher → reviewer)
- [ ] RAG with ChromaDB for in-depth analysis
- [ ] Persistent memory with SQLite
- [ ] Interactive Q&A beyond summaries
- [ ] Code snippet extraction and explanation
- [ ] Evaluation benchmarks
- [ ] OpenTelemetry tracing and observability
- [ ] Support for private repositories (with auth)
- [ ] Batch processing multiple repos
- [ ] Export summaries as markdown/PDF

## 📚 Development

### Install Development Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Run Tests (Future)

```bash
pytest tests/
```

### Code Style

Following PEP 8 conventions with type hints.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -m "Add your feature"`)
4. Push to branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 🙋 Support & Feedback

- **Issues**: Report bugs on [GitHub Issues](https://github.com/akhil13algo/RepoLens/issues)
- **Discussions**: Join conversations on GitHub Discussions
- **Email**: Contact via GitHub profile

## 🎓 Learning Resources

- [Streamlit Docs](https://docs.streamlit.io)
- [Groq API Docs](https://console.groq.com/docs)
- [GitHub REST API](https://docs.github.com/en/rest)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph)
- [ChromaDB Guide](https://docs.trychroma.com)

## 🌟 Acknowledgments

- **Streamlit** — For the amazing web framework
- **Groq** — For fast, free LLM inference
- **GitHub** — For the REST API
- **LangChain** — For LangGraph and ecosystem
- **Anthropic** — For Claude and insights

---

**Made with ❤️ by Akhil**

Give this project a ⭐ if you found it helpful!
