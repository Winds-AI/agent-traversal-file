package analyzer

import (
	"strings"
	"testing"

	protocol "github.com/tliron/glsp/protocol_3_16"
)

func newTestDocument(content string) *Document {
	doc := &Document{
		URI:      "file:///test.iatf",
		Content:  content,
		Sections: make(map[string]*Section),
	}
	doc.Parse()
	return doc
}

func hasErrorContaining(doc *Document, needle string) bool {
	for _, err := range doc.Errors {
		if strings.Contains(err.Message, needle) {
			return true
		}
	}
	return false
}

func hasDiagnosticWithSeverity(doc *Document, needle string, severity protocol.DiagnosticSeverity) bool {
	for _, diag := range doc.Errors {
		if strings.Contains(diag.Message, needle) && diag.Severity == severity {
			return true
		}
	}
	return false
}

func TestParseSections_AnchoredTagsOnly(t *testing.T) {
	content := `:::IATF
===INDEX===
===CONTENT===
prefix {#fake}
{#real}
@summary: Real summary
# Real
Body
{/real}
prefix {/fake}`

	doc := newTestDocument(content)

	if _, ok := doc.Sections["real"]; !ok {
		t.Fatalf("expected real section to be parsed")
	}
	if _, ok := doc.Sections["fake"]; ok {
		t.Fatalf("expected fake inline tag not to be parsed as a section")
	}
	if len(doc.OrderedSections) != 1 {
		t.Fatalf("expected exactly one parsed section, got %d", len(doc.OrderedSections))
	}
}

func TestParseReferences_CodeFenceRequiresExactTripleBackticks(t *testing.T) {
	content := strings.Join([]string{
		":::IATF",
		"===INDEX===",
		"===CONTENT===",
		"{#a}",
		"@summary: section a",
		"# A",
		"```json",
		"{@missing}",
		"```",
		"{/a}",
	}, "\n")

	doc := newTestDocument(content)
	if !hasErrorContaining(doc, "Reference {@missing} at line") {
		t.Fatalf("expected missing-reference error from line after ```json fence opener")
	}
}

func TestParseReferences_IgnoreInsideExactFence(t *testing.T) {
	content := strings.Join([]string{
		":::IATF",
		"===INDEX===",
		"===CONTENT===",
		"{#a}",
		"@summary: section a",
		"# A",
		"```",
		"{@missing}",
		"```",
		"{/a}",
	}, "\n")

	doc := newTestDocument(content)
	if hasErrorContaining(doc, "Reference {@missing} at line") {
		t.Fatalf("did not expect missing-reference error for reference inside exact fenced block")
	}
}

func TestDuplicateSectionError_UsesCLIMessage(t *testing.T) {
	content := `:::IATF
===INDEX===
===CONTENT===
{#dup}
@summary: first
# First
alpha
{/dup}

{#dup}
@summary: second
# Second
beta
{/dup}`

	doc := newTestDocument(content)

	var duplicateMessage string
	for _, err := range doc.Errors {
		if strings.Contains(err.Message, "Duplicate section ID: dup") {
			duplicateMessage = err.Message
			break
		}
	}
	if duplicateMessage == "" {
		t.Fatalf("expected duplicate section ID error")
	}
}

func TestValidateReferences_NestedOuterReferenceIsNotSelfReference(t *testing.T) {
	content := `:::IATF
===INDEX===
===CONTENT===
{#outer}
@summary: outer
# Outer
{#inner}
@summary: inner
# Inner
{@outer}
{/inner}
{/outer}`

	doc := newTestDocument(content)
	if hasErrorContaining(doc, "self-reference not allowed") {
		t.Fatalf("did not expect self-reference error for inner section referencing outer section")
	}
}

func TestNestingDepth3_NoIndex_DoesNotError(t *testing.T) {
	content := `:::IATF
===CONTENT===
{#a}
@summary: a
# A
{#b}
@summary: b
# B
{#c}
@summary: c
# C
{/c}
{/b}
{/a}`

	doc := newTestDocument(content)
	if hasErrorContaining(doc, "Section nesting exceeds maximum depth of 2") {
		t.Fatalf("did not expect nesting-depth error when INDEX is missing")
	}
	if hasErrorContaining(doc, "Section nesting exceeds 2 levels") {
		t.Fatalf("did not expect nesting-depth error when INDEX is missing")
	}
}

func TestNestingDepth3_WithIndex_Errors(t *testing.T) {
	content := `:::IATF
===INDEX===
===CONTENT===
{#a}
@summary: a
# A
{#b}
@summary: b
# B
{#c}
@summary: c
# C
{/c}
{/b}
{/a}`

	doc := newTestDocument(content)
	if !hasErrorContaining(doc, "Section nesting exceeds 2 levels: c") {
		t.Fatalf("expected nesting-depth error when INDEX exists")
	}
}

func TestDiagnosticsParity_MissingIndexIsWarning(t *testing.T) {
	content := `:::IATF
===CONTENT===
{#intro}
@summary: intro
# Intro
body
{/intro}`

	doc := newTestDocument(content)
	if !hasDiagnosticWithSeverity(doc, "No INDEX section (Run 'iatf rebuild' to create)", protocol.DiagnosticSeverityWarning) {
		t.Fatalf("expected missing-index warning with CLI message")
	}
}

func TestDiagnosticsParity_MissingContentIsError(t *testing.T) {
	content := `:::IATF
===INDEX===`

	doc := newTestDocument(content)
	if !hasDiagnosticWithSeverity(doc, "Missing CONTENT section", protocol.DiagnosticSeverityError) {
		t.Fatalf("expected missing-content error with CLI message")
	}
}

func TestDiagnosticsParity_ContentOutsideSection(t *testing.T) {
	content := `:::IATF
===INDEX===
===CONTENT===
orphan text`

	doc := newTestDocument(content)
	if !hasErrorContaining(doc, "Content outside section block at line 4") {
		t.Fatalf("expected content-outside-section error")
	}
}
