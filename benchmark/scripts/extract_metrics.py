#!/usr/bin/env python3
"""
Extract metrics from OpenCode's SQLite database.

OpenCode stores session data in ~/.opencode/opencode.db including:
- Token usage (prompt_tokens, completion_tokens)
- Cost calculations
- Message history with tool calls
"""

import sqlite3
import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class SessionMetrics:
    """Metrics extracted from an OpenCode session."""
    session_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    tool_calls: int
    message_count: int
    model: str
    created_at: datetime
    finished_at: Optional[datetime]


def get_db_path(config_path: Optional[str] = None) -> Path:
    """Get the OpenCode database path."""
    if config_path:
        return Path(os.path.expanduser(config_path))

    # Default location
    return Path.home() / ".opencode" / "opencode.db"


def get_latest_session_id(db_path: Path) -> Optional[str]:
    """Get the most recent session ID from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id FROM sessions
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def extract_session_metrics(db_path: Path, session_id: str) -> Optional[SessionMetrics]:
    """
    Extract metrics for a specific session from OpenCode's database.

    Args:
        db_path: Path to opencode.db
        session_id: The session ID to extract metrics for

    Returns:
        SessionMetrics object with extracted data, or None if session not found
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Get session info
        cursor.execute("""
            SELECT id, model, prompt_tokens, completion_tokens, cost,
                   created_at, updated_at
            FROM sessions
            WHERE id = ?
        """, (session_id,))

        session_row = cursor.fetchone()
        if not session_row:
            return None

        # Count messages and tool calls
        cursor.execute("""
            SELECT COUNT(*) as message_count
            FROM messages
            WHERE session_id = ?
        """, (session_id,))
        message_count = cursor.fetchone()["message_count"]

        # Count tool calls from message content
        cursor.execute("""
            SELECT content
            FROM messages
            WHERE session_id = ? AND role = 'assistant'
        """, (session_id,))

        tool_calls = 0
        for row in cursor.fetchall():
            content = row["content"]
            if content:
                # Try to parse as JSON to count tool_use blocks
                try:
                    content_data = json.loads(content)
                    if isinstance(content_data, list):
                        tool_calls += sum(
                            1 for item in content_data
                            if isinstance(item, dict) and item.get("type") == "tool_use"
                        )
                except (json.JSONDecodeError, TypeError):
                    # Count tool call markers in text
                    tool_calls += content.count("tool_use")

        # Parse timestamps
        created_at = datetime.fromisoformat(session_row["created_at"].replace("Z", "+00:00"))
        finished_at = None
        if session_row["updated_at"]:
            finished_at = datetime.fromisoformat(session_row["updated_at"].replace("Z", "+00:00"))

        prompt_tokens = session_row["prompt_tokens"] or 0
        completion_tokens = session_row["completion_tokens"] or 0

        return SessionMetrics(
            session_id=session_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=session_row["cost"] or 0.0,
            tool_calls=tool_calls,
            message_count=message_count,
            model=session_row["model"] or "unknown",
            created_at=created_at,
            finished_at=finished_at
        )

    finally:
        conn.close()


def get_sessions_in_timerange(
    db_path: Path,
    start_time: datetime,
    end_time: datetime
) -> List[str]:
    """Get all session IDs created within a time range."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id FROM sessions
            WHERE created_at >= ? AND created_at <= ?
            ORDER BY created_at ASC
        """, (start_time.isoformat(), end_time.isoformat()))

        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def extract_answer_from_session(db_path: Path, session_id: str) -> Optional[str]:
    """
    Extract the final assistant answer from a session.

    Args:
        db_path: Path to opencode.db
        session_id: The session ID

    Returns:
        The assistant's final text response, or None
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Get the last assistant message
        cursor.execute("""
            SELECT content
            FROM messages
            WHERE session_id = ? AND role = 'assistant'
            ORDER BY created_at DESC
            LIMIT 1
        """, (session_id,))

        row = cursor.fetchone()
        if not row or not row["content"]:
            return None

        content = row["content"]

        # Try to extract text from structured content
        try:
            content_data = json.loads(content)
            if isinstance(content_data, list):
                text_parts = [
                    item.get("text", "")
                    for item in content_data
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                return "\n".join(text_parts) if text_parts else content
            elif isinstance(content_data, dict):
                return content_data.get("text", content)
        except (json.JSONDecodeError, TypeError):
            pass

        return content

    finally:
        conn.close()


def metrics_to_dict(metrics: SessionMetrics) -> Dict[str, Any]:
    """Convert SessionMetrics to a dictionary for JSON serialization."""
    return {
        "session_id": metrics.session_id,
        "prompt_tokens": metrics.prompt_tokens,
        "completion_tokens": metrics.completion_tokens,
        "total_tokens": metrics.total_tokens,
        "cost": metrics.cost,
        "tool_calls": metrics.tool_calls,
        "message_count": metrics.message_count,
        "model": metrics.model,
        "created_at": metrics.created_at.isoformat(),
        "finished_at": metrics.finished_at.isoformat() if metrics.finished_at else None
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract metrics from OpenCode database")
    parser.add_argument("--db", help="Path to opencode.db")
    parser.add_argument("--session", help="Session ID (default: latest)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    db_path = get_db_path(args.db)

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        exit(1)

    session_id = args.session or get_latest_session_id(db_path)
    if not session_id:
        print("No sessions found in database")
        exit(1)

    metrics = extract_session_metrics(db_path, session_id)

    if not metrics:
        print(f"Session not found: {session_id}")
        exit(1)

    if args.json:
        print(json.dumps(metrics_to_dict(metrics), indent=2))
    else:
        print(f"Session: {metrics.session_id}")
        print(f"Model: {metrics.model}")
        print(f"Prompt tokens: {metrics.prompt_tokens:,}")
        print(f"Completion tokens: {metrics.completion_tokens:,}")
        print(f"Total tokens: {metrics.total_tokens:,}")
        print(f"Cost: ${metrics.cost:.6f}")
        print(f"Tool calls: {metrics.tool_calls}")
        print(f"Messages: {metrics.message_count}")
