package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

const VERSION = "1.0.0"

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
}

func validateNesting(lines []string, contentStart int) error {
	openPattern := regexp.MustCompile(`^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	closePattern := regexp.MustCompile(`^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	openSections := []string{}

	for _, line := range lines[contentStart:] {
		if match := openPattern.FindStringSubmatch(line); match != nil {
			openSections = append(openSections, match[1])
		} else if match := closePattern.FindStringSubmatch(line); match != nil {
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
		fmt.Printf("ATF Tools v%s\n", VERSION)
		os.Exit(0)
	case "rebuild":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: atf rebuild <file>")
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
			fmt.Fprintln(os.Stderr, "Usage: atf watch <file>")
			os.Exit(1)
		}
		os.Exit(watchCommand(os.Args[2]))
	case "unwatch":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: atf unwatch <file>")
			os.Exit(1)
		}
		os.Exit(unwatchCommand(os.Args[2]))
	case "validate":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: atf validate <file>")
			os.Exit(1)
		}
		os.Exit(validateCommand(os.Args[2]))
	case "index":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: Missing file argument")
			fmt.Fprintln(os.Stderr, "Usage: atf index <file>")
			os.Exit(1)
		}
		os.Exit(indexCommand(os.Args[2]))
	case "read":
		if len(os.Args) < 4 {
			fmt.Fprintln(os.Stderr, "Error: Missing arguments")
			fmt.Fprintln(os.Stderr, "Usage: atf read <file> <section-id>")
			fmt.Fprintln(os.Stderr, "       atf read <file> --title \"Title\"")
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
	default:
		fmt.Fprintf(os.Stderr, "Error: Unknown command: %s\n", command)
		fmt.Fprintln(os.Stderr, "Run 'atf --help' for usage information")
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Printf(`ATF Tools v%s

Usage:
    atf rebuild <file>              Rebuild index for a single file
    atf rebuild-all [directory]     Rebuild all .atf files in directory
    atf watch <file>                Watch file and auto-rebuild on changes
    atf unwatch <file>              Stop watching a file
    atf watch --list                List all watched files
    atf validate <file>             Validate ATF file structure
    atf index <file>                Output INDEX section only
    atf read <file> <section-id>    Extract section by ID
    atf read <file> --title "Title" Extract section by title
    atf --help                      Show this help message
    atf --version                   Show version

Examples:
    atf rebuild document.atf
    atf rebuild-all ./docs
    atf watch api-reference.atf
    atf validate my-doc.atf
    atf index document.atf
    atf read document.atf intro
    atf read document.atf --title "Introduction"

For more information, visit: https://github.com/atf-tools/atf
`, VERSION)
}

