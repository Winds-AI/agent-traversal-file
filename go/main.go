package main

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"syscall"
	"time"
)

var Version = "dev" // Set at build time via ldflags

func detectPreferredEOL(content []byte) string {
	// Preserve CRLF if the file contains any CRLF sequences. This avoids introducing mixed line endings
	// and keeps diffs smaller when users are on Windows.
	if bytes.Contains(content, []byte("\r\n")) {
		return "\r\n"
	}
	return "\n"
}

func normalizeNewlines(s string) string {
	// Make parsing/hashing stable across CRLF/LF, and avoid "\r" breaking hashes.
	s = strings.ReplaceAll(s, "\r\n", "\n")
	s = strings.ReplaceAll(s, "\r", "\n")
	return s
}

func splitNormalizedLines(content []byte) ([]string, string) {
	eol := detectPreferredEOL(content)
	text := normalizeNewlines(string(content))
	return strings.Split(text, "\n"), eol
}

// Pre-compiled regex patterns for section parsing
var (
	sectionOpenPattern  = regexp.MustCompile(`^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	sectionClosePattern = regexp.MustCompile(`^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	referencePattern    = regexp.MustCompile(`\{@([a-zA-Z][a-zA-Z0-9_-]*)\}`)
)

type Section struct {
	ID           string
	Title        string
	Start        int
	End          int
	Level        int
	Summary      string
	Created      string
	Modified     string
	XHash        string
	WordCount    int
	ContentLines []string // Actual content (excluding metadata)
}

type WatchState map[string]WatchInfo

type WatchInfo struct {
	Started      string  `json:"started"`
	LastModified float64 `json:"last_modified"`
	PID          int     `json:"pid,omitempty"`
}

func validateNesting(lines []string, contentStart int) error {
	openSections := []string{}

	for _, line := range lines[contentStart:] {
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			openSections = append(openSections, match[1])
		} else if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
			id := match[1]
			if len(openSections) > 0 && openSections[len(openSections)-1] == id {
				openSections = openSections[:len(openSections)-1]
			} else {
				return fmt.Errorf("closing tag without matching opening: %s", id)
			}
		}
	}

	if len(openSections) > 0 {
		return fmt.Errorf("unclosed section: %s", openSections[len(openSections)-1])
	}

	return nil
}

func isCodeFenceLine(line string) bool {
	return strings.TrimSpace(line) == "```"
}

// ReferenceLocation stores information about where a reference was found
type ReferenceLocation struct {
	LineNum           int
	ContainingSection string
}

// extractReferences extracts all {@section-id} references from content, ignoring fenced code blocks.
// Returns a map of section_id -> list of ReferenceLocation where it's referenced.
func extractReferences(lines []string, contentStart int) map[string][]ReferenceLocation {
	references := make(map[string][]ReferenceLocation)
	openSections := []string{}
	inCodeFence := false

	for i := contentStart; i < len(lines); i++ {
		line := lines[i]
		lineNum := i + 1

		if inCodeFence {
			if isCodeFenceLine(line) {
				inCodeFence = false
			}
			continue
		}
		if isCodeFenceLine(line) {
			inCodeFence = true
			continue
		}

		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			openSections = append(openSections, match[1])
			continue
		}
		if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
			if len(openSections) > 0 && openSections[len(openSections)-1] == match[1] {
				openSections = openSections[:len(openSections)-1]
			} else {
				openSections = []string{}
			}
			continue
		}

		matches := referencePattern.FindAllStringSubmatch(line, -1)
		for _, match := range matches {
			target := match[1]
			containingSection := ""
			if len(openSections) > 0 {
				containingSection = openSections[len(openSections)-1]
			}
			references[target] = append(references[target], ReferenceLocation{
				LineNum:           lineNum,
				ContainingSection: containingSection,
			})
		}
	}

	return references
}

// validateReferences validates that all references point to existing sections and no self-references exist.
// Returns a list of error messages (empty if valid).
func validateReferences(lines []string, contentStart int, sections []Section) []string {
	errors := []string{}

	// Build set of valid section IDs
	validIDs := make(map[string]bool)
	for _, section := range sections {
		validIDs[section.ID] = true
	}

	// Extract references
	references := extractReferences(lines, contentStart)

	type referenceInstance struct {
		Target            string
		LineNum           int
		ContainingSection string
	}

	orderedRefs := []referenceInstance{}
	for target, locations := range references {
		for _, loc := range locations {
			orderedRefs = append(orderedRefs, referenceInstance{
				Target:            target,
				LineNum:           loc.LineNum,
				ContainingSection: loc.ContainingSection,
			})
		}
	}

	sort.Slice(orderedRefs, func(i, j int) bool {
		if orderedRefs[i].LineNum != orderedRefs[j].LineNum {
			return orderedRefs[i].LineNum < orderedRefs[j].LineNum
		}
		if orderedRefs[i].Target != orderedRefs[j].Target {
			return orderedRefs[i].Target < orderedRefs[j].Target
		}
		return orderedRefs[i].ContainingSection < orderedRefs[j].ContainingSection
	})

	// Validate each reference in deterministic order
	for _, ref := range orderedRefs {
		if !validIDs[ref.Target] {
			errors = append(errors, fmt.Sprintf("Reference {@%s} at line %d: target section does not exist", ref.Target, ref.LineNum))
		} else if ref.Target == ref.ContainingSection {
			errors = append(errors, fmt.Sprintf("Reference {@%s} at line %d: self-reference not allowed", ref.Target, ref.LineNum))
		}
	}

	return errors
}

