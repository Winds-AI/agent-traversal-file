Approach:
- Used only IATF retrieval commands against `document.iatf`: `iatf index`, batched `iatf find`, and targeted `iatf read-many`.
- Did not access `questions.yaml` (gold answers).
- Mapped each question to relevant section IDs, then synthesized concise answers from retrieved requirements and state/workflow definitions.
- Prioritized shared/global sections first, then read only modules needed for multihop workflow questions.
