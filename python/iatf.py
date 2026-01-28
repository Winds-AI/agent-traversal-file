#!/usr/bin/env python3
"""
IATF - Indexed Agent Traversable File

A tool for managing self-indexing documents optimized for AI agent navigation.

Usage:
    iatf rebuild <file>              Rebuild index for a file
    iatf rebuild-all [directory]     Rebuild all .iatf files
    iatf watch <file>                Watch and auto-rebuild on changes
    iatf unwatch <file>              Stop watching a file
    iatf validate <file>             Validate iatf file

Author: IATF Tools Project
License: MIT
"""

import sys
import os
import re
import hashlib
import time
import json
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

# Fix Unicode encoding on Windows console
if os.name == "nt":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def get_version():
    """Get version from VERSION file or fallback to dev"""
    try:
        # Look for VERSION file relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        version_file = os.path.join(os.path.dirname(script_dir), "VERSION")
        with open(version_file, "r") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        return "dev"

VERSION = get_version()

# Watch state file
WATCH_STATE_FILE = Path.home() / ".iatf" / "watch.json"


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def prompt_user_confirmation(message: str, default: bool = False) -> bool:
    """Prompt user for yes/no confirmation. Reads from piped input if available."""
    prompt_suffix = "[y/N]" if not default else "[Y/n]"

    try:
        if not sys.stdin.isatty():
            return default
        # Print prompt (works for both interactive and piped input)
        print(f"{message} {prompt_suffix}: ", end="", flush=True)
        response = sys.stdin.readline().strip().lower()
        if response == "":
            return default
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def check_watched_file(filepath: Path) -> bool:
    """
    Check if a file is being watched by another process.
    Returns True if rebuild should proceed, False if cancelled.
    """
    if not WATCH_STATE_FILE.exists():
        return True

    try:
        watch_state = json.loads(WATCH_STATE_FILE.read_text())
    except Exception:
        return True

    abs_path = str(filepath.resolve())
    if abs_path not in watch_state:
        return True

    info = watch_state[abs_path]
    pid = info.get("pid")

    # If no PID field (old format) or PID is not running, proceed
    if pid is None or not is_process_running(pid):
        return True

    # File is being watched by a running process
    print(f"\nWarning: This file is being watched by another process (PID {pid})")
    print("A manual rebuild will trigger an automatic rebuild from the watch process.")
    print("This will cause the file to be rebuilt twice.")
    print()
    print("Options:")
    print("  - Press 'y' to proceed with manual rebuild anyway")
    print("  - Press 'N' (default) to cancel")
    print(f"  - Run 'iatf unwatch {filepath}' to stop watching first")
    print()

    return prompt_user_confirmation("Continue with manual rebuild[OK] ", default=False)


class IATFSection:
    """Represents a section in an iatf document"""

    def __init__(self, section_id: str, title: str, start_line: int):
        self.id = section_id
        self.title = title
        self.start_line = start_line
        self.end_line = 0
        self.level = 1
        self.summary = ""
        self.created = ""
        self.modified = ""
        self.x_hash = ""
        self.word_count = 0
        self.in_header = True
        self.summary_continuation = False
        self.content_lines = []  # Actual content (excluding metadata)


def parse_content_section(lines: List[str], content_start: int) -> List[IATFSection]:
    """Parse CONTENT section and extract all sections"""
    sections = []
    stack = []

    open_pattern = re.compile(r"^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}")
    close_pattern = re.compile(r"^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}")

    for i in range(content_start, len(lines)):
        line = lines[i]

        # Opening tag: {#id}
        if match := open_pattern.match(line):
            section_id = match.group(1)
            section = IATFSection(section_id, section_id, i + 1)  # 1-indexed
            section.level = len(stack) + 1
            stack.append(section)
            sections.append(section)
            continue

        # Header annotations (only immediately after opening tag)
        if stack and stack[-1].in_header:
            if line.startswith("@"):
                if line.startswith("@summary:"):
                    stack[-1].summary = line[9:].strip()
                    stack[-1].summary_continuation = True
                elif line.startswith("@created:"):
                    # @created is stored in INDEX, not CONTENT
                    stack[-1].summary_continuation = False
                continue
            if line.startswith((" ", "\t")) and getattr(stack[-1], "summary_continuation", False):
                stack[-1].summary = f"{stack[-1].summary} {line.strip()}"
                continue
            stack[-1].in_header = False
            stack[-1].summary_continuation = False

        # Closing tag: {/id}
        if match := close_pattern.match(line):
            section_id = match.group(1)
            if stack and stack[-1].id == section_id:
                stack[-1].end_line = i + 1  # 1-indexed
                stack.pop()
            continue

        # Collect actual content lines (excluding opening/closing tags and metadata)
        if stack and not stack[-1].in_header:
            # Extract title from first heading
            if line.startswith("#") and not stack[-1].title.startswith("#"):
                stack[-1].title = line.lstrip("#").strip()
            # Add to content_lines
            stack[-1].content_lines.append(line)

    return sections