func findDuplicateSectionIDs(sections []Section) []string {
	seen := make(map[string]int)
	duplicates := []string{}
	for _, section := range sections {
		seen[section.ID]++
		if seen[section.ID] == 2 {
			duplicates = append(duplicates, section.ID)
		}
	}
	return duplicates
}

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	command := os.Args[1]

	switch command {
	case "--help", "-h", "help":
		printUsage()
		os.Exit(0)
	case "--version", "-v", "version":
		fmt.Printf("IATF Tools v%s\n", Version)
		os.Exit(0)
	case "rebuild":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: iatf rebuild <file>")
			os.Exit(1)
		}
		os.Exit(rebuildCommand(os.Args[2]))
	case "rebuild-all":
		directory := "."
		if len(os.Args) >= 3 {
			directory = os.Args[2]
		}
		os.Exit(rebuildAllCommand(directory))
	case "watch":
		if len(os.Args) >= 3 && os.Args[2] == "--list" {
			os.Exit(listWatched())
		}
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: iatf watch <file> [--debug]")
			os.Exit(1)
		}
		debug := len(os.Args) >= 4 && os.Args[3] == "--debug"
		os.Exit(watchCommand(os.Args[2], debug))
	case "watch-dir":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing directory argument")
			fmt.Fprintln(os.Stderr, "Usage: iatf watch-dir <dir> [--debug]")
			os.Exit(1)
		}
		debug := len(os.Args) >= 4 && os.Args[3] == "--debug"
		os.Exit(watchDirCommand(os.Args[2], debug))
	case "unwatch":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: iatf unwatch <file>")
			os.Exit(1)
		}
		os.Exit(unwatchCommand(os.Args[2]))
	case "validate":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: iatf validate <file>")
			os.Exit(1)
		}
		os.Exit(validateCommand(os.Args[2]))
	case "index":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: iatf index <file>")
			os.Exit(1)
		}
		os.Exit(indexCommand(os.Args[2]))
	case "read":
		if len(os.Args) < 4 {
			fmt.Fprintln(os.Stderr, "Error: Missing arguments")
			fmt.Fprintln(os.Stderr, "Usage: iatf read <file> <section-id>")
			fmt.Fprintln(os.Stderr, "       iatf read <file> --title \"Title\"")
			os.Exit(1)
		}

		// Check for --title flag
		if os.Args[3] == "--title" {
			if len(os.Args) < 5 {
				fmt.Fprintln(os.Stderr, "Error: Missing title argument")
				os.Exit(1)
			}
			os.Exit(readByTitleCommand(os.Args[2], os.Args[4]))
		} else {
			os.Exit(readCommand(os.Args[2], os.Args[3]))
		}
	case "graph":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: iatf graph <file> [--show-incoming]")
			os.Exit(1)
		}
		showIncoming := false
		if len(os.Args) >= 4 && os.Args[3] == "--show-incoming" {
			showIncoming = true
		}
		os.Exit(graphCommand(os.Args[2], showIncoming))
	case "daemon":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing daemon subcommand")
			fmt.Fprintln(os.Stderr, "Usage: iatf daemon <start|stop|status|run|install|uninstall>")
			os.Exit(1)
		}
		subCmd := os.Args[2]
		switch subCmd {
		case "start":
			debug := len(os.Args) >= 4 && os.Args[3] == "--debug"
			os.Exit(daemonStartCommand(debug))
		case "stop":
			os.Exit(daemonStopCommand())
		case "status":
			os.Exit(daemonStatusCommand())
		case "run":
			debug := len(os.Args) >= 4 && os.Args[3] == "--debug"
			os.Exit(daemonRunCommand(debug))
		case "install":
			os.Exit(daemonInstallCommand())
		case "uninstall":
			os.Exit(daemonUninstallCommand())
		default:
			fmt.Fprintf(os.Stderr, "Error: Unknown daemon subcommand: %s\n", subCmd)
			fmt.Fprintln(os.Stderr, "Usage: iatf daemon <start|stop|status|run|install|uninstall>")
			os.Exit(1)
		}
	default:
		fmt.Fprintf(os.Stderr, "Error: Unknown command: %s\n", command)
		fmt.Fprintln(os.Stderr, "Run 'iatf --help' for usage information")
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Printf(`IATF Tools v%s

Usage:
    iatf rebuild <file>              Rebuild index for a single file
    iatf rebuild-all [directory]     Rebuild all .iatf files in directory
    iatf watch <file> [--debug]      Watch file and auto-rebuild on changes
    iatf watch-dir <dir> [--debug]   Watch directory tree for .iatf files
    iatf unwatch <file>              Stop watching a file
    iatf watch --list                List all watched files
    iatf validate <file>             Validate iatf file structure
    iatf index <file>                Output INDEX section only
    iatf read <file> <section-id>    Extract section by ID
    iatf read <file> --title "Title" Extract section by title
    iatf graph <file>                Show section reference graph
    iatf graph <file> --show-incoming  Show incoming references (impact analysis)
    iatf --help                      Show this help message
    iatf --version                   Show version

Daemon Commands:
    iatf daemon start [--debug]      Start system-wide daemon
    iatf daemon stop                 Stop running daemon
    iatf daemon status               Show daemon status and watched paths
    iatf daemon install              Install as OS service (auto-start on boot)
    iatf daemon uninstall            Remove OS service

Examples:
    iatf rebuild document.iatf
    iatf rebuild-all ./docs
    iatf watch api-reference.iatf
    iatf watch api-reference.iatf --debug
    iatf watch-dir ./docs
    iatf validate my-doc.iatf
    iatf index document.iatf
    iatf read document.iatf intro
    iatf read document.iatf --title "Introduction"
    iatf daemon start
    iatf daemon status

For more information, visit: https://github.com/Winds-AI/agent-traversal-file
`, Version)
}

func parseContentSection(lines []string, contentStart int) []Section {
	sections := []Section{}
	stack := []int{}
	inHeader := []bool{}
	summaryContinuation := []bool{}

	for i := contentStart; i < len(lines); i++ {
		line := lines[i]

		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			section := Section{
				ID:    match[1],
				Title: match[1],
				Start: i + 1, // 1-indexed
				Level: len(stack) + 1,
			}
			sections = append(sections, section)
			stack = append(stack, len(sections)-1)
			inHeader = append(inHeader, true)
			summaryContinuation = append(summaryContinuation, false)
			continue
		}

		if len(stack) > 0 && inHeader[len(inHeader)-1] {
			if strings.HasPrefix(line, "@") {
				if strings.HasPrefix(line, "@summary:") {
					sections[stack[len(stack)-1]].Summary = strings.TrimSpace(line[9:])
					summaryContinuation[len(summaryContinuation)-1] = true
				} else if strings.HasPrefix(line, "@created:") {
					// @created is stored in INDEX, not CONTENT
					summaryContinuation[len(summaryContinuation)-1] = false
				}
				continue
			}
			if (strings.HasPrefix(line, " ") || strings.HasPrefix(line, "\t")) && summaryContinuation[len(summaryContinuation)-1] {
				sections[stack[len(stack)-1]].Summary = fmt.Sprintf(
					"%s %s",
					sections[stack[len(stack)-1]].Summary,
					strings.TrimSpace(line),
				)
				continue
			}
			inHeader[len(inHeader)-1] = false
			summaryContinuation[len(summaryContinuation)-1] = false
		}

		if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
			if len(stack) > 0 && sections[stack[len(stack)-1]].ID == match[1] {
				idx := stack[len(stack)-1]
				sections[idx].End = i + 1 // 1-indexed
				stack = stack[:len(stack)-1]
				inHeader = inHeader[:len(inHeader)-1]
				summaryContinuation = summaryContinuation[:len(summaryContinuation)-1]
			}
			continue
		}

		if len(stack) > 0 && !inHeader[len(inHeader)-1] {
			if strings.HasPrefix(line, "#") && !strings.HasPrefix(sections[stack[len(stack)-1]].Title, "#") {
				sections[stack[len(stack)-1]].Title = strings.TrimSpace(strings.TrimLeft(line, "#"))
			}
			sections[stack[len(stack)-1]].ContentLines = append(sections[stack[len(stack)-1]].ContentLines, line)
		}
	}

	return sections
}

func computeContentHash(contentLines []string) string {
	contentText := strings.Join(contentLines, "\n")
	sum := sha256.Sum256([]byte(contentText))
	return hex.EncodeToString(sum[:])[:7]
}

func countWords(contentLines []string) int {
	text := strings.Join(contentLines, " ")
	return len(strings.Fields(text))
}

type indexMeta struct {
	Hash     string
	Modified string
	Created  string
}

func parseIndexMetadata(lines []string) map[string]indexMeta {
	indexStart := -1
	indexEnd := -1
	for i, line := range lines {
		if strings.TrimSpace(line) == "===INDEX===" {
			indexStart = i
		} else if strings.TrimSpace(line) == "===CONTENT===" {
			indexEnd = i
			break
		}
	}

	if indexStart == -1 || indexEnd == -1 {
		return map[string]indexMeta{}
	}

	entryRe := regexp.MustCompile(`^#{1,6}\s+.*\{#([a-zA-Z][a-zA-Z0-9_-]*)\s*\|`)
	metadata := map[string]indexMeta{}
	currentID := ""

	for _, line := range lines[indexStart+1 : indexEnd] {
		stripped := strings.TrimSpace(line)
		if stripped == "" {
			currentID = ""
			continue
		}

		if match := entryRe.FindStringSubmatch(stripped); match != nil {
			currentID = match[1]
			if _, exists := metadata[currentID]; !exists {
				metadata[currentID] = indexMeta{}
			}
			continue
		}

		if currentID == "" {
			continue
		}

		if strings.HasPrefix(stripped, "Hash:") {
			meta := metadata[currentID]
			meta.Hash = strings.TrimSpace(strings.TrimPrefix(stripped, "Hash:"))
			metadata[currentID] = meta
			continue
		}

		if strings.HasPrefix(stripped, "Created:") || strings.HasPrefix(stripped, "Modified:") {
			parts := strings.Split(stripped, "|")
			meta := metadata[currentID]
			for _, part := range parts {
				part = strings.TrimSpace(part)
				if strings.HasPrefix(part, "Created:") {
					meta.Created = strings.TrimSpace(strings.TrimPrefix(part, "Created:"))
				}
				if strings.HasPrefix(part, "Modified:") {
					meta.Modified = strings.TrimSpace(strings.TrimPrefix(part, "Modified:"))
				}
			}
			metadata[currentID] = meta
		}
	}

	return metadata
}

