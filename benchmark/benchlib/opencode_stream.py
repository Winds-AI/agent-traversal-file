from __future__ import annotations

import json
from typing import Any, Dict


def parse_opencode_json_stream(stdout: str) -> Dict[str, Any]:
    """
    Parse opencode's newline-delimited JSON event stream.

    Extracts session_id, answer text, token counts, cost, tool call count,
    and full tool call details (name, args, result) from the JSON events.

    Returns dict with keys: session_id, answer, prompt_tokens, completion_tokens,
                            total_tokens, cost, tool_calls, tool_call_details, raw_events
    """
    session_id = "unknown"
    text_parts: list[str] = []
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_reasoning_tokens = 0
    cache_read_tokens = 0
    cache_write_tokens = 0
    total_cost = 0.0

    # Track tool calls: toolCallId -> entry
    tool_map: Dict[str, Dict[str, Any]] = {}
    tool_call_ids_counted: set[str] = set()
    raw_events: list[dict[str, Any]] = []

    for raw_line in stdout.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        raw_events.append(event)

        if session_id == "unknown" and "sessionID" in event:
            session_id = event["sessionID"]

        event_type = event.get("type", "")
        part = event.get("part", {})

        if event_type == "text":
            text = part.get("text", "")
            if text:
                text_parts.append(text)
            continue

        if event_type == "tool_use":
            # Opencode event schema has varied over time. Support both:
            # - { toolCallId, toolName, state: "call"/"result", args, result }
            # - { callID, tool, state: {status,input,output} }
            tool_call_id = (
                part.get("toolCallId")
                or part.get("callID")
                or part.get("callId")
                or "unknown"
            )
            tool_name = part.get("toolName") or part.get("tool") or "unknown"

            raw_state = part.get("state", "")
            if isinstance(raw_state, dict):
                state_name = str(raw_state.get("status", "")) or "completed"
                args = raw_state.get("input", {}) or {}
                result = raw_state.get("output", "") or ""
            else:
                state_name = str(raw_state or "")
                args = part.get("args", {}) or {}
                result = part.get("result", "") or ""

            entry = tool_map.setdefault(
                tool_call_id,
                {
                    "toolCallId": tool_call_id,
                    "toolName": tool_name,
                    "args": {},
                    "result": "",
                    "state": state_name,
                },
            )

            if tool_name and (not entry.get("toolName") or entry["toolName"] == "unknown"):
                entry["toolName"] = tool_name

            if state_name in ("call", "partial-call"):
                entry["args"] = args
                entry["state"] = state_name
                # Count each tool call id once (avoids double-counting on result/other states).
                tool_call_ids_counted.add(tool_call_id)
            elif state_name == "result":
                entry["result"] = result
                entry["state"] = "completed"
            else:
                # Preserve any other metadata without counting extra tool calls.
                if args:
                    entry["args"] = args
                if result:
                    entry["result"] = result
                if state_name:
                    entry["state"] = state_name
                # If the tool event provides full details in one shot (common),
                # count it once.
                if tool_call_id != "unknown":
                    tool_call_ids_counted.add(tool_call_id)

            continue

        if event_type == "step_finish":
            tokens = part.get("tokens", {}) or {}
            total_prompt_tokens += tokens.get("input", 0) or 0
            total_completion_tokens += tokens.get("output", 0) or 0
            total_reasoning_tokens += tokens.get("reasoning", 0) or 0
            cache = tokens.get("cache", {}) or {}
            cache_read_tokens += cache.get("read", 0) or 0
            cache_write_tokens += cache.get("write", 0) or 0
            total_cost += part.get("cost", 0.0) or 0.0

    answer = "\n".join(text_parts)
    return {
        "session_id": session_id,
        "answer": answer,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "reasoning_tokens": total_reasoning_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "cost": total_cost,
        "tool_calls": len(tool_call_ids_counted),
        "tool_call_details": list(tool_map.values()),
        "raw_events": raw_events,
    }
