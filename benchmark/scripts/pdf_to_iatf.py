#!/usr/bin/env python3
"""
PDF to IATF Converter for FinanceBench

Converts financial PDF documents to IATF format using:
1. pdfplumber/PyMuPDF for text extraction with page info
2. LLM (OpenAI GPT-4) for section detection and summarization
3. IATF builder for generating valid .iatf files

Usage:
    python pdf_to_iatf.py --input financebench/pdfs/ --output iatf_docs/ --validate
    python pdf_to_iatf.py --input single_file.pdf --output output.iatf
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def extract_pdf_text_pdfplumber(pdf_path: str) -> list[dict]:
    """Extract text from PDF using pdfplumber with page numbers."""
    if pdfplumber is None:
        raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            pages.append({"page_num": i, "text": text, "char_count": len(text)})
    return pages


def extract_pdf_text_pymupdf(pdf_path: str) -> list[dict]:
    """Extract text from PDF using PyMuPDF with page numbers."""
    if fitz is None:
        raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")

    pages = []
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text()
        pages.append({"page_num": i + 1, "text": text, "char_count": len(text)})
    doc.close()
    return pages


def extract_pdf_text(pdf_path: str) -> list[dict]:
    """Extract text from PDF using available library."""
    if pdfplumber is not None:
        return extract_pdf_text_pdfplumber(pdf_path)
    elif fitz is not None:
        return extract_pdf_text_pymupdf(pdf_path)
    else:
        raise ImportError(
            "Neither pdfplumber nor PyMuPDF installed. Run: pip install pdfplumber pymupdf"
        )


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def generate_section_id(title: str) -> str:
    """Generate a valid IATF section ID from title."""
    # Convert to lowercase, replace spaces/special chars with hyphens
    section_id = title.lower()
    section_id = re.sub(r"[^a-z0-9]+", "-", section_id)
    section_id = re.sub(r"-+", "-", section_id)  # Remove consecutive hyphens
    section_id = section_id.strip("-")

    # Truncate to reasonable length
    if len(section_id) > 50:
        section_id = section_id[:50].rsplit("-", 1)[0]

    return section_id or "section"


def detect_sections_with_llm(
    pages: list[dict], client, model: str = "gpt-4o"
) -> list[dict]:
    """Use LLM to detect sections and generate summaries from PDF content."""
    # Combine all text (limit to avoid token limits)
    full_text = ""
    page_boundaries = []
    char_count = 0

    for page in pages:
        page_start = char_count
        full_text += f"\n\n=== PAGE {page['page_num']} ===\n\n{page['text']}"
        char_count = len(full_text)
        page_boundaries.append(
            {"page_num": page["page_num"], "start": page_start, "end": char_count}
        )

    # Truncate if too long (GPT-4 context limits)
    max_chars = 100000
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n\n[TRUNCATED...]"

    prompt = f"""Analyze this financial document and identify its logical sections. 
For each section, provide:
1. title - A descriptive title for the section
2. level - 1 for major sections (e.g., "Financial Statements", "Risk Factors"), 2 for subsections
3. start_page - The page number where this section starts
4. end_page - The page number where this section ends
5. summary - A 1-2 sentence summary of what this section contains

Focus on identifying:
- Major SEC filing sections (Business, Risk Factors, Financial Data, MD&A, Financial Statements, Notes)
- Financial statements (Income Statement, Balance Sheet, Cash Flow Statement)
- Key subsections within these

Return as a JSON array of section objects.

Document content:
{full_text}

Return ONLY valid JSON array, no other text."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=4000,
        )

        response_text = response.choices[0].message.content
        # Extract JSON from response
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            sections = json.loads(json_match.group())
            return sections
        else:
            print(f"Warning: Could not parse LLM response as JSON")
            return []
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return []