func generateIndex(sections []Section, contentHash string) []string {
	indexLines := []string{
		"===INDEX===",
		"<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->",
		fmt.Sprintf("<!-- Generated: %s -->", time.Now().UTC().Format(time.RFC3339)),
		fmt.Sprintf("<!-- Content-Hash: sha256:%s -->", contentHash),
		"",
	}

	for _, section := range sections {
		levelMarker := strings.Repeat("#", section.Level)
		indexLine := fmt.Sprintf("%s %s {#%s | lines:%d-%d | words:%d}",
			levelMarker, section.Title, section.ID, section.Start, section.End, section.WordCount)
		indexLines = append(indexLines, indexLine)

		if section.Summary != "" {
			indexLines = append(indexLines, fmt.Sprintf("> %s", section.Summary))
		}

		if section.Created != "" || section.Modified != "" {
			timestamps := []string{}
			if section.Created != "" {
				timestamps = append(timestamps, fmt.Sprintf("Created: %s", section.Created))
			}
			if section.Modified != "" {
				timestamps = append(timestamps, fmt.Sprintf("Modified: %s", section.Modified))
			}
			indexLines = append(indexLines, fmt.Sprintf("  %s", strings.Join(timestamps, " | ")))
		}

		if section.XHash != "" {
			indexLines = append(indexLines, fmt.Sprintf("  Hash: %s", section.XHash))
		}

		indexLines = append(indexLines, "")
	}

	return indexLines
}

func rebuildIndex(filePath string) error {
	raw, err := os.ReadFile(filePath)
	if err != nil {
		return err
	}

	lines, preferredEOL := splitNormalizedLines(raw)

	// Find CONTENT section
	contentStart := -1
	for i, line := range lines {
		if strings.TrimSpace(line) == "===CONTENT===" {
			contentStart = i + 1
			break
		}
	}

	if contentStart == -1 {
		return fmt.Errorf("no ===CONTENT=== section found")
	}

	// Validate nesting before parsing for index rebuild (fail-fast approach)
	if err := validateNesting(lines, contentStart); err != nil {
		return fmt.Errorf("invalid section nesting: %w", err)
	}

	// Parse sections
	sections := parseContentSection(lines, contentStart)

	if len(sections) == 0 {
		return fmt.Errorf("no sections found")
	}

	duplicateIDs := findDuplicateSectionIDs(sections)
	if len(duplicateIDs) > 0 {
		for _, id := range duplicateIDs {
			fmt.Fprintf(os.Stderr, "  - Duplicate section ID: %s\n", id)
		}
		return fmt.Errorf("%d duplicate section ID(s) found", len(duplicateIDs))
	}

	// Validate references before proceeding
	refErrors := validateReferences(lines, contentStart, sections)
	if len(refErrors) > 0 {
		for _, err := range refErrors {
			fmt.Fprintf(os.Stderr, "  - %s\n", err)
		}
		return fmt.Errorf("%d reference error(s) found", len(refErrors))
	}

	// Parse existing INDEX metadata (hash/modified)
	indexMeta := parseIndexMetadata(lines)

	// Auto-update Modified based on content hash changes
	today := time.Now().Format("2006-01-02")
	for i := range sections {
		// Compute current content hash
		newHash := computeContentHash(sections[i].ContentLines)
		meta := indexMeta[sections[i].ID]

		// Compute word count
		sections[i].WordCount = countWords(sections[i].ContentLines)

		// Update Created
		if meta.Created != "" {
			sections[i].Created = meta.Created
		} else {
			sections[i].Created = today
		}

		// Update Modified
		if meta.Hash != "" && meta.Hash != newHash {
			sections[i].Modified = today
		} else if meta.Hash != "" {
			sections[i].Modified = meta.Modified
		} else if meta.Modified != "" {
			sections[i].Modified = meta.Modified
		} else {
			sections[i].Modified = today
		}

		// Update hash for INDEX output
		sections[i].XHash = newHash
	}

	// Find where to insert INDEX
	headerEnd := -1
	indexEnd := -1

	for i, line := range lines {
		if strings.TrimSpace(line) == "===INDEX===" {
			headerEnd = i
		} else if strings.TrimSpace(line) == "===CONTENT===" {
			indexEnd = i
			break
		}
	}

	if headerEnd == -1 {
		// No existing INDEX, insert after header
		for i, line := range lines {
			if strings.TrimSpace(line) == ":::IATF" {
				headerEnd = i + 1
				// Skip metadata lines
				for i+1 < len(lines) && strings.HasPrefix(lines[i+1], "@") {
					i++
					headerEnd = i + 1
				}
				break
			}
		}
	}

	if headerEnd == -1 || indexEnd == -1 {
		return fmt.Errorf("invalid iatf file format")
	}

	// Recalculate indexEnd before rebuild
	indexEnd = -1
	for i, line := range lines {
		if strings.TrimSpace(line) == "===CONTENT===" {
			indexEnd = i
			break
		}
	}
	if indexEnd == -1 {
		return fmt.Errorf("===CONTENT=== section lost after metadata update")
	}

	// Recalculate content hash after updates (Git-style 7 chars)
	contentText := strings.Join(lines[contentStart:], "\n")
	sum := sha256.Sum256([]byte(contentText))
	contentHash := hex.EncodeToString(sum[:])[:7]

	// Generate new INDEX (two-pass to adjust absolute line numbers)
	newIndex := generateIndex(sections, contentHash)
	originalSpan := indexEnd - headerEnd
	newSpan := len(newIndex) + 1 // index + blank
	lineDelta := newSpan - originalSpan
	if lineDelta != 0 {
		for i := range sections {
			sections[i].Start += lineDelta
			sections[i].End += lineDelta
		}
		newIndex = generateIndex(sections, contentHash)
	}

	// Rebuild file (normalize spacing around INDEX)
	preLines := append([]string{}, lines[:headerEnd]...)
	for len(preLines) > 0 && strings.TrimSpace(preLines[len(preLines)-1]) == "" {
		preLines = preLines[:len(preLines)-1]
	}

	postLines := append([]string{}, lines[indexEnd:]...)
	for len(postLines) > 0 && strings.TrimSpace(postLines[0]) == "" {
		postLines = postLines[1:]
	}

	newLines := []string{}
	newLines = append(newLines, preLines...)
	newLines = append(newLines, "")
	newLines = append(newLines, newIndex...)
	newLines = append(newLines, "")
	newLines = append(newLines, postLines...)

	newContent := strings.Join(newLines, "\n")
	if preferredEOL == "\r\n" {
		newContent = strings.ReplaceAll(newContent, "\n", "\r\n")
	}

	return os.WriteFile(filePath, []byte(newContent), 0644)
}