def validate_nesting(lines: List[str], content_start: int) -> Optional[str]:
    """Return error message if nesting is invalid, else None."""
    open_sections = []
    open_pattern = re.compile(r"^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}")
    close_pattern = re.compile(r"^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}")

    for line in lines[content_start:]:
        if match := open_pattern.match(line):
            open_sections.append(match.group(1))
        elif match := close_pattern.match(line):
            section_id = match.group(1)
            if open_sections and open_sections[-1] == section_id:
                open_sections.pop()
            else:
                return f"Closing tag without matching opening: {section_id}"

    if open_sections:
        return f"Unclosed section: {open_sections[-1]}"

    return None


def extract_references(lines: List[str], content_start: int) -> Dict[str, List[tuple]]:
    """
    Extract all {@section-id} references from content, ignoring fenced code blocks.
    Only lines that are exactly ``` open/close a fence.
    Returns dict of section_id -> list of (line_num, containing_section) tuples.
    """
    references: Dict[str, List[tuple]] = {}

    open_pattern = re.compile(r"^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}")
    close_pattern = re.compile(r"^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}")
    ref_pattern = re.compile(r"\{@([a-zA-Z][a-zA-Z0-9_-]*)\}")

    def is_code_fence_line(value: str) -> bool:
        return value.strip() == "```"

    open_sections = []
    in_code_fence = False
    for i in range(content_start, len(lines)):
        line = lines[i]
        line_num = i + 1  # 1-indexed

        if in_code_fence:
            if is_code_fence_line(line):
                in_code_fence = False
            continue
        if is_code_fence_line(line):
            in_code_fence = True
            continue
        # Track current section
        if match := open_pattern.match(line):
            open_sections.append(match.group(1))
            continue
        if match := close_pattern.match(line):
            if open_sections and open_sections[-1] == match.group(1):
                open_sections.pop()
            else:
                open_sections.clear()
            continue

        # Find all references in this line
        for match in ref_pattern.finditer(line):
            target = match.group(1)
            containing_section = open_sections[-1] if open_sections else None
            if target not in references:
                references[target] = []
            references[target].append((line_num, containing_section))

    return references


def validate_references(lines: List[str], content_start: int, sections: List[IATFSection]) -> List[str]:
    """
    Validate that all references point to existing sections and no self-references exist.
    Returns list of error messages (empty if valid).
    """
    errors = []

    # Build set of valid section IDs
    valid_ids = {section.id for section in sections}

    # Extract references
    references = extract_references(lines, content_start)

    ordered_refs = []
    for target, locations in references.items():
        for line_num, containing_section in locations:
            ordered_refs.append((line_num, target, containing_section or ""))

    ordered_refs.sort()

    # Validate each reference in deterministic order
    for line_num, target, containing_section in ordered_refs:
        if target not in valid_ids:
            errors.append(f"Reference {{@{target}}} at line {line_num}: target section does not exist")
        elif target == containing_section:
            errors.append(f"Reference {{@{target}}} at line {line_num}: self-reference not allowed")

    return errors


def find_duplicate_section_ids(sections: List["IATFSection"]) -> List[str]:
    seen: Dict[str, int] = {}
    duplicates: List[str] = []
    for section in sections:
        seen[section.id] = seen.get(section.id, 0) + 1
        if seen[section.id] == 2:
            duplicates.append(section.id)
    return duplicates


def compute_content_hash(content_lines: List[str]) -> str:
    """Compute truncated SHA256 hash of content (Git-style 7 chars)"""
    content_text = "\n".join(content_lines)
    full_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
    return full_hash[:7]  # Git-style truncated hash


def count_words(content_lines: List[str]) -> int:
    """Count words in content lines"""
    text = " ".join(content_lines)
    # Split on whitespace and filter out empty strings
    words = [word for word in text.split() if word]
    return len(words)

def parse_index_metadata(lines: List[str]) -> Dict[str, Dict[str, str]]:
    """Parse INDEX section for per-section metadata (hash/modified)."""
    index_start = None
    index_end = None
    for i, line in enumerate(lines):
        if line.strip() == "===INDEX===":
            index_start = i
        elif line.strip() == "===CONTENT===":
            index_end = i
            break

    if index_start is None or index_end is None:
        return {}

    index_entry_re = re.compile(
        r"^#{1,6}\s+.*\{#([a-zA-Z][a-zA-Z0-9_-]*)\s*\|"
    )

    metadata: Dict[str, Dict[str, str]] = {}
    current_id: Optional[str] = None

    for line in lines[index_start + 1:index_end]:
        stripped = line.strip()
        if not stripped:
            current_id = None
            continue

        if match := index_entry_re.match(stripped):
            current_id = match.group(1)
            metadata.setdefault(current_id, {})
            continue

        if current_id is None:
            continue

        if stripped.startswith("Hash:"):
            metadata[current_id]["hash"] = stripped.split(":", 1)[1].strip()
            continue

        if stripped.startswith("Created:") or stripped.startswith("Modified:"):
            parts = [p.strip() for p in stripped.split("|")]
            for part in parts:
                if part.startswith("Created:"):
                    metadata[current_id]["created"] = part.split(":", 1)[1].strip()
                elif part.startswith("Modified:"):
                    metadata[current_id]["modified"] = part.split(":", 1)[1].strip()

    return metadata


