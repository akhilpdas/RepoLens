# Changelog

All notable changes to RepoLens will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Multi-agent workflow (planner → researcher → reviewer)
- RAG with ChromaDB for in-depth analysis
- Persistent memory with SQLite
- Interactive Q&A beyond summaries
- Code snippet extraction
- Evaluation benchmarks
- OpenTelemetry tracing

---

## [1.0.0] - 2025-04-12

### Added
- Initial release of RepoLens
- AI-powered GitHub repository summarization using Groq (Llama 3.3-70b)
- Experience-level tailored explanations (beginner, intermediate, advanced)
- Structured summaries including:
  - What the repo does
  - Key files to read first
  - How to run it
  - Architecture overview
  - Good first contribution ideas
- Streamlit web interface with sidebar and multi-column layout
- GitHub API integration for README and file tree fetching
- Environment variable configuration with `.env` support
- Error handling and fallback display of raw README
- Virtual environment setup
- Comprehensive documentation

### Technical Details
- Built with Python 3.13
- Streamlit 1.56.0 for UI
- Groq API client 1.1.2
- LangGraph and ChromaDB integration (for future features)
- 130+ total dependencies with exact version pinning

### Features
- ✅ Fetch public GitHub repos (no auth required)
- ✅ Parse README.md content
- ✅ Extract file/folder structure
- ✅ Generate AI summaries with Groq
- ✅ Experience level selection
- ✅ Error handling with fallbacks
- ✅ Clean, responsive web UI
- ✅ Free tier API support

### Documentation
- README.md - Main documentation
- SETUP.md - Step-by-step setup guide
- CONTRIBUTING.md - Contribution guidelines
- .env.example - Environment template
- .claude/workspace.md - Project workspace info
- requirements.txt - Frozen dependencies

### Known Limitations
- Private repositories not supported
- Single repo summarization per request
- No caching of results
- GitHub API rate limit: 60 requests/hour (unauthenticated)
- Groq free tier subject to rate limits (see docs)

---

## Version History

### Planning for Future Releases

#### v1.1.0 (Planned)
- User authentication for API keys
- Caching layer for frequently requested repos
- Export summaries as Markdown
- Improved error messages
- Support for GitHub authentication token

#### v2.0.0 (Planned)
- Multi-agent architecture
- RAG with ChromaDB
- Database persistence
- Advanced filtering and search
- Batch processing
- API endpoint

---

## Migration Guides

### Upgrading from v0.x to v1.0.0

If you were using an earlier version:

1. Update code:
   ```bash
   git pull origin main
   ```

2. Update dependencies:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt --upgrade
   ```

3. Update environment file:
   ```bash
   cp .env.example .env
   # Add your GROQ_API_KEY
   ```

4. Restart the app:
   ```bash
   streamlit run app.py
   ```

---

## Deprecations

None yet (v1.0.0 is the initial release).

---

## Security

### Reporting Security Issues

Please do NOT open public issues for security vulnerabilities.

Email security concerns to: [security contact - to be added]

### Security Considerations

- Never commit `.env` file to Git
- API keys should not be shared
- Only uses public GitHub API (no private repo access in v1.0.0)
- Groq API calls are encrypted in transit

---

## Performance

### Improvements Over Time

- v1.0.0: Initial release, baseline performance

### Benchmarks

- Average summary generation: 2-5 seconds
- GitHub API call: < 1 second
- Streamlit app startup: < 3 seconds

---

## Contributors

### v1.0.0
- **Akhil** - Initial development and documentation

---

## References

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Python Release Cycle](https://devguide.python.org/versions/)

---

**Last Updated**: 2025-04-12
**Current Version**: 1.0.0
**Status**: Active Development
