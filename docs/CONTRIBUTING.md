# Contributing to IATF Tools

Thank you for your interest in contributing to IATF Tools!

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/Winds-AI/agent-traversal-file/issues)
2. If not, create a new issue with:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Your OS and version
   - IATF Tools version (`iatf --version`)

### Suggesting Features

1. Check [Issues](https://github.com/Winds-AI/agent-traversal-file/issues) for existing feature requests
2. Create a new issue with:
   - Clear description of the feature
   - Use case / why it's needed
   - Example of how it would work

### Code Contributions

1. **Fork the repository**
2. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Test your changes**:
   ```bash
   # Build and test
   cd go
   go run main.go rebuild ../examples/simple.iatf
   go run main.go validate ../examples/simple.iatf
   ```
5. **Commit your changes** (use conventional commits):
   ```bash
   git commit -m "feat: add awesome feature"
   git commit -m "fix: resolve validation bug"
   ```
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request**

### Code Style

**Go:**
- Follow Go conventions (`gofmt`)
- Use descriptive variable names
- Add comments for exported functions
- Keep functions focused and small

**Commits:**
- Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, etc.
- This helps auto-generate changelogs in releases

### Testing

Before submitting:
- Test on multiple platforms if possible (Linux, macOS, Windows)
- Test all commands (rebuild, rebuild-all, watch, unwatch, validate, index, read)
- Verify installation scripts work (if modifying `installers/install.sh` or `installers/install.ps1`)
- Test with example files in `examples/` directory

### Areas We Need Help

- [x] **Editor Plugins**: VS Code ([Available](https://open-vsx.org/extension/Winds-AI/iatf))
- [ ] **Editor Plugins**: Vim, Neovim, Emacs, Sublime extensions
- [ ] **Language Server Protocol (LSP)**: Universal editor support
- [ ] **Conversion Tools**: Markdown -> IATF, HTML -> IATF
- [ ] **Documentation**: Examples, tutorials, use cases
- [ ] **Testing**: More comprehensive test suite
- [ ] **Localization**: Translations for error messages
- [ ] **Performance**: Optimize for very large files

### Documentation

When adding features:
- Update README.md
- Add examples if applicable
- Update docs/SPECIFICATION.md if format changes
- Add to CHANGELOG.md

### Ideas & Future Directions

See [IDEAS.md](./IDEAS.md) for a list of proposed features and experiments we're interested in, including:
- FUSE/Dokany/macFUSE filesystem mounting for transparent IATF access
- Editor plugins for auto-rebuilding index on save
- LSP integration for semantic navigation
- And more...

### Questions?

- Open a [Discussion](https://github.com/Winds-AI/agent-traversal-file/discussions)
- Ask in an issue
- Check existing documentation

## Code of Conduct

Be respectful, constructive, and helpful. We're all here to make IATF better!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.