def generate_index(sections: List[IATFSection], content_hash: str) -> List[str]:
    """Generate INDEX section from parsed sections"""
    index_lines = [
        "===INDEX===",
        "<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->",
        f"<!-- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} -->",
        f"<!-- Content-Hash: sha256:{content_hash} -->",
        "",
    ]

    for section in sections:
        # Level markers
        level_marker = "#" * section.level

        # Index line: # Title {#id | lines:start-end | words:count}
        index_line = f"{level_marker} {section.title} {{#{section.id} | lines:{section.start_line}-{section.end_line} | words:{section.word_count}}}"
        index_lines.append(index_line)

        # Summary
        if section.summary:
            index_lines.append(f"> {section.summary}")

        # Timestamps
        if section.created or section.modified:
            timestamps = []
            if section.created:
                timestamps.append(f"Created: {section.created}")
            if section.modified:
                timestamps.append(f"Modified: {section.modified}")
            index_lines.append(f"  {' | '.join(timestamps)}")

        # Hash (per-section)
        if section.x_hash:
            index_lines.append(f"  Hash: {section.x_hash}")

        index_lines.append("")  # Blank line after each entry

    return index_lines


def rebuild_index(filepath: Path) -> bool:
    """Rebuild the INDEX section of an iatf file"""
    try:
        content = filepath.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find CONTENT section
        content_start = None
        for i, line in enumerate(lines):
            if line.strip() == "===CONTENT===":
                content_start = i + 1
                break

        if content_start is None:
            print(
                f"Error: No ===CONTENT=== section found in {filepath}", file=sys.stderr
            )
            return False

        # Validate nesting before parsing for index rebuild
        nesting_error = validate_nesting(lines, content_start)
        if nesting_error:
            print(
                f"Error: Invalid section nesting in {filepath}: {nesting_error}",
                file=sys.stderr,
            )
            return False

        # Parse sections
        sections = parse_content_section(lines, content_start)

        # Parse existing INDEX metadata (hash/modified)
        index_meta = parse_index_metadata(lines)

        if not sections:
            print(f"Warning: No sections found in {filepath}", file=sys.stderr)
            return False

        duplicate_ids = find_duplicate_section_ids(sections)
        if duplicate_ids:
            for section_id in duplicate_ids:
                print(f"  - Duplicate section ID: {section_id}", file=sys.stderr)
            print(
                f"Error: {len(duplicate_ids)} duplicate section ID(s) found in {filepath}",
                file=sys.stderr,
            )
            return False

        # Validate references before proceeding
        ref_errors = validate_references(lines, content_start, sections)
        if ref_errors:
            for err in ref_errors:
                print(f"  - {err}", file=sys.stderr)
            print(f"[ERROR] {len(errors)} error(s) found:")
            return False

        # Auto-update Modified based on content hash changes
        today = datetime.now().date().isoformat()
        for section in sections:
            # Compute current content hash
            new_hash = compute_content_hash(section.content_lines)
            old_hash = index_meta.get(section.id, {}).get("hash", "")
            old_modified = index_meta.get(section.id, {}).get("modified", "")
            old_created = index_meta.get(section.id, {}).get("created", "")

            # Compute word count
            section.word_count = count_words(section.content_lines)

            # Update Created
            if old_created:
                section.created = old_created
            else:
                section.created = today

            # Update Modified
            if old_hash and old_hash != new_hash:
                section.modified = today
            elif old_hash:
                section.modified = old_modified
            else:
                section.modified = old_modified or today

            # Update hash for INDEX output
            section.x_hash = new_hash

        # Find where to insert INDEX
        header_end = None
        index_end = None

        for i, line in enumerate(lines):
            if line.strip() == "===INDEX===":
                header_end = i
            elif line.strip() == "===CONTENT===":
                index_end = i
                break

        if header_end is None:
            # No existing INDEX, insert after header
            for i, line in enumerate(lines):
                if line.strip() == ":::IATF":
                    header_end = i + 1
                    # Skip metadata lines
                    while i + 1 < len(lines) and lines[i + 1].startswith("@"):
                        i += 1
                        header_end = i + 1
                    break

        if header_end is None or index_end is None:
            print(f"Error: Invalid iatf file format in {filepath}", file=sys.stderr)
            return False

        # Recalculate content hash after updates (Git-style 7 chars)
        content_text = "\n".join(lines[content_start:])
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()[:7]

        # Generate new INDEX (two-pass to adjust absolute line numbers)
        new_index = generate_index(sections, content_hash)
        original_span = index_end - header_end
        new_span = len(new_index) + 1  # index + blank
        line_delta = new_span - original_span
        if line_delta:
            for section in sections:
                section.start_line += line_delta
                section.end_line += line_delta
            new_index = generate_index(sections, content_hash)

        # Rebuild file (normalize spacing around INDEX)
        pre_lines = lines[:header_end]
        while pre_lines and pre_lines[-1].strip() == "":
            pre_lines.pop()

        post_lines = lines[index_end:]
        while post_lines and post_lines[0].strip() == "":
            post_lines.pop(0)

        new_lines = pre_lines + [""] + new_index + [""] + post_lines

        new_content = "\n".join(new_lines)

        # Write back
        filepath.write_text(new_content, encoding="utf-8")
        return True

    except Exception as e:
        print(f"Error rebuilding {filepath}: {e}", file=sys.stderr)
        return False


