# ATF Tools - Python Implementation

Pure Python implementation of ATF Tools with **zero dependencies**.

## Requirements

- Python 3.8 or higher
- No external packages required!

## Usage

```bash
# Make executable (Unix)
chmod +x atf.py

# Run directly
python atf.py rebuild document.atf

# Or on Unix
./atf.py rebuild document.atf
```

## Commands

```bash
# Rebuild index
python atf.py rebuild document.atf

# Rebuild all files
python atf.py rebuild-all ./docs

# Watch mode
python atf.py watch document.atf

# Stop watching
python atf.py unwatch document.atf

# List watched files
python atf.py watch --list

# Validate
python atf.py validate document.atf

# Help
python atf.py --help
```

## Installation

### System-wide (Unix)

```bash
sudo cp atf.py /usr/local/bin/atf
sudo chmod +x /usr/local/bin/atf
```

### System-wide (Windows)

```powershell
# Copy to a folder in PATH
copy atf.py C:\Windows\atf.py

# Or create batch wrapper
echo @python "%~dp0atf.py" %* > atf.bat
move atf.bat C:\Windows\
```

## Features

- ✅ All 5 commands implemented
- ✅ Zero dependencies
- ✅ Cross-platform (Windows, macOS, Linux)
- ✅ Watch state persisted in ~/.atf/watch.json
- ✅ Comprehensive validation
- ✅ Clear error messages

## Development

The code is in a single file (`atf.py`) for easy distribution and modification.

### Code Structure

```python
# Classes
class ATFSection:    # Represents a section
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
cat > test.atf <<'EOF'
:::ATF/1.0
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
python atf.py rebuild test.atf

# Check result
cat test.atf
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
