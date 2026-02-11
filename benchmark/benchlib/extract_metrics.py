#!/usr/bin/env python3
"""
Extract metrics from OpenCode's SQLite database.

OpenCode stores session data in ~/.opencode/opencode.db including:
- Token usage (prompt_tokens, completion_tokens)
- Cost calculations
- Message history with tool calls
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    return Path.home() / ".opencode" / "opencode.db"


def get_latest_session_id(db_path: Path) -> Optional[str]:
    """Get the most recent session ID from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id FROM sessions
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def extract_session_metrics(db_path: Path, session_id: str) -> Optional[SessionMetrics]:
    """
    Extract metrics for a specific session from OpenCode's database.

    Returns SessionMetrics or None if session not found.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, model, prompt_tokens, completion_tokens, cost,
                   created_at, updated_at
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        )
        session_row = cursor.fetchone()
        if not session_row:
            return None

        cursor.execute(
            """
            SELECT COUNT(*) as message_count
            FROM messages
            WHERE session_id = ?
            """,
            (session_id,),
        )
        message_count = cursor.fetchone()["message_count"]

        cursor.execute(
            """
            SELECT content
            FROM messages
            WHERE session_id = ? AND role = 'assistant'
            """,
            (session_id,),
        )

        tool_calls = 0
        for row in cursor.fetchall():
            content = row["content"]
            if not content:
                continue

            try:
                content_data = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                tool_calls += content.count("tool_use")
                continue

            if isinstance(content_data, list):
                tool_calls += sum(
                    1
                    for item in content_data
                    if isinstance(item, dict) and item.get("type") == "tool_use"
                )
            else:
                # Fallback marker count for unexpected structures.
                tool_calls += content.count("tool_use")

        created_at = datetime.fromisoformat(
            session_row["created_at"].replace("Z", "+00:00")
        )
        finished_at = None
        if session_row["updated_at"]:
            finished_at = datetime.fromisoformat(
                session_row["updated_at"].replace("Z", "+00:00")
            )

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
            finished_at=finished_at,
        )
    finally:
        conn.close()


def get_sessions_in_timerange(
    db_path: Path, start_time: datetime, end_time: datetime
) -> List[str]:
    """Get all session IDs created within a time range."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id FROM sessions
            WHERE created_at >= ? AND created_at <= ?
            ORDER BY created_at ASC
            """,
            (start_time.isoformat(), end_time.isoformat()),
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def extract_answer_from_session(db_path: Path, session_id: str) -> Optional[str]:
    """Extract the final assistant answer text from a session."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT content
            FROM messages
            WHERE session_id = ? AND role = 'assistant'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        if not row or not row["content"]:
            return None

        content = row["content"]

        try:
            content_data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return content

        if isinstance(content_data, list):
            text_parts = [
                item.get("text", "")
                for item in content_data
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return "\n".join(text_parts) if text_parts else content

        if isinstance(content_data, dict):
            return content_data.get("text", content)

        return content
    finally:
        conn.close()


def metrics_to_dict(metrics: SessionMetrics) -> Dict[str, Any]:
    """Convert SessionMetrics to a JSON-serializable dictionary."""
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
        "finished_at": metrics.finished_at.isoformat() if metrics.finished_at else None,
    }