def rebuild_command(filepath: str) -> int:
    """Command: rebuild a single file"""
    path = Path(filepath)

    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    # Check if file is being watched by another process
    if not check_watched_file(path):
        print("Rebuild cancelled, no changes made.")
        return 1

    if not path.suffix == ".iatf":
        print(f"Warning: File doesn't have .iatf extension: {filepath}", file=sys.stderr)

    print(f"Rebuilding index: {filepath}")

    if rebuild_index(path):
        print("[OK] Index rebuilt successfully")
        return 0
    else:
        print("[ERROR] Failed to rebuild index", file=sys.stderr)
        return 1


def rebuild_all_command(directory: str = ".") -> int:
    """Command: rebuild all .iatf files in directory"""
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"Error: Directory not found: {directory}", file=sys.stderr)
        return 1

    # Find all .iatf files recursively
    iatf_files = list(dir_path.rglob("*.iatf"))

    if not iatf_files:
        print(f"No .iatf files found in {directory}")
        return 0

    print(f"Found {len(iatf_files)} .iatf file(s)")

    success_count = 0
    for filepath in iatf_files:
        print(f"\nProcessing: {filepath}")
        if rebuild_index(filepath):
            print("  [OK] Success")
            success_count += 1
        else:
            print("  [ERROR] Failed")

    print(f"\nCompleted: {success_count}/{len(iatf_files)} files rebuilt successfully")
    return 0 if success_count == len(iatf_files) else 1


def watch_command(filepath: str) -> int:
    """Command: watch a file and auto-rebuild on changes"""
    path = Path(filepath).resolve()

    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    # Load existing watch state
    WATCH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if WATCH_STATE_FILE.exists():
        watch_state = json.loads(WATCH_STATE_FILE.read_text())
    else:
        watch_state = {}

    # Add to watch list with PID
    watch_state[str(path)] = {
        "started": datetime.now().isoformat(),
        "last_modified": path.stat().st_mtime,
        "pid": os.getpid(),
    }

    WATCH_STATE_FILE.write_text(json.dumps(watch_state, indent=2))

    # Cleanup function to remove PID from watch state
    def cleanup_pid():
        try:
            if WATCH_STATE_FILE.exists():
                current_state = json.loads(WATCH_STATE_FILE.read_text())
                if str(path) in current_state:
                    # Only remove if it's still our PID
                    if current_state[str(path)].get("pid") == os.getpid():
                        del current_state[str(path)]
                        WATCH_STATE_FILE.write_text(json.dumps(current_state, indent=2))
        except Exception:
            pass  # Best effort cleanup

    # Register signal handler for SIGTERM
    def sigterm_handler(signum, frame):
        cleanup_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    print(f"Started watching: {filepath}")
    print(f"File will auto-rebuild on save")
    print(f"To stop: iatf unwatch {filepath}")
    print(f"\nPress Ctrl+C to stop watching (or close terminal to stop)")

    # Watch loop
    try:
        last_mtime = path.stat().st_mtime

        while True:
            time.sleep(1)  # Check every second
            try:
                watch_state = json.loads(WATCH_STATE_FILE.read_text())
            except Exception:
                # Watch state corrupt or unreadable - cleanup and exit
                cleanup_pid()
                print(f"\nWatch state file corrupt or unreadable, stopping watch")
                break

            if str(path) not in watch_state:
                # Entry removed by unwatch command - no cleanup needed
                print(f"\nWatch stopped via unwatch: {filepath}")
                break

            try:
                current_mtime = path.stat().st_mtime

                if current_mtime > last_mtime:
                    print(
                        f"\n[{datetime.now().strftime('%H:%M:%S')}] File changed, rebuilding..."
                    )
                    if rebuild_index(path):
                        print("  [OK] Index rebuilt")
                    else:
                        print("  [ERROR] Rebuild failed")
                    last_mtime = current_mtime
            except FileNotFoundError:
                cleanup_pid()
                print(f"\nWarning: File no longer exists: {filepath}")
                break

    except KeyboardInterrupt:
        cleanup_pid()
        print(f"\n\nWatch stopped")
        print(f"To resume: iatf watch {filepath}")
        print(f"To stop permanently: iatf unwatch {filepath}")

    return 0


