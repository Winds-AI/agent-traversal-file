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
	sectionOpenPattern  = regexp.MustCompile(`^\{#([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	sectionClosePattern = regexp.MustCompile(`^\{/([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	referencePattern    = regexp.MustCompile(`\{@([a-zA-Z][a-zA-Z0-9_-]*)\}`)
	annotationTag       = regexp.MustCompile(`^@([a-zA-Z][a-zA-Z0-9_-]*):`)
	indexDashEntryTag   = regexp.MustCompile(`^- ([a-zA-Z][a-zA-Z0-9_-]*) \{lines:\d+-\d+ \| words:\d+\}$`)
)

func isCodeFenceLine(line string) bool {
	return strings.TrimSpace(line) == "```"
}

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
	TargetID          string
	ContainingSection string
	Line              int // 0-indexed
	StartCol          int
	EndCol            int
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

	// Build navigation structures first (sections/references), then derive diagnostics
	// from the CLI-aligned validation pass.
	d.parseSections()
	d.parseReferences()
	d.Errors = d.buildParityDiagnostics()
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
	enforceMaxDepth := d.hasIndexBeforeContent()

	for i := contentStart; i < len(d.Lines); i++ {
		line := d.Lines[i]

		// Check for section open tag
		if matches := sectionOpenPattern.FindStringSubmatchIndex(line); matches != nil {
			id := line[matches[2]:matches[3]]
			startCol := matches[0]

			// Check for duplicate IDs
			if firstLine, exists := seenIDs[id]; exists {
				d.Errors = append(d.Errors, ValidationError{
					Message:  fmt.Sprintf("Duplicate section ID '%s' (first defined on line %d)", id, firstLine+1),
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

			// Look for summary annotation/title and validate section-header annotations.
			metadataErrors := d.extractSectionMetadata(section, i+1)
			d.Errors = append(d.Errors, metadataErrors...)

			d.Sections[id] = section
			d.OrderedSections = append(d.OrderedSections, section)
			stack = append(stack, section)

			// Match CLI behavior: enforce max depth only in INDEX-aware validation context.
			if enforceMaxDepth && len(stack) > 2 {
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

func (d *Document) hasIndexBeforeContent() bool {
	indexSeen := false
	for _, line := range d.Lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "===INDEX===" {
			indexSeen = true
		}
		if trimmed == "===CONTENT===" {
			return indexSeen
		}
	}
	return false
}

// extractSectionMetadata extracts @summary and title from section content.
// Only @summary is treated as section-header metadata; other @annotations are rejected.
func (d *Document) extractSectionMetadata(section *Section, startLine int) []ValidationError {
	validationErrors := []ValidationError{}
	inHeader := true
	summaryContinuation := false

	for i := startLine; i < len(d.Lines) && i < startLine+10; i++ {
		line := d.Lines[i]
		trimmed := strings.TrimSpace(line)

		// Stop if we hit a close tag or another open tag
		if sectionOpenPattern.MatchString(line) || sectionClosePattern.MatchString(line) {
			break
		}

		trimmedLeft := strings.TrimLeft(line, " \t")
		if inHeader {
			if strings.HasPrefix(trimmedLeft, "@summary:") {
				section.Summary = strings.TrimSpace(strings.TrimPrefix(trimmedLeft, "@summary:"))
				summaryContinuation = true
				continue
			}
			if summaryContinuation && (strings.HasPrefix(line, " ") || strings.HasPrefix(line, "\t")) {
				continuation := strings.TrimSpace(line)
				if continuation != "" {
					if section.Summary == "" {
						section.Summary = continuation
					} else {
						section.Summary += " " + continuation
					}
				}
				continue
			}
			if match := annotationTag.FindStringSubmatch(trimmedLeft); match != nil && match[1] != "summary" {
				annotation := "@" + match[1]
				startCol := strings.Index(line, "@")
				if startCol < 0 {
					startCol = 0
				}
				validationErrors = append(validationErrors, ValidationError{
					Message:  "Only @summary is allowed in section header; found " + annotation,
					Line:     i,
					StartCol: startCol,
					EndCol:   startCol + len(annotation),
					Severity: protocol.DiagnosticSeverityError,
				})
			}
			inHeader = false
			summaryContinuation = false
		}

		// Extract title from first heading after metadata header.
		if strings.HasPrefix(trimmed, "#") && section.Title == section.ID {
			section.Title = strings.TrimSpace(strings.TrimLeft(trimmed, "#"))
		}
	}

	return validationErrors
}

// parseReferences parses all cross-references in the document
func (d *Document) parseReferences() {
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

	inCodeFence := false
	openSections := []string{}

	for i := contentStart; i < len(d.Lines); i++ {
		line := d.Lines[i]
		// Track code fences
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

		if matches := sectionOpenPattern.FindStringSubmatch(line); matches != nil {
			openSections = append(openSections, matches[1])
			continue
		}
		if matches := sectionClosePattern.FindStringSubmatch(line); matches != nil {
			id := matches[1]
			if len(openSections) > 0 && openSections[len(openSections)-1] == id {
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

		// Find all references in this line
		matches := referencePattern.FindAllStringSubmatchIndex(line, -1)
		for _, match := range matches {
			targetID := line[match[2]:match[3]]
			d.References = append(d.References, Reference{
				TargetID:          targetID,
				ContainingSection: containingSection,
				Line:              i,
				StartCol:          match[0],
				EndCol:            match[1],
			})
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
			"",
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
			"",
		)
	}

	if openerCol, prefix, ok := activeOpenerPrefix(beforeCursor, "{/"); ok {
		current := d.currentOpenSectionIDAtLine(line)
		return d.buildSectionIDCompletions(
			line,
			openerCol,
			col,
			prefix,
			protocol.CompletionItemKindClass,
			settings.SmartInsert,
			current,
		)
	}

	if prefix, ok := metadataPrefix(beforeCursor); ok {
		return d.buildMetadataCompletions(line, prefix)
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

func (d *Document) buildMetadataCompletions(line int, prefix string) []protocol.CompletionItem {
	keys := []string{}
	switch {
	case d.inDocumentHeaderRange(line):
		keys = []string{"title", "purpose"}
	case d.inSectionAnnotationHeaderAtLine(line):
		keys = []string{"summary"}
	default:
		return nil
	}

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
	preferredID string,
) []protocol.CompletionItem {
	items := []protocol.CompletionItem{}
	seen := make(map[string]bool)
	prefixLower := strings.ToLower(prefix)

	type candidate struct {
		section *Section
		index   int
		score   int
	}
	candidates := []candidate{}

	for i, section := range d.OrderedSections {
		if section == nil || seen[section.ID] {
			continue
		}
		seen[section.ID] = true

		score := scoreIDMatch(section.ID, prefixLower)
		if score <= 0 {
			continue
		}
		if preferredID != "" && section.ID == preferredID {
			score += 1000
		}
		candidates = append(candidates, candidate{
			section: section,
			index:   i,
			score:   score,
		})
	}

	sort.SliceStable(candidates, func(i, j int) bool {
		if candidates[i].score != candidates[j].score {
			return candidates[i].score > candidates[j].score
		}
		return candidates[i].index < candidates[j].index
	})

	for i, c := range candidates {
		section := c.section

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

func (d *Document) inDocumentHeaderRange(line int) bool {
	if line <= 0 {
		return false
	}

	limit := len(d.Lines)
	for i, text := range d.Lines {
		trimmed := strings.TrimSpace(text)
		if trimmed == "===INDEX===" || trimmed == "===CONTENT===" {
			limit = i
			break
		}
	}

	return line < limit
}

func (d *Document) inSectionAnnotationHeaderAtLine(line int) bool {
	contentStart := -1
	for i, text := range d.Lines {
		if strings.TrimSpace(text) == "===CONTENT===" {
			contentStart = i + 1
			break
		}
	}
	if contentStart == -1 || line < contentStart {
		return false
	}

	type sectionState struct {
		id                  string
		inHeader            bool
		summaryContinuation bool
	}

	stack := []sectionState{}
	for i := contentStart; i < len(d.Lines) && i < line; i++ {
		text := d.Lines[i]
		if matches := sectionOpenPattern.FindStringSubmatch(text); matches != nil {
			stack = append(stack, sectionState{
				id:                  matches[1],
				inHeader:            true,
				summaryContinuation: false,
			})
			continue
		}
		if matches := sectionClosePattern.FindStringSubmatch(text); matches != nil {
			if len(stack) > 0 && stack[len(stack)-1].id == matches[1] {
				stack = stack[:len(stack)-1]
			}
			continue
		}
		if len(stack) == 0 {
			continue
		}

		top := &stack[len(stack)-1]
		if !top.inHeader {
			continue
		}

		trimmedLeft := strings.TrimLeft(text, " \t")
		if strings.HasPrefix(trimmedLeft, "@summary:") {
			top.summaryContinuation = true
			continue
		}
		if top.summaryContinuation && (strings.HasPrefix(text, " ") || strings.HasPrefix(text, "\t")) {
			continue
		}

		top.inHeader = false
		top.summaryContinuation = false
	}

	return len(stack) > 0 && stack[len(stack)-1].inHeader
}

func (d *Document) buildTitleCompletions(line int, col int, prefix string) []protocol.CompletionItem {
	candidates := d.collectTitleCandidates()
	items := []protocol.CompletionItem{}
	startCol := col - len(prefix)
	if startCol < 0 {
		startCol = 0
	}
	titleCounts := make(map[string]int)
	for _, candidate := range candidates {
		titleCounts[candidate.Title]++
	}
	for i, candidate := range candidates {
		title := candidate.Title
		if prefix != "" && !strings.HasPrefix(strings.ToLower(title), strings.ToLower(prefix)) {
			continue
		}
		sortText := fmt.Sprintf("1%03d-%s", i, strings.ToLower(title))
		detail := "Section title"
		if titleCounts[title] > 1 && candidate.ID != "" {
			detail = "Section title (" + candidate.ID + ")"
		}
		items = append(items, protocol.CompletionItem{
			Label:      title,
			Kind:       ptrCompletionItemKind(protocol.CompletionItemKindText),
			Detail:     ptrString(detail),
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

type TitleCandidate struct {
	Title string
	ID    string
}

func (d *Document) collectTitleCandidates() []TitleCandidate {
	seen := make(map[string]bool)
	candidates := []TitleCandidate{}

	for _, candidate := range d.collectIndexTitles() {
		key := candidate.Title + "::" + candidate.ID
		if candidate.Title == "" || seen[key] {
			continue
		}
		seen[key] = true
		candidates = append(candidates, candidate)
	}
	for _, section := range d.OrderedSections {
		if section == nil {
			continue
		}
		title := strings.TrimSpace(section.Title)
		if title == "" {
			continue
		}
		candidate := TitleCandidate{
			Title: title,
			ID:    section.ID,
		}
		key := candidate.Title + "::" + candidate.ID
		if seen[key] {
			continue
		}
		seen[key] = true
		candidates = append(candidates, candidate)
	}
	return candidates
}

func (d *Document) collectIndexTitles() []TitleCandidate {
	titles := []TitleCandidate{}
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

		if matches := indexDashEntryTag.FindStringSubmatch(strings.TrimSpace(line)); matches != nil {
			sectionID := strings.TrimSpace(matches[1])
			if sectionID != "" {
				titles = append(titles, TitleCandidate{
					Title: sectionID,
					ID:    sectionID,
				})
			}
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
		"",
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

func scoreIDMatch(id string, prefixLower string) int {
	if prefixLower == "" {
		return 10
	}
	idLower := strings.ToLower(id)
	if idLower == prefixLower {
		return 900
	}
	if strings.HasPrefix(idLower, prefixLower) {
		return 700
	}
	if strings.Contains(idLower, prefixLower) {
		return 500
	}
	if isSubsequence(prefixLower, idLower) {
		return 300
	}
	return 0
}

func isSubsequence(needle string, haystack string) bool {
	if needle == "" {
		return true
	}
	j := 0
	for i := 0; i < len(haystack) && j < len(needle); i++ {
		if haystack[i] == needle[j] {
			j++
		}
	}
	return j == len(needle)
}

func (d *Document) currentOpenSectionIDAtLine(line int) string {
	contentStart := -1
	for i, text := range d.Lines {
		if strings.TrimSpace(text) == "===CONTENT===" {
			contentStart = i + 1
			break
		}
	}
	if contentStart == -1 || line < contentStart {
		return ""
	}
	stack := []string{}
	for i := contentStart; i <= line && i < len(d.Lines); i++ {
		text := d.Lines[i]
		if matches := sectionOpenPattern.FindStringSubmatch(text); matches != nil {
			stack = append(stack, matches[1])
		}
		if matches := sectionClosePattern.FindStringSubmatch(text); matches != nil {
			id := matches[1]
			if len(stack) > 0 && stack[len(stack)-1] == id {
				stack = stack[:len(stack)-1]
			}
		}
	}
	if len(stack) == 0 {
		return ""
	}
	return stack[len(stack)-1]
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
				content += fmt.Sprintf("\n\n*Lines %d-%d*", section.Start+1, section.End+1)

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
