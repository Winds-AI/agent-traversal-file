#!/usr/bin/env python3
"""
IATF Retriever for FinanceBench Benchmark

Efficient document navigation using IATF format.
Uses the INDEX section for reasoning-based retrieval
and loads only relevant sections.

Usage:
    from iatf_retriever import IATFRetriever

    retriever = IATFRetriever("document.iatf")
    answer, metrics = retriever.answer_question("What was the revenue in Q3 2023?")
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


@dataclass
class RetrievalMetrics:
    """Metrics tracking for retrieval operations."""

    index_tokens: int = 0
    reasoning_tokens: int = 0
    content_tokens: int = 0
    answer_tokens: int = 0
    total_tokens: int = 0
    sections_retrieved: int = 0
    total_sections: int = 0
    retrieval_ratio: float = 0.0


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens using tiktoken."""
    if tiktoken is None:
        # Fallback: estimate ~4 chars per token
        return len(text) // 4

    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4


def parse_index_entries(index_text: str) -> dict:
    """Parse IATF index into structured dict.

    Expected format:
    # Title {#section-id | lines:start-end | words:count}
      @summary: Summary text
    """
    sections = {}

    # Pattern for index entries
    # Matches: # Title {#id | lines:start-end | words:count}
    pattern = re.compile(
        r"^(#+)\s+(.+?)\s+\{#([a-zA-Z0-9_-]+)\s*\|\s*lines:(\d+)-(\d+)\s*\|\s*words:(\d+)\}",
        re.MULTILINE,
    )

    # Pattern for summaries
    summary_pattern = re.compile(r"^\s+@summary:\s*(.+)$", re.MULTILINE)

    for match in pattern.finditer(index_text):
        level = len(match.group(1))
        title = match.group(2).strip()
        section_id = match.group(3)
        start_line = int(match.group(4))
        end_line = int(match.group(5))
        word_count = int(match.group(6))

        # Look for summary after this line
        match_end = match.end()
        remaining = index_text[match_end : match_end + 500]
        summary_match = summary_pattern.match(remaining)
        summary = summary_match.group(1) if summary_match else ""

        sections[f"#{section_id}"] = {
            "id": section_id,
            "level": level,
            "title": title,
            "start_line": start_line,
            "end_line": end_line,
            "word_count": word_count,
            "summary": summary,
        }

    return sections


def format_index_for_llm(index: dict) -> str:
    """Format index in readable form for LLM reasoning."""
    formatted = []
    for section_id, info in index.items():
        line_info = f"lines {info['start_line']}-{info['end_line']}"
        words = f"{info['word_count']} words"

        entry = f"{section_id} | {info['title']} ({line_info}, {words})"
        if info.get("summary"):
            entry += f"\n  Summary: {info['summary']}"

        formatted.append(entry)

    return "\n\n".join(formatted)


def read_lines(file_path: str, start: int, end: int) -> str:
    """Read specific line range from file (1-indexed)."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        return "".join(lines[start - 1 : end])


class IATFRetriever:
    """Efficient document navigation using IATF format."""

    def __init__(
        self,
        iatf_file_path: str,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.file_path = iatf_file_path
        self.model = model
        self.client = None

        if openai_api_key and OpenAI:
            self.client = OpenAI(api_key=openai_api_key)
        elif OpenAI:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)

        self.index = {}
        self.index_text = ""
        self.metrics = RetrievalMetrics()

        self._load_index()

    def _load_index(self):
        """Load only INDEX section (until ===CONTENT===)."""
        index_lines = []

        with open(self.file_path, "r", encoding="utf-8") as f:
            in_index = False
            for line in f:
                if "===INDEX===" in line:
                    in_index = True
                    continue
                elif "===CONTENT===" in line:
                    break
                elif in_index:
                    index_lines.append(line)

        self.index_text = "".join(index_lines)
        self.index = parse_index_entries(self.index_text)
        self.metrics.index_tokens = count_tokens(self.index_text)
        self.metrics.total_sections = len(self.index)

    def get_index_summary(self) -> str:
        """Get a formatted summary of the index."""
        return format_index_for_llm(self.index)

    def retrieve_relevant_sections(
        self, question: str, max_sections: int = 5
    ) -> list[str]:
        """Use LLM reasoning to select relevant sections."""
        if not self.client:
            # Fallback: keyword matching
            return self._keyword_match_sections(question, max_sections)

        index_text = format_index_for_llm(self.index)

        prompt = f"""You are analyzing a financial document index to answer a question.

Document Index:
{index_text}

Question: {question}

Task: Identify which sections would contain information to answer this question.
Return section IDs in order of relevance (most relevant first).