def unwatch_command(filepath: str) -> int:
    """Command: stop watching a file"""
    path = Path(filepath).resolve()

    if not WATCH_STATE_FILE.exists():
        print(f"No files are being watched")
        return 0

    watch_state = json.loads(WATCH_STATE_FILE.read_text())

    if str(path) in watch_state:
        del watch_state[str(path)]
        WATCH_STATE_FILE.write_text(json.dumps(watch_state, indent=2))
        print(f"Stopped watching: {filepath}")
        return 0
    else:
        print(f"File is not being watched: {filepath}")
        return 1


def list_watched() -> int:
    """List all watched files"""
    if not WATCH_STATE_FILE.exists():
        print("No files are being watched")
        return 0

    watch_state = json.loads(WATCH_STATE_FILE.read_text())

    if not watch_state:
        print("No files are being watched")
        return 0

    print(f"Watching {len(watch_state)} file(s):\n")
    for filepath, info in watch_state.items():
        started = info["started"]
        print(f"  {filepath}")
        print(f"    Since: {started}")

    return 0


def index_command(filepath: str) -> int:
    """Command: output only the INDEX section"""
    path = Path(filepath)

    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    try:
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find INDEX section boundaries
        index_start = None
        index_end = None

        for i, line in enumerate(lines):
            if line.strip() == "===INDEX===":
                index_start = i
            elif line.strip() == "===CONTENT===":
                index_end = i
                break

        if index_start is None or index_end is None:
            print("Error: INDEX not generated", file=sys.stderr)
            return 1

        content_start = index_end + 1
        nesting_error = validate_nesting(lines, content_start)
        if nesting_error:
            print(f"Error: Invalid section nesting: {nesting_error}", file=sys.stderr)
            return 1

        # Output INDEX section (lines between markers, excluding the markers)
        for line in lines[index_start + 1:index_end]:
            print(line)

        return 0

    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1


def read_command(filepath: str, section_id: str) -> int:
    """Command: extract specific section by ID"""
    path = Path(filepath)

    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    try:
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find INDEX and CONTENT section start
        index_start = None
        content_start = None
        for i, line in enumerate(lines):
            if line.strip() == "===CONTENT===":
                content_start = i + 1
                break
            if line.strip() == "===INDEX===":
                index_start = i

        if index_start is None:
            print("Error: No ===INDEX=== section found", file=sys.stderr)
            return 1

        if content_start is None:
            print("Error: No ===CONTENT=== section found", file=sys.stderr)
            return 1

        # Parse sections
        sections = parse_content_section(lines, content_start)

        # Find matching section by ID
        target_section = None
        for section in sections:
            if section.id == section_id:
                target_section = section
                break

        if target_section is None:
            print(f"Error: Section not found: {section_id}", file=sys.stderr)
            return 1

        # Extract and output section lines (convert from 1-indexed to 0-indexed)
        section_lines = lines[target_section.start_line - 1:target_section.end_line]
        for line in section_lines:
            print(line)

        return 0

    except Exception as e:
        print(f"Error reading section: {e}", file=sys.stderr)
        return 1


def read_by_title_command(filepath: str, title: str) -> int:
    """Command: extract section by fuzzy title match"""
    path = Path(filepath)

    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    try:
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find INDEX section
        index_start = None
        index_end = None

        for i, line in enumerate(lines):
            if line.strip() == "===INDEX===":
                index_start = i
            elif line.strip() == "===CONTENT===":
                index_end = i
                break

        if index_start is None or index_end is None:
            print("Error: Invalid iatf file format", file=sys.stderr)
            return 1

        # Parse INDEX entries to extract title->ID mappings (preserve order)
        index_entry_pattern = re.compile(
            r"^#{1,6}\s+(.+[OK] )\s*\{#([a-zA-Z][a-zA-Z0-9_-]*)\s*\|.*\}$"
        )

        entries = []
        for line in lines[index_start + 1:index_end]:
            match = index_entry_pattern.match(line.strip())
            if match:
                entries.append((match.group(1), match.group(2)))

        # Find best title match
        matched_id = None

        # 1. Exact match (case-insensitive)
        for entry_title, entry_id in entries:
            if entry_title.lower() == title.lower():
                matched_id = entry_id
                break

        # 2. Contains match (case-insensitive)
        if matched_id is None:
            title_lower = title.lower()
            for entry_title, entry_id in entries:
                if title_lower in entry_title.lower():
                    matched_id = entry_id
                    break

        if matched_id is None:
            print(f"Error: No section found with title matching: {title}", file=sys.stderr)
            return 1

        # Delegate to read_command
        return read_command(str(path), matched_id)

    except Exception as e:
        print(f"Error reading section: {e}", file=sys.stderr)
        return 1


