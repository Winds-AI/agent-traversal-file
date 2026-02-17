# Task List

> **Note:** This project previously had both Python and Go implementations. As of January 2025, only the Go implementation is maintained. All Python references in this document are historical.

## Task 1: Add PID-based warning for rebuild on watched files

**Priority:** Medium
**Status:** Completed

### Summary
Prevents redundant double rebuilds when manually running `iatf rebuild` on a file that's being watched.

### What was implemented

**Go (`go/main.go` + platform files):
- `go/process_unix.go` - Unix PID check using `Signal(0)`
- `go/process_windows.go` - Windows PID check using `OpenProcess` API
- `promptUserConfirmation()` - interactive prompt, returns default for non-TTY
- `checkWatchedFile()` - validates PID and prompts user
- `watchCommand()` - stores PID, cleans up on SIGINT/SIGTERM
- `rebuildCommand()` - checks for watched files before rebuild

### Behavior

When rebuilding a watched file:
```
Warning: This file is being watched by another process (PID 12345)
A manual rebuild will trigger an automatic rebuild from the watch process.
This will cause the file to be rebuilt twice.

Options:
  - Press 'y' to proceed with manual rebuild anyway
  - Press 'N' (default) to cancel
  - Run 'iatf unwatch file.iatf' to stop watching first

Continue with manual rebuild? [y/N]:
```

**Exit codes:**
- User cancels -> exit 1 with "Rebuild cancelled, no changes made."
- User confirms -> proceeds with rebuild
- Non-interactive (CI/scripts) -> returns default (cancel)

### Edge cases handled
- Stale PID (process dead) -> proceeds without warning
- Corrupt watch state â†’ cleans up and exits watch
- File deleted during watch â†’ cleans up PID
- Windows support â†’ uses `OpenProcess` API instead of Unix signals
- Non-TTY stdin â†’ returns default to avoid hanging in CI

### Documentation
- README.md updated with rebuild warning info
- Watch state file format documented


---

## Task 2: VSCode Extension for Syntax Highlighting

**Priority:** High
**Status:** Completed

### Summary

Developed and published a VSCode extension providing comprehensive syntax highlighting for IATF files, making it easier for developers to read and edit IATF documents in VSCode editors.

### What was implemented

