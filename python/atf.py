#!/usr/bin/env python3
"""
ATF - Agent Traversable File

A tool for managing self-indexing documents optimized for AI agent navigation.

Usage:
    atf rebuild <file>              Rebuild index for a file
    atf rebuild-all [directory]     Rebuild all .atf files
    atf watch <file>                Watch and auto-rebuild on changes
    atf unwatch <file>              Stop watching a file
    atf validate <file>             Validate ATF file

Author: ATF Tools Project
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

VERSION = "1.0.0"

# Watch daemon state file
WATCH_STATE_FILE = Path.home() / ".atf" / "watch.json"


class ATFSection:
    """Represents a section in an ATF document"""

    def __init__(self, section_id: str, title: str, start_line: int):
        self.id = section_id
        self.title = title
        self.start_line = start_line
        self.end_line = 0
        self.level = 1
        self.summary = ""
        self.created = ""
        self.modified = ""


def parse_content_section(lines: List[str], content_start: int) -> List[ATFSection]:
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
            section = ATFSection(section_id, section_id, i + 1)  # 1-indexed
            section.level = len(stack) + 1
            stack.append(section)
            sections.append(section)

        # Annotations
        elif line.startswith("@summary:") and stack:
            stack[-1].summary = line[9:].strip()
        elif line.startswith("@created:") and stack:
            stack[-1].created = line[9:].strip()
        elif line.startswith("@modified:") and stack:
            stack[-1].modified = line[10:].strip()

        # Extract title from first heading
        elif line.startswith("#") and stack and not stack[-1].title.startswith("#"):
            stack[-1].title = line.lstrip("#").strip()

        # Closing tag: {/id}
        elif match := close_pattern.match(line):
            section_id = match.group(1)
            if stack and stack[-1].id == section_id:
                stack[-1].end_line = i + 1  # 1-indexed
                stack.pop()

    return sections


def generate_index(sections: List[ATFSection]) -> List[str]:
    """Generate INDEX section from parsed sections"""
    index_lines = [
        "===INDEX===",
        "<!-- AUTO-GENERATED - DO NOT EDIT -->",
        f"<!-- Generated: {datetime.now(timezone.utc).isoformat()} -->",
        "",
    ]

    for section in sections:
        # Level markers
        level_marker = "#" * section.level

        # Index line: # Title {#id | lines:start-end}
        index_line = f"{level_marker} {section.title} {{#{section.id} | lines:{section.start_line}-{section.end_line}}}"
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

        index_lines.append("")  # Blank line after each entry

    return index_lines


def rebuild_index(filepath: Path) -> bool:
    """Rebuild the INDEX section of an ATF file"""
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

        # Parse sections
        sections = parse_content_section(lines, content_start)

        if not sections:
            print(f"Warning: No sections found in {filepath}", file=sys.stderr)
            return False

        # Generate new INDEX
        new_index = generate_index(sections)

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
                if line.strip().startswith(":::ATF/"):
                    header_end = i + 1
                    # Skip metadata lines
                    while i + 1 < len(lines) and lines[i + 1].startswith("@"):
                        i += 1
                        header_end = i + 1
                    break

        if header_end is None:
            print(f"Error: Invalid ATF file format in {filepath}", file=sys.stderr)
            return False

        # Rebuild file
        new_lines = lines[:header_end] + [""] + new_index + [""] + lines[index_end:]

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

    if not path.suffix == ".atf":
        print(f"Warning: File doesn't have .atf extension: {filepath}", file=sys.stderr)

    print(f"Rebuilding index: {filepath}")

    if rebuild_index(path):
        print(f"✓ Index rebuilt successfully")
        return 0
    else:
        print(f"✗ Failed to rebuild index", file=sys.stderr)
        return 1


def rebuild_all_command(directory: str = ".") -> int:
    """Command: rebuild all .atf files in directory"""
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"Error: Directory not found: {directory}", file=sys.stderr)
        return 1

    # Find all .atf files recursively
    atf_files = list(dir_path.rglob("*.atf"))

    if not atf_files:
        print(f"No .atf files found in {directory}")
        return 0

    print(f"Found {len(atf_files)} .atf file(s)")

    success_count = 0
    for filepath in atf_files:
        print(f"\nProcessing: {filepath}")
        if rebuild_index(filepath):
            print(f"  ✓ Success")
            success_count += 1
        else:
            print(f"  ✗ Failed")

    print(f"\nCompleted: {success_count}/{len(atf_files)} files rebuilt successfully")
    return 0 if success_count == len(atf_files) else 1


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

    # Add to watch list
    watch_state[str(path)] = {
        "started": datetime.now().isoformat(),
        "last_modified": path.stat().st_mtime,
    }

    WATCH_STATE_FILE.write_text(json.dumps(watch_state, indent=2))

    print(f"Started watching: {filepath}")
    print(f"File will auto-rebuild on save")
    print(f"To stop: atf unwatch {filepath}")
    print(
        f"\nPress Ctrl+C to stop watching (or close terminal - watch continues in background)"
    )

    # Watch loop
    try:
        last_mtime = path.stat().st_mtime

        while True:
            time.sleep(1)  # Check every second

            try:
                current_mtime = path.stat().st_mtime

                if current_mtime > last_mtime:
                    print(
                        f"\n[{datetime.now().strftime('%H:%M:%S')}] File changed, rebuilding..."
                    )
                    if rebuild_index(path):
                        print(f"  ✓ Index rebuilt")
                    else:
                        print(f"  ✗ Rebuild failed")
                    last_mtime = current_mtime
            except FileNotFoundError:
                print(f"\nWarning: File no longer exists: {filepath}")
                break

    except KeyboardInterrupt:
        print(f"\n\nWatch stopped (but still in background)")
        print(f"To resume: atf watch {filepath}")
        print(f"To stop permanently: atf unwatch {filepath}")

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


def validate_command(filepath: str) -> int:
    """Command: validate an ATF file"""
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
        if not lines[0].startswith(":::ATF/"):
            errors.append("Missing format declaration (:::ATF/1.0)")
        else:
            print("✓ Format declaration found")

        # Check 2: INDEX section
        has_index = any(line.strip() == "===INDEX===" for line in lines)
        if has_index:
            print("✓ INDEX section found")
        else:
            warnings.append("No INDEX section (run 'atf rebuild' to create)")

        # Check 3: CONTENT section
        has_content = any(line.strip() == "===CONTENT===" for line in lines)
        if has_content:
            print("✓ CONTENT section found")
        else:
            errors.append("Missing CONTENT section")

        # Check 4: Section IDs are unique
        section_ids = []
        for line in lines:
            if match := re.match(r"^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}", line):
                section_id = match.group(1)
                if section_id in section_ids:
                    errors.append(f"Duplicate section ID: {section_id}")
                section_ids.append(section_id)

        if section_ids:
            print(f"✓ Found {len(section_ids)} section(s) with unique IDs")
        else:
            warnings.append("No sections found in CONTENT")

        # Check 5: All sections are closed
        open_sections = []
        for line in lines:
            if match := re.match(r"^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}", line):
                open_sections.append(match.group(1))
            elif match := re.match(r"^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}", line):
                section_id = match.group(1)
                if open_sections and open_sections[-1] == section_id:
                    open_sections.pop()
                else:
                    errors.append(f"Closing tag without matching opening: {section_id}")

        if open_sections:
            for section_id in open_sections:
                errors.append(f"Unclosed section: {section_id}")
        else:
            print("✓ All sections properly closed")

        # Summary
        print()
        if errors:
            print(f"✗ {len(errors)} error(s) found:")
            for error in errors:
                print(f"  - {error}")

        if warnings:
            print(f"⚠ {len(warnings)} warning(s):")
            for warning in warnings:
                print(f"  - {warning}")

        if not errors and not warnings:
            print("✓ File is valid!")
            return 0
        elif not errors:
            print("\n✓ File is valid (with warnings)")
            return 0
        else:
            print(f"\n✗ File is invalid")
            return 1

    except Exception as e:
        print(f"Error validating file: {e}", file=sys.stderr)
        return 1


def print_usage():
    """Print usage information"""
    print(f"""ATF Tools v{VERSION}

