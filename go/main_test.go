package main

import (
	"bytes"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestRebuildPreservesSectionMetadataWhenContentUnchanged(t *testing.T) {
	orig, err := os.ReadFile(filepath.Join("..", "examples", "simple.iatf"))
	if err != nil {
		t.Fatalf("read example: %v", err)
	}

	// This fixture is CRLF in-repo; rebuild should not cause spurious hash/Modified churn.
	origPreferredEOL := detectPreferredEOL(orig)

	tmpDir := t.TempDir()
	tmpFile := filepath.Join(tmpDir, "simple.iatf")
	if err := os.WriteFile(tmpFile, orig, 0644); err != nil {
		t.Fatalf("write tmp: %v", err)
	}

	beforeLines, _ := splitNormalizedLines(orig)
	beforeMeta := parseIndexMetadata(beforeLines)
	if len(beforeMeta) == 0 {
		t.Fatalf("expected index metadata from fixture, got none")
	}

	if err := rebuildIndex(tmpFile); err != nil {
		t.Fatalf("rebuildIndex: %v", err)
	}

	after, err := os.ReadFile(tmpFile)
	if err != nil {
		t.Fatalf("read rebuilt: %v", err)
	}

	// Ensure we don't introduce mixed line endings.
	afterPreferredEOL := detectPreferredEOL(after)
	if afterPreferredEOL != origPreferredEOL {
		t.Fatalf("preferred EOL changed: before=%q after=%q", origPreferredEOL, afterPreferredEOL)
	}
	if afterPreferredEOL == "\r\n" {
		if bytes.Contains(after, []byte("\n")) && bytes.Count(after, []byte("\n")) != bytes.Count(after, []byte("\r\n")) {
			t.Fatalf("rebuilt file contains mixed line endings (expected CRLF only)")
		}
	}

	afterLines, _ := splitNormalizedLines(after)
	afterMeta := parseIndexMetadata(afterLines)

	for id, before := range beforeMeta {
		afterEntry, ok := afterMeta[id]
		if !ok {
			t.Fatalf("missing section in rebuilt index: %s", id)
		}
		if before.Created != afterEntry.Created {
			t.Fatalf("Created changed for %s: before=%q after=%q", id, before.Created, afterEntry.Created)
		}
		if before.Modified != afterEntry.Modified {
			t.Fatalf("Modified changed for %s: before=%q after=%q", id, before.Modified, afterEntry.Modified)
		}
		if before.Hash != afterEntry.Hash {
			t.Fatalf("Hash changed for %s: before=%q after=%q", id, before.Hash, afterEntry.Hash)
		}
	}
}

func TestRebuildUpdatesOnlyChangedSectionModified(t *testing.T) {
	orig, err := os.ReadFile(filepath.Join("..", "examples", "simple.iatf"))
	if err != nil {
		t.Fatalf("read example: %v", err)
	}
	origPreferredEOL := detectPreferredEOL(orig)

	tmpDir := t.TempDir()
	tmpFile := filepath.Join(tmpDir, "simple.iatf")
	if err := os.WriteFile(tmpFile, orig, 0644); err != nil {
		t.Fatalf("write tmp: %v", err)
	}

	lines, _ := splitNormalizedLines(orig)
	beforeMeta := parseIndexMetadata(lines)

	// Change a line in the "intro" section only.
	replaced := false
	for i := range lines {
		if strings.Contains(lines[i], "IATF keeps an INDEX cache and CONTENT source-of-truth in one file.") {
			lines[i] = strings.ReplaceAll(lines[i], "IATF keeps an INDEX cache and CONTENT source-of-truth in one file.", "IATF keeps an INDEX cache and CONTENT source-of-truth in one file. Updated.")
			replaced = true
			break
		}
	}
	if !replaced {
		t.Fatalf("fixture line to modify not found")
	}

	updated := strings.Join(lines, "\n")
	if origPreferredEOL == "\r\n" {
		updated = strings.ReplaceAll(updated, "\n", "\r\n")
	}
	if err := os.WriteFile(tmpFile, []byte(updated), 0644); err != nil {
		t.Fatalf("write modified tmp: %v", err)
	}

	if err := rebuildIndex(tmpFile); err != nil {
		t.Fatalf("rebuildIndex: %v", err)
	}

	after, err := os.ReadFile(tmpFile)
	if err != nil {
		t.Fatalf("read rebuilt: %v", err)
	}
	afterLines, _ := splitNormalizedLines(after)
	afterMeta := parseIndexMetadata(afterLines)
	today := time.Now().Format("2006-01-02")

	// "intro" should update, the other sections should not.
	for id, before := range beforeMeta {
		afterEntry := afterMeta[id]
		switch id {
		case "intro":
			if afterEntry.Hash == before.Hash {
				t.Fatalf("expected intro hash to change, but did not")
			}
			if afterEntry.Modified != today {
				t.Fatalf("expected intro modified to be today's date (%s), got %q", today, afterEntry.Modified)
			}
		default:
			if afterEntry.Hash != before.Hash {
				t.Fatalf("unexpected hash change for %s: before=%q after=%q", id, before.Hash, afterEntry.Hash)
			}
			if afterEntry.Modified != before.Modified {
				t.Fatalf("unexpected modified change for %s: before=%q after=%q", id, before.Modified, afterEntry.Modified)
			}
		}
	}
}

func TestValidateRejectsUnsupportedSectionHeaderAnnotation(t *testing.T) {
	lines := []string{
		":::IATF",
		"===CONTENT===",
		"{#example}",
		"@created: 2026-02-17",
		"# Example",
		"Body",
		"{/example}",
	}

	result := validateLines(lines)
	if len(result.Errors) == 0 {
		t.Fatalf("expected validation error for unsupported section annotation")
	}

	found := false
	for _, err := range result.Errors {
		if strings.Contains(err, "Unsupported section annotation @created") {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("expected unsupported annotation error, got: %v", result.Errors)
	}
}

func TestValidateAllowsAtSymbolInSectionContent(t *testing.T) {
	lines := []string{
		":::IATF",
		"===CONTENT===",
		"{#example}",
		"@summary: Example summary",
		"# Example",
		"@username mentions stay as normal content text.",
		"Body",
		"{/example}",
	}

	result := validateLines(lines)
	if len(result.Errors) != 0 {
		t.Fatalf("expected no validation errors, got: %v", result.Errors)
	}

	sections := parseContentSection(lines, 2)
	if len(sections) != 1 {
		t.Fatalf("expected 1 section, got %d", len(sections))
	}
	if sections[0].Summary != "Example summary" {
		t.Fatalf("unexpected summary: %q", sections[0].Summary)
	}

	foundContentLine := false
	for _, line := range sections[0].ContentLines {
		if strings.Contains(line, "@username mentions stay as normal content text.") {
			foundContentLine = true
			break
		}
	}
	if !foundContentLine {
		t.Fatalf("expected @content line to remain in section body, got: %v", sections[0].ContentLines)
	}
}

func TestValidateAllowsLeadingAtTextWithoutAnnotationSyntax(t *testing.T) {
	lines := []string{
		":::IATF",
		"===CONTENT===",
		"{#example}",
		"@username plain text line, not an annotation",
		"# Example",
		"Body",
		"{/example}",
	}

	result := validateLines(lines)
	if len(result.Errors) != 0 {
		t.Fatalf("expected no validation errors, got: %v", result.Errors)
	}
}

func TestReadManyReturnsSectionsInRequestedOrder(t *testing.T) {
	tmpDir := t.TempDir()
	tmpFile := filepath.Join(tmpDir, "simple.iatf")

	orig, err := os.ReadFile(filepath.Join("..", "examples", "simple.iatf"))
	if err != nil {
		t.Fatalf("read example: %v", err)
	}
	if err := os.WriteFile(tmpFile, orig, 0644); err != nil {
		t.Fatalf("write tmp: %v", err)
	}

	exitCode, stdout, stderr := captureCommandOutput(t, func() int {
		return readManyCommand(tmpFile, []string{"workflow", "intro"})
	})
	if exitCode != 0 {
		t.Fatalf("expected success exit code, got %d stderr=%q", exitCode, stderr)
	}

	workflowMarker := "@section: workflow"
	introMarker := "@section: intro"
	if !strings.Contains(stdout, workflowMarker) || !strings.Contains(stdout, introMarker) {
		t.Fatalf("missing read-many section markers in output: %q", stdout)
	}
	if strings.Index(stdout, workflowMarker) >= strings.Index(stdout, introMarker) {
		t.Fatalf("expected workflow output before intro output: %q", stdout)
	}
	if !strings.Contains(stdout, "Run `iatf rebuild` after editing CONTENT.") {
		t.Fatalf("expected workflow section body in output: %q", stdout)
	}
	if !strings.Contains(stdout, "IATF keeps an INDEX cache and CONTENT source-of-truth in one file.") {
		t.Fatalf("expected intro section body in output: %q", stdout)
	}
}

func TestReadManyFailsWhenAnySectionMissing(t *testing.T) {
	tmpDir := t.TempDir()
	tmpFile := filepath.Join(tmpDir, "simple.iatf")

	orig, err := os.ReadFile(filepath.Join("..", "examples", "simple.iatf"))
	if err != nil {
		t.Fatalf("read example: %v", err)
	}
	if err := os.WriteFile(tmpFile, orig, 0644); err != nil {
		t.Fatalf("write tmp: %v", err)
	}

	exitCode, stdout, stderr := captureCommandOutput(t, func() int {
		return readManyCommand(tmpFile, []string{"workflow", "does-not-exist"})
	})
	if exitCode == 0 {
		t.Fatalf("expected failure exit code when section missing")
	}
	if !strings.Contains(stderr, "Error: Section(s) not found:") {
		t.Fatalf("expected missing-section error, got stderr=%q", stderr)
	}
	if !strings.Contains(stderr, "does-not-exist") {
		t.Fatalf("expected missing ID in stderr, got stderr=%q", stderr)
	}
	if strings.Contains(stdout, "@section: workflow") {
		t.Fatalf("expected no partial section output on failure, got stdout=%q", stdout)
	}
}

func captureCommandOutput(t *testing.T, fn func() int) (int, string, string) {
	t.Helper()

	oldStdout := os.Stdout
	oldStderr := os.Stderr

	stdoutReader, stdoutWriter, err := os.Pipe()
	if err != nil {
		t.Fatalf("stdout pipe: %v", err)
	}
	stderrReader, stderrWriter, err := os.Pipe()
	if err != nil {
		t.Fatalf("stderr pipe: %v", err)
	}

	os.Stdout = stdoutWriter
	os.Stderr = stderrWriter

	exitCode := fn()

	if err := stdoutWriter.Close(); err != nil {
		t.Fatalf("close stdout writer: %v", err)
	}
	if err := stderrWriter.Close(); err != nil {
		t.Fatalf("close stderr writer: %v", err)
	}
	os.Stdout = oldStdout
	os.Stderr = oldStderr

	stdoutBytes, err := io.ReadAll(stdoutReader)
	if err != nil {
		t.Fatalf("read stdout: %v", err)
	}
	stderrBytes, err := io.ReadAll(stderrReader)
	if err != nil {
		t.Fatalf("read stderr: %v", err)
	}
	return exitCode, string(stdoutBytes), string(stderrBytes)
}
