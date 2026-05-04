# Evals

Hand-curated 30-question evaluation set for the code-rag pipeline, targeting `pallets/flask`.

## Why this matters

Without evals, every change to the chunker, embedder, or retriever is a guess. With evals, "we tried X and recall@5 went from 0.62 to 0.81" is a defensible claim. This directory is what turns code-rag from "yet another RAG demo" into "a measured RAG system."

## Files

- **`dataset.json`** — the 30 questions. Schema in `src/code_rag/evals/types.py`.
- `../src/code_rag/evals/types.py` — `EvalQuestion`, `GroundTruthSpan`, `load_dataset`.
- `../src/code_rag/evals/verify.py` — sanity check: file paths exist, line ranges in bounds, keywords present.
- `../tests/test_evals.py` — schema and counting tests (`pytest -v`).

## Categories (10 each)

| Category | What it tests | Example |
|---|---|---|
| `where_defined` | Symbol lookup. Can the retriever find a class or function by name? | "Where is the Flask class defined?" |
| `how_works` | Conceptual / mechanism questions. Tests semantic understanding, not keyword match. | "How does the current_app proxy resolve to the actual Flask app?" |
| `what_calls` | Call-graph questions. Tests whether the retriever surfaces the *caller* not just the callee. | "What invokes the before_request handlers?" |

Categories are deliberately distinct so we can report per-category recall and see which question types the pipeline handles well vs. badly. Real users ask all three kinds; a system that aces `where_defined` but bombs `what_calls` is half-built.

## Schema

```jsonc
{
  "id": "Q01",
  "category": "where_defined",
  "question": "Where is the Flask class defined?",
  "ground_truth": [
    {
      "file_path": "src/flask/app.py",
      "start_line": 109,
      "end_line": 150,
      "rationale": "class Flask(App): is at line 109; the docstring and class-level definitions span the next ~40 lines."
    }
  ],
  "expected_keywords": ["class Flask", "App"],
  "confidence": "high",
  "notes": ""
}
```

`confidence: "medium"` flags questions where the canonical answer is debatable or spans multiple files. The verifier accepts these but they should be reviewed before publishing benchmark numbers.

## Recall metric

A retrieved chunk is a **hit** if its `[start_line, end_line]` range overlaps any ground-truth span on the same `file_path`. Since the chunker emits per-method chunks for big classes, this overlap rule lets retrieval find Flask's methods without needing the (no-longer-emitted) Flask class chunk.

```
recall@k = #questions where any of top-k retrieved chunks hit a ground-truth span
           ----------------------------------------------------------------------
                                  total questions
```

For week 1 we report `recall@5`. Later: MRR (mean reciprocal rank) and faithfulness (LLM-as-judge on whether the generated answer is grounded in the retrieved chunks).

## Running the verifier

```bash
.venv/Scripts/python -m code_rag.evals.verify
```

Should print "OK - all structural checks passed." If a `file_path` was renamed in flask main, the verifier flags it and you update the dataset.

## Extending

To add a question:

1. Read the relevant flask source. Don't guess — open the file, copy the line numbers.
2. Append to `dataset.json` with the next sequential ID.
3. Add `expected_keywords` that should appear in a correct answer body (used by the verifier as a soft check, and later by the LLM-as-judge faithfulness scorer).
4. Set `confidence: "medium"` if the canonical answer is debatable.
5. Run `python -m code_rag.evals.verify` to confirm.
6. Run `pytest tests/test_evals.py -v` to confirm schema tests still pass.

## Versioning

The `version` field in `dataset.json` follows semver. Bump minor when adding questions; bump major when restructuring the schema or changing the recall metric.
