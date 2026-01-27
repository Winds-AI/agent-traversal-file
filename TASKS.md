# Task List

## Task 1: Add PID-based warning for rebuild on watched files

**Priority:** Medium
**Status:** Completed

### Summary
Prevents redundant double rebuilds when manually running `iatf rebuild` on a file that's being watched.

### What was implemented

**Python (`python/iatf.py`):**
- `is_process_running(pid)` - checks if process exists
- `prompt_user_confirmation()` - interactive yes/no prompt
- `check_watched_file()` - validates PID and prompts user
- `watch_command()` - stores PID, cleans up on exit/signals
- `rebuild_command()` - checks for watched files before rebuild

**Go (`go/main.go` + platform files):**
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
- User cancels → exit 1 with "Rebuild cancelled, no changes made."
- User confirms → proceeds with rebuild
- Non-interactive (CI/scripts) → returns default (cancel)

### Edge cases handled
- Stale PID (process dead) → proceeds without warning
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
- Format declaration highlighting (`:::IATF/1.0`)
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
- ✅ `QUICKSTART.md` - Added Editor Setup section with extension link
- ✅ `SPECIFICATION.md` - Added section 11A "Editor Support" with extension details
- ✅ `IDEAS.md` - Updated Editor Plugins status to "Partially Implemented"
- ✅ `CONTRIBUTING.md` - Marked VSCode extension as completed
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
2. Build maps of section → [referenced sections] (outgoing) and section → [who references it] (incoming)
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

**Both Python and Go implementations required:**

**Python (`python/iatf.py`):**
```python
def graph_command(file_path: str):
    """Display section reference graph."""
    # 1. Parse file to extract sections
    sections = parse_content_sections(file_path)

    # 2. Extract references from each section
    reference_map = {}
    for section_id, section_content in sections.items():
        refs = extract_references(section_content)
        reference_map[section_id] = refs

    # 3. Output in compact format
    print(f"@graph: {os.path.basename(file_path)}")
    print()

    for section_id in sections.keys():
        refs = reference_map.get(section_id, [])
        if refs:
            print(f"{section_id} -> {', '.join(refs)}")
        else:
            print(section_id)
```

**Go (`go/main.go`):**
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
- [ ] `SPECIFICATION.md` - Document graph output format
- [ ] Example output for `examples/cross-references.iatf`

### Success Criteria

- ✅ Command works in both Python and Go implementations
- ✅ Output is consistent between implementations
- ✅ Handles all edge cases gracefully
- ✅ Reuses existing validation logic (no code duplication)
- ✅ Clear, minimal, token-efficient output
- ✅ Documented with examples

---

## Task 4: Benchmark IATF against PageIndex on FinanceBench

**Priority:** High
**Status:** In Progress

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

**Key File:** `eval.py`
- `check_answer_equivalence()` - validates answers using LLM judge
- Handles numerical flexibility (1.2 ≈ 1.23, fractions ≈ percentages)
- Semantic evaluation (meaning/conclusion equivalence)
- Hybrid multi-model evaluation (GPT-4o, o1-mini, o3-mini ensemble)
- Returns boolean correctness per question

**Usage:**
```python
is_correct = await check_answer_equivalence(
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

**1.2 Build PDF → IATF Converter**

**Tool Stack:**
- `pdfplumber` or `PyMuPDF` - text extraction with page info
- LLM (GPT-4) - section detection and summarization
- IATF builder - generate valid `.iatf` files

**Conversion Pipeline:**
```python
def pdf_to_iatf(pdf_path, output_path):
    # 1. Extract text with page numbers
    pages = extract_pdf_text(pdf_path)

    # 2. Detect sections using LLM
    sections = detect_sections(pages)
    # Uses GPT-4 to identify:
    #   - Headers (bold, larger fonts, TOC entries)
    #   - Topic changes (semantic breaks)
    #   - Financial statement boundaries

    # 3. Generate summaries for each section
    for section in sections:
        section['summary'] = generate_summary(section['content'])

    # 4. Build IATF structure
    iatf_content = build_iatf(
        title=extract_title(pdf_path),
        sections=sections,
        metadata={
            'created': today(),
            'source': 'financebench',
            'doc_type': extract_doc_type(pdf_path)
        }
    )

    # 5. Write and validate
    write_iatf(output_path, iatf_content)
    run_iatf_validate(output_path)
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
- Complex tables → may need special handling
- Multi-column layouts → proper text ordering
- Footnotes and references → associate with correct sections
- Charts/graphs → summarize in text form

