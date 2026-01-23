# IATF Tools - Python Implementation

Pure Python implementation of IATF Tools with **zero dependencies**.

## Requirements

- Python 3.8 or higher
- No external packages required!

## Usage

```bash
# Make executable (Unix)
chmod +x iatf.py

# Run directly
python iatf.py rebuild document.iatf

# Or on Unix
./iatf.py rebuild document.iatf
```

## Commands

```bash
# Rebuild index
python iatf.py rebuild document.iatf

# Rebuild all files
python iatf.py rebuild-all ./docs

# Watch mode
python iatf.py watch document.iatf

# Stop watching
python iatf.py unwatch document.iatf

# List watched files
python iatf.py watch --list

# Validate
python iatf.py validate document.iatf

# Help
python iatf.py --help
```

## Installation

### System-wide (Unix)

```bash
sudo cp iatf.py /usr/local/bin/iatf
sudo chmod +x /usr/local/bin/iatf
```

### System-wide (Windows)

```powershell
# Copy to a folder in PATH
copy iatf.py C:\Windows\iatf.py

# Or create batch wrapper
echo @python "%~dp0iatf.py" %* > iatf.bat
move iatf.bat C:\Windows\
```

## Features

- ✅ All 5 commands implemented
- ✅ Zero dependencies
- ✅ Cross-platform (Windows, macOS, Linux)
- ✅ Watch state persisted in ~/.iatf/watch.json
- ✅ Comprehensive validation
- ✅ Clear error messages

## Development

The code is in a single file (`iatf.py`) for easy distribution and modification.

### Code Structure

```python
# Classes
class IATFSection:    # Represents a section
class WatchState:    # (uses JSON, no class needed)

# Core Functions
parse_content_section()  # Parse CONTENT to extract sections
generate_index()         # Generate INDEX from sections
rebuild_index()          # Main rebuild logic

# Commands
rebuild_command()        # Rebuild single file
rebuild_all_command()    # Rebuild directory
watch_command()          # Watch mode
unwatch_command()        # Stop watching
validate_command()       # Validation
```

## Testing

```bash
# Create test file
cat > test.iatf <<'EOF'
:::IATF/1.0
@title: Test

===CONTENT===

{#test}
@summary: Test section
@created: 2025-01-20
@modified: 2025-01-20
# Test
Content here
{/test}
EOF

# Test rebuild
python iatf.py rebuild test.iatf

# Check result
cat test.iatf
```

## Extending

To add new commands:

1. Add command handler function (e.g., `new_command()`)
2. Add to `main()` function's command dispatch
3. Update `print_usage()` with new command

## Performance

- Small files (<1000 lines): < 50ms
- Medium files (1000-5000 lines): < 200ms
- Large files (>5000 lines): < 500ms

## Why Python?

- Easy to read and modify
- Works everywhere Python is installed
- Great for prototyping and learning
- Reference implementation for other languages

## Alternatives

- **Go version**: Faster, single binary, no runtime needed
- See `../go/` directory

## License

MIT License - see ../LICENSE






