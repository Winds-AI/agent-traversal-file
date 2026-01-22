---
name: code-review
description: Review code changes for bugs, logic errors, regressions, and missing tests. Use when the user asks for a code review, review of uncommitted files, or review of specific diffs/files/PR changes. Default to uncommitted changes unless the user specifies another input source.
---

# Code Review

## Overview

Perform a targeted, high-signal review focused on correctness, risk, and gaps.

## Workflow

1. Identify scope.
   - If the user hasn't stated what feature they implemented, ask that first.
   - If the user specifies files/diff/commit/PR, use that scope.
   - Otherwise, use git status + git diff for uncommitted changes.
   - If input is ambiguous, ask a single clarification question and proceed with the safest interpretation.
2. Inspect changes.
   - Read the relevant diffs and any impacted code paths.
   - Use fast search (rg) for symbol usage, related logic, or tests.
3. Evaluate risks.
   - Prioritize correctness, behavior changes, error handling, edge cases, concurrency, and compatibility.
   - Check exit codes, return values, and default paths.
4. Check parity and consistency.
   - If multiple implementations exist (e.g., Go/Python), compare behavior for discrepancies.
5. Testing gaps.
   - Note missing tests or missing manual validation steps.

## Output

Return findings first, ordered by severity. Each finding should include:
- severity (High/Medium/Low)
- file path with line reference if possible
- description of the issue and likely impact
- suggested fix or verification step

After findings, include:
- Open questions or assumptions
- Brief change summary only if needed
- Suggested next steps (tests, validations)