**Quality Assurance:**
- Manual review of 10 sample conversions
- Validate all files with `iatf validate`
- Check line number accuracy
- Verify summary quality

**1.3 Convert All Documents**
```bash
python scripts/convert_financebench.py \
  --input financebench/pdfs/ \
  --output iatf_docs/ \
  --validate
```

**Output:** 150 `.iatf` files corresponding to benchmark documents

#### Phase 2: Build IATF Retrieval System (Week 2)

**2.1 Core Retriever Class**

```python
class IATFRetriever:
    """Efficient document navigation using IATF format."""

    def __init__(self, iatf_file_path: str):
        self.file_path = iatf_file_path
        self.index = self._load_index()
        self.metrics = {
            'index_tokens': 0,
            'reasoning_tokens': 0,
            'content_tokens': 0,
            'total_tokens': 0,
            'sections_retrieved': 0,
            'total_sections': len(self.index)
        }

    def _load_index(self) -> dict:
        """Load only INDEX section (until ===CONTENT===)."""
        index_lines = []
        with open(self.file_path, 'r') as f:
            in_index = False
            for line in f:
                if '===INDEX===' in line:
                    in_index = True
                elif '===CONTENT===' in line:
                    break
                elif in_index:
                    index_lines.append(line)

        # Parse index entries
        parsed = parse_index_entries(''.join(index_lines))
        self.metrics['index_tokens'] = count_tokens(''.join(index_lines))
        return parsed

    def retrieve_relevant_sections(
        self,
        question: str,
        model: str = "gpt-4"
    ) -> list[str]:
        """Use LLM reasoning to select relevant sections."""

        # Format index for LLM
        index_text = format_index_for_llm(self.index)

        prompt = f"""You are analyzing a financial document index to answer a question.

Document Index:
{index_text}

Question: {question}

Task: Identify which sections would contain information to answer this question.
Return section IDs in order of relevance (most relevant first).

Rules:
- Only return section IDs that exist in the index
- Include parent sections if child sections are relevant
- Aim for 2-5 sections maximum
- If uncertain, include rather than exclude

Format: Return JSON array of section IDs
Example: ["#revenue-q3", "#operating-expenses", "#cash-flow"]
"""

        response = get_completion(prompt, model)
        self.metrics['reasoning_tokens'] += count_tokens(prompt + response)

        section_ids = json.loads(response)
        return section_ids

    def load_sections(self, section_ids: list[str]) -> str:
        """Load specific sections by line numbers from INDEX."""
        content_parts = []

        for section_id in section_ids:
            if section_id not in self.index:
                continue

            start_line = self.index[section_id]['start_line']
            end_line = self.index[section_id]['end_line']

            # Read specific line range
            section_content = read_lines(self.file_path, start_line, end_line)
            content_parts.append(section_content)
            self.metrics['sections_retrieved'] += 1
            self.metrics['content_tokens'] += count_tokens(section_content)

        return '\n\n'.join(content_parts)

    def answer_question(
        self,
        question: str,
        model: str = "gpt-4"
    ) -> tuple[str, dict]:
        """Full QA pipeline with metrics tracking."""

        # Step 1: Index-based section selection
        relevant_sections = self.retrieve_relevant_sections(question, model)

        # Step 2: Load only relevant sections
        context = self.load_sections(relevant_sections)

        # Step 3: Generate answer
        answer_prompt = f"""Based on the following document sections, answer the question.

Question: {question}

Context:
{context}

Instructions:
- Answer based ONLY on information in the context
- Be precise with numbers, dates, and financial figures
- If the context doesn't contain the answer, say "Information not found"
- Provide direct answers without unnecessary explanation

Answer:"""

        answer = get_completion(answer_prompt, model)
        self.metrics['total_tokens'] = (
            self.metrics['index_tokens'] +
            self.metrics['reasoning_tokens'] +
            self.metrics['content_tokens'] +
            count_tokens(answer_prompt + answer)
        )

        return answer, self.metrics

def read_lines(file_path: str, start: int, end: int) -> str:
    """Read specific line range from file (1-indexed)."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
        return ''.join(lines[start-1:end])
```