**Extension Features:**
- Format declaration highlighting (`:::IATF`)
- Section delimiter highlighting (`===INDEX===`, `===CONTENT===`)
- Index entry syntax highlighting (headings, IDs, line ranges, word counts)
- Content block tags (`{#id}`, `{/id}`)
- Section references (`{@section-id}`) with link-like appearance
- Metadata annotations (`@summary:`, `@created:`, `@modified:`)
- Code fence delimiters (` ``` `)
- HTML-style comments (`<!-- -->`)
- Optimized color scheme for readability

**Color Scheme Design:**
- **Section delimiters** - Bright magenta (#C586C0, bold) - Critical structural landmarks
- **Section IDs** - Gold (#DCDCAA) - Easy to track across INDEX and CONTENT
- **References** - Bright cyan (#4FC1FF, underlined) - Link-like for cross-references
- **Headings** - Blue (#569CD6, bold) - Markdown-like familiarity
- **Metadata** - Light blue (#9CDCFE) - Distinguishable from content
- **Line numbers & dates** - Light green (#B5CEA8) - Standard numeric values
- **Summaries** - Muted green (#6A9955, italic) - Quote-like appearance
- **Hash values** - Cyan (#4EC9B0) - Distinctive for hex codes
- **Block markers** - Gray (#808080) - Structure without distraction

**Files Created:**
- `vscode/iatf/package.json` - Extension manifest with color theme configuration
- `vscode/iatf/syntaxes/iatf.tmLanguage.json` - TextMate grammar for syntax highlighting
- `vscode/iatf/language-configuration.json` - Language configuration (brackets, comments)
- `vscode/iatf/extension.js` - Extension entry point
- `vscode/iatf/README.md` - Extension documentation
- `vscode/iatf/CHANGELOG.md` - Version history
- `vscode/iatf/LICENSE` - MIT License

### Publishing

**Marketplace:** [https://open-vsx.org/extension/Winds-AI/iatf](https://open-vsx.org/extension/Winds-AI/iatf)

**Publisher:** Winds-AI
**Extension ID:** `Winds-AI.iatf`
**Current Version:** 0.0.5

### Documentation Updates

Updated the following files to mention the VSCode extension:

- ✅ `README.md` - Added to Installation section and marked as completed in Contributing
- ✅ `docs/QUICKSTART.md` - Added Editor Setup section with extension link
- ✅ `docs/SPECIFICATION.md` - Added section 11A "Editor Support" with extension details
- ✅ `docs/IDEAS.md` - Updated Editor Plugins status to "Partially Implemented"
- ✅ `docs/CONTRIBUTING.md` - Marked VSCode extension as completed
- ✅ `vscode/iatf/README.md` - Comprehensive extension documentation

### Benefits

1. **Improved readability** - Color-coded syntax makes IATF files easier to scan
2. **Visual hierarchy** - Distinct colors for INDEX vs CONTENT sections
3. **Error prevention** - Syntax highlighting helps spot formatting issues
4. **Professional appearance** - IATF files look polished in VSCode
5. **Developer adoption** - Lowers barrier to entry for new users
6. **Cross-editor support** - Works in VSCode, and VSCode forks

### Future Enhancements (Not in Current Version)

- [ ] Auto-rebuild on save integration
- [ ] IntelliSense for section IDs
- [ ] Go to Definition for references (`{@section-id}`)
- [ ] Validation warnings inline
- [ ] Section folding/outlining
- [ ] Live preview of INDEX while editing CONTENT

---

## Task 3: Implement `iatf graph` command

**Priority:** High
**Status:** In Progress

### Summary
Implement a new `graph` command that displays section-to-section cross-references in a compact, token-efficient text format. This helps AI agents understand the relationship network between sections without loading the full document.

### Background & Motivation

**Problem:** Agents need to understand document structure and dependencies:
- "Which sections reference this section?" (impact analysis when editing)
- "What sections does this section depend on?" (reading path)
- "How are concepts interconnected?" (conceptual graph)

**Current Limitations:**
- `index` command shows hierarchy (parent-child) only
- No way to see cross-reference relationships via `{@section-id}` syntax
- Agents must read full content to discover dependencies

### Output Format: Compact Text

**Default format** (outgoing references only):
```text
@graph: document.iatf

section-id -> referenced-id-1, referenced-id-2
another-section -> referenced-id-3
section-with-no-refs
```

**Legend:**
- `section-id -> target-id` = section references target (outgoing reference)
- Standalone `section-id` = section exists but has no outgoing references
- One line per section that has references, clean and minimal

**Example:**
```text
@graph: api-docs.iatf

intro -> setup, auth
auth -> security-model, api-design, session-mgmt
api-endpoints -> auth, data-model
setup -> prerequisites
deployment -> auth, api-endpoints
monitoring
troubleshooting -> api-endpoints, auth
```

### Command Specification

```bash
iatf graph <file> [--show-incoming]
```

**Behavior:**
1. Parse the CONTENT section to extract all `{@section-id}` references
2. Build maps of section -> [referenced sections] (outgoing) and section -> [who references it] (incoming)
3. Output in compact text format based on flag
4. Exit code 0 on success, non-zero on error

**Rules:**
- Default: show outgoing references (what each section points to)
- With `--show-incoming`: show incoming references (who points to this section)
- Ignore references inside code blocks (`` ` `` and ` ``` `)
- Show sections in order they appear in the document
- If a section has no references, show just the ID on its own line
- References are comma-separated and sorted alphabetically

### Implementation Details

**Go (`go/main.go):
```go
func graphCommand(filePath string) error {
    // 1. Parse file
    sections, err := parseContentSections(filePath)
    if err != nil {
        return err
    }

    // 2. Extract references
    referenceMap := make(map[string][]string)
    for sectionID, content := range sections {
        refs := extractReferences(content)
        referenceMap[sectionID] = refs
    }

    // 3. Output
    fmt.Printf("@graph: %s\n\n", filepath.Base(filePath))

    for sectionID := range sections {
        refs := referenceMap[sectionID]
        if len(refs) > 0 {
            fmt.Printf("%s -> %s\n", sectionID, strings.Join(refs, ", "))
        } else {
            fmt.Println(sectionID)
        }
    }

    return nil
}
```

