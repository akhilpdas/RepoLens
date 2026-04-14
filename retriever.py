"""RepoLens retriever — RAG module using ChromaDB for chunk-based retrieval.

Indexes: README, docs/, config files, package manifests, and selected source files.
Every answer can cite retrieved chunks with source file + line info.
"""

import os
import hashlib
import requests
import base64
import chromadb
from chromadb.config import Settings

# Files/patterns to auto-index (beyond README)
CONFIG_PATTERNS = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod", "Gemfile", "pom.xml", "build.gradle",
    "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "requirements.txt", "tsconfig.json", "webpack.config.js",
    "vite.config.ts", "vite.config.js",
}

DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}

# Source extensions to selectively index (entry points only)
SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb"}

# Max files to index per category
MAX_DOC_FILES = 10
MAX_SOURCE_FILES = 5


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def _fetch_file_content(owner: str, repo: str, path: str):
    """Fetch a single file's content from GitHub."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    resp = requests.get(api_url, timeout=15)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("type") != "file":
        return None
    try:
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return None


def _fetch_tree_recursive(owner: str, repo: str) -> list[dict]:
    """Fetch the full recursive file tree."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    resp = requests.get(api_url, timeout=20)
    if resp.status_code != 200:
        return []
    return resp.json().get("tree", [])


def _select_files_to_index(tree: list[dict]) -> list[str]:
    """Select which files to index based on our rules."""
    files_to_index = []
    doc_count = 0
    source_count = 0

    for item in tree:
        if item["type"] != "blob":
            continue

        path = item["path"]
        name = os.path.basename(path)
        _, ext = os.path.splitext(name.lower())

        # Always index: README variants
        if name.lower().startswith("readme"):
            files_to_index.append(path)
            continue

        # Always index: config/manifest files
        if name in CONFIG_PATTERNS:
            files_to_index.append(path)
            continue

        # Index: docs/ folder files
        if ("docs/" in path or "doc/" in path) and ext in DOC_EXTENSIONS:
            if doc_count < MAX_DOC_FILES:
                files_to_index.append(path)
                doc_count += 1
            continue

        # Index: top-level doc files
        if "/" not in path and ext in DOC_EXTENSIONS:
            files_to_index.append(path)
            continue

        # Selectively index: entry-point source files
        if ext in SOURCE_EXTENSIONS and source_count < MAX_SOURCE_FILES:
            # Prefer files that look like entry points
            entry_names = {"main", "app", "index", "server", "cli", "__main__", "manage"}
            stem = os.path.splitext(name)[0].lower()
            if stem in entry_names or "/" not in path:
                files_to_index.append(path)
                source_count += 1

    return files_to_index


class RepoRetriever:
    """Manages a ChromaDB collection for a single repo's indexed chunks."""

    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.collection_name = f"{owner}_{repo}".replace("-", "_").replace(".", "_")[:60]
        self.client = chromadb.Client(Settings(anonymized_telemetry=False))
        self.collection = None
        self.indexed_files: list[str] = []
        self.chunk_count = 0

    def index(self, status_callback=None) -> dict:
        """Index the repo's key files into ChromaDB.

        Returns:
            dict with indexing stats.
        """
        # Get or create collection (fresh each time for simplicity)
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Fetch tree and select files
        if status_callback:
            status_callback("Fetching file tree...")
        tree = _fetch_tree_recursive(self.owner, self.repo)
        files_to_index = _select_files_to_index(tree)

        if status_callback:
            status_callback(f"Indexing {len(files_to_index)} files...")

        all_docs = []
        all_metas = []
        all_ids = []

        for path in files_to_index:
            if status_callback:
                status_callback(f"Reading {path}...")

            content = _fetch_file_content(self.owner, self.repo, path)
            if not content:
                continue

            self.indexed_files.append(path)
            chunks = _chunk_text(content)

            for i, chunk in enumerate(chunks):
                doc_id = hashlib.md5(f"{path}:{i}".encode()).hexdigest()
                all_docs.append(chunk)
                all_metas.append({"source": path, "chunk_index": i, "repo": f"{self.owner}/{self.repo}"})
                all_ids.append(doc_id)

        # Batch add to ChromaDB
        if all_docs:
            # ChromaDB has batch size limits, add in batches of 100
            for batch_start in range(0, len(all_docs), 100):
                batch_end = batch_start + 100
                self.collection.add(
                    documents=all_docs[batch_start:batch_end],
                    metadatas=all_metas[batch_start:batch_end],
                    ids=all_ids[batch_start:batch_end],
                )

        self.chunk_count = len(all_docs)

        return {
            "files_indexed": len(self.indexed_files),
            "chunks_created": self.chunk_count,
            "files": self.indexed_files,
        }

    def query(self, question: str, n_results: int = 5) -> list[dict]:
        """Retrieve the most relevant chunks for a question.

        Returns:
            List of dicts with 'content', 'source', 'chunk_index', 'distance'.
        """
        if not self.collection or self.chunk_count == 0:
            return []

        results = self.collection.query(
            query_texts=[question],
            n_results=min(n_results, self.chunk_count),
        )

        chunks = []
        for i in range(len(results["documents"][0])):
            chunks.append({
                "content": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "chunk_index": results["metadatas"][0][i]["chunk_index"],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return chunks

    def get_context_string(self, question: str, n_results: int = 5) -> str:
        """Get a formatted string of retrieved chunks for injection into prompts."""
        chunks = self.query(question, n_results)
        if not chunks:
            return "(No relevant chunks found)"

        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"[Chunk {i}] Source: {chunk['source']} (chunk #{chunk['chunk_index']})\n"
                f"{chunk['content'][:500]}"
            )
        return "\n\n---\n\n".join(parts)
