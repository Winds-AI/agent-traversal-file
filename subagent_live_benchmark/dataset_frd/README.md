# FRD Benchmark Dataset Metadata

## Chosen Domain
ProcureSphere Cloud: enterprise procurement and accounts payable (source-to-pay) SaaS for multi-entity organizations.

## Files
- `document.txt`: plain-text FRD dataset for retrieval benchmarking.
- `document.iatf`: same FRD represented as IATF `CONTENT` sections with indexed IDs/summaries.

## Rough Scale
- Plain-text line count (`document.txt`): ~1990 lines.
- IATF line count (`document.iatf`): ~2130 lines (includes IATF metadata and generated index).
- Total section count (IATF `CONTENT`): ~67 sections.

## Section Distribution (Approximate)
- Foundation and governance sections: ~24.
- Module functional sections: ~20.
- Cross-cutting catalogs and edge cases: ~4.
- NFR sections: ~7.
- Rollout, migration, support, testing, acceptance, and operations: ~12.

## Coverage Included
- Modules and page layouts.
- Form fields and validation rules.
- Workflow/state behavior and role/permission model.
- Edge cases, notifications, and report catalog.
- Integration packages and operational safeguards.
- Non-functional requirements.
- Rollout, migration, hypercare, and support ops.
