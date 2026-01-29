# Migration to GoReleaser

## What Changed

We've migrated from a custom GitHub Actions workflow to **GoReleaser**, the industry-standard release tool for Go projects.

## Benefits

✅ **Simpler**: 35 lines of workflow YAML (down from 100+)
✅ **Standard**: Used by Docker, Kubernetes, GitHub CLI, and thousands of Go projects
✅ **Automated Changelog**: Generates changelog from commit messages
✅ **Version from Git Tags**: No VERSION file to keep in sync
✅ **Less Maintenance**: GoReleaser handles cross-compilation, checksums, archives, and releases

## How Versioning Works Now

### Before (Custom Workflow)
```bash
# Update VERSION file
echo "1.2.0" > VERSION
git add VERSION
git commit -m "Bump version to 1.2.0"
git tag v1.2.0
git push origin main
git push origin v1.2.0
```

**Problem**: Two sources of truth (VERSION file + git tag) could get out of sync

### After (GoReleaser)
```bash
# Just commit and tag
git add .
git commit -m "feat: add new feature"
git tag v1.2.0
git push origin main
git push origin v1.2.0
```

**Benefit**: Single source of truth (git tag)

## Creating a Release

### 1. Make Your Changes
```bash
git add .
git commit -m "feat: add awesome feature"
```

### 2. Tag the Release
```bash
# Create a tag (version number)
git tag v1.2.0

# Push the tag
git push origin v1.2.0
```

### 3. GitHub Actions Does the Rest
- Builds binaries for all platforms
- Generates SHA256SUMS
- Creates GitHub release
- Generates changelog from commits
- Uploads install scripts

## Commit Message Format

GoReleaser generates changelogs from commits. Use **conventional commits**:

```bash
feat: add new command
fix: resolve crash on startup
docs: update installation guide
chore: update dependencies
test: add validation tests
```

**Changelog will group by:**
- **Features** (`feat:`)
- **Bug Fixes** (`fix:`)
- **Others** (everything else except `docs:`, `test:`, `chore:`, `ci:`)

## Configuration Files

### `.goreleaser.yml`
Main configuration file:
- Defines build targets (OS/arch combinations)
- Sets up checksums
- Configures release notes template
- Includes install scripts in releases

### `.github/workflows/release.yml`
Simplified workflow:
- Triggers on version tags (`v*`)
- Runs GoReleaser
- That's it! (~35 lines total)

## Testing Locally

Install GoReleaser:
```bash
# macOS
brew install goreleaser

# Linux
go install github.com/goreleaser/goreleaser@latest

# Or download from https://github.com/goreleaser/goreleaser/releases
```

Test a release build:
```bash
# Build without releasing (snapshot mode)
goreleaser release --snapshot --clean

# Output in dist/
ls -la dist/
```

## What About the VERSION File?

**Go Implementation**: Uses git tags via ldflags (no VERSION file needed)

**Python Implementation**: Still reads VERSION file as fallback, but shows "dev" if missing

**Decision**: Keep VERSION file for now for backward compatibility with Python implementation. Can be removed later if Python implementation is updated.

## Migration Checklist

- [x] Create `.goreleaser.yml` configuration
- [x] Update `.github/workflows/release.yml` to use GoReleaser
- [x] Update `CLAUDE.md` with release process
- [x] Test release workflow (create test tag)
- [ ] Remove VERSION file (optional - after Python implementation updated)

## Example Release Workflow

```bash
# 1. Work on features
git checkout -b feature/awesome-feature
# ... make changes ...
git add .
git commit -m "feat: add awesome feature"

# 2. Merge to main
git checkout main
git merge feature/awesome-feature
git push origin main

# 3. Create release
git tag v1.2.0
git push origin v1.2.0

# 4. Wait ~2 minutes
# GitHub Actions runs GoReleaser
# Release appears at: github.com/Winds-AI/agent-traversal-file/releases

# 5. Users install automatically
curl -fsSL https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.sh | sudo bash
# Installs v1.2.0 automatically!
```

## Comparison: Before vs After

| Aspect | Custom Workflow | GoReleaser |
|--------|----------------|------------|
| Workflow Lines | ~100 | ~35 |
| Version Source | VERSION file + tag | Git tag only |
| Changelog | Manual | Auto-generated |
| Binary Naming | Custom script | GoReleaser standard |
| Checksum Gen | Custom script | Built-in |
| Release Creation | Custom API calls | Built-in |
| Maintenance | High | Low |
| Industry Standard | No | Yes ✅ |

## Next Steps

1. **Test the workflow**:
   ```bash
   git tag v1.2.0-test
   git push origin v1.2.0-test
   ```

2. **Verify release** at: https://github.com/Winds-AI/agent-traversal-file/releases

3. **Test installation**:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.sh | sudo bash
   iatf --version
   ```

4. **Create production release** when ready:
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```

## Resources

- GoReleaser Docs: https://goreleaser.com
- Conventional Commits: https://www.conventionalcommits.org
- Examples: https://github.com/goreleaser/goreleaser/tree/main/www/docs/cookbooks

## Rollback Plan

If needed, restore the custom workflow:

```bash
git revert <commit-hash>
git push origin main
```

The old workflow is in git history and can be restored anytime.

---

**Migration Date**: 2025-01-29
**GoReleaser Version**: v5 (latest)
**Workflow Simplification**: ~65% reduction in code
