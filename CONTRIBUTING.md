# Contributing to RepoLens 🤝

Thank you for your interest in contributing to RepoLens! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and inclusive. We welcome contributions from everyone, regardless of experience level.

## How to Contribute

### Reporting Bugs

Found a bug? Help us fix it!

1. **Search existing issues** — Check if it's already reported
2. **Create a new issue** with:
   - Clear title: "Bug: [description]"
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots (if applicable)
   - Environment (OS, Python version, etc.)

Example:
```
Bug: App crashes when pasting GitHub URL without https://

Steps to reproduce:
1. Open app at http://localhost:8501
2. Paste "github.com/owner/repo" in URL field
3. Click submit

Expected: URL is auto-corrected to "https://github.com/owner/repo"
Actual: App crashes with error

Environment:
- OS: macOS 14.2
- Python: 3.13.0
- Streamlit: 1.56.0
```

### Suggesting Features

Have a great idea? We'd love to hear it!

1. **Search existing discussions** — Check if it's been suggested
2. **Create a feature request** with:
   - Clear title: "Feature: [description]"
   - Problem it solves
   - Proposed solution
   - Alternative approaches

Example:
```
Feature: Export summaries as Markdown

Problem: Users want to save repo summaries for later reference

Proposed Solution:
- Add "Export as Markdown" button
- Generate formatted markdown with all summary sections
- Allow download as .md file

Benefits:
- Easy sharing between team members
- Can be committed to knowledge base
- Integrates with docs systems
```

### Submitting Pull Requests

#### Setup Development Environment

```bash
# Fork the repo on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/RepoLens.git
cd RepoLens

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create feature branch
git checkout -b feature/my-feature
```

#### Make Your Changes

1. **Keep commits atomic** — One feature/fix per commit
2. **Write clear commit messages**:
   ```
   feat: add export to markdown functionality
   
   - Add "Export" button to summary section
   - Generate formatted markdown output
   - Support download as .md file
   ```

3. **Follow code style**:
   - PEP 8 conventions
   - Use type hints where possible
   - Clear variable/function names
   - Comments for complex logic

4. **Test your changes**:
   ```bash
   # Run the app locally
   streamlit run app.py
   
   # Test with different repos
   # Test with different experience levels
   # Check error handling
   ```

#### Submit Pull Request

```bash
# Push to your fork
git push origin feature/my-feature

# Go to GitHub and create Pull Request
```

**PR Template** (fill out when creating):
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Enhancement
- [ ] Documentation

## Related Issues
Closes #123

## Testing
How was this tested?

## Screenshots
If applicable, add screenshots

## Checklist
- [ ] Code follows PEP 8 style
- [ ] Comments added for complex logic
- [ ] Tested locally
- [ ] No breaking changes
- [ ] Updated documentation
```

---

## Development Workflow

### Project Structure

```
RepoLens/
├── app.py              # Main application
├── requirements.txt    # Dependencies
├── .env.example       # Environment template
├── README.md          # Main documentation
├── SETUP.md           # Setup guide
├── CONTRIBUTING.md    # This file
└── .claude/           # Claude Code config
```

### Key Files

- **app.py** — Main Streamlit app
  - `parse_repo()` — Extract owner/repo from URL
  - `fetch_readme()` — Get README from GitHub API
  - `fetch_repo_tree()` — Get file listing
  - `summarize_repo()` — Call Groq API for summary

### Adding Features

When adding a feature:

1. **Create a function** with clear purpose
2. **Add docstring** explaining what it does
3. **Use type hints** for parameters and return values
4. **Handle errors** gracefully
5. **Test thoroughly** with different inputs

Example:
```python
def export_to_markdown(summary: str, repo_name: str) -> str:
    """Export summary as formatted markdown.
    
    Args:
        summary: The AI-generated summary
        repo_name: Repository name for title
        
    Returns:
        Formatted markdown string
        
    Raises:
        ValueError: If summary or repo_name is empty
    """
    if not summary or not repo_name:
        raise ValueError("Summary and repo_name cannot be empty")
    
    markdown = f"# {repo_name}\n\n{summary}"
    return markdown