**2.2 Utility Functions**

```python
def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens using tiktoken."""
    import tiktoken
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def parse_index_entries(index_text: str) -> dict:
    """Parse IATF index into structured dict."""
    # Regex pattern: # Title {#id | lines:start-end | words:count}
    pattern = r'^(#+)\s+(.+?)\s+\{#([a-zA-Z0-9-_]+)\s+\|\s+lines:(\d+)-(\d+)'

    sections = {}
    for line in index_text.split('\n'):
        match = re.match(pattern, line)
        if match:
            level, title, section_id, start, end = match.groups()
            sections[f"#{section_id}"] = {
                'level': len(level),
                'title': title,
                'start_line': int(start),
                'end_line': int(end),
                'summary': extract_summary(index_text, line)
            }
    return sections

def format_index_for_llm(index: dict) -> str:
    """Format index in readable form for LLM reasoning."""
    formatted = []
    for section_id, info in index.items():
        formatted.append(
            f"{section_id} | {info['title']} (lines {info['start_line']}-{info['end_line']})\n"
            f"  Summary: {info.get('summary', 'N/A')}"
        )
    return '\n\n'.join(formatted)
```

#### Phase 3: Run Evaluation (Week 3)

**3.1 Evaluation Script**

```python
import json
import asyncio
from tqdm import tqdm
import pandas as pd
from eval import check_answer_equivalence

async def evaluate_iatf_on_financebench():
    """Run full evaluation on 150 benchmark questions."""

    # Load questions
    questions = []
    with open('financebench/questions.jsonl', 'r') as f:
        questions = [json.loads(line) for line in f]

    results = []

    for q in tqdm(questions, desc="Evaluating"):
        question_id = q['question_id']
        question_text = q['question']
        gold_answer = q['answer']
        doc_name = q['doc_name']

        # Find IATF file
        iatf_file = f"iatf_docs/{doc_name}.iatf"

        if not os.path.exists(iatf_file):
            print(f"Missing IATF file: {iatf_file}")
            continue

        try:
            # Initialize retriever
            retriever = IATFRetriever(iatf_file)

            # Get answer with metrics
            start_time = time.time()
            predicted_answer, metrics = retriever.answer_question(
                question_text,
                model="gpt-4"
            )
            latency = time.time() - start_time

            # Evaluate correctness
            is_correct = await check_answer_equivalence(
                predicted_answer,
                gold_answer,
                question_text,
                model="gpt-4o"
            )

            results.append({
                'question_id': question_id,
                'question': question_text,
                'predicted_answer': predicted_answer,
                'gold_answer': gold_answer,
                'correct': is_correct,
                'latency_seconds': latency,
                'index_tokens': metrics['index_tokens'],
                'reasoning_tokens': metrics['reasoning_tokens'],
                'content_tokens': metrics['content_tokens'],
                'total_tokens': metrics['total_tokens'],
                'sections_retrieved': metrics['sections_retrieved'],
                'total_sections': metrics['total_sections'],
                'retrieval_ratio': metrics['sections_retrieved'] / metrics['total_sections']
            })

        except Exception as e:
            print(f"Error on {question_id}: {e}")
            results.append({
                'question_id': question_id,
                'error': str(e)
            })

    # Save results
    df = pd.DataFrame(results)
    df.to_json('results/iatf_results.jsonl', orient='records', lines=True)
    df.to_csv('results/iatf_results.csv', index=False)

    # Calculate summary statistics
    accuracy = df['correct'].mean()
    avg_tokens = df['total_tokens'].mean()
    avg_latency = df['latency_seconds'].mean()
    avg_retrieval_ratio = df['retrieval_ratio'].mean()

    print(f"\n{'='*60}")
    print(f"IATF FinanceBench Evaluation Results")
    print(f"{'='*60}")
    print(f"Accuracy: {accuracy*100:.2f}% ({df['correct'].sum()}/{len(df)} correct)")
    print(f"Avg Total Tokens: {avg_tokens:.0f}")
    print(f"Avg Latency: {avg_latency:.2f}s")
    print(f"Avg Retrieval Ratio: {avg_retrieval_ratio*100:.1f}% of sections loaded")
    print(f"{'='*60}\n")

    return df

# Run evaluation
if __name__ == "__main__":
    asyncio.run(evaluate_iatf_on_financebench())
```

