# Ablation: vector vs bm25 vs hybrid

_Generated 2026-05-03T16:54:42+00:00_

## Setup

- **Embedder:** `BAAI/bge-small-en-v1.5`
- **Chunker:** AST (tree-sitter), MAX_CLASS_LINES=100
- **Chunks indexed:** 304
- **Questions:** 30
- **k:** 5

## Recall@5 by mode and category

| Mode | overall | where_defined | how_works | what_calls |
|---|---|---|---|---|
| **vector** | 0.700 | 0.500 | 0.900 | 0.700 |
| **bm25** | 0.633 | 0.300 | 0.800 | 0.800 |
| **hybrid** | 0.700 | 0.400 | 0.900 | 0.800 |

## Latency (ms per query)

| Mode | p50 | p95 | max |
|---|---|---|---|
| vector | 0.04 | 0.07 | 0.23 |
| bm25 | 1.06 | 1.86 | 2.08 |
| hybrid | 0.74 | 1.42 | 1.58 |

## Per-question hits

| Q | category | vector | bm25 | hybrid |
|---|---|---|---|---|
| Q01 | where_defined | miss | miss | miss |
| Q02 | where_defined | miss | miss | miss |
| Q03 | where_defined | miss | miss | miss |
| Q04 | where_defined | miss | miss | miss |
| Q05 | where_defined | OK | OK | OK |
| Q06 | where_defined | miss | miss | miss |
| Q07 | where_defined | OK | OK | OK |
| Q08 | where_defined | OK | miss | OK |
| Q09 | where_defined | OK | miss | miss |
| Q10 | where_defined | OK | OK | OK |
| Q11 | how_works | miss | OK | OK |
| Q12 | how_works | OK | miss | miss |
| Q13 | how_works | OK | OK | OK |
| Q14 | how_works | OK | OK | OK |
| Q15 | how_works | OK | OK | OK |
| Q16 | how_works | OK | OK | OK |
| Q17 | how_works | OK | miss | OK |
| Q18 | how_works | OK | OK | OK |
| Q19 | how_works | OK | OK | OK |
| Q20 | how_works | OK | OK | OK |
| Q21 | what_calls | OK | OK | OK |
| Q22 | what_calls | OK | OK | OK |
| Q23 | what_calls | OK | OK | OK |
| Q24 | what_calls | OK | OK | OK |
| Q25 | what_calls | miss | OK | OK |
| Q26 | what_calls | miss | miss | miss |
| Q27 | what_calls | OK | OK | OK |
| Q28 | what_calls | miss | miss | miss |
| Q29 | what_calls | OK | OK | OK |
| Q30 | what_calls | OK | OK | OK |

## Diagnostics

- Questions hybrid retrieves that NEITHER single mode does: 0  (`none`)
- Questions all 3 modes miss (chunker / dataset issues): 7  (`Q01, Q02, Q03, Q04, Q06, Q26, Q28`)

## Notes

- Vector is bge-small-en-v1.5 cosine over L2-normalized embeddings.
- BM25 uses code-aware tokenization (camelCase + snake_case split, lowercased).
- Hybrid uses Reciprocal Rank Fusion (c=60, fetch_k=20 per retriever).

## Raw results (JSON)

<details><summary>per-question per-mode</summary>

```json
[
  {
    "id": "Q01",
    "category": "where_defined",
    "vector": false,
    "bm25": false,
    "hybrid": false
  },
  {
    "id": "Q02",
    "category": "where_defined",
    "vector": false,
    "bm25": false,
    "hybrid": false
  },
  {
    "id": "Q03",
    "category": "where_defined",
    "vector": false,
    "bm25": false,
    "hybrid": false
  },
  {
    "id": "Q04",
    "category": "where_defined",
    "vector": false,
    "bm25": false,
    "hybrid": false
  },
  {
    "id": "Q05",
    "category": "where_defined",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q06",
    "category": "where_defined",
    "vector": false,
    "bm25": false,
    "hybrid": false
  },
  {
    "id": "Q07",
    "category": "where_defined",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q08",
    "category": "where_defined",
    "vector": true,
    "bm25": false,
    "hybrid": true
  },
  {
    "id": "Q09",
    "category": "where_defined",
    "vector": true,
    "bm25": false,
    "hybrid": false
  },
  {
    "id": "Q10",
    "category": "where_defined",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q11",
    "category": "how_works",
    "vector": false,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q12",
    "category": "how_works",
    "vector": true,
    "bm25": false,
    "hybrid": false
  },
  {
    "id": "Q13",
    "category": "how_works",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q14",
    "category": "how_works",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q15",
    "category": "how_works",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q16",
    "category": "how_works",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q17",
    "category": "how_works",
    "vector": true,
    "bm25": false,
    "hybrid": true
  },
  {
    "id": "Q18",
    "category": "how_works",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q19",
    "category": "how_works",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q20",
    "category": "how_works",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q21",
    "category": "what_calls",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q22",
    "category": "what_calls",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q23",
    "category": "what_calls",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q24",
    "category": "what_calls",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q25",
    "category": "what_calls",
    "vector": false,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q26",
    "category": "what_calls",
    "vector": false,
    "bm25": false,
    "hybrid": false
  },
  {
    "id": "Q27",
    "category": "what_calls",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q28",
    "category": "what_calls",
    "vector": false,
    "bm25": false,
    "hybrid": false
  },
  {
    "id": "Q29",
    "category": "what_calls",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q30",
    "category": "what_calls",
    "vector": true,
    "bm25": true,
    "hybrid": true
  }
]
```

</details>
