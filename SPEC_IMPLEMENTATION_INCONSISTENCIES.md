# Specification vs Implementation Inconsistencies

**Analysis Date**: 2026-01-21
**Spec Version**: v1.0
**Implementations Analyzed**: Python (atf.py), Go (main.go)

---

## CRITICAL Issues

### 1. 🚨 Go Implementation Missing `===CONTENT===` Delimiter

**Severity**: CRITICAL - File corruption
**Location**: `go/main.go:463-467`

**Issue**:
The Go implementation fails to write the `===CONTENT===` delimiter when rebuilding the file.

**Evidence**:
```bash
$ grep -n "===" examples/simple.atf
15:===INDEX===
# Missing ===CONTENT=== !
```

**Code Analysis** (go/main.go:463-467):
```go
// Rebuild file
newLines := append(lines[:headerEnd], "")
newLines = append(newLines, newIndex...)
newLines = append(newLines, "")
newLines = append(newLines, lines[indexEnd:]...)
```

**Problem**:
- `lines[indexEnd:]` includes the `===CONTENT===` line (at `indexEnd`)
- But this line gets lost somewhere in the reconstruction
- The `updateContentMetadata()` function modifies `lines` in-place, potentially causing index shifts

**Impact**:
- Files rebuilt with Go are corrupted and cannot be read by Python
- Violates spec requirement (Section 12, Rule #3): "Have exactly one `===CONTENT===` section"

**Fix Required**:
Ensure `===CONTENT===` delimiter is explicitly preserved or re-added during file reconstruction.

---

## High Priority Issues

### 2. AUTO-GENERATED Comment Mismatch

**Severity**: HIGH - Spec/Implementation divergence
**Locations**:
- Spec: SPECIFICATION.md:109, 115, 445, 569
- Python: python/atf.py:221
- Go: go/main.go:321

**Spec Says**:
```
<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->
```

**Implementation Uses**:
```
<!-- AUTO-GENERATED - DO NOT EDIT -->
```

**Impact**: Minor - Documentation inconsistency

**Recommendation**: Update implementations to match spec exactly, OR update spec to match implementation.

---

### 3. Timestamp Format Minor Inconsistency

**Severity**: MEDIUM - Format inconsistency
**Locations**:
- Spec: SPECIFICATION.md:110
- Python: python/atf.py:222
- Go: go/main.go:322

**Spec Shows**:
```
<!-- Generated: 2025-01-19T10:30:00Z -->
```

**Python Implementation**:
```python
f"<!-- Generated: {datetime.now(timezone.utc).isoformat()} -->"
```

**Python Output**:
```
<!-- Generated: 2026-01-21T18:39:41.546302+00:00 -->
```
**Problem**: Uses `+00:00` instead of `Z`, includes microseconds

**Go Implementation**:
```go
fmt.Sprintf("<!-- Generated: %s -->", time.Now().UTC().Format(time.RFC3339))
```

**Go Output**:
```
<!-- Generated: 2026-01-21T19:01:35Z -->
```
**Status**: ✅ Go matches spec format

**Impact**:
- Python timestamps are longer and use different timezone notation
- Both are valid ISO 8601, but inconsistent with spec example

**Recommendation**:
Update Python to match Go:
```python
f"<!-- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} -->"
```

---

## Low Priority Issues

### 4. Optional `words:count` Not Implemented

**Severity**: LOW - Optional feature
**Locations**:
- Spec: SPECIFICATION.md:124, 146
- Python: python/atf.py:generate_index()
- Go: go/main.go:generateIndex()

**Spec Says** (Section 3.2):
```
[level-marker] Title {#id | lines:start-end | words:count}
   - `words:count` (Optional): Word count of section
```

**Implementation Outputs**:
```
# How It Works {#intro | lines:35-56}
```

**Status**:
- Spec marks `words:` as **optional**, so omission is spec-compliant
- However, spec examples all show it included

**Impact**: None - Optional feature

**Recommendation**:
Either:
1. Implement word counting (low priority)
2. Update spec examples to omit `words:` consistently

---

## Confirmed Correct Implementations

### ✅ Maximum Nesting Depth Enforcement

**Spec** (Section 3.3, line 169):
> "Implementations may enforce a maximum nesting depth (this project enforces 2 levels)"

**Python Implementation** (atf.py:685-687):
```python
if section.level > 2:
    errors.append(
        f"Section nesting exceeds 2 levels: {section.id}"
    )
```

**Go Implementation** (main.go:868-869):
```go
if section.Level > 2 {
    errors = append(errors, fmt.Sprintf("Section nesting exceeds 2 levels: %s", section.ID))
}
```

**Status**: ✅ Both implementations correctly enforce 2-level maximum

---

### ✅ @hash Automatic Tracking

**Spec** (Section 4.2, lines 226-257): Fully documented

**Implementation**: Both Python and Go correctly implement:
- Parse `@hash:` annotation
- Compute Git-style 7-character SHA256 hash
- Auto-update `@modified` when content changes
- Write `@hash` back to CONTENT section

**Status**: ✅ Fully aligned with spec

---

### ✅ Validation Rules

**Spec** (Section 12): Lists 9 validation rules

**Python & Go**: Both implement comprehensive validation including:
- Format declaration check
- Single INDEX/CONTENT section check
- INDEX before CONTENT order check
- Unique section IDs
- Proper nesting
- Content hash verification

**Status**: ✅ All required validation rules implemented

---

## Summary

| Issue | Severity | Python | Go | Action Required |
|-------|----------|--------|-----|-----------------|
| Missing `===CONTENT===` delimiter | 🚨 CRITICAL | ✅ | ❌ | Fix Go immediately |
| AUTO-GENERATED comment text | HIGH | ❌ | ❌ | Update both or spec |
| Timestamp format | MEDIUM | ❌ | ✅ | Update Python |
| Optional `words:` field | LOW | N/A | N/A | Optional enhancement |
| Max nesting enforcement | - | ✅ | ✅ | None |
| @hash tracking | - | ✅ | ✅ | None |
| Validation rules | - | ✅ | ✅ | None |

---

## Immediate Actions Required

1. **URGENT**: Fix Go `===CONTENT===` bug before any further testing
2. Update implementations to use exact AUTO-GENERATED comment from spec
3. Align Python timestamp format with Go (and spec)
4. Decide on `words:count` - implement or remove from spec examples

---

## Testing Recommendations

1. After fixing Go bug, run both implementations on same files
2. Verify byte-for-byte identical output (except timestamps)
3. Test round-trip: Python → Go → Python → Go
4. Add regression tests for `===CONTENT===` preservation
