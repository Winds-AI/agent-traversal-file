package analyzer

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
	"sync"

	protocol "github.com/tliron/glsp/protocol_3_16"
)

// Pre-compiled regex patterns for IATF parsing (matching go/main.go patterns)
var (
	sectionOpenPattern  = regexp.MustCompile(`\{#([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	sectionClosePattern = regexp.MustCompile(`\{/([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	referencePattern    = regexp.MustCompile(`\{@([a-zA-Z][a-zA-Z0-9_-]*)\}`)
)

// Section represents an IATF section with its metadata
type Section struct {
	ID       string
	Title    string
	Summary  string
	Start    int // 0-indexed line number
	End      int // 0-indexed line number
	Level    int
	StartCol int
	EndCol   int
}

// Reference represents a cross-reference to a section
type Reference struct {
	TargetID string
	Line     int // 0-indexed
	StartCol int
	EndCol   int
}

// Document represents a parsed IATF document
type Document struct {
	URI             string
	Content         string
	Lines           []string
	Sections        map[string]*Section // ID -> Section
	OrderedSections []*Section          // Sections in order of appearance
	References      []Reference         // All references found
	Errors          []ValidationError
	mu              sync.RWMutex
}

// ValidationError represents a validation error in the document
type ValidationError struct {
	Message  string
	Line     int // 0-indexed
	StartCol int
	EndCol   int
	Severity protocol.DiagnosticSeverity
}

// CompletionSettings controls completion behavior.
type CompletionSettings struct {
	Mode          string
	IncludeTitles bool
	SmartInsert   bool
}

// DefaultCompletionSettings returns the default completion behavior.
func DefaultCompletionSettings() CompletionSettings {
	return CompletionSettings{
		Mode:          "context",
		IncludeTitles: true,
		SmartInsert:   true,
	}
}

// DocumentStore manages all open documents
type DocumentStore struct {
	documents map[string]*Document
	mu        sync.RWMutex
}

// NewDocumentStore creates a new document store
func NewDocumentStore() *DocumentStore {
	return &DocumentStore{
		documents: make(map[string]*Document),
	}
}

// Open opens a new document and parses it
func (ds *DocumentStore) Open(uri string, content string) {
	ds.mu.Lock()
	defer ds.mu.Unlock()

	doc := &Document{
		URI:      uri,
		Content:  content,
		Sections: make(map[string]*Section),
	}
	doc.Parse()
	ds.documents[uri] = doc
}

// Update updates an existing document and re-parses it
func (ds *DocumentStore) Update(uri string, content string) {
	ds.mu.Lock()
	defer ds.mu.Unlock()

	if doc, exists := ds.documents[uri]; exists {
		doc.mu.Lock()
		doc.Content = content
		doc.mu.Unlock()
		doc.Parse()
	} else {
		doc := &Document{
			URI:      uri,
			Content:  content,
			Sections: make(map[string]*Section),
		}
		doc.Parse()
		ds.documents[uri] = doc
	}
}

// Close closes a document
func (ds *DocumentStore) Close(uri string) {
	ds.mu.Lock()
	defer ds.mu.Unlock()
	delete(ds.documents, uri)
}

// Get returns a document by URI
func (ds *DocumentStore) Get(uri string) *Document {
	ds.mu.RLock()
	defer ds.mu.RUnlock()
	return ds.documents[uri]
}

// Parse parses the document content
func (d *Document) Parse() {
	d.mu.Lock()
	defer d.mu.Unlock()

	d.Lines = strings.Split(d.Content, "\n")
	d.Sections = make(map[string]*Section)
	d.OrderedSections = nil
	d.References = nil
	d.Errors = nil

	d.validate()
	d.parseSections()
	d.parseReferences()
	d.validateReferences()
}

// validate performs basic validation of the IATF file structure
func (d *Document) validate() {
	// Check format declaration
	if len(d.Lines) == 0 || strings.TrimSpace(d.Lines[0]) != ":::IATF" {
		d.Errors = append(d.Errors, ValidationError{
			Message:  "Missing format declaration (:::IATF) at the beginning of the file",
			Line:     0,
			StartCol: 0,
			EndCol:   len(d.Lines[0]),
			Severity: protocol.DiagnosticSeverityError,
		})
	}

	// Find INDEX and CONTENT sections
	hasIndex := false
	hasContent := false
	indexLine := -1
	contentLine := -1

	for i, line := range d.Lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "===INDEX===" {
			hasIndex = true
			indexLine = i
		} else if trimmed == "===CONTENT===" {
			hasContent = true
			contentLine = i
		}
	}

	if !hasContent {
		lastLine := len(d.Lines) - 1
		if lastLine < 0 {
			lastLine = 0
		}
		d.Errors = append(d.Errors, ValidationError{
			Message:  "Missing ===CONTENT=== section",
			Line:     lastLine,
			StartCol: 0,
			EndCol:   1,
			Severity: protocol.DiagnosticSeverityError,
		})
	}

	if !hasIndex {
		d.Errors = append(d.Errors, ValidationError{
			Message:  "Missing ===INDEX=== section (Run 'iatf rebuild' to create)",
			Line:     0,
			StartCol: 0,
			EndCol:   1,
			Severity: protocol.DiagnosticSeverityWarning,
		})
	}

	if hasIndex && hasContent && indexLine > contentLine {
		d.Errors = append(d.Errors, ValidationError{
			Message:  "INDEX section must appear before CONTENT section",
			Line:     indexLine,
			StartCol: 0,
			EndCol:   len(d.Lines[indexLine]),
			Severity: protocol.DiagnosticSeverityError,
		})
	}
}

// parseSections parses all section tags in the document
func (d *Document) parseSections() {
	// Find CONTENT section start
	contentStart := -1
	for i, line := range d.Lines {
		if strings.TrimSpace(line) == "===CONTENT===" {
			contentStart = i + 1
			break
		}
	}

	if contentStart == -1 {
		return
	}

	// Parse sections using a stack for nesting
	stack := []*Section{}
	seenIDs := make(map[string]int) // ID -> first occurrence line

	for i := contentStart; i < len(d.Lines); i++ {
		line := d.Lines[i]

		// Check for section open tag
		if matches := sectionOpenPattern.FindStringSubmatchIndex(line); matches != nil {
			id := line[matches[2]:matches[3]]
			startCol := matches[0]

			// Check for duplicate IDs
			if firstLine, exists := seenIDs[id]; exists {
				d.Errors = append(d.Errors, ValidationError{
					Message:  "Duplicate section ID '" + id + "' (first defined on line " + string(rune(firstLine+1)) + ")",
					Line:     i,
					StartCol: startCol,
					EndCol:   matches[1],
					Severity: protocol.DiagnosticSeverityError,
				})
			} else {
				seenIDs[id] = i
			}

			section := &Section{
				ID:       id,
				Title:    id, // Default title to ID
				Start:    i,
				StartCol: startCol,
				Level:    len(stack) + 1,
			}

			// Look for summary annotation and title in the following lines
			d.extractSectionMetadata(section, i+1)

			d.Sections[id] = section
			d.OrderedSections = append(d.OrderedSections, section)
			stack = append(stack, section)

			// Check nesting depth
			if len(stack) > 2 {
				d.Errors = append(d.Errors, ValidationError{
					Message:  "Section nesting exceeds maximum depth of 2",
					Line:     i,
					StartCol: startCol,
					EndCol:   matches[1],
					Severity: protocol.DiagnosticSeverityError,
				})
			}
		}

		// Check for section close tag
		if matches := sectionClosePattern.FindStringSubmatchIndex(line); matches != nil {
			id := line[matches[2]:matches[3]]

			if len(stack) == 0 {
				d.Errors = append(d.Errors, ValidationError{
					Message:  "Closing tag {/" + id + "} without matching opening tag",
					Line:     i,
					StartCol: matches[0],
					EndCol:   matches[1],
					Severity: protocol.DiagnosticSeverityError,
				})
			} else if stack[len(stack)-1].ID != id {
				d.Errors = append(d.Errors, ValidationError{
					Message:  "Closing tag {/" + id + "} does not match expected {/" + stack[len(stack)-1].ID + "}",
					Line:     i,
					StartCol: matches[0],
					EndCol:   matches[1],
					Severity: protocol.DiagnosticSeverityError,
				})
			} else {
				stack[len(stack)-1].End = i
				stack[len(stack)-1].EndCol = matches[1]
				stack = stack[:len(stack)-1]
			}
		}
	}

	// Check for unclosed sections
	for _, section := range stack {
		d.Errors = append(d.Errors, ValidationError{
			Message:  "Unclosed section: " + section.ID,
			Line:     section.Start,
			StartCol: section.StartCol,
			EndCol:   section.StartCol + len("{#"+section.ID+"}"),
			Severity: protocol.DiagnosticSeverityError,
		})
	}
}

// extractSectionMetadata extracts @summary and title from section content
func (d *Document) extractSectionMetadata(section *Section, startLine int) {
	for i := startLine; i < len(d.Lines) && i < startLine+10; i++ {
		line := d.Lines[i]
		trimmed := strings.TrimSpace(line)

		// Stop if we hit a close tag or another open tag
		if sectionOpenPattern.MatchString(line) || sectionClosePattern.MatchString(line) {
			break
		}

		// Extract @summary
		if strings.HasPrefix(trimmed, "@summary:") {
			section.Summary = strings.TrimSpace(strings.TrimPrefix(trimmed, "@summary:"))
			continue
		}

		// Extract title from first heading
		if strings.HasPrefix(trimmed, "#") && section.Title == section.ID {
			section.Title = strings.TrimSpace(strings.TrimLeft(trimmed, "#"))
		}
	}
}

// parseReferences parses all cross-references in the document
func (d *Document) parseReferences() {
	inCodeFence := false

	for i, line := range d.Lines {
		// Track code fences
		if strings.TrimSpace(line) == "```" || strings.HasPrefix(strings.TrimSpace(line), "```") {
			inCodeFence = !inCodeFence
			continue
		}

		if inCodeFence {
			continue
		}

		// Find all references in this line
		matches := referencePattern.FindAllStringSubmatchIndex(line, -1)
		for _, match := range matches {
			targetID := line[match[2]:match[3]]
			d.References = append(d.References, Reference{
				TargetID: targetID,
				Line:     i,
				StartCol: match[0],
				EndCol:   match[1],
			})
		}
	}
}

// validateReferences checks that all references point to valid sections
func (d *Document) validateReferences() {
	for _, ref := range d.References {
		if _, exists := d.Sections[ref.TargetID]; !exists {
			d.Errors = append(d.Errors, ValidationError{
				Message:  "Reference {@" + ref.TargetID + "} points to non-existent section",
				Line:     ref.Line,
				StartCol: ref.StartCol,
				EndCol:   ref.EndCol,
				Severity: protocol.DiagnosticSeverityError,
			})
		}
	}

	// Check for self-references
	for _, ref := range d.References {
		for _, section := range d.OrderedSections {
			if ref.Line >= section.Start && ref.Line <= section.End {
				if ref.TargetID == section.ID {
					d.Errors = append(d.Errors, ValidationError{
						Message:  "Self-reference not allowed: {@" + ref.TargetID + "}",
						Line:     ref.Line,
						StartCol: ref.StartCol,
						EndCol:   ref.EndCol,
						Severity: protocol.DiagnosticSeverityError,
					})
				}
				break
			}
		}
	}
}

// GetDiagnostics returns LSP diagnostics for the document
func (d *Document) GetDiagnostics() []protocol.Diagnostic {
	d.mu.RLock()
	defer d.mu.RUnlock()

	diagnostics := make([]protocol.Diagnostic, len(d.Errors))
	for i, err := range d.Errors {
		diagnostics[i] = protocol.Diagnostic{
			Range: protocol.Range{
				Start: protocol.Position{Line: protocol.UInteger(err.Line), Character: protocol.UInteger(err.StartCol)},
				End:   protocol.Position{Line: protocol.UInteger(err.Line), Character: protocol.UInteger(err.EndCol)},
			},
			Severity: &err.Severity,
			Source:   ptrString("iatf"),
			Message:  err.Message,
		}
	}
	return diagnostics
}

// GetCompletions returns completion items at the given position
func (d *Document) GetCompletions(
	pos protocol.Position,
	context *protocol.CompletionContext,
	settings CompletionSettings,
) []protocol.CompletionItem {
	d.mu.RLock()
	defer d.mu.RUnlock()

	line := int(pos.Line)
	if line >= len(d.Lines) {
		return nil
	}

	lineContent := d.Lines[line]
	col := int(pos.Character)
	if col > len(lineContent) {
		col = len(lineContent)
	}

	beforeCursor := lineContent[:col]
	mode := normalizeCompletionMode(settings.Mode)
	if mode == "manual" && context != nil &&
		context.TriggerKind == protocol.CompletionTriggerKindTriggerCharacter {
		return nil
	}

	if openerCol, prefix, ok := activeOpenerPrefix(beforeCursor, "{@"); ok {
		return d.buildSectionIDCompletions(
			line,
			openerCol,
			col,
			prefix,
			protocol.CompletionItemKindReference,
			settings.SmartInsert,
		)
	}

	if openerCol, prefix, ok := activeOpenerPrefix(beforeCursor, "{#"); ok {
		return d.buildSectionIDCompletions(
			line,
			openerCol,
			col,
			prefix,
			protocol.CompletionItemKindClass,
			settings.SmartInsert,
		)
	}

	if openerCol, prefix, ok := activeOpenerPrefix(beforeCursor, "{/"); ok {
		return d.buildSectionIDCompletions(
			line,
			openerCol,
			col,
			prefix,
			protocol.CompletionItemKindClass,
			settings.SmartInsert,
		)
	}

	if prefix, ok := metadataPrefix(beforeCursor); ok {
		return buildMetadataCompletions(prefix)
	}

	if settings.IncludeTitles {
		if prefix, ok := d.titlePrefixForLine(line, beforeCursor); ok {
			return d.buildTitleCompletions(line, col, prefix)
		}
	}

	if mode == "aggressive" {
		return d.buildAggressiveCompletions(line, col, beforeCursor, settings)
	}

	return nil
}

func normalizeCompletionMode(mode string) string {
	mode = strings.ToLower(strings.TrimSpace(mode))
	if mode == "manual" || mode == "aggressive" {
		return mode
	}
	return "context"
}

func activeOpenerPrefix(beforeCursor string, opener string) (int, string, bool) {
	idx := strings.LastIndex(beforeCursor, opener)
	if idx == -1 {
		return -1, "", false
	}
	typed := beforeCursor[idx+len(opener):]
	if strings.Contains(typed, "}") {
		return -1, "", false
	}
	if strings.ContainsAny(typed, " \t") {
		return -1, "", false
	}
	return idx + len(opener), typed, true
}

func metadataPrefix(beforeCursor string) (string, bool) {
	trimLeft := strings.TrimLeft(beforeCursor, " \t")
	if !strings.HasPrefix(trimLeft, "@") {
		return "", false
	}
	if strings.Contains(trimLeft, ":") {
		return "", false
	}
	typed := strings.TrimPrefix(trimLeft, "@")
	return typed, true
}

func buildMetadataCompletions(prefix string) []protocol.CompletionItem {
	keys := []string{"title", "purpose", "summary", "created", "modified", "hash"}
	items := []protocol.CompletionItem{}
	for i, key := range keys {
		if strings.HasPrefix(key, prefix) {
			insert := "@" + key + ": "
			sortText := fmt.Sprintf("0%02d-%s", i, key)
			items = append(items, protocol.CompletionItem{
				Label:      "@" + key,
				Kind:       ptrCompletionItemKind(protocol.CompletionItemKindKeyword),
				Detail:     ptrString("IATF metadata"),
				FilterText: ptrString(key),
				SortText:   &sortText,
				InsertText: &insert,
				Preselect:  ptrBool(false),
			})
		}
	}
	return items
}

func (d *Document) buildSectionIDCompletions(
	line int,
	startCol int,
	endCol int,
	prefix string,
	kind protocol.CompletionItemKind,
	smartInsert bool,
) []protocol.CompletionItem {
	items := []protocol.CompletionItem{}
	seen := make(map[string]bool)
	for i, section := range d.OrderedSections {
		if section == nil || seen[section.ID] {
			continue
		}
		seen[section.ID] = true
		if !strings.HasPrefix(section.ID, prefix) {
			continue
		}

		insert := section.ID
		if smartInsert && !hasClosingBraceAfterCursor(d.Lines[line], endCol) {
			insert += "}"
		}
		sortText := fmt.Sprintf("0%03d-%s", i, section.ID)
		item := protocol.CompletionItem{
			Label:      section.ID,
			Kind:       ptrCompletionItemKind(kind),
			Detail:     ptrString(section.Title),
			FilterText: ptrString(section.ID),
			SortText:   &sortText,
			Preselect:  ptrBool(prefix == section.ID),
			TextEdit: protocol.TextEdit{
				Range: protocol.Range{
					Start: protocol.Position{Line: protocol.UInteger(line), Character: protocol.UInteger(startCol)},
					End:   protocol.Position{Line: protocol.UInteger(line), Character: protocol.UInteger(endCol)},
				},
				NewText: insert,
			},
		}
		if section.Summary != "" {
			item.Documentation = section.Summary
		}
		items = append(items, item)
	}
	return items
}

func hasClosingBraceAfterCursor(lineContent string, col int) bool {
	if col < 0 || col > len(lineContent) {
		return false
	}
	return strings.Contains(lineContent[col:], "}")
}

func (d *Document) titlePrefixForLine(line int, beforeCursor string) (string, bool) {
	trim := strings.TrimSpace(beforeCursor)
	if strings.Contains(trim, "{#") {
		return "", false
	}
	if !isHeadingLine(beforeCursor) {
		return "", false
	}
	if !d.inIndexRange(line) && !d.inContentRange(line) {
		return "", false
	}
	return strings.TrimSpace(stripHeadingPrefix(beforeCursor)), true
}

func isHeadingLine(line string) bool {
	trimLeft := strings.TrimLeft(line, " \t")
	if !strings.HasPrefix(trimLeft, "#") {
		return false
	}
	hashRun := 0
	for hashRun < len(trimLeft) && trimLeft[hashRun] == '#' {
		hashRun++
	}
	if hashRun == 0 || hashRun > 6 {
		return false
	}
	if hashRun >= len(trimLeft) || trimLeft[hashRun] != ' ' {
		return false
	}
	return true
}

func stripHeadingPrefix(line string) string {
	trimLeft := strings.TrimLeft(line, " \t")
	i := 0
	for i < len(trimLeft) && trimLeft[i] == '#' {
		i++
	}
	if i < len(trimLeft) && trimLeft[i] == ' ' {
		return trimLeft[i+1:]
	}
	return trimLeft
}

func (d *Document) inIndexRange(line int) bool {
	indexLine := -1
	contentLine := len(d.Lines)
	for i, v := range d.Lines {
		trim := strings.TrimSpace(v)
		if trim == "===INDEX===" {
			indexLine = i
		}
		if trim == "===CONTENT===" {
			contentLine = i
			break
		}
	}
	return indexLine != -1 && line > indexLine && line < contentLine
}

func (d *Document) inContentRange(line int) bool {
	contentLine := -1
	for i, v := range d.Lines {
		if strings.TrimSpace(v) == "===CONTENT===" {
			contentLine = i
			break
		}
	}
	return contentLine != -1 && line > contentLine
}

func (d *Document) buildTitleCompletions(line int, col int, prefix string) []protocol.CompletionItem {
	titles := d.collectTitleCandidates()
	items := []protocol.CompletionItem{}
	startCol := col - len(prefix)
	if startCol < 0 {
		startCol = 0
	}
	for i, title := range titles {
		if prefix != "" && !strings.HasPrefix(strings.ToLower(title), strings.ToLower(prefix)) {
			continue
		}
		sortText := fmt.Sprintf("1%03d-%s", i, strings.ToLower(title))
		items = append(items, protocol.CompletionItem{
			Label:      title,
			Kind:       ptrCompletionItemKind(protocol.CompletionItemKindText),
			Detail:     ptrString("Section title"),
			FilterText: ptrString(title),
			SortText:   &sortText,
			Preselect:  ptrBool(strings.EqualFold(prefix, title)),
			TextEdit: protocol.TextEdit{
				Range: protocol.Range{
					Start: protocol.Position{Line: protocol.UInteger(line), Character: protocol.UInteger(startCol)},
					End:   protocol.Position{Line: protocol.UInteger(line), Character: protocol.UInteger(col)},
				},
				NewText: title,
			},
		})
	}
	return items
}

func (d *Document) collectTitleCandidates() []string {
	seen := make(map[string]bool)
	titles := []string{}

	for _, title := range d.collectIndexTitles() {
		if title == "" || seen[title] {
			continue
		}
		seen[title] = true
		titles = append(titles, title)
	}
	for _, section := range d.OrderedSections {
		if section == nil {
			continue
		}
		title := strings.TrimSpace(section.Title)
		if title == "" || seen[title] {
			continue
		}
		seen[title] = true
		titles = append(titles, title)
	}
	return titles
}

func (d *Document) collectIndexTitles() []string {
	titles := []string{}
	inIndex := false
	for _, line := range d.Lines {
		trim := strings.TrimSpace(line)
		if trim == "===INDEX===" {
			inIndex = true
			continue
		}
		if trim == "===CONTENT===" {
			break
		}
		if !inIndex {
			continue
		}
		if !isHeadingLine(line) {
			continue
		}
		title := strings.TrimSpace(stripHeadingPrefix(line))
		if idx := strings.Index(title, "{#"); idx >= 0 {
			title = strings.TrimSpace(title[:idx])
		}
		if title != "" {
			titles = append(titles, title)
		}
	}
	return titles
}

func (d *Document) buildAggressiveCompletions(
	line int,
	col int,
	beforeCursor string,
	settings CompletionSettings,
) []protocol.CompletionItem {
	prefix := trailingWord(beforeCursor)
	if prefix == "" {
		return nil
	}
	items := []protocol.CompletionItem{}
	idItems := d.buildSectionIDCompletions(
		line,
		col-len(prefix),
		col,
		prefix,
		protocol.CompletionItemKindReference,
		settings.SmartInsert,
	)
	items = append(items, idItems...)
	if settings.IncludeTitles {
		items = append(items, d.buildTitleCompletions(line, col, prefix)...)
	}
	sort.SliceStable(items, func(i, j int) bool {
		li := strings.ToLower(items[i].Label)
		lj := strings.ToLower(items[j].Label)
		return li < lj
	})
	return items
}

func trailingWord(text string) string {
	lastBoundary := len(text)
	for i := len(text) - 1; i >= 0; i-- {
		r := text[i]
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '_' || r == '-' {
			continue
		}
		lastBoundary = i + 1
		break
	}
	if lastBoundary >= len(text) {
		return text
	}
	return text[lastBoundary:]
}

// GetHover returns hover information at the given position
func (d *Document) GetHover(pos protocol.Position) *protocol.Hover {
	d.mu.RLock()
	defer d.mu.RUnlock()

	line := int(pos.Line)
	if line >= len(d.Lines) {
		return nil
	}

	lineContent := d.Lines[line]
	col := int(pos.Character)

	// Check if hovering over a reference
	for _, ref := range d.References {
		if ref.Line == line && col >= ref.StartCol && col <= ref.EndCol {
			if section, exists := d.Sections[ref.TargetID]; exists {
				content := "**" + section.Title + "** (`{#" + section.ID + "}`)"
				if section.Summary != "" {
					content += "\n\n" + section.Summary
				}
				content += "\n\n*Lines " + string(rune(section.Start+1)) + "-" + string(rune(section.End+1)) + "*"

				return &protocol.Hover{
					Contents: protocol.MarkupContent{
						Kind:  protocol.MarkupKindMarkdown,
						Value: content,
					},
					Range: &protocol.Range{
						Start: protocol.Position{Line: protocol.UInteger(line), Character: protocol.UInteger(ref.StartCol)},
						End:   protocol.Position{Line: protocol.UInteger(line), Character: protocol.UInteger(ref.EndCol)},
					},
				}
			}
		}
	}

	// Check if hovering over a section open tag
	if matches := sectionOpenPattern.FindStringSubmatchIndex(lineContent); matches != nil {
		if col >= matches[0] && col <= matches[1] {
			id := lineContent[matches[2]:matches[3]]
			if section, exists := d.Sections[id]; exists {
				content := "**Section: " + section.Title + "**"
				if section.Summary != "" {
					content += "\n\n" + section.Summary
				}

				return &protocol.Hover{
					Contents: protocol.MarkupContent{
						Kind:  protocol.MarkupKindMarkdown,
						Value: content,
					},
					Range: &protocol.Range{
						Start: protocol.Position{Line: protocol.UInteger(line), Character: protocol.UInteger(matches[0])},
						End:   protocol.Position{Line: protocol.UInteger(line), Character: protocol.UInteger(matches[1])},
					},
				}
			}
		}
	}

	return nil
}

// GetDefinition returns the definition location for a reference at the given position
func (d *Document) GetDefinition(pos protocol.Position, uri string) *protocol.Location {
	d.mu.RLock()
	defer d.mu.RUnlock()

	line := int(pos.Line)
	if line >= len(d.Lines) {
		return nil
	}

	col := int(pos.Character)

	// Check if on a reference
	for _, ref := range d.References {
		if ref.Line == line && col >= ref.StartCol && col <= ref.EndCol {
			if section, exists := d.Sections[ref.TargetID]; exists {
				return &protocol.Location{
					URI: protocol.DocumentUri(uri),
					Range: protocol.Range{
						Start: protocol.Position{Line: protocol.UInteger(section.Start), Character: protocol.UInteger(section.StartCol)},
						End:   protocol.Position{Line: protocol.UInteger(section.Start), Character: protocol.UInteger(section.StartCol + len("{#"+section.ID+"}"))},
					},
				}
			}
		}
	}

	return nil
}

// GetReferences returns all references to a section at the given position
func (d *Document) GetReferences(pos protocol.Position, uri string) []protocol.Location {
	d.mu.RLock()
	defer d.mu.RUnlock()

	line := int(pos.Line)
	if line >= len(d.Lines) {
		return nil
	}

	lineContent := d.Lines[line]
	col := int(pos.Character)

	var sectionID string

	// Check if on a section open tag
	if matches := sectionOpenPattern.FindStringSubmatchIndex(lineContent); matches != nil {
		if col >= matches[0] && col <= matches[1] {
			sectionID = lineContent[matches[2]:matches[3]]
		}
	}

	// Check if on a reference
	for _, ref := range d.References {
		if ref.Line == line && col >= ref.StartCol && col <= ref.EndCol {
			sectionID = ref.TargetID
			break
		}
	}

	if sectionID == "" {
		return nil
	}

	// Find all references to this section
	locations := []protocol.Location{}
	for _, ref := range d.References {
		if ref.TargetID == sectionID {
			locations = append(locations, protocol.Location{
				URI: protocol.DocumentUri(uri),
				Range: protocol.Range{
					Start: protocol.Position{Line: protocol.UInteger(ref.Line), Character: protocol.UInteger(ref.StartCol)},
					End:   protocol.Position{Line: protocol.UInteger(ref.Line), Character: protocol.UInteger(ref.EndCol)},
				},
			})
		}
	}

	return locations
}

// GetDocumentSymbols returns document symbols for the outline view
func (d *Document) GetDocumentSymbols() []protocol.DocumentSymbol {
	d.mu.RLock()
	defer d.mu.RUnlock()

	// Build nested structure based on level
	symbols := []protocol.DocumentSymbol{}

	for _, section := range d.OrderedSections {
		sym := protocol.DocumentSymbol{
			Name:   section.Title,
			Detail: ptrString("{#" + section.ID + "}"),
			Kind:   protocol.SymbolKindClass,
			Range: protocol.Range{
				Start: protocol.Position{Line: protocol.UInteger(section.Start), Character: 0},
				End:   protocol.Position{Line: protocol.UInteger(section.End), Character: protocol.UInteger(len(d.Lines[section.End]))},
			},
			SelectionRange: protocol.Range{
				Start: protocol.Position{Line: protocol.UInteger(section.Start), Character: protocol.UInteger(section.StartCol)},
				End:   protocol.Position{Line: protocol.UInteger(section.Start), Character: protocol.UInteger(section.StartCol + len("{#"+section.ID+"}"))},
			},
		}

		// For level 1 sections, add to root
		if section.Level == 1 {
			symbols = append(symbols, sym)
		}
		// For nested sections, add to parent
		// Note: This simple implementation adds all at root level for now
		// A more complex implementation would build a proper tree
	}

	return symbols
}

// Helper functions
func ptrString(s string) *string {
	return &s
}

func ptrBool(v bool) *bool {
	return &v
}

func ptrCompletionItemKind(k protocol.CompletionItemKind) *protocol.CompletionItemKind {
	return &k
}
