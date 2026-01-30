# Security & Configuration

## Watch State

- Watch state stored in: `~/.iatf/watch.json`
- **Never commit** user-specific state files
- Add to `.gitignore` if not already present

## Installer Security

- Install scripts automatically verify SHA256 checksums from releases
- Checksums ensure binary integrity

## Installation Modes

Install scripts support both:
- **Privileged**: Requires sudo/admin (system-wide install)
- **Unprivileged**: User-local install (no elevated permissions)