def graph_command(filepath: str, show_incoming: bool = False) -> int:
    """Command: display section reference graph"""
    path = Path(filepath)

    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    try:
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find CONTENT section start
        content_start = None
        for i, line in enumerate(lines):
            if line.strip() == "===CONTENT===":
                content_start = i + 1
                break

        if content_start is None:
            print("Error: No ===CONTENT=== section found", file=sys.stderr)
            return 1

        nesting_error = validate_nesting(lines, content_start)
        if nesting_error:
            print(f"Error: Invalid section nesting: {nesting_error}", file=sys.stderr)
            return 1

        # Parse sections to get ordered list
        sections = parse_content_section(lines, content_start)

        if len(sections) == 0:
            print("Error: No sections found in CONTENT", file=sys.stderr)
            return 1

        # Extract references (returns map of target -> list of (line_num, containing_section))
        # This is the "incoming" map: targetID -> who references it
        incoming_refs_raw = extract_references(lines, content_start)

        # Build outgoing reference map (section -> what it references)
        outgoing_refs: Dict[str, List[str]] = {}
        for target_id, locations in incoming_refs_raw.items():
            for line_num, containing_section in locations:
                if containing_section:
                    # Add target_id to the list of refs from containing_section
                    if containing_section not in outgoing_refs:
                        outgoing_refs[containing_section] = []
                    if target_id not in outgoing_refs[containing_section]:
                        outgoing_refs[containing_section].append(target_id)

        # Build simplified incoming reference map
        incoming_refs: Dict[str, List[str]] = {}
        for target_id, locations in incoming_refs_raw.items():
            for line_num, containing_section in locations:
                if containing_section:
                    if target_id not in incoming_refs:
                        incoming_refs[target_id] = []
                    if containing_section not in incoming_refs[target_id]:
                        incoming_refs[target_id].append(containing_section)

        # Sort references for deterministic output
        for section_id in outgoing_refs:
            outgoing_refs[section_id].sort()
        for section_id in incoming_refs:
            incoming_refs[section_id].sort()

        # Output in compact format
        print(f"@graph: {path.name}\n")

        if show_incoming:
            # Show incoming references (who references this section)
            for section in sections:
                refs = incoming_refs.get(section.id, [])
                if refs:
                    print(f"{section.id} <- {', '.join(refs)}")
                else:
                    print(section.id)
        else:
            # Show outgoing references (what this section references)
            for section in sections:
                refs = outgoing_refs.get(section.id, [])
                if refs:
                    print(f"{section.id} -> {', '.join(refs)}")
                else:
                    print(section.id)

        return 0

    except Exception as e:
        print(f"Error generating graph: {e}", file=sys.stderr)
        return 1