func parseContentSection(lines []string, contentStart int) []Section {
	sections := []Section{}
	stack := []int{}
	inHeader := []bool{}
	summaryContinuation := []bool{}

	openPattern := regexp.MustCompile(`^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	closePattern := regexp.MustCompile(`^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}`)

	for i := contentStart; i < len(lines); i++ {
		line := lines[i]

		// Opening tag
		if match := openPattern.FindStringSubmatch(line); match != nil {
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
					sections[stack[len(stack)-1]].Created = strings.TrimSpace(line[9:])
					summaryContinuation[len(summaryContinuation)-1] = false
				} else if strings.HasPrefix(line, "@modified:") {
					sections[stack[len(stack)-1]].Modified = strings.TrimSpace(line[10:])
					summaryContinuation[len(summaryContinuation)-1] = false
				} else if strings.HasPrefix(line, "@hash:") {
					sections[stack[len(stack)-1]].XHash = strings.TrimSpace(line[6:])
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

		// Closing tag: {/id}
		if match := closePattern.FindStringSubmatch(line); match != nil {
			if len(stack) > 0 && sections[stack[len(stack)-1]].ID == match[1] {
				idx := stack[len(stack)-1]
				sections[idx].End = i + 1 // 1-indexed
				stack = stack[:len(stack)-1]
				inHeader = inHeader[:len(inHeader)-1]
				summaryContinuation = summaryContinuation[:len(summaryContinuation)-1]
			}
			continue
		}

		// Collect actual content lines (excluding opening/closing tags and metadata)
		if len(stack) > 0 && !inHeader[len(inHeader)-1] {
			// Extract title from first heading
			if strings.HasPrefix(line, "#") && !strings.HasPrefix(sections[stack[len(stack)-1]].Title, "#") {
				sections[stack[len(stack)-1]].Title = strings.TrimSpace(strings.TrimLeft(line, "#"))
			}
			// Add to ContentLines
			sections[stack[len(stack)-1]].ContentLines = append(sections[stack[len(stack)-1]].ContentLines, line)
		}
	}

	return sections
}

func computeContentHash(contentLines []string) string {
	// Compute truncated SHA256 hash of content (Git-style 7 chars)
	contentText := strings.Join(contentLines, "\n")
	sum := sha256.Sum256([]byte(contentText))
	fullHash := hex.EncodeToString(sum[:])
	return fullHash[:7] // Git-style truncated hash
}

func countWords(contentLines []string) int {
	// Count words in content lines
	text := strings.Join(contentLines, " ")
	// Split on whitespace and count non-empty strings
	words := strings.Fields(text)
	return len(words)
}

func updateContentMetadata(lines []string, contentStart int, sections []Section) []string {
	// Create a map of section_id -> section for quick lookup
	sectionMap := make(map[string]*Section)
	for i := range sections {
		sectionMap[sections[i].ID] = &sections[i]
	}

	// Track current section being processed
	var currentSectionID string
	var metadataEndLine int

	openPattern := regexp.MustCompile(`^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	closePattern := regexp.MustCompile(`^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}`)

	i := contentStart
	for i < len(lines) {
		line := lines[i]

		// Opening tag
		if match := openPattern.FindStringSubmatch(line); match != nil {
			currentSectionID = match[1]
			metadataEndLine = 0
			i++
			continue
		}

		// Closing tag
		if match := closePattern.FindStringSubmatch(line); match != nil {
			currentSectionID = ""
			i++
			continue
		}

		// Process metadata lines
		if currentSectionID != "" {
			if section, ok := sectionMap[currentSectionID]; ok {
				// Check if we're still in metadata
				if strings.HasPrefix(line, "@") {
					if strings.HasPrefix(line, "@modified:") {
						// Update @modified
						lines[i] = fmt.Sprintf("@modified: %s", section.Modified)
					} else if strings.HasPrefix(line, "@hash:") {
						// Update @hash
						lines[i] = fmt.Sprintf("@hash: %s", section.XHash)
					}
					i++
					continue
				} else if metadataEndLine == 0 {
					// We've reached the end of metadata, insert missing fields if needed
					metadataEndLine = i

					// Check if @hash needs to be inserted
					// Look back to see if we already have @hash
					hasHash := false
					for j := i - 1; j > contentStart; j-- {
						if strings.HasPrefix(lines[j], fmt.Sprintf("{#%s}", currentSectionID)) {
							break
						}
						if strings.HasPrefix(lines[j], "@hash:") {
							hasHash = true
							break
						}
					}

					// Insert @hash if missing
					if !hasHash && section.XHash != "" {
						// Insert at current position
						newLines := make([]string, len(lines)+1)
						copy(newLines[:i], lines[:i])
						newLines[i] = fmt.Sprintf("@hash: %s", section.XHash)
						copy(newLines[i+1:], lines[i:])
						lines = newLines
						i++
					}
				}
			}
		}

		i++
	}

	return lines
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

		indexLines = append(indexLines, "")
	}

	return indexLines
}

func rebuildIndex(filepath string) error {
	content, err := os.ReadFile(filepath)
	if err != nil {
		return err
	}

	lines := strings.Split(string(content), "\n")

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

	// Auto-update @modified based on content hash changes
	today := time.Now().Format("2006-01-02")
	for i := range sections {
		// Compute current content hash
		newHash := computeContentHash(sections[i].ContentLines)
		oldHash := sections[i].XHash

		// Compute word count
		sections[i].WordCount = countWords(sections[i].ContentLines)

		// Check if content changed
		if oldHash != "" && oldHash != newHash {
			// Content changed! Update @modified
			sections[i].Modified = today
		} else if oldHash == "" {
			// New section or first time with hash tracking
			if sections[i].Modified == "" {
				sections[i].Modified = today
			}
		}
		// else: hash matches, preserve existing @modified

		// Update hash for writing back
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
			if strings.HasPrefix(strings.TrimSpace(line), ":::ATF/") {
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
		return fmt.Errorf("invalid ATF file format")
	}

	// Update @modified and @hash in CONTENT section
	lines = updateContentMetadata(lines, contentStart, sections)

	// Recalculate indexEnd after updateContentMetadata (lines may have been inserted)
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
	newSpan := 1 + len(newIndex) + 1 // blank + index + blank
	lineDelta := newSpan - originalSpan
	if lineDelta != 0 {
		for i := range sections {
			sections[i].Start += lineDelta
			sections[i].End += lineDelta
		}
		newIndex = generateIndex(sections, contentHash)
	}

	// Rebuild file
	newLines := []string{}
	newLines = append(newLines, lines[:headerEnd]...)
	newLines = append(newLines, "")
	newLines = append(newLines, newIndex...)
	newLines = append(newLines, "")
	newLines = append(newLines, lines[indexEnd:]...)

	newContent := strings.Join(newLines, "\n")

	return os.WriteFile(filepath, []byte(newContent), 0644)
}

func rebuildCommand(filepath string) int {
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filepath)
		return 1
	}

	fmt.Printf("Rebuilding index: %s\n", filepath)

	if err := rebuildIndex(filepath); err != nil {
		fmt.Fprintf(os.Stderr, "✗ Failed to rebuild index: %v\n", err)
		return 1
	}

	fmt.Println("✓ Index rebuilt successfully")
	return 0
}

