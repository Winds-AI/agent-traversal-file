package analyzer

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"

	protocol "github.com/tliron/glsp/protocol_3_16"
)

type contentSection struct {
	ID    string
	Start int // 1-indexed
	End   int // 1-indexed
	Level int
}

type referenceLocation struct {
	LineNum           int // 1-indexed
	ContainingSection string
	StartCol          int
	EndCol            int
}

func (d *Document) buildParityDiagnostics() []ValidationError {
	lines := d.Lines
	diagnostics := []ValidationError{}

	lineLen := func(line int) int {
		if line < 0 || line >= len(lines) {
			return 1
		}
		return len(lines[line])
	}

	addDiagnostic := func(message string, severity protocol.DiagnosticSeverity, line int, startCol int, endCol int) {
		if len(lines) == 0 {
			line = 0
			startCol = 0
			endCol = 1
		} else {
			if line < 0 {
				line = 0
			}
			if line >= len(lines) {
				line = len(lines) - 1
			}
			if startCol < 0 {
				startCol = 0
			}
			maxCol := len(lines[line])
			if startCol > maxCol {
				startCol = maxCol
			}
			if endCol < startCol {
				endCol = startCol
			}
			if endCol > maxCol {
				endCol = maxCol
			}
			if endCol < startCol {
				endCol = startCol
			}
		}

		diagnostics = append(diagnostics, ValidationError{
			Message:  message,
			Line:     line,
			StartCol: startCol,
			EndCol:   endCol,
			Severity: severity,
		})
	}

	if len(lines) == 0 || strings.TrimSpace(lines[0]) != ":::IATF" {
		addDiagnostic("Missing format declaration (:::IATF)", protocol.DiagnosticSeverityError, 0, 0, lineLen(0))
	}

	indexPositions := []int{}
	contentPositions := []int{}
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "===INDEX===" {
			indexPositions = append(indexPositions, i)
		} else if trimmed == "===CONTENT===" {
			contentPositions = append(contentPositions, i)
		}
	}

	hasIndex := len(indexPositions) > 0
	hasContent := len(contentPositions) > 0

	if !hasIndex {
		addDiagnostic("No INDEX section (Run 'iatf rebuild' to create)", protocol.DiagnosticSeverityWarning, 0, 0, lineLen(0))
	}
	if !hasContent {
		lastLine := len(lines) - 1
		if lastLine < 0 {
			lastLine = 0
		}
		addDiagnostic("Missing CONTENT section", protocol.DiagnosticSeverityError, lastLine, 0, lineLen(lastLine))
	}

	if len(indexPositions) > 1 {
		addDiagnostic("Multiple INDEX sections found", protocol.DiagnosticSeverityError, indexPositions[1], 0, lineLen(indexPositions[1]))
	}
	if len(contentPositions) > 1 {
		addDiagnostic("Multiple CONTENT sections found", protocol.DiagnosticSeverityError, contentPositions[1], 0, lineLen(contentPositions[1]))
	}
	if hasIndex && hasContent && indexPositions[0] > contentPositions[0] {
		addDiagnostic("INDEX section appears after CONTENT", protocol.DiagnosticSeverityError, indexPositions[0], 0, lineLen(indexPositions[0]))
	}

	indexStart := -1
	contentStart := -1
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "===INDEX===" {
			indexStart = i
		} else if trimmed == "===CONTENT===" {
			contentStart = i + 1
			break
		}
	}

	invalidNesting := false
	if contentStart != -1 {
		if msg, line, ok := validateNestingAtLine(lines, contentStart); ok {
			addDiagnostic("Invalid section nesting: "+msg, protocol.DiagnosticSeverityError, line, 0, lineLen(line))
		}
	}

	if hasIndex {
		contentHashLine := ""
		contentHashLineIdx := -1
		if indexStart != -1 && contentStart != -1 {
			for i := indexStart; i < contentStart && i < len(lines); i++ {
				if strings.HasPrefix(lines[i], "<!-- Content-Hash:") {
					contentHashLine = lines[i]
					contentHashLineIdx = i
					break
				}
			}
		}
		if contentHashLine != "" && contentStart != -1 {
			hashRe := regexp.MustCompile(`^<!-- Content-Hash:\s*([a-z0-9]+):([a-f0-9]+)\s*-->$`)
			matches := hashRe.FindStringSubmatch(strings.TrimSpace(contentHashLine))
			if matches == nil {
				addDiagnostic("Invalid Content-Hash format in INDEX", protocol.DiagnosticSeverityWarning, contentHashLineIdx, 0, lineLen(contentHashLineIdx))
			} else {
				algo := matches[1]
				expectedHash := matches[2]
				if algo != "sha256" {
					addDiagnostic(fmt.Sprintf("Unsupported Content-Hash algorithm: %s", algo), protocol.DiagnosticSeverityWarning, contentHashLineIdx, 0, lineLen(contentHashLineIdx))
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
						addDiagnostic("INDEX Content-Hash does not match CONTENT (index may be stale)", protocol.DiagnosticSeverityWarning, contentHashLineIdx, 0, lineLen(contentHashLineIdx))
					}
				}
			}
		} else {
			line := indexStart
			if line < 0 {
				line = 0
			}
			addDiagnostic("INDEX missing Content-Hash (Run 'iatf rebuild' to add)", protocol.DiagnosticSeverityWarning, line, 0, lineLen(line))
		}
	}

	openSections := []string{}
	for i, line := range lines {
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			openSections = append(openSections, match[1])
		} else if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
			id := match[1]
			if len(openSections) > 0 && openSections[len(openSections)-1] == id {
				openSections = openSections[:len(openSections)-1]
			} else {
				addDiagnostic(fmt.Sprintf("Closing tag without matching opening: %s", id), protocol.DiagnosticSeverityError, i, 0, lineLen(i))
				invalidNesting = true
			}
		}
	}
	if len(openSections) > 0 {
		for _, id := range openSections {
			line := findSectionOpenLine(lines, id)
			addDiagnostic(fmt.Sprintf("Unclosed section: %s", id), protocol.DiagnosticSeverityError, line, 0, lineLen(line))
		}
		invalidNesting = true
	}

	if !invalidNesting && contentStart != -1 {
		for _, issue := range validateSectionAnnotationsWithLocations(lines, contentStart) {
			addDiagnostic(issue.Message, issue.Severity, issue.Line, issue.StartCol, issue.EndCol)
		}

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
				addDiagnostic(fmt.Sprintf("Content outside section block at line %d", i+1), protocol.DiagnosticSeverityError, i, 0, lineLen(i))
				break
			}
		}
	}

	if !invalidNesting && hasIndex && contentStart != -1 && indexStart != -1 {
		indexEntryRe := regexp.MustCompile(`^- ([a-zA-Z][a-zA-Z0-9_-]*) \{lines:(\d+)-(\d+) \| words:\d+\}$`)
		indexRanges := map[string][2]int{}
		for i := indexStart + 1; i < contentStart && i < len(lines); i++ {
			match := indexEntryRe.FindStringSubmatch(strings.TrimSpace(lines[i]))
			if match == nil {
				continue
			}
			id := match[1]
			startNum, errStart := strconv.Atoi(match[2])
			endNum, errEnd := strconv.Atoi(match[3])
			if _, exists := indexRanges[id]; exists {
				addDiagnostic(fmt.Sprintf("Duplicate INDEX section ID: %s", id), protocol.DiagnosticSeverityError, i, 0, lineLen(i))
				continue
			}
			if errStart != nil || errEnd != nil || startNum < 1 || endNum < startNum || endNum > len(lines) {
				addDiagnostic(fmt.Sprintf("Invalid line range for INDEX section: %s", id), protocol.DiagnosticSeverityError, i, 0, lineLen(i))
			}
			indexRanges[id] = [2]int{startNum, endNum}
		}

		contentSections := map[string][2]int{}
		parsedSections := parseContentSectionsForValidation(lines, contentStart)
		for _, section := range parsedSections {
			contentSections[section.ID] = [2]int{section.Start, section.End}
			if section.Level > 2 {
				line := section.Start - 1
				addDiagnostic(fmt.Sprintf("Section nesting exceeds 2 levels: %s", section.ID), protocol.DiagnosticSeverityError, line, 0, lineLen(line))
			}
		}

		for id := range indexRanges {
			if _, exists := contentSections[id]; !exists {
				addDiagnostic(fmt.Sprintf("INDEX references missing CONTENT section: %s", id), protocol.DiagnosticSeverityError, indexStart, 0, lineLen(indexStart))
			}
		}
		for id := range contentSections {
			if _, exists := indexRanges[id]; !exists {
				addDiagnostic(fmt.Sprintf("CONTENT section missing from INDEX: %s", id), protocol.DiagnosticSeverityError, indexStart, 0, lineLen(indexStart))
			}
		}
		for id, contentRange := range contentSections {
			if indexRange, exists := indexRanges[id]; exists && indexRange != contentRange {
				addDiagnostic(fmt.Sprintf("INDEX line range mismatch for section: %s", id), protocol.DiagnosticSeverityError, indexStart, 0, lineLen(indexStart))
			}
		}
	}

	sectionIDs := make(map[string]bool)
	for i, line := range lines {
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			id := match[1]
			if sectionIDs[id] {
				addDiagnostic(fmt.Sprintf("Duplicate section ID: %s", id), protocol.DiagnosticSeverityError, i, 0, lineLen(i))
			}
			sectionIDs[id] = true
		}
	}
	if len(sectionIDs) == 0 {
		line := 0
		if contentStart > 0 {
			line = contentStart - 1
		}
		addDiagnostic("No sections found in CONTENT", protocol.DiagnosticSeverityWarning, line, 0, lineLen(line))
	}

	if !invalidNesting && contentStart != -1 {
		parsedSectionsForRefs := parseContentSectionsForValidation(lines, contentStart)
		for _, issue := range validateReferencesWithLocations(lines, contentStart, parsedSectionsForRefs) {
			addDiagnostic(issue.Message, issue.Severity, issue.Line, issue.StartCol, issue.EndCol)
		}
	}

	return diagnostics
}

