# Changelog

## 0.1.3 - 2026-02-11

### Fixed
- Prevented preview command registration from failing when `vscode-languageclient` is unavailable in packaged installs
- Extension now degrades gracefully by disabling LSP features instead of failing activation

## 0.1.2 - 2026-02-11

### Added
- New `IATF: Open Preview` command for `.iatf` files
- Editor title toolbar button for quick preview access (same editor group, not split by default)
- Live preview panel that updates as the source document changes
- In-preview Table of Contents for quick section jump navigation
- Clickable `{@section-id}` references that jump to target sections in preview

### Changed
- Preview now focuses on reader-friendly output: section title, section summary, and section content only
- Technical metadata (hashes, created/modified markers, annotation syntax) is hidden in preview
- `{@section-id}` references are visually highlighted in preview content, with missing targets marked clearly

## 0.1.1 - 2026-02-11

### Changed
- Reworked syntax highlighting hierarchy to reduce visual noise in `.iatf` files
- Promoted `@title`, section summaries, and `Created`/`Modified` dates with dedicated scopes and stronger emphasis
- De-emphasized low-priority metadata such as hashes, separators, braces, and index scaffolding
- Split key/value captures for metadata fields to allow precise theming control

## 0.0.5 - 2026-01-26

### Added
- Comprehensive color theme with semantic color assignments
- Optimized color scheme for readability and visual hierarchy
- Token color customizations in package.json for all IATF elements

### Enhanced
- Section delimiter colors (bright magenta, bold)
- Section ID highlighting (gold, consistent across INDEX and CONTENT)
- Reference highlighting with link-like appearance (bright cyan, underlined)
- Metadata and annotation colors (light blue)
- Improved README with feature list and color scheme documentation

## 0.0.4

### Fixed
- Updated package.json metadata
- Improved marketplace presentation

## 0.0.3

### Added
- Enhanced TextMate grammar patterns
- Support for all IATF syntax elements

## 0.0.2

### Added
- Additional syntax patterns for content blocks
- Reference syntax highlighting
- Comment support

## 0.0.1 - Initial Release

### Added
- Initial TextMate grammar for IATF syntax highlighting
- Basic support for headers, INDEX, and CONTENT sections
- Section block tags and metadata highlighting