func rebuildCommand(filePath string) int {
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filePath)
		return 1
	}

	if !checkWatchedFile(filePath) {
		fmt.Println("Rebuild cancelled, no changes made.")
		return 1
	}

	fmt.Printf("Rebuilding index: %s\n", filePath)

	if err := rebuildIndex(filePath); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] Failed to rebuild index: %v\n", err)
		return 1
	}

	fmt.Println("[OK] Index rebuilt successfully")
	return 0
}

func rebuildAllCommand(directory string) int {
	if _, err := os.Stat(directory); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: Directory not found: %s\n", directory)
		return 1
	}

	var iatfFiles []string
	err := filepath.Walk(directory, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && filepath.Ext(path) == ".iatf" {
			iatfFiles = append(iatfFiles, path)
		}
		return nil
	})

	if err != nil {
		fmt.Fprintf(os.Stderr, "Error walking directory: %v\n", err)
		return 1
	}

	if len(iatfFiles) == 0 {
		fmt.Printf("No .iatf files found in %s\n", directory)
		return 0
	}

	fmt.Printf("Found %d .iatf file(s)\n", len(iatfFiles))

	successCount := 0
	for _, file := range iatfFiles {
		fmt.Printf("\nProcessing: %s\n", file)
		if err := rebuildIndex(file); err != nil {
			fmt.Printf("  [ERROR] Failed: %v\n", err)
		} else {
			fmt.Println("  [OK] Success")
			successCount++
		}
	}

	fmt.Printf("\nCompleted: %d/%d files rebuilt successfully\n", successCount, len(iatfFiles))

	if successCount == len(iatfFiles) {
		return 0
	}
	return 1
}

func getWatchStateFile() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".iatf", "watch.json")
}

func loadWatchState() (WatchState, error) {
	stateFile := getWatchStateFile()
	data, err := os.ReadFile(stateFile)
	if err != nil {
		if os.IsNotExist(err) {
			return make(WatchState), nil
		}
		return nil, err
	}

	var state WatchState
	err = json.Unmarshal(data, &state)
	return state, err
}

func saveWatchState(state WatchState) error {
	stateFile := getWatchStateFile()
	os.MkdirAll(filepath.Dir(stateFile), 0755)

	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(stateFile, data, 0644)
}

func promptUserConfirmation(message string, defaultValue bool) bool {
	promptSuffix := "[y/N]"
	if defaultValue {
		promptSuffix = "[Y/n]"
	}

	// Check if stdin is a terminal
	stat, _ := os.Stdin.Stat()
	if (stat.Mode() & os.ModeCharDevice) == 0 {
		// Not a terminal - return default to avoid hanging in CI/scripts
		return defaultValue
	}

	// Interactive terminal
	reader := bufio.NewReader(os.Stdin)
	fmt.Printf("%s %s: ", message, promptSuffix)
	response, err := reader.ReadString('\n')
	if err != nil {
		fmt.Println()
		return false
	}
	response = strings.TrimSpace(strings.ToLower(response))
	if response == "" {
		return defaultValue
	}
	return response == "y" || response == "yes"
}

func checkWatchedFile(filePath string) bool {
	state, err := loadWatchState()
	if err != nil {
		return true
	}

	absPath, err := filepath.Abs(filePath)
	if err != nil {
		return true
	}

	info, exists := state[absPath]
	if !exists {
		return true
	}

	// If no PID field (old format) or PID is not running, proceed
	if info.PID == 0 || !isProcessRunning(info.PID) {
		return true
	}

	// File is being watched by a running process
	fmt.Printf("\nWarning: This file is being watched by another process (PID %d)\n", info.PID)
	fmt.Println("A manual rebuild will trigger an automatic rebuild from the watch process.")
	fmt.Println("This will cause the file to be rebuilt twice.")
	fmt.Println()
	fmt.Println("Options:")
	fmt.Println("  - Press 'y' to proceed with manual rebuild anyway")
	fmt.Println("  - Press 'N' (default) to cancel")
	fmt.Printf("  - Run 'iatf unwatch %s' to stop watching first\n", filePath)
	fmt.Println()

	return promptUserConfirmation("Continue with manual rebuild", false)
}

func watchCommand(filePath string, debug bool) int {
	absPath, err := filepath.Abs(filePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}

	if _, err := os.Stat(absPath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filePath)
		return 1
	}

	state, err := loadWatchState()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading watch state: %v\n", err)
		return 1
	}

	pid := os.Getpid()
	info, _ := os.Stat(absPath)
	state[absPath] = WatchInfo{
		Started:      time.Now().Format(time.RFC3339),
		LastModified: float64(info.ModTime().Unix()),
		PID:          pid,
	}

	if err := saveWatchState(state); err != nil {
		fmt.Fprintf(os.Stderr, "Error saving watch state: %v\n", err)
		return 1
	}

	// Cleanup function to remove PID from watch state
	cleanupPID := func() {
		currentState, err := loadWatchState()
		if err != nil {
			return
		}
		if watchInfo, exists := currentState[absPath]; exists {
			// Only remove if it's still our PID
			if watchInfo.PID == pid {
				delete(currentState, absPath)
				saveWatchState(currentState)
			}
		}
	}

	// Setup signal handling for cleanup
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	fmt.Printf("Watching: %s\n", filePath)

	lastMod := info.ModTime()
	ticker := time.NewTicker(250 * time.Millisecond)
	defer ticker.Stop()

	var debounceTimer *time.Timer
	var timerMu sync.Mutex

	for {
		select {
		case <-sigChan:
			timerMu.Lock()
			if debounceTimer != nil {
				debounceTimer.Stop()
			}
			timerMu.Unlock()
			cleanupPID()
			if debug {
				fmt.Println("\nWatch stopped")
			}
			return 0
		case <-ticker.C:
			state, err := loadWatchState()
			if err == nil {
				if _, exists := state[absPath]; !exists {
					if debug {
						fmt.Printf("\nWatch stopped via unwatch: %s\n", filePath)
					}
					return 0
				}
			}

			currentInfo, err := os.Stat(absPath)
			if err != nil {
				cleanupPID()
				if debug {
					fmt.Printf("\nWarning: File no longer exists: %s\n", filePath)
				}
				return 0
			}

			if currentInfo.ModTime().After(lastMod) {
				lastMod = currentInfo.ModTime()
				if debug {
					fmt.Printf("[%s] Change detected, waiting 3s...\n", filepath.Base(absPath))
				}

				timerMu.Lock()
				if debounceTimer != nil {
					debounceTimer.Stop()
				}
				debounceTimer = time.AfterFunc(3*time.Second, func() {
					processFileForWatch(absPath, debug)
				})
				timerMu.Unlock()
			}
		}
	}
}

// processFileForWatch validates and rebuilds a single file
func processFileForWatch(filePath string, debug bool) {
	valid, errors := validateFileQuiet(filePath)
	if !valid {
		if debug {
			fmt.Printf("[%s] Validation failed:\n", filepath.Base(filePath))
			for _, e := range errors {
				fmt.Printf("  - %s\n", e)
			}
		}
		return
	}
	if err := rebuildIndex(filePath); err != nil {
		if debug {
			fmt.Printf("[%s] Rebuild failed: %v\n", filepath.Base(filePath), err)
		}
		return
	}
	if debug {
		fmt.Printf("[%s] Index rebuilt\n", filepath.Base(filePath))
	}
}