func validateNestingAtLine(lines []string, contentStart int) (string, int, bool) {
	openSections := []string{}
	openLines := []int{}

	for i := contentStart; i < len(lines); i++ {
		line := lines[i]
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			openSections = append(openSections, match[1])
			openLines = append(openLines, i)
		} else if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
			id := match[1]
			if len(openSections) > 0 && openSections[len(openSections)-1] == id {
				openSections = openSections[:len(openSections)-1]
				openLines = openLines[:len(openLines)-1]
			} else {
				return fmt.Sprintf("closing tag without matching opening: %s", id), i, true
			}
		}
	}

	if len(openSections) > 0 {
		last := len(openSections) - 1
		return fmt.Sprintf("unclosed section: %s", openSections[last]), openLines[last], true
	}

	return "", -1, false
}

func findSectionOpenLine(lines []string, id string) int {
	for i, line := range lines {
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil && match[1] == id {
			return i
		}
	}
	return 0
}

func validateSectionAnnotationsWithLocations(lines []string, contentStart int) []ValidationError {
	errors := []ValidationError{}
	type sectionHeaderState struct {
		ID                  string
		InHeader            bool
		SummaryContinuation bool
	}
	stack := []sectionHeaderState{}

	for i := contentStart; i < len(lines); i++ {
		line := lines[i]

		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			stack = append(stack, sectionHeaderState{
				ID:                  match[1],
				InHeader:            true,
				SummaryContinuation: false,
			})
			continue
		}

		if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
			if len(stack) > 0 && stack[len(stack)-1].ID == match[1] {
				stack = stack[:len(stack)-1]
			} else {
				stack = []sectionHeaderState{}
			}
			continue
		}

		if len(stack) == 0 {
			continue
		}

		top := &stack[len(stack)-1]
		if !top.InHeader {
			continue
		}

		trimmedHeader := strings.TrimLeft(line, " \t")
		if strings.HasPrefix(trimmedHeader, "@summary:") {
			top.SummaryContinuation = true
			continue
		}
		if top.SummaryContinuation && (strings.HasPrefix(line, " ") || strings.HasPrefix(line, "\t")) {
			continue
		}
		if match := annotationTag.FindStringSubmatch(trimmedHeader); match != nil {
			annotation := "@" + match[1]
			startCol := strings.Index(line, "@")
			if startCol < 0 {
				startCol = 0
			}
			errors = append(errors, ValidationError{
				Message:  fmt.Sprintf("Unsupported section annotation %s at line %d (only @summary is allowed)", annotation, i+1),
				Line:     i,
				StartCol: startCol,
				EndCol:   startCol + len(annotation),
				Severity: protocol.DiagnosticSeverityError,
			})
		}

		top.InHeader = false
		top.SummaryContinuation = false
	}

	return errors
}

