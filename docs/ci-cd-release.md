# CI/CD & Release

## CI/CD Pipeline

- **Tool**: GoReleaser (config: `.goreleaser.yml`)
- **Workflow**: Single job (`.github/workflows/release.yml`)
- **Platforms**: Windows (amd64), macOS (amd64, arm64), Linux (amd64, arm64)

### Release Artifacts

- Compiled binaries for all platforms
- Install scripts (`install.sh`, `install.ps1`)
- SHA256SUMS
- Auto-generated changelog

### Triggering Releases

- Automatic: Push version tags (`v*`)
- Manual: Workflow dispatch in GitHub Actions
- **Note**: Version is read from git tags (no VERSION file needed)

## Release Process

### Creating a Release

1. Commit all changes:
   ```bash
   git add . && git commit -m "feat: your changes"
   ```

2. Create and push tag:
   ```bash
   git tag v1.2.0 && git push origin v1.2.0
   ```

3. GitHub Actions automatically builds and releases

### Changelog

- GoReleaser generates changelog from commit messages
- Use conventional commits: `feat:`, `fix:`, `docs:`, etc.

### Local Testing

Test releases before pushing:
```bash
goreleaser release --snapshot --clean
```

### Installer Verification

If you modify installers, verify behavior on at least one target platform.