func unwatchCommand(filePath string) int {
	absPath, _ := filepath.Abs(filePath)

	state, err := loadWatchState()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading watch state: %v\n", err)
		return 1
	}

	if _, exists := state[absPath]; exists {
		delete(state, absPath)
		if err := saveWatchState(state); err != nil {
			fmt.Fprintf(os.Stderr, "Error saving watch state: %v\n", err)
			return 1
		}
		fmt.Printf("Stopped watching: %s\n", filePath)
		return 0
	}

	fmt.Printf("File is not being watched: %s\n", filePath)
	return 1
}

func listWatched() int {
	state, err := loadWatchState()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading watch state: %v\n", err)
		return 1
	}

	if len(state) == 0 {
		fmt.Println("No files are being watched")
		return 0
	}

	fmt.Printf("Watching %d file(s):\n\n", len(state))
	for path, info := range state {
		fmt.Printf("  %s\n", path)
		fmt.Printf("    Since: %s\n", info.Started)
	}

	return 0
}

// fileState tracks per-file debounce state for directory watching
type fileState struct {
	lastModTime time.Time
	timer       *time.Timer
}

func watchDirCommand(dirPath string, debug bool) int {
	absDir, err := filepath.Abs(dirPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}

	info, err := os.Stat(absDir)
	if os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: Directory not found: %s\n", dirPath)
		return 1
	}
	if !info.IsDir() {
		fmt.Fprintf(os.Stderr, "Error: Not a directory: %s\n", dirPath)
		return 1
	}

	files := make(map[string]*fileState)
	var filesMu sync.Mutex

	// Initial scan to find all .iatf files
	var watchedFiles []string
	filepath.WalkDir(absDir, func(path string, d fs.DirEntry, err error) error {
		if err == nil && !d.IsDir() && strings.HasSuffix(path, ".iatf") {
			watchedFiles = append(watchedFiles, path)
			stat, _ := os.Stat(path)
			files[path] = &fileState{lastModTime: stat.ModTime()}
		}
		return nil
	})

	if len(watchedFiles) == 0 {
		fmt.Println("No .iatf files found in directory")
		return 0
	}

	fmt.Println("Watching:")
	for _, f := range watchedFiles {
		fmt.Printf("  %s\n", f)
	}

	// Setup signal handling
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	ticker := time.NewTicker(250 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-sigChan:
			filesMu.Lock()
			for _, state := range files {
				if state.timer != nil {
					state.timer.Stop()
				}
			}
			filesMu.Unlock()
			if debug {
				fmt.Println("\nWatch stopped")
			}
			return 0
		case <-ticker.C:
			filepath.WalkDir(absDir, func(path string, d fs.DirEntry, err error) error {
				if err != nil || d.IsDir() || !strings.HasSuffix(path, ".iatf") {
					return nil
				}

				stat, statErr := os.Stat(path)
				if statErr != nil {
					return nil
				}

				filesMu.Lock()
				state, exists := files[path]

				if !exists {
					// New file detected
					files[path] = &fileState{lastModTime: stat.ModTime()}
					filesMu.Unlock()
					if debug {
						fmt.Printf("New file detected: %s\n", path)
					}
					return nil
				}

				if stat.ModTime().After(state.lastModTime) {
					state.lastModTime = stat.ModTime()
					if debug {
						fmt.Printf("[%s] Change detected, waiting 3s...\n", filepath.Base(path))
					}

					if state.timer != nil {
						state.timer.Stop()
					}
					pathCopy := path // Capture for closure
					state.timer = time.AfterFunc(3*time.Second, func() {
						processFileForWatch(pathCopy, debug)
					})
				}
				filesMu.Unlock()
				return nil
			})

			// Check for deleted files
			filesMu.Lock()
			for path, state := range files {
				if _, err := os.Stat(path); os.IsNotExist(err) {
					if state.timer != nil {
						state.timer.Stop()
					}
					delete(files, path)
					if debug {
						fmt.Printf("Stopped watching (deleted): %s\n", path)
					}
				}
			}
			filesMu.Unlock()
		}
	}
}

// DaemonConfig holds the daemon configuration
type DaemonConfig struct {
	WatchPaths []string `json:"watch_paths"`
}

func getDaemonConfigPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".iatf", "daemon.json")
}

func getDaemonPIDPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".iatf", "daemon.pid")
}

func getDaemonLogPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".iatf", "daemon.log")
}

func loadDaemonConfig() DaemonConfig {
	configPath := getDaemonConfigPath()
	data, err := os.ReadFile(configPath)
	if err != nil {
		return DaemonConfig{}
	}

	var config DaemonConfig
	json.Unmarshal(data, &config)
	return config
}

func saveDaemonPID(pid int) error {
	pidPath := getDaemonPIDPath()
	os.MkdirAll(filepath.Dir(pidPath), 0755)
	return os.WriteFile(pidPath, []byte(fmt.Sprintf("%d", pid)), 0644)
}

func loadDaemonPID() (int, error) {
	pidPath := getDaemonPIDPath()
	data, err := os.ReadFile(pidPath)
	if err != nil {
		return 0, err
	}

	var pid int
	_, err = fmt.Sscanf(string(data), "%d", &pid)
	return pid, err
}

func removeDaemonPIDFile() {
	os.Remove(getDaemonPIDPath())
}

func checkDaemonRunning() (bool, int) {
	pid, err := loadDaemonPID()
	if err != nil {
		return false, 0
	}

	if isProcessRunning(pid) {
		return true, pid
	}

	// Clean up stale PID file
	removeDaemonPIDFile()
	return false, 0
}

func daemonStartCommand(debug bool) int {
	config := loadDaemonConfig()
	if len(config.WatchPaths) == 0 {
		fmt.Println("No watch paths configured.")
		fmt.Printf("Add paths to %s\n", getDaemonConfigPath())
		fmt.Println("\nExample config:")
		fmt.Println(`{
    "watch_paths": [
        "/path/to/your/projects",
        "/another/path"
    ]
}`)
		return 1
	}

	if isRunning, pid := checkDaemonRunning(); isRunning {
		fmt.Printf("Daemon already running (PID %d)\n", pid)
		return 1
	}

	// Start detached process
	args := []string{"daemon", "run"}
	if debug {
		args = append(args, "--debug")
	}

	cmd := exec.Command(os.Args[0], args...)
	cmd.SysProcAttr = daemonSysProcAttr()

	if err := cmd.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "Error starting daemon: %v\n", err)
		return 1
	}

	saveDaemonPID(cmd.Process.Pid)
	fmt.Printf("Daemon started (PID %d)\n", cmd.Process.Pid)
	fmt.Printf("Watching %d path(s)\n", len(config.WatchPaths))
	return 0
}

func daemonStopCommand() int {
	pid, err := loadDaemonPID()
	if err != nil {
		fmt.Println("Daemon not running")
		return 1
	}

	if !isProcessRunning(pid) {
		removeDaemonPIDFile()
		fmt.Println("Daemon not running (stale PID file removed)")
		return 1
	}

	process, err := os.FindProcess(pid)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error finding process: %v\n", err)
		return 1
	}

	if err := process.Signal(syscall.SIGTERM); err != nil {
		fmt.Fprintf(os.Stderr, "Error stopping daemon: %v\n", err)
		return 1
	}

	removeDaemonPIDFile()
	fmt.Println("Daemon stopped")
	return 0
}