Usage:
    atf rebuild <file>              Rebuild index for a single file
    atf rebuild-all [directory]     Rebuild all .atf files in directory
    atf watch <file>                Watch file and auto-rebuild on changes
    atf unwatch <file>              Stop watching a file
    atf watch --list                List all watched files
    atf validate <file>             Validate ATF file structure
    atf --help                      Show this help message
    atf --version                   Show version

Examples:
    atf rebuild document.atf
    atf rebuild-all ./docs
    atf watch api-reference.atf
    atf validate my-doc.atf

For more information, visit: https://github.com/atf-tools/atf
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
        print(f"ATF Tools v{VERSION}")
        return 0

    elif command == "rebuild":
        if len(sys.argv) < 3:
            print("Error: Missing file argument", file=sys.stderr)
            print("Usage: atf rebuild <file>", file=sys.stderr)
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
            print("Usage: atf watch <file>", file=sys.stderr)
            return 1
        return watch_command(sys.argv[2])

    elif command == "unwatch":
        if len(sys.argv) < 3:
            print("Error: Missing file argument", file=sys.stderr)
            print("Usage: atf unwatch <file>", file=sys.stderr)
            return 1
        return unwatch_command(sys.argv[2])

    elif command == "validate":
        if len(sys.argv) < 3:
            print("Error: Missing file argument", file=sys.stderr)
            print("Usage: atf validate <file>", file=sys.stderr)
            return 1
        return validate_command(sys.argv[2])

    else:
        print(f"Error: Unknown command: {command}", file=sys.stderr)
        print("Run 'atf --help' for usage information", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
