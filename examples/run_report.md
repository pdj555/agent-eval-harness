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
| latency p50 | 0.49s |
| latency p90 | 0.60s |
| reliability | 100.0% |
| mean steps | 4.0 |

| task | solved | latency | cost | detail |
|---|---|---|---|---|
| fizzbuzz-plus | yes | 0.45s | $20.4000 | 5 passed in 0.01s |
| fix-binary-search | yes | 0.48s | $20.4000 | 9 passed in 0.02s |
| retry-backoff | yes | 0.48s | $20.4000 | 4 passed in 0.01s |
| lru-cache | yes | 0.54s | $20.4000 | 5 passed in 0.02s |
| csv-summary | yes | 0.47s | $20.4000 | 2 passed in 0.02s |
| balanced-parens | yes | 0.49s | $20.4000 | 6 passed in 0.02s |
| fizzbuzz-plus | yes | 0.56s | $20.4000 | 5 passed in 0.01s |
| fix-binary-search | yes | 0.47s | $20.4000 | 9 passed in 0.02s |
| retry-backoff | yes | 0.48s | $20.4000 | 4 passed in 0.01s |
| lru-cache | yes | 0.50s | $20.4000 | 5 passed in 0.02s |
| csv-summary | yes | 0.69s | $20.4000 | 2 passed in 0.02s |
| balanced-parens | yes | 0.60s | $20.4000 | 6 passed in 0.01s |

# Eval report: steady (baseline)

| metric | value |
|---|---|
| tasks | 6 |
| runs | 12 |
| solve rate | 66.7% |
| pass@2 | 66.7% |
| mean cost / task | $42.0000 |
| cost per solve | $63.0000 |
| latency p50 | 0.64s |
| latency p90 | 1.62s |
| reliability | 66.7% |
| mean steps | 4.0 |

| task | solved | latency | cost | detail |
|---|---|---|---|---|
| fizzbuzz-plus | yes | 0.63s | $42.0000 | 5 passed in 0.01s |
| fix-binary-search | yes | 0.79s | $42.0000 | 9 passed in 0.04s |
| retry-backoff | no | 0.75s | $42.0000 | 2 failed, 2 passed in 0.04s |
| lru-cache | yes | 1.83s | $42.0000 | 5 passed in 0.03s |
| csv-summary | yes | 1.62s | $42.0000 | 2 passed in 0.02s |
| balanced-parens | no | 0.79s | $42.0000 | 3 failed, 3 passed in 0.04s |
| fizzbuzz-plus | yes | 0.64s | $42.0000 | 5 passed in 0.02s |
| fix-binary-search | yes | 0.59s | $42.0000 | 9 passed in 0.02s |
| retry-backoff | no | 0.58s | $42.0000 | 2 failed, 2 passed in 0.03s |
| lru-cache | yes | 0.61s | $42.0000 | 5 passed in 0.02s |
| csv-summary | yes | 0.53s | $42.0000 | 2 passed in 0.01s |
| balanced-parens | no | 0.59s | $42.0000 | 3 failed, 3 passed in 0.03s |

# Eval report: weak (baseline)

| metric | value |
|---|---|
| tasks | 6 |
| runs | 12 |
| solve rate | 16.7% |
| pass@2 | 16.7% |
| mean cost / task | $84.0000 |
| cost per solve | $504.0000 |
| latency p50 | 0.82s |
| latency p90 | 1.01s |
| reliability | 16.7% |
| mean steps | 4.0 |

| task | solved | latency | cost | detail |
|---|---|---|---|---|
| fizzbuzz-plus | yes | 0.68s | $84.0000 | 5 passed in 0.01s |
| fix-binary-search | no | 0.84s | $84.0000 | 1 error in 0.13s |
| retry-backoff | no | 0.76s | $84.0000 | 2 failed, 2 passed in 0.03s |
| lru-cache | no | 0.80s | $84.0000 | 1 error in 0.11s |
| csv-summary | no | 0.78s | $84.0000 | 1 error in 0.10s |
| balanced-parens | no | 1.09s | $84.0000 | 3 failed, 3 passed in 0.16s |
| fizzbuzz-plus | yes | 0.71s | $84.0000 | 5 passed in 0.01s |
| fix-binary-search | no | 0.86s | $84.0000 | 1 error in 0.14s |
| retry-backoff | no | 0.71s | $84.0000 | 2 failed, 2 passed in 0.03s |
| lru-cache | no | 0.83s | $84.0000 | 1 error in 0.11s |
| csv-summary | no | 1.01s | $84.0000 | 1 error in 0.13s |
| balanced-parens | no | 0.82s | $84.0000 | 3 failed, 3 passed in 0.05s |

# Ablation comparison

| variant | solve rate | cost/solve | p50 latency | reliability |
|---|---|---|---|---|
| baseline | 66.7% | $63.0000 | 0.64s | 66.7% |
| cot | 83.3% | $99.0000 | 0.79s | 83.3% |

Winner by solve rate: **cot**