func daemonStatusCommand() int {
	config := loadDaemonConfig()

	if isRunning, pid := checkDaemonRunning(); isRunning {
		fmt.Printf("Daemon: running (PID %d)\n", pid)
	} else {
		fmt.Println("Daemon: stopped")
	}

	fmt.Printf("\nWatch paths (%d):\n", len(config.WatchPaths))
	if len(config.WatchPaths) == 0 {
		fmt.Printf("  (none configured)\n")
		fmt.Printf("\nAdd paths to %s\n", getDaemonConfigPath())
	} else {
		for _, p := range config.WatchPaths {
			fmt.Printf("  %s\n", p)
		}
	}

	installed, service := isServiceInstalled()
	if installed {
		fmt.Printf("\nOS Service: installed (%s)\n", service)
	} else {
		fmt.Println("\nOS Service: not installed")
	}
	return 0
}

func daemonRunCommand(debug bool) int {
	config := loadDaemonConfig()
	if len(config.WatchPaths) == 0 {
		return 1
	}

	// Redirect output to log file
	logPath := getDaemonLogPath()
	os.MkdirAll(filepath.Dir(logPath), 0755)
	logFile, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err == nil {
		os.Stdout = logFile
		os.Stderr = logFile
	}

	fmt.Printf("[%s] Daemon started\n", time.Now().Format(time.RFC3339))
	for _, p := range config.WatchPaths {
		fmt.Printf("  Watching: %s\n", p)
	}

	// Watch all configured paths
	watchMultipleDirs(config.WatchPaths, debug)
	return 0
}

// watchMultipleDirs watches multiple directories simultaneously
func watchMultipleDirs(paths []string, debug bool) {
	files := make(map[string]*fileState)
	var filesMu sync.Mutex

	// Initial scan of all paths
	for _, dirPath := range paths {
		filepath.WalkDir(dirPath, func(path string, d fs.DirEntry, err error) error {
			if err == nil && !d.IsDir() && strings.HasSuffix(path, ".iatf") {
				stat, _ := os.Stat(path)
				files[path] = &fileState{lastModTime: stat.ModTime()}
			}
			return nil
		})
	}

	// Setup signal handling
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	ticker := time.NewTicker(250 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-sigChan:
			filesMu.Lock()
			for _, state := range files {
				if state.timer != nil {
					state.timer.Stop()
				}
			}
			filesMu.Unlock()
			fmt.Printf("[%s] Daemon stopped\n", time.Now().Format(time.RFC3339))
			return
		case <-ticker.C:
			for _, dirPath := range paths {
				filepath.WalkDir(dirPath, func(path string, d fs.DirEntry, err error) error {
					if err != nil || d.IsDir() || !strings.HasSuffix(path, ".iatf") {
						return nil
					}

					stat, statErr := os.Stat(path)
					if statErr != nil {
						return nil
					}

					filesMu.Lock()
					state, exists := files[path]

					if !exists {
						files[path] = &fileState{lastModTime: stat.ModTime()}
						filesMu.Unlock()
						if debug {
							fmt.Printf("[%s] New file: %s\n", time.Now().Format(time.RFC3339), path)
						}
						return nil
					}

					if stat.ModTime().After(state.lastModTime) {
						state.lastModTime = stat.ModTime()
						if debug {
							fmt.Printf("[%s] Change: %s\n", time.Now().Format(time.RFC3339), path)
						}

						if state.timer != nil {
							state.timer.Stop()
						}
						pathCopy := path
						state.timer = time.AfterFunc(3*time.Second, func() {
							valid, errors := validateFileQuiet(pathCopy)
							if !valid {
								fmt.Printf("[%s] Validation failed: %s\n", time.Now().Format(time.RFC3339), pathCopy)
								for _, e := range errors {
									fmt.Printf("  - %s\n", e)
								}
								return
							}
							if err := rebuildIndex(pathCopy); err != nil {
								fmt.Printf("[%s] Rebuild failed: %s - %v\n", time.Now().Format(time.RFC3339), pathCopy, err)
								return
							}
							fmt.Printf("[%s] Rebuilt: %s\n", time.Now().Format(time.RFC3339), pathCopy)
						})
					}
					filesMu.Unlock()
					return nil
				})
			}

			// Check for deleted files
			filesMu.Lock()
			for path, state := range files {
				if _, err := os.Stat(path); os.IsNotExist(err) {
					if state.timer != nil {
						state.timer.Stop()
					}
					delete(files, path)
					if debug {
						fmt.Printf("[%s] Deleted: %s\n", time.Now().Format(time.RFC3339), path)
					}
				}
			}
			filesMu.Unlock()
		}
	}
}

func indexCommand(filePath string) int {
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filePath)
		return 1
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		return 1
	}

	lines, _ := splitNormalizedLines(content)

	indexStart := -1
	indexEnd := -1
	for i, line := range lines {
		if strings.TrimSpace(line) == "===INDEX===" {
			indexStart = i
		} else if strings.TrimSpace(line) == "===CONTENT===" {
			indexEnd = i
			break
		}
	}

	if indexStart == -1 || indexEnd == -1 {
		fmt.Fprintln(os.Stderr, "Error: INDEX not generated")
		return 1
	}

	contentStart := indexEnd + 1
	if err := validateNesting(lines, contentStart); err != nil {
		fmt.Fprintf(os.Stderr, "Error: Invalid section nesting: %v\n", err)
		return 1
	}

	for _, line := range lines[indexStart+1 : indexEnd] {
		fmt.Println(line)
	}

	return 0
}

func readCommand(filePath string, sectionID string) int {
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filePath)
		return 1
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		return 1
	}

	lines, _ := splitNormalizedLines(content)

	indexStart := -1
	contentStart := -1
	for i, line := range lines {
		if strings.TrimSpace(line) == "===CONTENT===" {
			contentStart = i + 1
			break
		}
		if strings.TrimSpace(line) == "===INDEX===" {
			indexStart = i
		}
	}

	if indexStart == -1 {
		fmt.Fprintln(os.Stderr, "Error: No ===INDEX=== section found")
		return 1
	}

	if contentStart == -1 {
		fmt.Fprintln(os.Stderr, "Error: No ===CONTENT=== section found")
		return 1
	}

	sections := parseContentSection(lines, contentStart)

	var targetSection *Section
	for i := range sections {
		if sections[i].ID == sectionID {
			targetSection = &sections[i]
			break
		}
	}

	if targetSection == nil {
		fmt.Fprintf(os.Stderr, "Error: Section not found: %s\n", sectionID)
		return 1
	}

	sectionLines := lines[targetSection.Start-1 : targetSection.End]
	for _, line := range sectionLines {
		fmt.Println(line)
	}

	return 0
}

func readByTitleCommand(filePath string, title string) int {
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filePath)
		return 1
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		return 1
	}

	lines, _ := splitNormalizedLines(content)

	indexStart := -1
	indexEnd := -1
	for i, line := range lines {
		if strings.TrimSpace(line) == "===INDEX===" {
			indexStart = i
		} else if strings.TrimSpace(line) == "===CONTENT===" {
			indexEnd = i
			break
		}
	}

	if indexStart == -1 || indexEnd == -1 {
		fmt.Fprintln(os.Stderr, "Error: Invalid iatf file format")
		return 1
	}

	indexEntryPattern := regexp.MustCompile(`^#{1,6}\s+(.+)\s*\{#([a-zA-Z][a-zA-Z0-9_-]*)\s*\|.*\}$`)

	type indexEntry struct {
		title string
		id    string
	}

	entries := []indexEntry{}
	for _, line := range lines[indexStart+1 : indexEnd] {
		match := indexEntryPattern.FindStringSubmatch(strings.TrimSpace(line))
		if match != nil {
			entries = append(entries, indexEntry{title: match[1], id: match[2]})
		}
	}

	var matchedID string

	for _, entry := range entries {
		if strings.EqualFold(entry.title, title) {
			matchedID = entry.id
			break
		}
	}

	if matchedID == "" {
		titleLower := strings.ToLower(title)
		for _, entry := range entries {
			if strings.Contains(strings.ToLower(entry.title), titleLower) {
				matchedID = entry.id
				break
			}
		}
	}

	if matchedID == "" {
		fmt.Fprintf(os.Stderr, "Error: No section found with title matching: %s\n", title)
		return 1
	}

	return readCommand(filePath, matchedID)
}