def validate_command(filepath: str) -> int:
    """Command: validate an iatf file"""
    path = Path(filepath)

    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    print(f"Validating: {filepath}\n")

    try:
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")

        errors = []
        warnings = []

        # Check 1: Format declaration
        if lines[0].strip() != ":::IATF":
            errors.append("Missing format declaration (:::IATF)")
        else:
            print("[OK] Format declaration found")

        # Check 2: INDEX/CONTENT sections and order
        index_positions = [i for i, line in enumerate(lines) if line.strip() == "===INDEX==="]
        content_positions = [i for i, line in enumerate(lines) if line.strip() == "===CONTENT==="]
        has_index = bool(index_positions)
        has_content = bool(content_positions)

        if has_index:
            print("[OK] INDEX section found")
        else:
            warnings.append("No INDEX section (Run 'iatf rebuild' to create)")

        if has_content:
            print("[OK] CONTENT section found")
        else:
            errors.append("Missing CONTENT section")

        if len(index_positions) > 1:
            errors.append("Multiple INDEX sections found")
        if len(content_positions) > 1:
            errors.append("Multiple CONTENT sections found")
        if has_index and has_content:
            if index_positions[0] > content_positions[0]:
                errors.append("INDEX section appears after CONTENT")

        # Check 4: Content hash matches (if present)
        content_start = None
        index_start = None
        for i, line in enumerate(lines):
            if line.strip() == "===INDEX===":
                index_start = i
            elif line.strip() == "===CONTENT===":
                content_start = i + 1
                break

        if content_start is not None:
            nesting_error = validate_nesting(lines, content_start)
            if nesting_error:
                errors.append(f"Invalid section nesting: {nesting_error}")

        if has_index:
            content_hash_line = None
            if index_start is not None and content_start is not None:
                for line in lines[index_start:content_start]:
                    if line.startswith("<!-- Content-Hash:"):
                        content_hash_line = line
                        break
            if content_hash_line and content_start is not None:
                match = re.match(
                    r"^<!-- Content-Hash:\s*([a-z0-9]+):([a-f0-9]+)\s*-->$",
                    content_hash_line.strip(),
                )
                if not match:
                    warnings.append("Invalid Content-Hash format in INDEX")
                else:
                    algo = match.group(1)
                    expected_hash = match.group(2)
                    if algo != "sha256":
                        warnings.append(f"Unsupported Content-Hash algorithm: {algo}")
                    else:
                        content_text = "\n".join(lines[content_start:])
                        actual_hash = hashlib.sha256(
                            content_text.encode("utf-8")
                        ).hexdigest()
                        if len(expected_hash) == 7:
                            hash_matches = actual_hash.startswith(expected_hash)
                        else:
                            hash_matches = actual_hash == expected_hash
                        if not hash_matches:
                            warnings.append(
                                "INDEX Content-Hash does not match CONTENT (index may be stale)"
                            )
            else:
                warnings.append("INDEX missing Content-Hash (Run 'iatf rebuild' to add)")

        # Check 5: All sections are properly closed and nested
        open_sections = []
        invalid_nesting = False
        for line in lines:
            if match := re.match(r"^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}", line):
                open_sections.append(match.group(1))
            elif match := re.match(r"^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}", line):
                section_id = match.group(1)
                if open_sections and open_sections[-1] == section_id:
                    open_sections.pop()
                else:
                    errors.append(f"Closing tag without matching opening: {section_id}")
                    invalid_nesting = True

        if open_sections:
            for section_id in open_sections:
                errors.append(f"Unclosed section: {section_id}")
            invalid_nesting = True
        if not invalid_nesting:
            print("[OK] All sections properly closed")

        # Check 6: No content outside section blocks
        if not invalid_nesting and content_start is not None:
            open_pattern = re.compile(r"^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}")
            close_pattern = re.compile(r"^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}")
            open_sections = []
            for i in range(content_start, len(lines)):
                line = lines[i]
                if match := open_pattern.match(line):
                    open_sections.append(match.group(1))
                    continue
                if match := close_pattern.match(line):
                    if open_sections and open_sections[-1] == match.group(1):
                        open_sections.pop()
                    continue
                if not open_sections and line.strip():
                    errors.append(f"Content outside section block at line {i + 1}")
                    break

        # Check 7: INDEX entries match CONTENT
        if (
            not invalid_nesting
            and has_index
            and content_start is not None
            and index_start is not None
        ):
            index_entry_re = re.compile(
                r"^#{1,6}\s+.*\{#([a-zA-Z][a-zA-Z0-9_-]*)\s*\|\s*lines:(\d+)-(\d+)[^}]*\}$"
            )
            index_ranges = {}
            for line in lines[index_start + 1 : content_start]:
                match = index_entry_re.match(line.strip())
                if not match:
                    continue
                section_id = match.group(1)
                start_line = int(match.group(2))
                end_line = int(match.group(3))
                if section_id in index_ranges:
                    errors.append(f"Duplicate INDEX section ID: {section_id}")
                    continue
                index_ranges[section_id] = (start_line, end_line)
                if start_line < 1 or end_line < start_line or end_line > len(lines):
                    errors.append(f"Invalid line range for INDEX section: {section_id}")

            parsed_sections = parse_content_section(lines, content_start)
            content_sections = {
                section.id: (section.start_line, section.end_line)
                for section in parsed_sections
            }

            for section in parsed_sections:
                if section.level > 2:
                    errors.append(
                        f"Section nesting exceeds 2 levels: {section.id}"
                    )

            for section_id in index_ranges:
                if section_id not in content_sections:
                    errors.append(f"INDEX references missing CONTENT section: {section_id}")

            for section_id in content_sections:
                if section_id not in index_ranges:
                    errors.append(f"CONTENT section missing from INDEX: {section_id}")

            for section_id, content_range in content_sections.items():
                if section_id in index_ranges:
                    if index_ranges[section_id] != content_range:
                        errors.append(
                            f"INDEX line range mismatch for section: {section_id}"
                        )

        # Check 8: Section IDs are unique
        section_ids = []
        for line in lines:
            if match := re.match(r"^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}", line):
                section_id = match.group(1)
                if section_id in section_ids:
                    errors.append(f"Duplicate section ID: {section_id}")
                section_ids.append(section_id)

        if section_ids:
            print(f"[OK] Found {len(section_ids)} section(s) with unique IDs")
        else:
            warnings.append("No sections found in CONTENT")

        # Check 9: References valid
        if not invalid_nesting and content_start is not None:
            parsed_sections_for_refs = parse_content_section(lines, content_start)
            ref_errors = validate_references(lines, content_start, parsed_sections_for_refs)
            if not ref_errors:
                print("[OK] All references valid")
            else:
                for ref_err in ref_errors:
                    errors.append(ref_err)

        # Summary
        print()
        if errors:
            print(f"[ERROR] {len(errors)} error(s) found:")
            for error in errors:
                print(f"  - {error}")

        if warnings:
            print(f"[WARN] {len(warnings)} warning(s):")
            for warning in warnings:
                print(f"  - {warning}")

        if not errors and not warnings:
            print("[OK] File is valid!")
            return 0
        elif not errors:
            print("\n[WARN] File is valid (with warnings)")
            return 0
        else:
            print("\n[ERROR] File is invalid")
            return 1

    except Exception as e:
        print(f"Error validating file: {e}", file=sys.stderr)
        return 1


