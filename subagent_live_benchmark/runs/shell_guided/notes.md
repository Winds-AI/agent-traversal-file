# Retrieval Notes

- Source files used: `subagent_live_benchmark/dataset_frd/questions_only.yaml`, `subagent_live_benchmark/dataset_frd/document.txt`
- Forbidden file `questions.yaml` was not opened.
- Retrieval method: section discovery with `rg -n '^#'`, then focused `sed -n` slices.

## Evidence Map

- `q01`: Sections 8, 9 (`REQ-PERM-006`, `REQ-PERM-007`)
- `q02`: Section 13 (global form standards: idempotency/date/currency)
- `q03`: Section 39 (S1/S2 SLA and communication cadence)
- `q04`: Section 35 (RTO, RPO, backup + DR drill cadence)
- `q05`: Module Integration Hub (primary object, states, connector dependencies)
- `q06`: Section 37 (R1-R4 rollout + governance cadence)
- `q07`: Sections 8, 9 (`R4`, `R5`, `REQ-PERM-004`)
- `q08`: Sections 10 + Requisition/Approval/Budget modules
- `q09`: Sections 10 + Invoice Intake + Matching module + edge case EC-003
- `q10`: Section 22 + Integration Hub module + Notification Catalog `N-010` + Support console rules
- `q11`: Sections 37, 45, and KPI ownership in section 4
- `q12`: Sections 9, 17, 18, 27 + Analytics/Compliance modules
- `q13`: Sections 20 + 26 (channels, digest, retries, final failure)
- `q14`: Section 28 (I-001 through I-006)
- `q15`: Section 29 (NFR-PERF-001 through NFR-PERF-006)
- `q16`: Section 36 (M1-M5 + data quality/reconciliation controls)
- `q17`: Section 44 (`GL-002`, `GL-003`, `GL-004`, `GL-006`, `GL-007`)
- `q18`: Sections 38 and 39 (tiers, intake, case data, severity cadence)