def detect_sections_heuristic(pages: list[dict]) -> list[dict]:
    """Fallback heuristic section detection without LLM.

    Focuses on finding actual section headers (ITEM 1, PART I, etc.)
    that appear in SEC financial filings.
    """
    sections = []
    seen_titles = set()  # Track unique section titles

    # SEC filing section patterns - capture full title line
    # Pattern format: (regex, level, title_extractor)
    major_headers = [
        # ITEM patterns - capture full item title
        (r"^(ITEM\s+\d+[A-Z]?\.?\s*[-–]?\s*[A-Za-z][A-Za-z\s,&']+)", 1),
        # PART patterns
        (r"^(PART\s+(?:I|II|III|IV|V|VI)\b[^-–\n]*)", 1),
        # Financial statement headers
        (r"^(CONSOLIDATED\s+STATEMENTS?\s+OF\s+[A-Z][A-Za-z\s]+)", 2),
        (r"^(CONSOLIDATED\s+BALANCE\s+SHEETS?)", 2),
        (r"^(NOTES\s+TO\s+(?:THE\s+)?CONSOLIDATED\s+FINANCIAL\s+STATEMENTS?)", 2),
        # MD&A
        (r"^(MANAGEMENT['']?S?\s+DISCUSSION\s+AND\s+ANALYSIS[^\n]*)", 1),
        # Risk Factors
        (r"^(RISK\s+FACTORS)\s*$", 1),
    ]

    for page in pages:
        page_text = page["text"]
        page_num = page["page_num"]

        # Skip pages that look like TOC (many lines ending with page numbers)
        lines = page_text.split("\n")
        toc_indicators = sum(
            1
            for line in lines
            if re.search(r"\.{2,}\s*\d+\s*$", line.strip())  # ....... 45
            or re.search(r"\s{3,}\d+\s*$", line.strip())  # spaces then number
        )
        if toc_indicators > 5:  # Likely a TOC page
            continue

        for pattern_str, level in major_headers:
            pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
            matches = pattern.finditer(page_text)

            for match in matches:
                # Extract and clean the full title
                title = match.group(1).strip()
                title = re.sub(r"\s+", " ", title)
                title = title.rstrip(".")

                # Truncate very long titles
                if len(title) > 80:
                    title = title[:77] + "..."

                # Create a normalized key for deduplication
                title_key = re.sub(r"[^a-zA-Z0-9]", "", title.lower())[:30]
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                sections.append(
                    {
                        "title": title,
                        "level": level,
                        "start_page": page_num,
                        "end_page": page_num,
                        "summary": f"SEC filing section: {title}",
                        "_match_pos": match.start(),  # Track position for same-page ordering
                    }
                )

    # Sort sections by page, then by position within page
    sections.sort(key=lambda s: (s["start_page"], s.get("_match_pos", 0)))

    # Remove internal tracking field
    for sec in sections:
        sec.pop("_match_pos", None)

    # Assign end pages intelligently
    for i, section in enumerate(sections):
        if i < len(sections) - 1:
            next_section = sections[i + 1]
            if next_section["start_page"] > section["start_page"]:
                # Next section starts on a later page
                section["end_page"] = next_section["start_page"] - 1
            else:
                # Next section on same page - just use current page
                section["end_page"] = section["start_page"]
        else:
            # Last section extends to end of document
            section["end_page"] = (
                pages[-1]["page_num"] if pages else section["start_page"]
            )

        # Ensure end_page >= start_page
        section["end_page"] = max(section["end_page"], section["start_page"])

    # If no sections found, create logical page-based chunks
    if not sections:
        total_pages = len(pages)
        if total_pages > 0:
            chunk_size = max(10, total_pages // 10)  # ~10 sections
            for chunk_start in range(0, total_pages, chunk_size):
                start_page = chunk_start + 1
                end_page = min(chunk_start + chunk_size, total_pages)
                sections.append(
                    {
                        "title": f"Document Pages {start_page}-{end_page}",
                        "level": 1,
                        "start_page": start_page,
                        "end_page": end_page,
                        "summary": f"Content from pages {start_page} to {end_page}",
                    }
                )

    return sections


def get_content_for_section(pages: list[dict], start_page: int, end_page: int) -> str:
    """Get text content for a specific page range."""
    content = []
    for page in pages:
        if start_page <= page["page_num"] <= end_page:
            content.append(page["text"])
    return "\n\n".join(content)


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def build_iatf(
    title: str, sections: list[dict], pages: list[dict], metadata: dict
) -> str:
    """Build IATF file content from sections.

    The IATF format requires accurate line numbers in the INDEX.
    We build the file in two passes:
    1. First pass: Build content and calculate actual line numbers
    2. Second pass: Build INDEX with correct line numbers
    """
    # Track section IDs for uniqueness
    section_ids = {}
    section_data = []

    # Pre-calculate all section data
    for section in sections:
        base_id = generate_section_id(section["title"])

        # Ensure unique ID
        if base_id in section_ids:
            section_ids[base_id] += 1
            section_id = f"{base_id}-{section_ids[base_id]}"
        else:
            section_ids[base_id] = 1
            section_id = base_id

        # Get content for this section
        content = get_content_for_section(
            pages, section["start_page"], section["end_page"]
        )

        word_count = count_words(content)
        summary = section.get("summary", "")

        section_data.append(
            {
                "id": section_id,
                "title": section["title"],
                "level": section.get("level", 1),
                "content": content,
                "word_count": word_count,
                "summary": summary,
            }
        )

    # Build the file structure to calculate line numbers
    # Header lines
    header_lines = [
        ":::IATF/1.0",
        "",
        "===INDEX===",
        "",
    ]

    # Calculate INDEX section lines (we'll replace with actual later)
    index_lines = []
    for sec in section_data:
        prefix = "#" * sec["level"]
        # Placeholder - will be updated
        index_lines.append(
            f"{prefix} {sec['title']} {{#{sec['id']} | lines:0-0 | words:{sec['word_count']}}}"
        )
        if sec["summary"]:
            index_lines.append(f"  @summary: {sec['summary']}")

    index_lines.append("")  # Blank line after index entries

    # Metadata lines
    meta_lines = []
    if metadata:
        if "created" in metadata:
            meta_lines.append(f"@created: {metadata['created']}")
        if "source" in metadata:
            meta_lines.append(f"@source: {metadata['source']}")
        if "doc_type" in metadata:
            meta_lines.append(f"@doc_type: {metadata['doc_type']}")
        meta_lines.append("")  # Blank line after metadata

    # Content section header
    content_header = ["===CONTENT===", ""]

    # Calculate where CONTENT starts (1-indexed line number)
    content_start = (
        len(header_lines) + len(index_lines) + len(meta_lines) + len(content_header) + 1
    )

    # Build content and track line numbers
    content_lines = []
    current_line = content_start

    for sec in section_data:
        # Opening tag line
        sec["start_line"] = current_line
        content_lines.append(f"{{#{sec['id']}}}")
        current_line += 1

        # Blank line after opening tag
        content_lines.append("")
        current_line += 1

        # Content lines
        content_text_lines = sec["content"].split("\n")
        content_lines.extend(content_text_lines)
        current_line += len(content_text_lines)

        # Blank line before closing tag
        content_lines.append("")
        current_line += 1

        # Closing tag line
        content_lines.append(f"{{/{sec['id']}}}")
        sec["end_line"] = current_line
        current_line += 1

        # Blank line between sections
        content_lines.append("")
        current_line += 1

    # Now rebuild INDEX with correct line numbers
    index_lines = []
    for sec in section_data:
        prefix = "#" * sec["level"]
        index_line = (
            f"{prefix} {sec['title']} "
            f"{{#{sec['id']} | lines:{sec['start_line']}-{sec['end_line']} "
            f"| words:{sec['word_count']}}}"
        )
        index_lines.append(index_line)
        if sec["summary"]:
            index_lines.append(f"  @summary: {sec['summary']}")

    index_lines.append("")  # Blank line after index entries

    # Assemble final file
    all_lines = header_lines + index_lines + meta_lines + content_header + content_lines

    return "\n".join(all_lines)


def convert_pdf_to_iatf(
    pdf_path: str,
    output_path: str,
    openai_api_key: Optional[str] = None,
    model: str = "gpt-4o",
    validate: bool = False,
    verbose: bool = False,
) -> bool:
    """Convert a single PDF to IATF format."""
    if verbose:
        print(f"Converting: {pdf_path}")

    # Extract text
    try:
        pages = extract_pdf_text(pdf_path)
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return False

    if not pages:
        print(f"No text extracted from {pdf_path}")
        return False

    if verbose:
        print(
            f"  Extracted {len(pages)} pages, {sum(p['char_count'] for p in pages)} chars"
        )

    # Detect sections
    sections = []
    if openai_api_key and OpenAI:
        try:
            client = OpenAI(api_key=openai_api_key)
            sections = detect_sections_with_llm(pages, client, model)
            if verbose:
                print(f"  LLM detected {len(sections)} sections")
        except Exception as e:
            print(f"  LLM section detection failed: {e}")

    # Fallback to heuristic
    if not sections:
        sections = detect_sections_heuristic(pages)
        if verbose:
            print(f"  Heuristic detected {len(sections)} sections")

    # If still no sections, create a single section
    if not sections:
        sections = [
            {
                "title": "Document Content",
                "level": 1,
                "start_page": 1,
                "end_page": len(pages),
                "summary": "Full document content",
            }
        ]

    # Extract title and metadata
    pdf_name = Path(pdf_path).stem
    title = pdf_name.replace("_", " ")

    metadata = {
        "created": datetime.now().strftime("%Y-%m-%d"),
        "source": "financebench",
        "doc_type": "financial-report",
    }

    # Build IATF content
    iatf_content = build_iatf(title, sections, pages, metadata)

    # Write output
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(iatf_content)
        if verbose:
            print(f"  Wrote: {output_path}")
    except Exception as e:
        print(f"Error writing {output_path}: {e}")
        return False

    # Validate if requested
    if validate:
        try:
            result = subprocess.run(
                ["iatf", "validate", output_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                print(f"  Validation failed: {result.stderr or result.stdout}")
                return False
            if verbose:
                print(f"  Validation passed")
        except FileNotFoundError:
            if verbose:
                print("  Warning: iatf CLI not found, skipping validation")
        except Exception as e:
            print(f"  Validation error: {e}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert financial PDFs to IATF format"
    )
    parser.add_argument(
        "--input", "-i", required=True, help="Input PDF file or directory"
    )
    parser.add_argument(
        "--output", "-o", required=True, help="Output IATF file or directory"
    )
    parser.add_argument(
        "--validate", "-v", action="store_true", help="Validate generated IATF files"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY"),
        help="OpenAI API key for LLM section detection",
    )
    parser.add_argument(
        "--model", default="gpt-4o", help="OpenAI model for section detection"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of files to process (0 = no limit)",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if input_path.is_file():
        # Single file
        if output_path.suffix != ".iatf":
            output_path = output_path / f"{input_path.stem}.iatf"

        success = convert_pdf_to_iatf(
            str(input_path),
            str(output_path),
            openai_api_key=args.api_key,
            model=args.model,
            validate=args.validate,
            verbose=args.verbose,
        )
        sys.exit(0 if success else 1)

    elif input_path.is_dir():
        # Directory of PDFs
        output_path.mkdir(parents=True, exist_ok=True)

        pdf_files = list(input_path.glob("*.pdf"))
        if args.limit > 0:
            pdf_files = pdf_files[: args.limit]

        print(f"Processing {len(pdf_files)} PDF files...")

        success_count = 0
        fail_count = 0

        for i, pdf_file in enumerate(pdf_files, 1):
            iatf_output = output_path / f"{pdf_file.stem}.iatf"

            print(f"[{i}/{len(pdf_files)}] {pdf_file.name}")

            success = convert_pdf_to_iatf(
                str(pdf_file),
                str(iatf_output),
                openai_api_key=args.api_key,
                model=args.model,
                validate=args.validate,
                verbose=args.verbose,
            )

            if success:
                success_count += 1
            else:
                fail_count += 1

            # Rate limiting for API calls
            if args.api_key:
                time.sleep(0.5)

        print(f"\nCompleted: {success_count} succeeded, {fail_count} failed")
        sys.exit(0 if fail_count == 0 else 1)

    else:
        print(f"Error: Input path does not exist: {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()