func rebuildAllCommand(directory string) int {
	if _, err := os.Stat(directory); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: Directory not found: %s\n", directory)
		return 1
	}

	var atfFiles []string
	err := filepath.Walk(directory, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && filepath.Ext(path) == ".atf" {
			atfFiles = append(atfFiles, path)
		}
		return nil
	})

	if err != nil {
		fmt.Fprintf(os.Stderr, "Error walking directory: %v\n", err)
		return 1
	}

	if len(atfFiles) == 0 {
		fmt.Printf("No .atf files found in %s\n", directory)
		return 0
	}

	fmt.Printf("Found %d .atf file(s)\n", len(atfFiles))

	successCount := 0
	for _, file := range atfFiles {
		fmt.Printf("\nProcessing: %s\n", file)
		if err := rebuildIndex(file); err != nil {
			fmt.Printf("  ✗ Failed: %v\n", err)
		} else {
			fmt.Println("  ✓ Success")
			successCount++
		}
	}

	fmt.Printf("\nCompleted: %d/%d files rebuilt successfully\n", successCount, len(atfFiles))

	if successCount == len(atfFiles) {
		return 0
	}
	return 1
}

func getWatchStateFile() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".atf", "watch.json")
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

func watchCommand(filePath string) int {
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

	info, _ := os.Stat(absPath)
	state[absPath] = WatchInfo{
		Started:      time.Now().Format(time.RFC3339),
		LastModified: float64(info.ModTime().Unix()),
	}

	if err := saveWatchState(state); err != nil {
		fmt.Fprintf(os.Stderr, "Error saving watch state: %v\n", err)
		return 1
	}

	fmt.Printf("Started watching: %s\n", filePath)
	fmt.Println("File will auto-rebuild on save")
	fmt.Printf("To stop: atf unwatch %s\n\n", filePath)
	fmt.Println("Press Ctrl+C to stop watching")

	lastMod := info.ModTime()
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		state, err := loadWatchState()
		if err == nil {
			if _, exists := state[absPath]; !exists {
				fmt.Printf("\nWatch stopped via unwatch: %s\n", filePath)
				break
			}
		}

		currentInfo, err := os.Stat(absPath)
		if err != nil {
			fmt.Printf("\nWarning: File no longer exists: %s\n", filePath)
			break
		}

		if currentInfo.ModTime().After(lastMod) {
			fmt.Printf("\n[%s] File changed, rebuilding...\n", time.Now().Format("15:04:05"))
			if err := rebuildIndex(absPath); err != nil {
				fmt.Printf("  ✗ Rebuild failed: %v\n", err)
			} else {
				fmt.Println("  ✓ Index rebuilt")
			}
			lastMod = currentInfo.ModTime()
		}
	}

	return 0
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

func indexCommand(filepath string) int {
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filepath)
		return 1
	}

	content, err := os.ReadFile(filepath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		return 1
	}

	lines := strings.Split(string(content), "\n")

	// Find INDEX section boundaries
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
		fmt.Fprintln(os.Stderr, "Error: Invalid ATF file format")
		return 1
	}

	// Output INDEX section (lines between markers, excluding the markers)
	for _, line := range lines[indexStart+1 : indexEnd] {
		fmt.Println(line)
	}

	return 0
}

func readCommand(filepath string, sectionID string) int {
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filepath)
		return 1
	}

	content, err := os.ReadFile(filepath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		return 1
	}

	lines := strings.Split(string(content), "\n")

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

	// Parse sections
	sections := parseContentSection(lines, contentStart)

	// Find matching section by ID
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

	// Extract and output section lines (convert from 1-indexed to 0-indexed)
	sectionLines := lines[targetSection.Start-1 : targetSection.End]
	for _, line := range sectionLines {
		fmt.Println(line)
	}

	return 0
}

