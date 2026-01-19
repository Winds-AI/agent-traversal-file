package main

import (
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
	ID       string
	Title    string
	Start    int
	End      int
	Level    int
	Summary  string
	Created  string
	Modified string
}

type WatchState map[string]WatchInfo

type WatchInfo struct {
	Started      string  `json:"started"`
	LastModified float64 `json:"last_modified"`
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
    atf --help                      Show this help message
    atf --version                   Show version

Examples:
    atf rebuild document.atf
    atf rebuild-all ./docs
    atf watch api-reference.atf
    atf validate my-doc.atf

For more information, visit: https://github.com/atf-tools/atf
`, VERSION)
}

func parseContentSection(lines []string, contentStart int) []Section {
	sections := []Section{}
	stack := []*Section{}

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
			stack = append(stack, &section)
			sections = append(sections, section)
		} else if strings.HasPrefix(line, "@summary:") && len(stack) > 0 {
			stack[len(stack)-1].Summary = strings.TrimSpace(line[9:])
		} else if strings.HasPrefix(line, "@created:") && len(stack) > 0 {
			stack[len(stack)-1].Created = strings.TrimSpace(line[9:])
		} else if strings.HasPrefix(line, "@modified:") && len(stack) > 0 {
			stack[len(stack)-1].Modified = strings.TrimSpace(line[10:])
		} else if strings.HasPrefix(line, "#") && len(stack) > 0 && !strings.HasPrefix(stack[len(stack)-1].Title, "#") {
			stack[len(stack)-1].Title = strings.TrimSpace(strings.TrimLeft(line, "#"))
		} else if match := closePattern.FindStringSubmatch(line); match != nil {
			if len(stack) > 0 && stack[len(stack)-1].ID == match[1] {
				idx := len(sections) - len(stack)
				sections[idx].End = i + 1 // 1-indexed
				sections[idx].Summary = stack[len(stack)-1].Summary
				sections[idx].Created = stack[len(stack)-1].Created
				sections[idx].Modified = stack[len(stack)-1].Modified
				sections[idx].Title = stack[len(stack)-1].Title
				stack = stack[:len(stack)-1]
			}
		}
	}

	return sections
}

func generateIndex(sections []Section) []string {
	indexLines := []string{
		"===INDEX===",
		"<!-- AUTO-GENERATED - DO NOT EDIT -->",
		fmt.Sprintf("<!-- Generated: %s -->", time.Now().UTC().Format(time.RFC3339)),
		"",
	}

	for _, section := range sections {
		levelMarker := strings.Repeat("#", section.Level)
		indexLine := fmt.Sprintf("%s %s {#%s | lines:%d-%d}",
			levelMarker, section.Title, section.ID, section.Start, section.End)
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

	// Parse sections
	sections := parseContentSection(lines, contentStart)

	if len(sections) == 0 {
		return fmt.Errorf("no sections found")
	}

	// Generate new INDEX
	newIndex := generateIndex(sections)

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

	if headerEnd == -1 {
		return fmt.Errorf("invalid ATF file format")
	}

	// Rebuild file
	newLines := append(lines[:headerEnd], "")
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

	// Check 2: INDEX section
	hasIndex := false
	for _, line := range lines {
		if strings.TrimSpace(line) == "===INDEX===" {
			hasIndex = true
			break
		}
	}
	if hasIndex {
		fmt.Println("✓ INDEX section found")
	} else {
		warnings = append(warnings, "No INDEX section (run 'atf rebuild' to create)")
	}

	// Check 3: CONTENT section
	hasContent := false
	for _, line := range lines {
		if strings.TrimSpace(line) == "===CONTENT===" {
			hasContent = true
			break
		}
	}
	if hasContent {
		fmt.Println("✓ CONTENT section found")
	} else {
		errors = append(errors, "Missing CONTENT section")
	}

	// Check 4: Section IDs unique
	sectionIDs := make(map[string]bool)
	openPattern := regexp.MustCompile(`^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}`)
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

	// Check 5: All sections closed
	openSections := []string{}
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
			}
		}
	}

	if len(openSections) > 0 {
		for _, id := range openSections {
			errors = append(errors, fmt.Sprintf("Unclosed section: %s", id))
		}
	} else {
		fmt.Println("✓ All sections properly closed")
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