**Reuse Existing Logic:**
- Reference extraction already exists for validation (`extractReferences`)
- Section parsing already exists for rebuild
- Should NOT duplicate code - refactor to shared functions

### Edge Cases

1. **Circular references** - Allowed, show both directions:
   ```text
   intro -> auth
   auth -> intro
   ```

2. **Self-references** - Should not appear (validation prevents them)

3. **Missing targets** - Should not appear (validation prevents them)

4. **Sections with no references** - Show standalone:
   ```text
   intro -> auth
   standalone-section
   auth -> intro
   ```

5. **Empty file** - Output just the header:
   ```text
   @graph: file.iatf

   (no sections found)
   ```

6. **Invalid IATF file** - Error message and exit code 1

### Testing

Test with existing example files:

```bash
# Should show cross-references
./iatf graph examples/cross-references.iatf

# Expected output:
@graph: cross-references.iatf

section1 -> section2, section3
section2 -> section3
section3 -> section1
section4
```

### Implemented Features

- ✅ Compact text output format
- ✅ Outgoing references (default)
- ✅ `--show-incoming` flag for reverse references (impact analysis)

### Future Enhancements (Not Currently Implemented)

These are **deferred** for future versions if needed:

- ~~`--format=json|mermaid|table`~~ - Other output formats
- ~~`--depth=N`~~ - Limit depth
- ~~`--types=hierarchy|references`~~ - Filter relationship types

The current implementation covers the most common use cases.

### Documentation Updates

After implementation, update:
- [ ] `README.md` - Add `graph` to command list with example
- [ ] `docs/SPECIFICATION.md` - Document graph output format
- [ ] Example output for `examples/cross-references.iatf`

### Success Criteria

- ✅ Command works in Go implementation
- ✅ Handles all edge cases gracefully
- ✅ Reuses existing validation logic (no code duplication)
- ✅ Clear, minimal, token-efficient output
- ✅ Documented with examples

---

## Task 4: Benchmark IATF against PageIndex on FinanceBench

**Priority:** High
**Status:** Pending

> **Note:** This task describes the benchmark approach. Any implementation scripts should be written in Go (the current maintained language) or as language-agnostic pseudocode.

### Summary
Validate IATF format effectiveness by benchmarking against PageIndex's 98.7% accuracy on the FinanceBench dataset. This will prove whether IATF's line-level granularity and self-indexing approach can match or exceed existing solutions while maintaining claimed token efficiency (80-95% savings).

### Background & Motivation

**Problem:** IATF needs empirical validation that it actually saves tokens and maintains high accuracy for document navigation tasks.

**Comparison Target:** PageIndex achieved 98.7% accuracy on FinanceBench by using:
- JSON-based tree structure with page-level indices
- Hierarchical nodes with summaries
- Reasoning-based retrieval (vectorless RAG)
- Two-file system (PDF + JSON index)

**IATF Advantages to Test:**
- Line-level precision (vs page-level)
- Single-file system (vs PDF + JSON)
- Human-readable plain text (vs JSON)
- Richer metadata (word counts, timestamps, content hash)
- Cross-references with validation