func graphCommand(filePath string, showIncoming bool) int {
	// Extract base filename first before any shadowing
	baseFilename := filepath.Base(filePath)

	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filePath)
		return 1
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		return 1
	}

	lines, _ := splitNormalizedLines(content)

	// Find CONTENT section start
	contentStart := -1
	for i, line := range lines {
		if strings.TrimSpace(line) == "===CONTENT===" {
			contentStart = i + 1
			break
		}
	}

	if contentStart == -1 {
		fmt.Fprintln(os.Stderr, "Error: No ===CONTENT=== section found")
		return 1
	}

	if err := validateNesting(lines, contentStart); err != nil {
		fmt.Fprintf(os.Stderr, "Error: Invalid section nesting: %v\n", err)
		return 1
	}

	// Parse sections to get ordered list
	sections := parseContentSection(lines, contentStart)

	if len(sections) == 0 {
		fmt.Fprintln(os.Stderr, "Error: No sections found in CONTENT")
		return 1
	}

	// Extract references (returns map of target -> locations where it's referenced)
	// This is the "incoming" map: targetID -> who references it
	incomingRefsMap := extractReferences(lines, contentStart)

	// Build outgoing reference map (section -> what it references)
	outgoingRefs := make(map[string][]string)
	for targetID, locations := range incomingRefsMap {
		for _, loc := range locations {
			if loc.ContainingSection != "" {
				// Add targetID to the list of refs from ContainingSection
				if !contains(outgoingRefs[loc.ContainingSection], targetID) {
					outgoingRefs[loc.ContainingSection] = append(outgoingRefs[loc.ContainingSection], targetID)
				}
			}
		}
	}

	// Convert incoming refs to simpler format
	incomingRefs := make(map[string][]string)
	for targetID, locations := range incomingRefsMap {
		for _, loc := range locations {
			if loc.ContainingSection != "" {
				if !contains(incomingRefs[targetID], loc.ContainingSection) {
					incomingRefs[targetID] = append(incomingRefs[targetID], loc.ContainingSection)
				}
			}
		}
	}

	// Sort references for deterministic output
	for sectionID := range outgoingRefs {
		sort.Strings(outgoingRefs[sectionID])
	}
	for sectionID := range incomingRefs {
		sort.Strings(incomingRefs[sectionID])
	}

	// Output in compact format
	fmt.Printf("@graph: %s\n\n", baseFilename)

	if showIncoming {
		// Show incoming references (who references this section)
		for _, section := range sections {
			refs := incomingRefs[section.ID]
			if len(refs) > 0 {
				fmt.Printf("%s <- %s\n", section.ID, strings.Join(refs, ", "))
			} else {
				fmt.Println(section.ID)
			}
		}
	} else {
		// Show outgoing references (what this section references)
		for _, section := range sections {
			refs := outgoingRefs[section.ID]
			if len(refs) > 0 {
				fmt.Printf("%s -> %s\n", section.ID, strings.Join(refs, ", "))
			} else {
				fmt.Println(section.ID)
			}
		}
	}

	return 0
}

func contains(slice []string, value string) bool {
	for _, item := range slice {
		if item == value {
			return true
		}
	}
	return false
}

// validateFileQuiet performs validation without printing, returns errors
func validateFileQuiet(filePath string) (bool, []string) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return false, []string{fmt.Sprintf("Cannot read file: %v", err)}
	}

	lines, _ := splitNormalizedLines(content)
	errors := []string{}

	// Check format declaration
	if len(lines) == 0 || strings.TrimSpace(lines[0]) != ":::IATF" {
		errors = append(errors, "Missing format declaration (:::IATF)")
	}

	// Check INDEX and CONTENT sections exist
	indexPositions := []int{}
	contentPositions := []int{}
	for i, line := range lines {
		if strings.TrimSpace(line) == "===INDEX===" {
			indexPositions = append(indexPositions, i)
		} else if strings.TrimSpace(line) == "===CONTENT===" {
			contentPositions = append(contentPositions, i)
		}
	}

	hasContent := len(contentPositions) > 0
	if !hasContent {
		errors = append(errors, "Missing CONTENT section")
	}

	if len(indexPositions) > 1 {
		errors = append(errors, "Multiple INDEX sections found")
	}
	if len(contentPositions) > 1 {
		errors = append(errors, "Multiple CONTENT sections found")
	}
	if len(indexPositions) > 0 && hasContent && indexPositions[0] > contentPositions[0] {
		errors = append(errors, "INDEX section appears after CONTENT")
	}

	// Validate nesting
	contentStart := -1
	for i, line := range lines {
		if strings.TrimSpace(line) == "===CONTENT===" {
			contentStart = i + 1
			break
		}
	}

	if contentStart != -1 {
		if err := validateNesting(lines, contentStart); err != nil {
			errors = append(errors, fmt.Sprintf("Invalid section nesting: %v", err))
		}
	}

	// Check for unclosed/mismatched sections
	openSections := []string{}
	for _, line := range lines {
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			openSections = append(openSections, match[1])
		} else if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
			id := match[1]
			if len(openSections) > 0 && openSections[len(openSections)-1] == id {
				openSections = openSections[:len(openSections)-1]
			} else {
				errors = append(errors, fmt.Sprintf("Closing tag without matching opening: %s", id))
			}
		}
	}
	for _, id := range openSections {
		errors = append(errors, fmt.Sprintf("Unclosed section: %s", id))
	}

	// Check for duplicate section IDs
	sectionIDs := make(map[string]bool)
	for _, line := range lines {
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			id := match[1]
			if sectionIDs[id] {
				errors = append(errors, fmt.Sprintf("Duplicate section ID: %s", id))
			}
			sectionIDs[id] = true
		}
	}

	// Validate references
	if contentStart != -1 && len(openSections) == 0 {
		parsedSections := parseContentSection(lines, contentStart)
		refErrors := validateReferences(lines, contentStart, parsedSections)
		errors = append(errors, refErrors...)
	}

	return len(errors) == 0, errors
}