**3.2 Baseline Comparison**

Also measure performance of loading full documents:

```python
def evaluate_full_document_baseline():
    """Measure tokens/accuracy without IATF indexing."""

    for q in questions:
        # Load entire CONTENT section
        full_content = load_full_content(iatf_file)

        # Answer with full context
        answer = answer_with_full_context(question, full_content)

        # Track tokens (much higher)
        baseline_tokens = count_tokens(full_content)
```

**Comparison Metrics:**
- Token reduction: `(baseline_tokens - iatf_tokens) / baseline_tokens * 100`
- Accuracy delta: `iatf_accuracy - baseline_accuracy`

#### Phase 4: Analysis & Iteration (Week 4)

**4.1 Performance Analysis**

Generate visualizations and reports:

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Accuracy distribution
plt.figure(figsize=(10, 6))
sns.barplot(x=['PageIndex', 'IATF', 'Full Doc Baseline'],
            y=[98.7, iatf_accuracy, baseline_accuracy])
plt.title('Accuracy Comparison on FinanceBench')
plt.ylabel('Accuracy (%)')
plt.savefig('results/accuracy_comparison.png')

# Token efficiency
plt.figure(figsize=(10, 6))
df.plot(x='question_id', y=['index_tokens', 'content_tokens'], kind='bar', stacked=True)
plt.title('Token Usage Breakdown by Question')
plt.ylabel('Token Count')
plt.savefig('results/token_breakdown.png')

# Retrieval precision
plt.figure(figsize=(10, 6))
plt.scatter(df['retrieval_ratio'], df['correct'])
plt.xlabel('Retrieval Ratio (sections loaded / total)')
plt.ylabel('Correctness')
plt.title('Does Loading More Sections Improve Accuracy?')
plt.savefig('results/retrieval_analysis.png')
```

**4.2 Error Analysis**

```python
# Analyze incorrect answers
errors = df[df['correct'] == False]

for _, row in errors.iterrows():
    print(f"\nQuestion: {row['question']}")
    print(f"Predicted: {row['predicted_answer']}")
    print(f"Gold: {row['gold_answer']}")
    print(f"Sections Retrieved: {row['sections_retrieved']}")

    # Identify error type
    error_type = classify_error(row)
    # Types:
    #   - RETRIEVAL: Correct section not loaded
    #   - REASONING: Section loaded but wrong answer
    #   - CONVERSION: PDF→IATF conversion issue
    #   - AMBIGUOUS: Unclear if answer is truly wrong
```

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
- [x] `benchmark/scripts/pdf_to_iatf.py` - PDF conversion tool
- [x] `benchmark/scripts/iatf_retriever.py` - Retrieval system
- [x] `benchmark/scripts/evaluate.py` - Evaluation pipeline
- [x] `benchmark/scripts/analyze.py` - Result analysis and visualization

**Data:**
- [ ] `benchmark/iatf_docs/` - 150 converted IATF files (pending conversion)
- [ ] `benchmark/results/iatf_results.jsonl` - Raw evaluation results (pending run)
- [ ] `benchmark/results/iatf_results.csv` - Spreadsheet format (pending run)
- [ ] `benchmark/results/baseline_results.jsonl` - Full document baseline (pending run)

**Documentation:**
- [x] `benchmark/BENCHMARK.md` - Detailed methodology and usage
- [ ] `benchmark/results/summary_report.md` - Executive summary (pending run)
- [ ] `benchmark/results/error_analysis.md` - Error breakdown (pending run)
- [ ] Visual charts (accuracy, tokens, latency comparisons) (pending run)

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

**Python Packages:**
```bash
pip install -r benchmark/requirements.txt
# Or manually:
pip install pdfplumber PyMuPDF tiktoken openai pandas matplotlib seaborn tqdm
```

**External Repos (already cloned to benchmark/data/):**
```bash
# Already cloned during implementation:
# benchmark/data/financebench
# benchmark/data/Mafin2.5-FinanceBench
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


