# Ablation: vector vs bm25 vs hybrid

_Generated 2026-05-03T17:02:23+00:00_

## Setup

- **Embedder:** `BAAI/bge-small-en-v1.5`
- **Chunker:** AST (tree-sitter), MAX_CLASS_LINES=100
- **Chunks indexed:** 342
- **Questions:** 30
- **k:** 5

## Recall@5 by mode and category

| Mode | overall | where_defined | how_works | what_calls |
|---|---|---|---|---|
| **vector** | 0.867 | 1.000 | 0.900 | 0.700 |
| **bm25** | 0.667 | 0.500 | 0.800 | 0.700 |
| **hybrid** | 0.900 | 0.900 | 1.000 | 0.800 |

## Latency (ms per query)

| Mode | p50 | p95 | max |
|---|---|---|---|
| vector | 0.04 | 0.06 | 0.25 |
| bm25 | 1.21 | 1.76 | 2.29 |
| hybrid | 0.88 | 1.54 | 1.56 |

## Per-question hits

| Q | category | vector | bm25 | hybrid |
|---|---|---|---|---|
| Q01 | where_defined | OK | miss | OK |
| Q02 | where_defined | OK | miss | OK |
| Q03 | where_defined | OK | OK | OK |
| Q04 | where_defined | OK | OK | OK |
| Q05 | where_defined | OK | OK | OK |
| Q06 | where_defined | OK | miss | OK |
| Q07 | where_defined | OK | OK | OK |
| Q08 | where_defined | OK | miss | OK |
| Q09 | where_defined | OK | miss | miss |
| Q10 | where_defined | OK | OK | OK |
| Q11 | how_works | miss | OK | OK |
| Q12 | how_works | OK | OK | OK |
| Q13 | how_works | OK | OK | OK |
| Q14 | how_works | OK | miss | OK |
| Q15 | how_works | OK | OK | OK |
| Q16 | how_works | OK | OK | OK |
| Q17 | how_works | OK | miss | OK |
| Q18 | how_works | OK | OK | OK |
| Q19 | how_works | OK | OK | OK |
| Q20 | how_works | OK | OK | OK |
| Q21 | what_calls | OK | miss | OK |
| Q22 | what_calls | OK | miss | OK |
| Q23 | what_calls | OK | OK | OK |
| Q24 | what_calls | OK | OK | OK |
| Q25 | what_calls | miss | OK | OK |
| Q26 | what_calls | miss | miss | miss |
| Q27 | what_calls | OK | OK | OK |
| Q28 | what_calls | miss | OK | miss |
| Q29 | what_calls | OK | OK | OK |
| Q30 | what_calls | OK | OK | OK |

## Diagnostics

- Questions hybrid retrieves that NEITHER single mode does: 0  (`none`)
- Questions all 3 modes miss (chunker / dataset issues): 1  (`Q26`)

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
    "vector": true,
    "bm25": false,
    "hybrid": true
  },
  {
    "id": "Q02",
    "category": "where_defined",
    "vector": true,
    "bm25": false,
    "hybrid": true
  },
  {
    "id": "Q03",
    "category": "where_defined",
    "vector": true,
    "bm25": true,
    "hybrid": true
  },
  {
    "id": "Q04",
    "category": "where_defined",
    "vector": true,
    "bm25": true,
    "hybrid": true
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
    "vector": true,
    "bm25": false,
    "hybrid": true
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
    "bm25": true,
    "hybrid": true
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
    "bm25": false,
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
    "bm25": false,
    "hybrid": true
  },
  {
    "id": "Q22",
    "category": "what_calls",
    "vector": true,
    "bm25": false,
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
    "bm25": true,
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