Rules:
- Only return section IDs that exist in the index (format: #section-id)
- Include parent sections if child sections are relevant
- Aim for 2-{max_sections} sections maximum
- If uncertain, include rather than exclude

Format: Return ONLY a JSON array of section IDs
Example: ["#revenue-q3", "#operating-expenses", "#cash-flow"]"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
            )

            response_text = response.choices[0].message.content
            self.metrics.reasoning_tokens += count_tokens(prompt + response_text)

            # Extract JSON array
            json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if json_match:
                section_ids = json.loads(json_match.group())
                # Validate section IDs exist
                valid_ids = [sid for sid in section_ids if sid in self.index]
                return valid_ids[:max_sections]

            return self._keyword_match_sections(question, max_sections)

        except Exception as e:
            print(f"LLM section selection failed: {e}")
            return self._keyword_match_sections(question, max_sections)

    def _keyword_match_sections(
        self, question: str, max_sections: int = 5
    ) -> list[str]:
        """Fallback keyword-based section selection."""
        keywords = set(question.lower().split())

        # Remove common words
        stopwords = {
            "what",
            "is",
            "the",
            "for",
            "in",
            "of",
            "a",
            "an",
            "to",
            "and",
            "or",
            "was",
            "were",
        }
        keywords -= stopwords

        scored = []
        for section_id, info in self.index.items():
            text = f"{info['title']} {info.get('summary', '')}".lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((section_id, score))

        # Sort by score descending
        scored.sort(key=lambda x: -x[1])

        return [sid for sid, _ in scored[:max_sections]]

    def load_sections(self, section_ids: list[str]) -> str:
        """Load specific sections by line numbers from INDEX."""
        content_parts = []

        for section_id in section_ids:
            if section_id not in self.index:
                continue

            info = self.index[section_id]
            start_line = info["start_line"]
            end_line = info["end_line"]

            # Read specific line range
            section_content = read_lines(self.file_path, start_line, end_line)
            content_parts.append(f"=== {info['title']} ===\n{section_content}")

            self.metrics.sections_retrieved += 1
            self.metrics.content_tokens += count_tokens(section_content)

        return "\n\n".join(content_parts)

    def load_full_content(self) -> str:
        """Load the entire CONTENT section (for baseline comparison)."""
        content_lines = []

        with open(self.file_path, "r", encoding="utf-8") as f:
            in_content = False
            for line in f:
                if "===CONTENT===" in line:
                    in_content = True
                    continue
                elif in_content:
                    content_lines.append(line)

        return "".join(content_lines)

    def answer_question(
        self, question: str, max_sections: int = 5
    ) -> tuple[str, RetrievalMetrics]:
        """Full QA pipeline with metrics tracking."""
        # Reset metrics for this query
        self.metrics = RetrievalMetrics(
            index_tokens=count_tokens(self.index_text), total_sections=len(self.index)
        )

        if not self.client:
            return "Error: OpenAI client not configured", self.metrics

        # Step 1: Index-based section selection
        relevant_sections = self.retrieve_relevant_sections(question, max_sections)

        if not relevant_sections:
            # Fallback: try to load first few sections
            relevant_sections = list(self.index.keys())[:3]

        # Step 2: Load only relevant sections
        context = self.load_sections(relevant_sections)

        if not context.strip():
            return "No relevant sections found in document", self.metrics

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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": answer_prompt}],
                temperature=0,
                max_tokens=500,
            )

            answer = response.choices[0].message.content
            self.metrics.answer_tokens = count_tokens(answer_prompt + answer)

        except Exception as e:
            answer = f"Error generating answer: {e}"
            self.metrics.answer_tokens = 0

        # Calculate totals
        self.metrics.total_tokens = (
            self.metrics.index_tokens
            + self.metrics.reasoning_tokens
            + self.metrics.content_tokens
            + self.metrics.answer_tokens
        )

        if self.metrics.total_sections > 0:
            self.metrics.retrieval_ratio = (
                self.metrics.sections_retrieved / self.metrics.total_sections
            )

        return answer, self.metrics

    def answer_with_full_context(self, question: str) -> tuple[str, int]:
        """Answer using full document content (baseline comparison)."""
        if not self.client:
            return "Error: OpenAI client not configured", 0

        full_content = self.load_full_content()

        # Truncate if too long
        max_chars = 100000
        if len(full_content) > max_chars:
            full_content = full_content[:max_chars] + "\n\n[TRUNCATED...]"

        prompt = f"""Based on the following document, answer the question.

Question: {question}

Document:
{full_content}

Instructions:
- Answer based ONLY on information in the document
- Be precise with numbers, dates, and financial figures
- If the document doesn't contain the answer, say "Information not found"

Answer:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
            )

            answer = response.choices[0].message.content
            total_tokens = count_tokens(prompt + answer)

            return answer, total_tokens

        except Exception as e:
            return f"Error: {e}", 0


def main():
    """Test the retriever on a sample file."""
    import argparse

    parser = argparse.ArgumentParser(description="IATF Retriever")
    parser.add_argument("file", help="IATF file to query")
    parser.add_argument("question", help="Question to answer")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"))
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    retriever = IATFRetriever(args.file, openai_api_key=args.api_key, model=args.model)

    if args.verbose:
        print(f"Loaded {len(retriever.index)} sections")
        print(f"Index tokens: {retriever.metrics.index_tokens}")
        print()

    answer, metrics = retriever.answer_question(args.question)

    print(f"Question: {args.question}")
    print(f"Answer: {answer}")
    print()

    if args.verbose:
        print("Metrics:")
        print(f"  Index tokens: {metrics.index_tokens}")
        print(f"  Reasoning tokens: {metrics.reasoning_tokens}")
        print(f"  Content tokens: {metrics.content_tokens}")
        print(f"  Answer tokens: {metrics.answer_tokens}")
        print(f"  Total tokens: {metrics.total_tokens}")
        print(
            f"  Sections retrieved: {metrics.sections_retrieved}/{metrics.total_sections}"
        )
        print(f"  Retrieval ratio: {metrics.retrieval_ratio:.1%}")


if __name__ == "__main__":
    main()