func readByTitleCommand(filepath string, title string) int {
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filepath)
		return 1
	}

	content, err := os.ReadFile(filepath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		return 1
	}

	lines := strings.Split(string(content), "\n")

	// Find INDEX section
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
		fmt.Fprintln(os.Stderr, "Error: Invalid ATF file format")
		return 1
	}

	// Parse INDEX entries to extract title->ID mappings (preserve order)
	indexEntryPattern := regexp.MustCompile(`^#{1,6}\s+(.+?)\s*\{#([a-zA-Z][a-zA-Z0-9_-]*)\s*\|.*\}$`)

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

	// Find best title match (deterministic order)
	var matchedID string

	// 1. Exact match (case-insensitive)
	for _, entry := range entries {
		if strings.EqualFold(entry.title, title) {
			matchedID = entry.id
			break
		}
	}

	// 2. Contains match (case-insensitive)
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

	// Delegate to readCommand
	return readCommand(filepath, matchedID)
}

func validateCommand(filepath string) int {
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: File not found: %s\n", filepath)
		return 1
	}

	fmt.Printf("Validating: %s\n\n", filepath)

	content, err := os.ReadFile(filepath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file: %v\n", err)
		return 1
	}

	lines := strings.Split(string(content), "\n")
	errors := []string{}
	warnings := []string{}

	// Check 1: Format declaration
	if !strings.HasPrefix(lines[0], ":::ATF/") {
		errors = append(errors, "Missing format declaration (:::ATF/1.0)")
	} else {
		fmt.Println("✓ Format declaration found")
	}

	// Check 2: INDEX/CONTENT sections and order
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
		fmt.Println("✓ INDEX section found")
	} else {
		warnings = append(warnings, "No INDEX section (run 'atf rebuild' to create)")
	}

	if hasContent {
		fmt.Println("✓ CONTENT section found")
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

	// Check 4: Content hash matches (if present)
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
			matches := hashRe.FindStringSubmatch(contentHashLine)
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
					if actualHash != expectedHash {
						warnings = append(warnings, "INDEX Content-Hash does not match CONTENT (index may be stale)")
					}
				}
			}
		} else {
			warnings = append(warnings, "INDEX missing Content-Hash (run 'atf rebuild' to add)")
		}
	}

	// Check 5: All sections are properly closed and nested
	openSections := []string{}
	invalidNesting := false
	openPattern := regexp.MustCompile(`^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	closePattern := regexp.MustCompile(`^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	for _, line := range lines {
		if match := openPattern.FindStringSubmatch(line); match != nil {
			openSections = append(openSections, match[1])
		} else if match := closePattern.FindStringSubmatch(line); match != nil {
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
		fmt.Println("✓ All sections properly closed")
	}

	// Check 6: No content outside section blocks
	if !invalidNesting && contentStart != -1 {
		contentOpen := []string{}
		for i := contentStart; i < len(lines); i++ {
			line := lines[i]
			if match := openPattern.FindStringSubmatch(line); match != nil {
				contentOpen = append(contentOpen, match[1])
				continue
			}
			if match := closePattern.FindStringSubmatch(line); match != nil {
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

	// Check 7: INDEX entries match CONTENT
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

	// Check 8: Section IDs unique
	sectionIDs := make(map[string]bool)
	for _, line := range lines {
		if match := openPattern.FindStringSubmatch(line); match != nil {
			id := match[1]
			if sectionIDs[id] {
				errors = append(errors, fmt.Sprintf("Duplicate section ID: %s", id))
			}
			sectionIDs[id] = true
		}
	}

	if len(sectionIDs) > 0 {
		fmt.Printf("✓ Found %d section(s) with unique IDs\n", len(sectionIDs))
	} else {
		warnings = append(warnings, "No sections found in CONTENT")
	}

	// Summary
	fmt.Println()
	if len(errors) > 0 {
		fmt.Printf("✗ %d error(s) found:\n", len(errors))
		for _, err := range errors {
			fmt.Printf("  - %s\n", err)
		}
	}

	if len(warnings) > 0 {
		fmt.Printf("⚠ %d warning(s):\n", len(warnings))
		for _, warn := range warnings {
			fmt.Printf("  - %s\n", warn)
		}
	}

	if len(errors) == 0 && len(warnings) == 0 {
		fmt.Println("✓ File is valid!")
		return 0
	} else if len(errors) == 0 {
		fmt.Println("\n✓ File is valid (with warnings)")
		return 0
	}

	fmt.Println("\n✗ File is invalid")
	return 1
}