func parseContentSectionsForValidation(lines []string, contentStart int) []contentSection {
	sections := []contentSection{}
	stack := []int{}

	for i := contentStart; i < len(lines); i++ {
		line := lines[i]
		if match := sectionOpenPattern.FindStringSubmatch(line); match != nil {
			section := contentSection{
				ID:    match[1],
				Start: i + 1,
				Level: len(stack) + 1,
			}
			sections = append(sections, section)
			stack = append(stack, len(sections)-1)
			continue
		}

		if match := sectionClosePattern.FindStringSubmatch(line); match != nil {
			if len(stack) > 0 && sections[stack[len(stack)-1]].ID == match[1] {
				idx := stack[len(stack)-1]
				sections[idx].End = i + 1
				stack = stack[:len(stack)-1]
			}
			continue
		}
	}

	return sections
}

func extractReferencesWithLocations(lines []string, contentStart int) map[string][]referenceLocation {
	references := make(map[string][]referenceLocation)
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

		containingSection := ""
		if len(openSections) > 0 {
			containingSection = openSections[len(openSections)-1]
		}

		matches := referencePattern.FindAllStringSubmatchIndex(line, -1)
		for _, match := range matches {
			target := line[match[2]:match[3]]
			references[target] = append(references[target], referenceLocation{
				LineNum:           lineNum,
				ContainingSection: containingSection,
				StartCol:          match[0],
				EndCol:            match[1],
			})
		}
	}

	return references
}