```

---

## Code Standards

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints: `def func(x: str) -> int:`
- Max line length: 100 characters
- Use f-strings: `f"Hello {name}"`

### Naming Conventions

- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`
- Private: `_leading_underscore`

### Comments

```python
# Good: Explains WHY
if temperature > 0.9:
    # Increase temperature to encourage diversity
    temperature = 0.95

# Avoid: Explains WHAT (code is obvious)
if temperature > 0.9:
    temperature = 0.95
```

---

## Testing

### Manual Testing

```bash
# Test with different repos
- https://github.com/anthropics/claude-code
- https://github.com/torvalds/linux
- https://github.com/streamlit/streamlit

# Test with different experience levels
- Beginner
- Intermediate
- Advanced

# Test error cases
- Invalid URL
- Private repo
- Repo without README
- API timeout
```

### Future: Automated Tests

```bash
# Once tests are added
pytest tests/
pytest tests/ -v  # Verbose
pytest tests/ --cov  # With coverage
```

---

## Documentation

### README Updates

If changing features, update [README.md](README.md):
- Feature list
- Usage instructions
- Troubleshooting (if applicable)
- Tech stack (if dependencies changed)

### Code Documentation

Add docstrings to all functions:

```python
def summarize_repo(readme: str, files: list[str], user_level: str) -> str:
    """Generate AI summary of repository.
    
    Uses Groq API to create structured summary tailored to
    the user's experience level (beginner/intermediate/advanced).
    
    Args:
        readme: Full text of README.md file
        files: List of top-level filenames/directories
        user_level: User experience level (controls explanation depth)
        
    Returns:
        Structured markdown summary with sections:
        - What this repo does
        - Key files to read
        - How to run it
        - Architecture
        - Good first contributions
        
    Raises:
        ValueError: If readme or files is empty
        APIError: If Groq API call fails
        
    Example:
        >>> summary = summarize_repo(
        ...     readme="# MyProject\\nDoes cool stuff",
        ...     files=["main.py", "utils.py", "README.md"],
        ...     user_level="beginner"
        ... )
    """
```

---

## Commit Message Guidelines

Good commit messages make history readable:

### Format

```
<type>: <subject>

<body>

<footer>
```

### Types

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Code style (no logic change)
- `refactor:` Refactoring code
- `perf:` Performance improvement
- `test:` Adding tests
- `chore:` Build, deps, tooling

### Examples

```
feat: add markdown export functionality

- Add export button to summary section
- Generate properly formatted markdown
- Support file download

Closes #45

---

fix: handle repos without README gracefully

Previously crashed when repo had no README.
Now displays helpful message and shows file structure.

Fixes #32

---

docs: update setup guide for Windows users

Added Windows-specific virtual environment activation commands.
```

---

## Pull Request Review Process

1. **Code Review** — Maintainer reviews code for quality
2. **Testing** — Changes are tested in various scenarios
3. **CI Checks** — Automated checks run (when implemented)
4. **Feedback** — Suggestions may be requested
5. **Approval** — Once approved, PR is merged

### During Review

- Be open to feedback
- Respond to comments
- Make requested changes
- Re-request review when ready

---

## Release Process

When releasing a new version:

1. Update version in `pyproject.toml` (when added)
2. Update [CHANGELOG.md](CHANGELOG.md) (when added)
3. Create GitHub release with notes
4. Tag commit with version: `v1.2.3`

---

## Areas for Contribution

### High Priority

- [ ] Add unit tests for core functions
- [ ] Improve error messages
- [ ] Add support for private repos (with token)
- [ ] Performance optimization

### Medium Priority

- [ ] Export to PDF
- [ ] Batch process multiple repos
- [ ] Add caching for frequently requested repos
- [ ] Support for different summarization styles

### Low Priority

- [ ] Dark mode theme
- [ ] Internationalization (i18n)
- [ ] Additional AI models
- [ ] Browser extension

---

## Getting Help

- **Questions?** Open a discussion: https://github.com/akhil13algo/RepoLens/discussions
- **Need guidance?** Comment on an issue
- **Stuck?** Reach out in issues or discussions

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License (same as the project).

---

**Thank you for contributing to RepoLens! 🙏**

Your contributions help make this project better for everyone.
