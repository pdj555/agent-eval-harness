# agent-eval-harness: worked example

# Eval report: golden (baseline)

| metric | value |
|---|---|
| tasks | 6 |
| runs | 12 |
| solve rate | 100.0% |
| pass@2 | 100.0% |
| mean cost / task | $20.4000 |
| cost per solve | $20.4000 |
| latency p50 | 0.34s |
| latency p90 | 0.35s |
| reliability | 100.0% |
| mean steps | 4.0 |

| task | solved | latency | cost | detail |
|---|---|---|---|---|
| fizzbuzz-plus | yes | 0.35s | $20.4000 | 5 passed in 0.01s |
| fix-binary-search | yes | 0.34s | $20.4000 | 9 passed in 0.02s |
| retry-backoff | yes | 0.32s | $20.4000 | 4 passed in 0.01s |
| lru-cache | yes | 0.34s | $20.4000 | 5 passed in 0.02s |
| csv-summary | yes | 0.34s | $20.4000 | 2 passed in 0.01s |
| balanced-parens | yes | 0.32s | $20.4000 | 6 passed in 0.01s |
| fizzbuzz-plus | yes | 0.32s | $20.4000 | 5 passed in 0.01s |
| fix-binary-search | yes | 0.33s | $20.4000 | 9 passed in 0.02s |
| retry-backoff | yes | 0.34s | $20.4000 | 4 passed in 0.01s |
| lru-cache | yes | 0.35s | $20.4000 | 5 passed in 0.02s |
| csv-summary | yes | 0.34s | $20.4000 | 2 passed in 0.01s |
| balanced-parens | yes | 0.33s | $20.4000 | 6 passed in 0.01s |

# Eval report: steady (baseline)

| metric | value |
|---|---|
| tasks | 6 |
| runs | 12 |
| solve rate | 66.7% |
| pass@2 | 66.7% |
| mean cost / task | $42.0000 |
| cost per solve | $63.0000 |
| latency p50 | 0.44s |
| latency p90 | 0.46s |
| reliability | 66.7% |
| mean steps | 4.0 |

| task | solved | latency | cost | detail |
|---|---|---|---|---|
| fizzbuzz-plus | yes | 0.43s | $42.0000 | 5 passed in 0.01s |
| fix-binary-search | yes | 0.46s | $42.0000 | 9 passed in 0.02s |
| retry-backoff | no | 0.46s | $42.0000 | 2 failed, 2 passed in 0.03s |
| lru-cache | yes | 0.43s | $42.0000 | 5 passed in 0.02s |
| csv-summary | yes | 0.44s | $42.0000 | 2 passed in 0.02s |
| balanced-parens | no | 0.44s | $42.0000 | 3 failed, 3 passed in 0.03s |
| fizzbuzz-plus | yes | 0.45s | $42.0000 | 5 passed in 0.01s |
| fix-binary-search | yes | 0.43s | $42.0000 | 9 passed in 0.02s |
| retry-backoff | no | 0.44s | $42.0000 | 2 failed, 2 passed in 0.03s |
| lru-cache | yes | 0.44s | $42.0000 | 5 passed in 0.02s |
| csv-summary | yes | 0.42s | $42.0000 | 2 passed in 0.01s |
| balanced-parens | no | 0.43s | $42.0000 | 3 failed, 3 passed in 0.03s |

# Eval report: weak (baseline)

| metric | value |
|---|---|
| tasks | 6 |
| runs | 12 |
| solve rate | 16.7% |
| pass@2 | 16.7% |
| mean cost / task | $84.0000 |
| cost per solve | $504.0000 |
| latency p50 | 0.66s |
| latency p90 | 0.69s |
| reliability | 16.7% |
| mean steps | 4.0 |

| task | solved | latency | cost | detail |
|---|---|---|---|---|
| fizzbuzz-plus | yes | 0.57s | $84.0000 | 5 passed in 0.01s |
| fix-binary-search | no | 0.69s | $84.0000 | 1 error in 0.12s |
| retry-backoff | no | 0.58s | $84.0000 | 2 failed, 2 passed in 0.03s |
| lru-cache | no | 0.73s | $84.0000 | 1 error in 0.12s |
| csv-summary | no | 0.66s | $84.0000 | 1 error in 0.10s |
| balanced-parens | no | 0.58s | $84.0000 | 3 failed, 3 passed in 0.03s |
| fizzbuzz-plus | yes | 0.57s | $84.0000 | 5 passed in 0.01s |
| fix-binary-search | no | 0.67s | $84.0000 | 1 error in 0.11s |
| retry-backoff | no | 0.59s | $84.0000 | 2 failed, 2 passed in 0.03s |
| lru-cache | no | 0.69s | $84.0000 | 1 error in 0.11s |
| csv-summary | no | 0.67s | $84.0000 | 1 error in 0.10s |
| balanced-parens | no | 0.60s | $84.0000 | 3 failed, 3 passed in 0.03s |

# Ablation comparison

| variant | solve rate | cost/solve | p50 latency | reliability |
|---|---|---|---|---|
| baseline | 66.7% | $63.0000 | 0.43s | 66.7% |
| cot | 83.3% | $99.0000 | 0.51s | 83.3% |

Winner by solve rate: **cot**