def print_usage():
    """Print usage information"""
    print(f"""IATF Tools v{VERSION}

Usage:
    iatf rebuild <file>              Rebuild index for a single file
    iatf rebuild-all [directory]     Rebuild all .iatf files in directory
    iatf watch <file>                Watch file and auto-rebuild on changes
    iatf unwatch <file>              Stop watching a file
    iatf watch --list                List all watched files
    iatf validate <file>             Validate iatf file structure
    iatf index <file>                Output INDEX section only
    iatf read <file> <section-id>    Extract section by ID
    iatf read <file> --title "Title" Extract section by title
    iatf graph <file>                Show section reference graph
    iatf graph <file> --show-incoming  Show incoming references (impact analysis)
    iatf --help                      Show this help message
    iatf --version                   Show version

Examples:
    iatf rebuild document.iatf
    iatf rebuild-all ./docs
    iatf watch api-reference.iatf
    iatf validate my-doc.iatf
    iatf index document.iatf
    iatf read document.iatf intro
    iatf read document.iatf --title "Introduction"

For more information, visit: https://github.com/Winds-AI/agent-traversal-file
""")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_usage()
        return 1

    command = sys.argv[1]

    if command in ["--help", "-h", "help"]:
        print_usage()
        return 0

    elif command in ["--version", "-v", "version"]:
        print(f"IATF Tools v{VERSION}")
        return 0

    elif command == "rebuild":
        if len(sys.argv) < 3:
            print("Error: Missing file argument", file=sys.stderr)
            print("Usage: iatf rebuild <file>", file=sys.stderr)
            return 1
        return rebuild_command(sys.argv[2])

    elif command == "rebuild-all":
        directory = sys.argv[2] if len(sys.argv) >= 3 else "."
        return rebuild_all_command(directory)

    elif command == "watch":
        if len(sys.argv) >= 3 and sys.argv[2] == "--list":
            return list_watched()
        if len(sys.argv) < 3:
            print("Error: Missing file argument", file=sys.stderr)
            print("Usage: iatf watch <file>", file=sys.stderr)
            return 1
        return watch_command(sys.argv[2])

    elif command == "unwatch":
        if len(sys.argv) < 3:
            print("Error: Missing file argument", file=sys.stderr)
            print("Usage: iatf unwatch <file>", file=sys.stderr)
            return 1
        return unwatch_command(sys.argv[2])

    elif command == "validate":
        if len(sys.argv) < 3:
            print("Error: Missing file argument", file=sys.stderr)
            print("Usage: iatf validate <file>", file=sys.stderr)
            return 1
        return validate_command(sys.argv[2])

    elif command == "index":
        if len(sys.argv) < 3:
            print("Error: Missing file argument", file=sys.stderr)
            print("Usage: iatf index <file>", file=sys.stderr)
            return 1
        return index_command(sys.argv[2])

    elif command == "read":
        if len(sys.argv) < 4:
            print("Error: Missing arguments", file=sys.stderr)
            print("Usage: iatf read <file> <section-id>", file=sys.stderr)
            print("       iatf read <file> --title \"Title\"", file=sys.stderr)
            return 1

        # Check for --title flag
        if sys.argv[3] == "--title":
            if len(sys.argv) < 5:
                print("Error: Missing title argument", file=sys.stderr)
                return 1
            return read_by_title_command(sys.argv[2], sys.argv[4])
        else:
            return read_command(sys.argv[2], sys.argv[3])

    elif command == "graph":
        if len(sys.argv) < 3:
            print("Error: Missing file argument", file=sys.stderr)
            print("Usage: iatf graph <file> [--show-incoming]", file=sys.stderr)
            return 1
        show_incoming = len(sys.argv) >= 4 and sys.argv[3] == "--show-incoming"
        return graph_command(sys.argv[2], show_incoming)

    else:
        print(f"Error: Unknown command: {command}", file=sys.stderr)
        print("Run 'iatf --help' for usage information", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
