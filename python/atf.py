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

# Watch state file
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
        self.in_header = True
        self.summary_continuation = False


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
            continue

        # Header annotations (only immediately after opening tag)
        if stack and stack[-1].in_header:
            if line.startswith("@"):
                if line.startswith("@summary:"):
                    stack[-1].summary = line[9:].strip()
                    stack[-1].summary_continuation = True
                elif line.startswith("@created:"):
                    stack[-1].created = line[9:].strip()
                    stack[-1].summary_continuation = False
                elif line.startswith("@modified:"):
                    stack[-1].modified = line[10:].strip()
                    stack[-1].summary_continuation = False
                continue
            if line.startswith((" ", "\t")) and getattr(stack[-1], "summary_continuation", False):
                stack[-1].summary = f"{stack[-1].summary} {line.strip()}"
                continue
            stack[-1].in_header = False
            stack[-1].summary_continuation = False

        # Extract title from first heading
        if line.startswith("#") and stack and not stack[-1].title.startswith("#"):
            stack[-1].title = line.lstrip("#").strip()

        # Closing tag: {/id}
        elif match := close_pattern.match(line):
            section_id = match.group(1)
            if stack and stack[-1].id == section_id:
                stack[-1].end_line = i + 1  # 1-indexed
                stack.pop()

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


def generate_index(sections: List[ATFSection], content_hash: str) -> List[str]:
    """Generate INDEX section from parsed sections"""
    index_lines = [
        "===INDEX===",
        "<!-- AUTO-GENERATED - DO NOT EDIT -->",
        f"<!-- Generated: {datetime.now(timezone.utc).isoformat()} -->",
        f"<!-- Content-Hash: sha256:{content_hash} -->",
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

        if not sections:
            print(f"Warning: No sections found in {filepath}", file=sys.stderr)
            return False

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

        if header_end is None or index_end is None:
            print(f"Error: Invalid ATF file format in {filepath}", file=sys.stderr)
            return False

        # Generate new INDEX (two-pass to adjust absolute line numbers)
        content_text = "\n".join(lines[content_start:])
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
        new_index = generate_index(sections, content_hash)
        original_span = index_end - header_end
        new_span = 1 + len(new_index) + 1  # blank + index + blank
        line_delta = new_span - original_span
        if line_delta:
            for section in sections:
                section.start_line += line_delta
                section.end_line += line_delta
            new_index = generate_index(sections, content_hash)

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
    print(f"\nPress Ctrl+C to stop watching (or close terminal to stop)")

    # Watch loop
    try:
        last_mtime = path.stat().st_mtime

        while True:
            time.sleep(1)  # Check every second
            try:
                watch_state = json.loads(WATCH_STATE_FILE.read_text())
            except Exception:
                watch_state = {}

            if str(path) not in watch_state:
                print(f"\nWatch stopped via unwatch: {filepath}")
                break

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
        print(f"\n\nWatch stopped")
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

        # Check 2: INDEX/CONTENT sections and order
        index_positions = [i for i, line in enumerate(lines) if line.strip() == "===INDEX==="]
        content_positions = [i for i, line in enumerate(lines) if line.strip() == "===CONTENT==="]
        has_index = bool(index_positions)
        has_content = bool(content_positions)

        if has_index:
            print("✓ INDEX section found")
        else:
            warnings.append("No INDEX section (run 'atf rebuild' to create)")

        if has_content:
            print("✓ CONTENT section found")
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
                    content_hash_line,
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
                        if actual_hash != expected_hash:
                            warnings.append(
                                "INDEX Content-Hash does not match CONTENT (index may be stale)"
                            )
            else:
                warnings.append("INDEX missing Content-Hash (run 'atf rebuild' to add)")

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
            print("✓ All sections properly closed")

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
            print(f"✓ Found {len(section_ids)} section(s) with unique IDs")
        else:
            warnings.append("No sections found in CONTENT")

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
