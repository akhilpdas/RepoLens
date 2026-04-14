"""RepoLens memory — SQLite-backed persistent user memory.

Stores:
- Last repo used
- User skill level
- Preferred explanation style
- Previous questions asked (last 20)
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "repolens_memory.db")


def _get_connection() -> sqlite3.Connection:
    """Get a SQLite connection, creating tables if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            skill_level TEXT DEFAULT 'intermediate',
            explanation_style TEXT DEFAULT 'balanced',
            last_repo TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS question_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            question TEXT NOT NULL,
            user_level TEXT NOT NULL,
            answer_preview TEXT DEFAULT '',
            quality_score INTEGER DEFAULT 0,
            asked_at TEXT NOT NULL
        )
    """)
    # Ensure profile row exists
    conn.execute("""
        INSERT OR IGNORE INTO user_profile (id, skill_level, explanation_style, last_repo, updated_at)
        VALUES (1, 'intermediate', 'balanced', '', '')
    """)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------
def get_profile() -> dict:
    """Get the user's stored profile."""
    conn = _get_connection()
    row = conn.execute("SELECT skill_level, explanation_style, last_repo, updated_at FROM user_profile WHERE id=1").fetchone()
    conn.close()
    if row:
        return {
            "skill_level": row[0],
            "explanation_style": row[1],
            "last_repo": row[2],
            "updated_at": row[3],
        }
    return {"skill_level": "intermediate", "explanation_style": "balanced", "last_repo": "", "updated_at": ""}


def update_profile(skill_level: str = None, explanation_style: str = None, last_repo: str = None):
    """Update the user's profile."""
    conn = _get_connection()
    updates = []
    params = []
    if skill_level:
        updates.append("skill_level = ?")
        params.append(skill_level)
    if explanation_style:
        updates.append("explanation_style = ?")
        params.append(explanation_style)
    if last_repo:
        updates.append("last_repo = ?")
        params.append(last_repo)
    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        conn.execute(f"UPDATE user_profile SET {', '.join(updates)} WHERE id=1", params)
        conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Question History
# ---------------------------------------------------------------------------
def add_question(repo: str, question: str, user_level: str, answer_preview: str = "", quality_score: int = 0):
    """Record a question in history."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO question_history (repo, question, user_level, answer_preview, quality_score, asked_at) VALUES (?, ?, ?, ?, ?, ?)",
        (repo, question, user_level, answer_preview[:500], quality_score, datetime.now().isoformat()),
    )
    conn.commit()

    # Keep only last 20 questions
    conn.execute("""
        DELETE FROM question_history WHERE id NOT IN (
            SELECT id FROM question_history ORDER BY asked_at DESC LIMIT 20
        )
    """)
    conn.commit()
    conn.close()


def get_history(limit: int = 10) -> list[dict]:
    """Get recent question history."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT repo, question, user_level, answer_preview, quality_score, asked_at FROM question_history ORDER BY asked_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "repo": r[0],
            "question": r[1],
            "user_level": r[2],
            "answer_preview": r[3],
            "quality_score": r[4],
            "asked_at": r[5],
        }
        for r in rows
    ]


def get_repo_history(repo: str, limit: int = 5) -> list[dict]:
    """Get recent questions for a specific repo."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT question, user_level, answer_preview, quality_score, asked_at FROM question_history WHERE repo=? ORDER BY asked_at DESC LIMIT ?",
        (repo, limit),
    ).fetchall()
    conn.close()
    return [
        {
            "question": r[0],
            "user_level": r[1],
            "answer_preview": r[2],
            "quality_score": r[3],
            "asked_at": r[4],
        }
        for r in rows
    ]


def get_memory_context(repo: str, user_level: str) -> str:
    """Build a memory context string to inject into prompts.

    Helps the LLM personalize answers based on past interactions.
    """
    profile = get_profile()
    past = get_repo_history(repo, limit=3)

    parts = [f"User skill level: {user_level}"]
    parts.append(f"Explanation style preference: {profile['explanation_style']}")

    if profile["last_repo"] and profile["last_repo"] != repo:
        parts.append(f"Previously explored: {profile['last_repo']}")

    if past:
        parts.append("Previous questions about this repo:")
        for q in past:
            parts.append(f"  - \"{q['question']}\" (level: {q['user_level']}, score: {q['quality_score']})")

    return "\n".join(parts)
