from __future__ import annotations

import subprocess
import time
from pathlib import Path

from rich.console import Console

import select


RAG_SERVER_PORT = 8808
RAG_SERVER_READY_MARKER = "Embedding model loaded and ready"


def start_rag_server(console: Console, benchmark_dir: Path) -> subprocess.Popen:
    """Start the RAG MCP server as a persistent background process."""
    server_script = benchmark_dir / "mcp-rag-server" / "server.py"
    venv_python = benchmark_dir.parent / ".venv" / "bin" / "python3"
    python_cmd = str(venv_python) if venv_python.exists() else "python3"

    cmd = [
        python_cmd,
        str(server_script),
        "--transport",
        "streamable-http",
        "--port",
        str(RAG_SERVER_PORT),
    ]

    console.print(
        f"[blue]Starting RAG MCP server on port {RAG_SERVER_PORT}...[/blue]"
    )

    return subprocess.Popen(
        cmd,
        cwd=str(benchmark_dir / "mcp-rag-server"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered where supported
    )


def wait_for_rag_server(
    console: Console, proc: subprocess.Popen, timeout: int = 300
) -> bool:
    """Wait for the RAG server to be fully ready (model loaded)."""
    start = time.time()
    console.print(
        "[yellow]Waiting for embedding model to load (this may take a few minutes on first run)...[/yellow]"
    )

    while time.time() - start < timeout:
        if proc.poll() is not None:
            remaining = proc.stdout.read() if proc.stdout else ""
            console.print(f"[red]RAG server died: {remaining}[/red]")
            return False

        if not proc.stdout:
            time.sleep(0.1)
            continue

        # Avoid blocking on readline(): only read when data is available.
        ready, _, _ = select.select([proc.stdout], [], [], 0.25)
        if not ready:
            continue

        line = proc.stdout.readline()
        if not line:
            continue

        stripped = line.strip()
        if stripped:
            console.print(f"[dim]{stripped}[/dim]")

        # Fail fast on common dependency errors; otherwise we'd sit until timeout
        # and rag_search would hang forever waiting for the embedding warmup.
        if "ModuleNotFoundError" in stripped or "No module named" in stripped:
            if "sentence_transformers" in stripped:
                console.print(
                    "[red]RAG server is missing dependency: sentence-transformers.[/red]"
                )
                return False

        if RAG_SERVER_READY_MARKER in stripped:
            console.print("[green]RAG server ready![/green]")
            time.sleep(2)
            return True

    console.print(f"[red]RAG server timed out after {timeout}s[/red]")
    return False


def stop_rag_server(console: Console, proc: subprocess.Popen) -> None:
    """Gracefully stop the RAG MCP server."""
    if proc.poll() is not None:
        return

    console.print("[blue]Shutting down RAG MCP server...[/blue]")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    console.print("[green]RAG server stopped.[/green]")
