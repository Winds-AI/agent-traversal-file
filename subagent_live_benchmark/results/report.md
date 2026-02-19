# Sub-Agent IATF Efficiency Benchmark

- Tokenizer model: `gpt-5`
- Question count: `18`

## Results

| Approach | Tool Calls | Retrieval Calls | Cmd Tokens | Output Tokens | Tool I/O Tokens | Retrieval I/O Tokens | Answer Tokens | Exact Match (all must_include) | Mean must_include Recall | Violations |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| iatf_primed | 9 | 8 | 590 | 22984 | 23574 | 22044 | 1200 | 5/18 | 0.571 | none |
| shell_guided | 11 | 8 | 242 | 22862 | 23104 | 21145 | 1159 | 3/18 | 0.596 | none |
| shell_unguided | 11 | 9 | 285 | 20670 | 20955 | 19411 | 1157 | 1/18 | 0.534 | none |

## Efficiency

| Approach | Tool I/O Tokens per Exact-Match Question | Retrieval I/O Tokens per Exact-Match Question |
|---|---:|---:|
| iatf_primed | 4714.80 | 4408.80 |
| shell_guided | 7701.33 | 7048.33 |
| shell_unguided | 20955.00 | 19411.00 |