func validateCommand(filePath string) int {
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filePath)
		return 1
	}

	fmt.Printf("Validating: %s\n\n", filePath)

	content, err := os.ReadFile(filePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		return 1
	}

	lines, _ := splitNormalizedLines(content)
	errors := []string{}
	warnings := []string{}

	if strings.TrimSpace(lines[0]) != ":::IATF" {
		errors = append(errors, "Missing format declaration (:::IATF)")
	} else {
		fmt.Println("[OK] Format declaration found")
	}
	indexPositions := []int{}
	contentPositions := []int{}
	for i, line := range lines {
		if strings.TrimSpace(line) == "===INDEX===" {
			indexPositions = append(indexPositions, i)
		} else if strings.TrimSpace(line) == "===CONTENT===" {
			contentPositions = append(contentPositions, i)
		}
	}
	hasIndex := len(indexPositions) > 0
	hasContent := len(contentPositions) > 0

	if hasIndex {
		fmt.Println("[OK] INDEX section found")
	} else {
		warnings = append(warnings, "No INDEX section (Run 'iatf rebuild' to create)")
	}

	if hasContent {
		fmt.Println("[OK] CONTENT section found")
	} else {
		errors = append(errors, "Missing CONTENT section")
	}

	if len(indexPositions) > 1 {
		errors = append(errors, "Multiple INDEX sections found")
	}
	if len(contentPositions) > 1 {
		errors = append(errors, "Multiple CONTENT sections found")
	}
	if hasIndex && hasContent && indexPositions[0] > contentPositions[0] {
		errors = append(errors, "INDEX section appears after CONTENT")
	}

	indexStart := -1
	contentStart := -1
	for i, line := range lines {
		if strings.TrimSpace(line) == "===INDEX===" {
			indexStart = i
		} else if strings.TrimSpace(line) == "===CONTENT===" {
			contentStart = i + 1
			break
		}
	}

	if contentStart != -1 {
		if err := validateNesting(lines, contentStart); err != nil {
			errors = append(errors, fmt.Sprintf("Invalid section nesting: %v", err))
		}
	}

	if hasIndex {
		contentHashLine := ""
		if indexStart != -1 && contentStart != -1 {
			for _, line := range lines[indexStart:contentStart] {
				if strings.HasPrefix(line, "<!-- Content-Hash:") {
					contentHashLine = line
					break
				}
			}
		}
		if contentHashLine != "" && contentStart != -1 {
			hashRe := regexp.MustCompile(`^<!-- Content-Hash:\s*([a-z0-9]+):([a-f0-9]+)\s*-->$`)
			matches := hashRe.FindStringSubmatch(strings.TrimSpace(contentHashLine))
			if matches == nil {
				warnings = append(warnings, "Invalid Content-Hash format in INDEX")
			} else {
				algo := matches[1]
				expectedHash := matches[2]
				if algo != "sha256" {
					warnings = append(warnings, fmt.Sprintf("Unsupported Content-Hash algorithm: %s", algo))
				} else {
					contentText := strings.Join(lines[contentStart:], "\n")
					sum := sha256.Sum256([]byte(contentText))
					actualHash := hex.EncodeToString(sum[:])
					hashMatches := false
					if len(expectedHash) == 7 {
						hashMatches = strings.HasPrefix(actualHash, expectedHash)
					} else {
						hashMatches = actualHash == expectedHash
					}
					if !hashMatches {
						warnings = append(warnings, "INDEX Content-Hash does not match CONTENT (index may be stale)")
					}
				}
			}
		} else {
			warnings = append(warnings, "INDEX missing Content-Hash (Run 'iatf rebuild' to add)")
		}
	}

	openSections := []string{}
	invalidNesting := false
	for _, line := range lines {
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			openSections = append(openSections, match[1])
		} else if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
			id := match[1]
			if len(openSections) > 0 && openSections[len(openSections)-1] == id {
				openSections = openSections[:len(openSections)-1]
			} else {
				errors = append(errors, fmt.Sprintf("Closing tag without matching opening: %s", id))
				invalidNesting = true
			}
		}
	}
	if len(openSections) > 0 {
		for _, id := range openSections {
			errors = append(errors, fmt.Sprintf("Unclosed section: %s", id))
		}
		invalidNesting = true
	}
	if !invalidNesting {
		fmt.Println("[OK] All sections properly closed")
	}

	if !invalidNesting && contentStart != -1 {
		contentOpen := []string{}
		for i := contentStart; i < len(lines); i++ {
			line := lines[i]
			if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
				contentOpen = append(contentOpen, match[1])
				continue
			}
			if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
				if len(contentOpen) > 0 && contentOpen[len(contentOpen)-1] == match[1] {
					contentOpen = contentOpen[:len(contentOpen)-1]
				}
				continue
			}
			if len(contentOpen) == 0 && strings.TrimSpace(line) != "" {
				errors = append(errors, fmt.Sprintf("Content outside section block at line %d", i+1))
				break
			}
		}
	}

	if !invalidNesting && hasIndex && contentStart != -1 && indexStart != -1 {
		indexEntryRe := regexp.MustCompile(`^#{1,6}\s+.*\{#([a-zA-Z][a-zA-Z0-9_-]*)\s*\|\s*lines:(\d+)-(\d+)[^}]*\}$`)
		indexRanges := map[string][2]int{}
		for _, line := range lines[indexStart+1 : contentStart] {
			match := indexEntryRe.FindStringSubmatch(strings.TrimSpace(line))
			if match == nil {
				continue
			}
			id := match[1]
			start := match[2]
			end := match[3]
			if _, exists := indexRanges[id]; exists {
				errors = append(errors, fmt.Sprintf("Duplicate INDEX section ID: %s", id))
				continue
			}
			startNum := 0
			endNum := 0
			fmt.Sscanf(start, "%d", &startNum)
			fmt.Sscanf(end, "%d", &endNum)
			if startNum < 1 || endNum < startNum || endNum > len(lines) {
				errors = append(errors, fmt.Sprintf("Invalid line range for INDEX section: %s", id))
			}
			indexRanges[id] = [2]int{startNum, endNum}
		}

		contentSections := map[string][2]int{}
		parsedSections := parseContentSection(lines, contentStart)
		for _, section := range parsedSections {
			contentSections[section.ID] = [2]int{section.Start, section.End}
			if section.Level > 2 {
				errors = append(errors, fmt.Sprintf("Section nesting exceeds 2 levels: %s", section.ID))
			}
		}

		for id := range indexRanges {
			if _, exists := contentSections[id]; !exists {
				errors = append(errors, fmt.Sprintf("INDEX references missing CONTENT section: %s", id))
			}
		}
		for id := range contentSections {
			if _, exists := indexRanges[id]; !exists {
				errors = append(errors, fmt.Sprintf("CONTENT section missing from INDEX: %s", id))
			}
		}
		for id, contentRange := range contentSections {
			if indexRange, exists := indexRanges[id]; exists {
				if indexRange != contentRange {
					errors = append(errors, fmt.Sprintf("INDEX line range mismatch for section: %s", id))
				}
			}
		}
	}

	sectionIDs := make(map[string]bool)
	for _, line := range lines {
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			id := match[1]
			if sectionIDs[id] {
				errors = append(errors, fmt.Sprintf("Duplicate section ID: %s", id))
			}
			sectionIDs[id] = true
		}
	}

	if len(sectionIDs) > 0 {
		fmt.Printf("[OK] Found %d section(s) with unique IDs\n", len(sectionIDs))
	} else {
		warnings = append(warnings, "No sections found in CONTENT")
	}

	if !invalidNesting && contentStart != -1 {
		parsedSectionsForRefs := parseContentSection(lines, contentStart)
		refErrors := validateReferences(lines, contentStart, parsedSectionsForRefs)
		if len(refErrors) == 0 {
			fmt.Println("[OK] All references valid")
		} else {
			for _, refErr := range refErrors {
				errors = append(errors, refErr)
			}
		}
	}

	fmt.Println()
	if len(errors) > 0 {
		fmt.Printf("[ERROR] %d error(s) found:\n", len(errors))
		for _, err := range errors {
			fmt.Printf("  - %s\n", err)
		}
	}

	if len(warnings) > 0 {
		fmt.Printf("[WARN] %d warning(s):\n", len(warnings))
		for _, warn := range warnings {
			fmt.Printf("  - %s\n", warn)
		}
	}

	if len(errors) == 0 && len(warnings) == 0 {
		fmt.Println("[OK] File is valid!")
		return 0
	} else if len(errors) == 0 {
		fmt.Println("\n[WARN] File is valid (with warnings)")
		return 0
	}

	fmt.Println("\n[ERROR] File is invalid")
	return 1
}
