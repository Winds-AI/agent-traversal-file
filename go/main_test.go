package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
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
		if strings.Contains(lines[i], "IATF (Indexed Agent Traversal Format) is a document format designed for AI agents.") {
			lines[i] = strings.ReplaceAll(lines[i], "IATF (Indexed Agent Traversal Format) is a document format designed for AI agents.", "IATF (Indexed Agent Traversal Format) is a document format designed for AI agents!!")
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

	// "intro" should update, the other sections should not.
	for id, before := range beforeMeta {
		afterEntry := afterMeta[id]
		switch id {
		case "intro":
			if afterEntry.Hash == before.Hash {
				t.Fatalf("expected intro hash to change, but did not")
			}
			if afterEntry.Modified == before.Modified {
				t.Fatalf("expected intro modified to change, but did not (still %q)", afterEntry.Modified)
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
