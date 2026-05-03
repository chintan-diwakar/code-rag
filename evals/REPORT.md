# Eval report (hybrid)

_Generated 2026-05-03T16:54:42+00:00_

## Configuration

- **Mode:** `hybrid` (headline)
- **Embedder:** `BAAI/bge-small-en-v1.5`
- **Chunker:** AST (tree-sitter), MAX_CLASS_LINES=100
- **Chunks indexed:** 304
- **Questions:** 30
- **k:** 5

See `ABLATION.md` for the comparison across vector / bm25 / hybrid.

## Results

| Slice | recall@5 | hits / total |
|---|---|---|
| **Overall** | **0.700** | 21/30 |
| where_defined | 0.400 | 4/10 |
| how_works | 0.900 | 9/10 |
| what_calls | 0.800 | 8/10 |

## Retrieval latency

- p50: 0.74 ms
- p95: 1.42 ms
- max: 1.58 ms

## Sample misses (first 5 of 9)

### Q01 [where_defined]
_Where is the Flask class defined?_

Ground truth:
- `src/flask/app.py:109-150`

Top-5 retrieved (none overlapped):
- 0.030  `src/flask/testing.py:27-94`  class `EnvironBuilder`
- 0.030  `src/flask/testing.py:265-298`  class `FlaskCliRunner`
- 0.030  `src/flask/sansio/blueprints.py:34-116`  class `BlueprintSetupState`
- 0.029  `src/flask/views.py:85-135`  method `as_view` (View)
- 0.029  `src/flask/views.py:138-191`  class `MethodView`

### Q02 [where_defined]
_Where is the Blueprint class defined?_

Ground truth:
- `src/flask/blueprints.py:18-50`

Top-5 retrieved (none overlapped):
- 0.033  `src/flask/sansio/blueprints.py:34-116`  class `BlueprintSetupState`
- 0.031  `src/flask/sansio/app.py:569-595`  method `register_blueprint` (App)
- 0.031  `src/flask/sansio/blueprints.py:255-271`  method `register_blueprint` (Blueprint)
- 0.030  `src/flask/sansio/blueprints.py:273-377`  method `register` (Blueprint)
- 0.029  `src/flask/wrappers.py:161-178`  method `blueprint` (Request)

### Q03 [where_defined]
_Where is the current_app proxy defined?_

Ground truth:
- `src/flask/globals.py:40-49`

Top-5 retrieved (none overlapped):
- 0.031  `src/flask/templating.py:21-33`  function `_default_template_ctx_processor`
- 0.031  `src/flask/app.py:1517-1564`  method `test_request_context` (Flask)
- 0.028  `src/flask/json/__init__.py:77-105`  function `loads`
- 0.016  `src/flask/ctx.py:235-257`  function `has_app_context`
- 0.016  `src/flask/app.py:414-445`  method `open_resource` (Flask)

### Q04 [where_defined]
_Where is the request global proxy defined?_

Ground truth:
- `src/flask/globals.py:57-59`

Top-5 retrieved (none overlapped):
- 0.030  `src/flask/templating.py:21-33`  function `_default_template_ctx_processor`
- 0.030  `src/flask/ctx.py:300-337`  method `__init__` (AppContext)
- 0.029  `src/flask/app.py:1517-1564`  method `test_request_context` (Flask)
- 0.028  `src/flask/app.py:509-560`  method `create_url_adapter` (Flask)
- 0.016  `src/flask/sessions.py:24-54`  class `SessionMixin`

### Q06 [where_defined]
_Where is the Flask Config class defined?_

Ground truth:
- `src/flask/config.py:50-100`

Top-5 retrieved (none overlapped):
- 0.032  `src/flask/sansio/app.py:479-493`  method `make_config` (App)
- 0.032  `src/flask/testing.py:27-94`  class `EnvironBuilder`
- 0.031  `src/flask/sansio/app.py:279-408`  method `__init__` (App)
- 0.029  `src/flask/config.py:20-47`  class `ConfigAttribute`
- 0.028  `src/flask/sansio/blueprints.py:34-116`  class `BlueprintSetupState`
