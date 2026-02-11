from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from rich.console import Console

from .extract_metrics import extract_answer_from_session
from .models import BenchmarkConfig, OpenCodeRun
from .opencode_stream import parse_opencode_json_stream


class OpenCodeIsolation:
    """
    Per-run isolation knobs for opencode:
    - cwd: used to avoid auto-discovery of opencode.json from repo parents
    - env: redirects XDG dirs and optionally HOME to control skills discovery
    """

    def __init__(self, *, cwd: Path, env: Dict[str, str], tmp: tempfile.TemporaryDirectory[str]):
        self.cwd = cwd
        self.env = env
        self._tmp = tmp

    def cleanup(self) -> None:
        self._tmp.cleanup()


def prepare_opencode_isolation(
    *,
    approach: str,
    approach_config: Dict[str, Any],
    run_cwd: Path,
) -> OpenCodeIsolation:
    """
    Create an isolated per-run opencode environment.

    Policy (defaults, can be overridden per-approach via config keys):
    - baseline/iatf: no MCP servers and no skills
    - rag_mcp: MCP enabled but no skills
    - (optional) skills approach: skills enabled but no MCP

    Recognized approach_config keys:
    - mcp_enabled: bool
    - skills_enabled: bool
    """
    mcp_enabled = bool(approach_config.get("mcp_enabled", approach == "rag_mcp"))
    skills_enabled = bool(approach_config.get("skills_enabled", False))

    tmp = tempfile.TemporaryDirectory(prefix="iatf-bench-opencode-")
    root = Path(tmp.name)
    cwd = run_cwd

    env = dict(os.environ)

    # Redirect all opencode writes to temp (sandbox + CI friendly).
    env["XDG_CACHE_HOME"] = str(root / "xdg" / "cache")
    env["XDG_CONFIG_HOME"] = str(root / "xdg" / "config")
    env["XDG_DATA_HOME"] = str(root / "xdg" / "data")
    env["XDG_STATE_HOME"] = str(root / "xdg" / "state")

    # Skills are discovered under $HOME/.claude/skills in opencode.
    # For "no skills" approaches we point HOME at an empty temp directory.
    if not skills_enabled:
        home = root / "home"
        home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(home)

    # Control MCP deterministically via OPENCODE_CONFIG (doesn't depend on cwd walk-up).
    if mcp_enabled:
        # benchmark/opencode.json enables the rag-server remote MCP entry.
        benchmark_dir = Path(__file__).resolve().parents[1]
        env["OPENCODE_CONFIG"] = str((benchmark_dir / "opencode.json").resolve())
    else:
        disable_cfg = root / "opencode_disable_mcp.json"
        disable_cfg.write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "mcp": {"rag-server": {"enabled": False}},
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        env["OPENCODE_CONFIG"] = str(disable_cfg)

    return OpenCodeIsolation(cwd=cwd, env=env, tmp=tmp)


def run_opencode(
    console: Console,
    config: BenchmarkConfig,
    prompt: str,
    working_dir: Path,
    *,
    opencode_cwd: Optional[Path] = None,
    opencode_env: Optional[Mapping[str, str]] = None,
    timeout_s: int = 300,
) -> OpenCodeRun:
    """
    Run OpenCode with a prompt and return parsed results.

    Preserves prior behavior:
    - Parse JSON stream for answer/session/metrics
    - DB fallback for missing answer when stream includes a concrete session_id
    """
    start_time = time.time()

    cmd = [
        config.opencode_path,
        "run",
        prompt,
        "-m",
        config.model,
        "--format",
        "json",
    ]

    try:
        console.print(
            f"  [dim]Running: {' '.join(cmd[:3])}... (model={config.model})[/dim]"
        )
        env = dict(os.environ)
        if opencode_env:
            env.update({k: str(v) for k, v in opencode_env.items()})

        result = subprocess.run(
            cmd,
            cwd=str(opencode_cwd or working_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        latency_ms = (time.time() - start_time) * 1000

        if result.returncode != 0:
            console.print(
                f"  [red]opencode exited with code {result.returncode}[/red]"
            )
            if result.stderr:
                console.print(f"  [red]stderr: {result.stderr[:500]}[/red]")
            if result.stdout:
                console.print(f"  [dim]stdout (first 500): {result.stdout[:500]}[/dim]")

        parsed = parse_opencode_json_stream(result.stdout or "")

        answer = parsed.get("answer", "") or ""
        session_id = parsed.get("session_id", "unknown") or "unknown"
        error: Optional[str] = None

        if result.returncode != 0:
            stderr_preview = (result.stderr or "").strip().replace("\n", " ")
            if stderr_preview:
                stderr_preview = f": {stderr_preview[:200]}"
            error = f"ERROR: opencode exited with code {result.returncode}{stderr_preview}"

        if not answer:
            console.print(
                f"  [yellow]No answer parsed from JSON stream (session={session_id})[/yellow]"
            )
            if result.stdout:
                console.print(
                    f"  [dim]Raw stdout (first 800):\n{result.stdout[:800]}[/dim]"
                )

        if not answer and session_id != "unknown":
            console.print(f"  [dim]Trying DB fallback for session {session_id}...[/dim]")
            try:
                if config.db_path.exists():
                    answer = extract_answer_from_session(config.db_path, session_id) or ""
            except Exception:
                # DB schema/path differences across opencode versions are common; don't fail the run.
                pass

        if not answer and not error:
            error = "ERROR: No answer parsed from opencode output"

        if answer.startswith("ERROR:") and not error:
            error = answer

        if not answer and error:
            answer = error

        console.print(
            f"  [dim]Result: session={session_id}, tokens={parsed.get('total_tokens', 0)}, answer_len={len(answer)}[/dim]"
        )

        return OpenCodeRun(
            answer=answer,
            session_id=session_id,
            latency_ms=latency_ms,
            prompt_tokens=int(parsed.get("prompt_tokens", 0) or 0),
            completion_tokens=int(parsed.get("completion_tokens", 0) or 0),
            total_tokens=int(parsed.get("total_tokens", 0) or 0),
            reasoning_tokens=int(parsed.get("reasoning_tokens", 0) or 0),
            cache_read_tokens=int(parsed.get("cache_read_tokens", 0) or 0),
            cache_write_tokens=int(parsed.get("cache_write_tokens", 0) or 0),
            cost=float(parsed.get("cost", 0.0) or 0.0),
            tool_calls=int(parsed.get("tool_calls", 0) or 0),
            tool_call_details=list(parsed.get("tool_call_details", []) or []),
            raw_events=list(parsed.get("raw_events", []) or []),
            error=error,
        )

    except subprocess.TimeoutExpired:
        latency_ms = (time.time() - start_time) * 1000
        return OpenCodeRun(
            answer="ERROR: Timeout",
            session_id="timeout",
            latency_ms=latency_ms,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            reasoning_tokens=0,
            cache_read_tokens=0,
            cache_write_tokens=0,
            cost=0.0,
            tool_calls=0,
            tool_call_details=[],
            raw_events=[],
            error="ERROR: Timeout",
        )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        msg = f"ERROR: {e}"
        return OpenCodeRun(
            answer=msg,
            session_id="error",
            latency_ms=latency_ms,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            reasoning_tokens=0,
            cache_read_tokens=0,
            cache_write_tokens=0,
            cost=0.0,
            tool_calls=0,
            tool_call_details=[],
            raw_events=[],
            error=msg,
        )
