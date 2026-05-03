# Eval report (hybrid)

_Generated 2026-05-03T17:02:23+00:00_

## Configuration

- **Mode:** `hybrid` (headline)
- **Embedder:** `BAAI/bge-small-en-v1.5`
- **Chunker:** AST (tree-sitter), MAX_CLASS_LINES=100
- **Chunks indexed:** 342
- **Questions:** 30
- **k:** 5

See `ABLATION.md` for the comparison across vector / bm25 / hybrid.

## Results

| Slice | recall@5 | hits / total |
|---|---|---|
| **Overall** | **0.900** | 27/30 |
| where_defined | 0.900 | 9/10 |
| how_works | 1.000 | 10/10 |
| what_calls | 0.800 | 8/10 |

## Retrieval latency

- p50: 0.88 ms
- p95: 1.54 ms
- max: 1.56 ms

## Sample misses (first 3 of 3)

### Q09 [where_defined]
_Where is the url_for function defined?_

Ground truth:
- `src/flask/helpers.py:200-253`

Top-5 retrieved (none overlapped):
- 0.031  `src/flask/sansio/scaffold.py:558-581`  method `url_value_preprocessor` (Scaffold)
- 0.030  `src/flask/app.py:1102-1222`  method `url_for` (Flask)
- 0.029  `src/flask/sansio/scaffold.py:583-595`  method `url_defaults` (Scaffold)
- 0.029  `src/flask/sansio/app.py:604-661`  method `add_url_rule` (App)
- 0.028  `src/flask/sansio/scaffold.py:367-433`  method `add_url_rule` (Scaffold)

### Q26 [what_calls]
_What handles exceptions raised by view functions?_

Ground truth:
- `src/flask/app.py:992-1019`
- `src/flask/app.py:1566-1617`

Top-5 retrieved (none overlapped):
- 0.031  `src/flask/app.py:830-863`  method `handle_http_exception` (Flask)
- 0.030  `src/flask/app.py:897-948`  method `handle_exception` (Flask)
- 0.029  `src/flask/views.py:85-135`  method `as_view` (View)
- 0.028  `src/flask/views.py:16-77`  class `View`
- 0.028  `src/flask/sansio/scaffold.py:597-639`  method `errorhandler` (Scaffold)

### Q28 [what_calls]
_What invokes teardown_request handlers when a request completes?_

Ground truth:
- `src/flask/app.py:1566-1617`
- `src/flask/ctx.py:260-540`

Top-5 retrieved (none overlapped):
- 0.033  `src/flask/sansio/scaffold.py:507-539`  method `teardown_request` (Scaffold)
- 0.032  `src/flask/app.py:1420-1451`  method `do_teardown_request` (Flask)
- 0.031  `src/flask/app.py:992-1019`  method `full_dispatch_request` (Flask)
- 0.031  `src/flask/sansio/blueprints.py:633-641`  method `teardown_app_request` (Blueprint)
- 0.031  `src/flask/sansio/app.py:826-855`  method `teardown_appcontext` (App)