func validateReferencesWithLocations(lines []string, contentStart int, sections []contentSection) []ValidationError {
	errors := []ValidationError{}
	validIDs := make(map[string]bool)
	for _, section := range sections {
		validIDs[section.ID] = true
	}

	references := extractReferencesWithLocations(lines, contentStart)

	type referenceInstance struct {
		Target            string
		LineNum           int
		ContainingSection string
		StartCol          int
		EndCol            int
	}

	orderedRefs := []referenceInstance{}
	for target, locations := range references {
		for _, loc := range locations {
			orderedRefs = append(orderedRefs, referenceInstance{
				Target:            target,
				LineNum:           loc.LineNum,
				ContainingSection: loc.ContainingSection,
				StartCol:          loc.StartCol,
				EndCol:            loc.EndCol,
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

	for _, ref := range orderedRefs {
		line := ref.LineNum - 1
		if !validIDs[ref.Target] {
			errors = append(errors, ValidationError{
				Message:  fmt.Sprintf("Reference {@%s} at line %d: target section does not exist", ref.Target, ref.LineNum),
				Line:     line,
				StartCol: ref.StartCol,
				EndCol:   ref.EndCol,
				Severity: protocol.DiagnosticSeverityError,
			})
		} else if ref.Target == ref.ContainingSection {
			errors = append(errors, ValidationError{
				Message:  fmt.Sprintf("Reference {@%s} at line %d: self-reference not allowed", ref.Target, ref.LineNum),
				Line:     line,
				StartCol: ref.StartCol,
				EndCol:   ref.EndCol,
				Severity: protocol.DiagnosticSeverityError,
			})
		}
	}

	return errors
}
