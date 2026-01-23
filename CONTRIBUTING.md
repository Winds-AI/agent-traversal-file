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
   # Python
   python python/iatf.py rebuild examples/simple.iatf
   
   # Go
   cd go
   go run main.go rebuild ../examples/simple.iatf
   ```
5. **Commit your changes**:
   ```bash
   git commit -m "Add feature: description"
   ```
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request**

### Code Style

**Python:**
- Follow PEP 8
- Use type hints where appropriate
- Add docstrings for functions
- Keep functions focused and small

**Go:**
- Follow Go conventions (`gofmt`)
- Use descriptive variable names
- Add comments for exported functions
- Keep functions focused and small

### Testing

Before submitting:
- Test on multiple platforms if possible
- Test all 5 commands (rebuild, rebuild-all, watch, unwatch, validate)
- Verify installers work (if modifying installer scripts)

### Areas We Need Help

- [ ] **Editor Plugins**: VS Code, Vim, Emacs extensions
- [ ] **Language Server Protocol (LSP)**: Universal editor support
- [ ] **Conversion Tools**: Markdown â†’ IATF, HTML â†’ IATF
- [ ] **Documentation**: Examples, tutorials, use cases
- [ ] **Testing**: More comprehensive test suite
- [ ] **Localization**: Translations for error messages
- [ ] **Performance**: Optimize for very large files

### Documentation

When adding features:
- Update README.md
- Add examples if applicable
- Update SPECIFICATION.md if format changes
- Add to CHANGELOG.md

### Ideas & Future Directions

See [IDEAS.md](IDEAS.md) for a list of proposed features and experiments we're interested in, including:
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