**Success Criteria:**
- Accuracy ≥ 95% (competitive with PageIndex's 98.7%)
- Token usage ≥ 70% less than loading full documents
- Clear performance profile showing where IATF excels/struggles

### Data Sources

#### 1. FinanceBench Dataset
**Repository:** https://github.com/patronus-ai/financebench

**Contents:**
- 150 annotated questions (open-source sample from 10,231 total)
- Question types: metrics-generated, domain-relevant (dg01-dg25), novel-generated
- Document types: 10-K annual reports, 10-Q quarterly reports, 8-K current reports, earnings call transcripts
- Data files:
  - `questions.jsonl` - question ID, text, gold answer, evidence, justification, doc reference
  - `metadata.jsonl` - doc name, type, period, URL, company, industry sector
  - `/pdfs/` directory - source PDF documents

**Question Format:**
```json
{
  "question_id": "dg01",
  "question": "What was Amazon's revenue in Q3 2023?",
  "answer": "$143.1 billion",
  "doc_name": "amazon_10q_2023_q3",
  "evidence": ["Page 5: Total net sales were $143.1 billion..."],
  "evidence_page_num": [5],
  "justification": "..."
}
```

#### 2. Evaluation Code
**Repository:** https://github.com/VectifyAI/Mafin2.5-FinanceBench

**Key File:** Evaluation module (reference implementation)
- `check_answer_equivalence()` - validates answers using LLM judge
- Handles numerical flexibility (1.2 ≈ 1.23, fractions ≈ percentages)
- Semantic evaluation (meaning/conclusion equivalence)
- Hybrid multi-model evaluation (GPT-4o, o1-mini, o3-mini ensemble)
- Returns boolean correctness per question

**Usage:**
```
check_answer_equivalence(
    predicted_answer="$143.1 billion",
    gold_answer="$143.1 billion",
    question="What was Amazon's revenue in Q3 2023?",
    model="gpt-4o"
)
```

#### 3. PageIndex Reference
**Repository:** https://github.com/VectifyAI/PageIndex
**Website:** https://pageindex.ai

**Format Structure:**
```json
{
  "title": "Financial Stability",
  "node_id": "0006",
  "start_index": 21,
  "end_index": 22,
  "summary": "The Federal Reserve...",
  "nodes": [
    {
      "title": "Monitoring Financial Vulnerabilities",
      "node_id": "0007",
      "start_index": 22,
      "end_index": 28,
      "summary": "..."
    }
  ]
}
```

### Key Differences: PageIndex vs IATF

| Aspect | PageIndex | IATF |
|--------|-----------|------|
| **Format** | JSON | Plain text with delimiters |
| **Addressing** | Page numbers (coarse) | Line numbers (fine) |
| **File Model** | Two files (PDF + JSON index) | Single file (INDEX + CONTENT) |
| **Hierarchy** | JSON nesting (unlimited depth) | Markdown levels (depth: 2) |
| **IDs** | Numeric (`"0006"`) | Semantic (`#financial-stability`) |
| **Editability** | Read-only PDFs | Fully editable text |
| **Sync** | Manual regeneration | Auto-rebuild with watch mode |
| **Metadata** | title, node_id, indices, summary | + word counts, timestamps, hash, tags |
| **Cross-refs** | Navigate tree structure | `{@section-id}` with validation |
| **Human Readable** | Requires JSON viewer | Direct text scanning |

**Core Philosophy:**
- **PageIndex:** Retrofit solution to index existing PDFs
- **IATF:** Native format for creating AI-navigable documents

### Implementation Approach

#### Phase 1: Data Preparation (Week 1)

**1.1 Clone Repositories**
```bash
# Get dataset
git clone https://github.com/patronus-ai/financebench.git

# Get evaluation code
git clone https://github.com/VectifyAI/Mafin2.5-FinanceBench.git
```

**1.2 Build PDF -> IATF Converter**

**Tool Stack:**
- `pdfplumber` or `PyMuPDF` - text extraction with page info
- LLM (GPT-4) - section detection and summarization
- IATF builder - generate valid `.iatf` files

**Conversion Pipeline:**
```
1. Extract text with page numbers from PDF
2. Detect sections using LLM
   - Identify headers (bold, larger fonts, TOC entries)
   - Find topic changes (semantic breaks)
   - Locate financial statement boundaries
3. Generate summaries for each section
4. Build IATF structure with metadata
5. Write output and validate with iatf validate
```

**Section Detection Strategy:**
```
Level 1 (#):
  - Document title (10-K, Quarterly Report, etc.)
  - Major sections (Financial Statements, Risk Factors, MD&A)

Level 2 (##):
  - Subsections (Balance Sheet, Income Statement, Q3 Results)
  - Statement line items (Revenue, Operating Expenses)
```

**Challenges:**
- Complex tables -> may need special handling
- Multi-column layouts -> proper text ordering
- Footnotes and references -> associate with correct sections
- Charts/graphs -> summarize in text form

**Quality Assurance:**
- Manual review of 10 sample conversions
- Validate all files with `iatf validate`
- Check line number accuracy
- Verify summary quality

**1.3 Convert All Documents**
```bash
# Script to convert PDFs to IATF format
convert_financebench \
  --input financebench/pdfs/ \
  --output iatf_docs/ \
  --validate
```

**Output:** 150 `.iatf` files corresponding to benchmark documents

#### Phase 2: Build IATF Retrieval System (Week 2)

**2.1 Core Retriever Algorithm**

The retriever should implement:

1. **Index Loading**
   - Read file until `===CONTENT===` delimiter
   - Parse index entries to extract section metadata (ID, line ranges, summaries)
   - Track token count of index for metrics

2. **Section Selection**
   - Format index with summaries for LLM consumption
   - Send prompt to LLM asking it to identify relevant section IDs
   - Parse JSON array response containing section IDs
   - Track reasoning tokens used

3. **Content Loading**
   - For each selected section ID:
     - Look up start/end line numbers from index
     - Read those specific lines from file
     - Track content tokens loaded
   - Concatenate all section content

4. **Answer Generation**
   - Build context prompt with loaded sections
   - Send to LLM with instructions for precise answers
   - Calculate total tokens used (index + reasoning + content + answer)
   - Return answer and metrics

**2.2 Utility Functions**

Required utility functions:

- **Token Counter**: Count tokens in text using appropriate tokenizer for target LLM
- **Index Parser**: Parse IATF index entries using regex pattern `# Title {#id | lines:start-end | words:count}`
- **Index Formatter**: Format parsed index entries into readable text for LLM consumption
- **Line Reader**: Read specific line ranges from file efficiently

#### Phase 3: Run Evaluation (Week 3)

**3.1 Evaluation Script**

Evaluation algorithm:

1. Load all 150 questions from `financebench/questions.jsonl`
2. For each question:
   - Extract question_id, question_text, gold_answer, doc_name
   - Locate corresponding IATF file: `iatf_docs/{doc_name}.iatf`
   - Skip if file missing
   - Initialize retriever with IATF file
   - Measure time and get predicted_answer with metrics
   - Check answer correctness using equivalence function
   - Store result with all metrics (tokens, latency, retrieval ratio)
3. Handle errors gracefully, storing error info
4. Save results to JSONL and CSV formats
5. Calculate and display summary statistics:
   - Accuracy percentage
   - Average total tokens
   - Average latency
   - Average retrieval ratio

**3.2 Baseline Comparison**

Also measure performance of loading full documents:

For each question:
1. Load entire CONTENT section of IATF file
2. Answer with full context (no index-based selection)
3. Track token count (will be much higher than IATF approach)
4. Calculate accuracy for comparison

**Comparison Metrics:**
- Token reduction: `(baseline_tokens - iatf_tokens) / baseline_tokens * 100`
- Accuracy delta: `iatf_accuracy - baseline_accuracy`

#### Phase 4: Analysis & Iteration (Week 4)

**4.1 Performance Analysis**

Generate visualizations and reports showing:

1. **Accuracy Comparison**: Bar chart comparing PageIndex (98.7%), IATF, and full document baseline
2. **Token Efficiency**: Stacked bar chart showing index tokens vs content tokens per question
3. **Retrieval Precision**: Scatter plot of retrieval ratio vs correctness to analyze correlation

**4.2 Error Analysis**

Analyze incorrect answers by:
- Listing failed questions with predicted vs gold answers
- Counting sections retrieved for each failure
- Classifying error types:
  - **RETRIEVAL**: Correct section not loaded
  - **REASONING**: Section loaded but wrong answer extracted
  - **CONVERSION**: PDF->IATF conversion lost information
  - **AMBIGUOUS**: Unclear if answer is truly wrong

**4.3 Iteration Strategy**

Based on error analysis, improve:

**If Accuracy < 90%:**
- [ ] Improve section detection in PDF conversion
- [ ] Enhance summary quality (more detailed summaries)
- [ ] Add financial-specific metadata (e.g., `@metric: revenue`, `@period: Q3-2023`)
- [ ] Implement multi-hop retrieval (follow cross-references)
- [ ] Tune section selection prompt

**If Token Usage Not Competitive:**
- [ ] Create more granular sections (smaller chunks)
- [ ] Improve section selection reasoning
- [ ] Add hierarchical retrieval (load parent summaries, then drill down)

**If Latency Too High:**
- [ ] Cache parsed indices in memory
- [ ] Parallelize section loading
- [ ] Use faster models for section selection (GPT-3.5 instead of GPT-4)

### Deliverables

**Code:**
- [ ] `cmd/pdf-convert` - PDF to IATF conversion tool
- [ ] `cmd/retriever` - IATF retrieval system
- [ ] `cmd/evaluate` - Evaluation pipeline
- [ ] `cmd/analyze` - Result analysis and visualization

**Data:**
- [ ] `iatf_docs/` - 150 converted IATF files
- [ ] `results/iatf_results.jsonl` - Raw evaluation results
- [ ] `results/iatf_results.csv` - Spreadsheet format
- [ ] `results/baseline_results.jsonl` - Full document baseline

**Documentation:**
- [ ] `BENCHMARK.md` - Detailed methodology and results
- [ ] `results/summary_report.md` - Executive summary
- [ ] `results/error_analysis.md` - Error breakdown and insights
- [ ] Visual charts (accuracy, tokens, latency comparisons)

**Benchmark Report Structure:**
```markdown
# IATF FinanceBench Benchmark Report

## Executive Summary
- Accuracy: X% (vs PageIndex 98.7%)
- Token Savings: X% (vs full document baseline)
- Avg Latency: Xs per question

## Methodology
[Describe conversion, retrieval, evaluation process]

## Results
[Tables, charts, statistics]

## Error Analysis
[What went wrong and why]

## Comparison with PageIndex
[Key differences in performance]

## Conclusions
[Is IATF competitive? Where does it excel/struggle?]

## Future Improvements
[Actionable next steps]
```

### Dependencies

**Required Tools:**
- PDF text extraction library
- LLM API client (OpenAI or compatible)
- Token counting library
- Data analysis and visualization tools

**External Repos:**
```bash
git clone https://github.com/patronus-ai/financebench.git
git clone https://github.com/VectifyAI/Mafin2.5-FinanceBench.git
```

**IATF Tools:**
- Ensure `iatf` CLI is built and in PATH
- Use `iatf validate` for all generated files

### Timeline Estimate

- **Week 1:** Data preparation and PDF conversion (5-7 days)
- **Week 2:** Build retrieval system (5-7 days)
- **Week 3:** Run evaluation and collect results (3-5 days)
- **Week 4:** Analysis, iteration, documentation (5-7 days)

**Total:** ~4 weeks for initial benchmark + iteration cycle

### Success Metrics

**Must Have:**
- ✅ Accuracy ≥ 90% on FinanceBench
- ✅ Token reduction ≥ 50% vs full documents
- ✅ Complete evaluation on all 150 questions

**Nice to Have:**
- ✅ Accuracy ≥ 95% (close to PageIndex)
- ✅ Token reduction ≥ 70%
- ✅ Latency ≤ 10s per question
- ✅ Clear insights on IATF strengths/weaknesses

### Notes

- This benchmark will provide empirical validation for IATF's claims
- Results will guide future format improvements
- Consider publishing results to establish credibility
- May want to test on other benchmarks (legal docs, technical manuals, etc.)


