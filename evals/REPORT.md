# Eval report

_Generated 2026-05-03T08:25:44+00:00_

## Configuration

- **Model:** `BAAI/bge-small-en-v1.5`
- **Retriever:** in-memory cosine
- **Chunker:** AST (tree-sitter), MAX_CLASS_LINES=100
- **Chunks indexed:** 304
- **Questions:** 30
- **k:** 5

## Results

| Slice | recall@5 | hits / total |
|---|---|---|
| **Overall** | **0.700** | 21/30 |
| where_defined | 0.500 | 5/10 |
| how_works | 0.900 | 9/10 |
| what_calls | 0.700 | 7/10 |

## Retrieval latency

- p50: 0.04 ms
- p95: 0.06 ms
- max: 0.31 ms

## Sample misses (showing first 5 of 9)

### Q01 [where_defined]
_Where is the Flask class defined?_

Ground truth:
- `src/flask/app.py:109-150`

Top-5 retrieved (none overlapped):
- 0.776  `src/flask/json/provider.py:19-105`  class `JSONProvider`
- 0.767  `src/flask/cli.py:293-372`  class `ScriptInfo`
- 0.756  `src/flask/templating.py:36-46`  class `Environment`
- 0.750  `src/flask/testing.py:265-298`  class `FlaskCliRunner`
- 0.743  `src/flask/wrappers.py:222-257`  class `Response`

### Q02 [where_defined]
_Where is the Blueprint class defined?_

Ground truth:
- `src/flask/blueprints.py:18-50`

Top-5 retrieved (none overlapped):
- 0.825  `src/flask/sansio/blueprints.py:34-116`  class `BlueprintSetupState`
- 0.781  `src/flask/wrappers.py:161-178`  method `blueprint` (Request)
- 0.781  `src/flask/sansio/app.py:597-602`  method `iter_blueprints` (App)
- 0.770  `src/flask/sansio/app.py:569-595`  method `register_blueprint` (App)
- 0.770  `src/flask/wrappers.py:180-195`  method `blueprints` (Request)

### Q03 [where_defined]
_Where is the current_app proxy defined?_

Ground truth:
- `src/flask/globals.py:40-49`

Top-5 retrieved (none overlapped):
- 0.748  `src/flask/ctx.py:235-257`  function `has_app_context`
- 0.744  `src/flask/ctx.py:300-337`  method `__init__` (AppContext)
- 0.736  `src/flask/app.py:1481-1499`  method `app_context` (Flask)
- 0.717  `src/flask/ctx.py:209-232`  function `has_request_context`
- 0.715  `src/flask/app.py:1517-1564`  method `test_request_context` (Flask)

### Q04 [where_defined]
_Where is the request global proxy defined?_

Ground truth:
- `src/flask/globals.py:57-59`

Top-5 retrieved (none overlapped):
- 0.730  `src/flask/ctx.py:300-337`  method `__init__` (AppContext)
- 0.723  `src/flask/ctx.py:209-232`  function `has_request_context`
- 0.719  `src/flask/app.py:1517-1564`  method `test_request_context` (Flask)
- 0.712  `src/flask/app.py:1501-1515`  method `request_context` (Flask)
- 0.711  `src/flask/testing.py:204-247`  method `open` (FlaskClient)

### Q06 [where_defined]
_Where is the Flask Config class defined?_

Ground truth:
- `src/flask/config.py:50-100`

Top-5 retrieved (none overlapped):
- 0.788  `src/flask/sansio/app.py:479-493`  method `make_config` (App)
- 0.760  `src/flask/testing.py:27-94`  class `EnvironBuilder`
- 0.751  `src/flask/testing.py:265-298`  class `FlaskCliRunner`
- 0.748  `src/flask/templating.py:36-46`  class `Environment`
- 0.747  `src/flask/config.py:20-47`  class `ConfigAttribute`

## Raw results (JSON)

<details><summary>per-question</summary>

```json
[
  {
    "id": "Q01",
    "category": "where_defined",
    "hit": false,
    "top_chunk": "src/flask/json/provider.py:19-105",
    "top_score": 0.7758779525756836
  },
  {
    "id": "Q02",
    "category": "where_defined",
    "hit": false,
    "top_chunk": "src/flask/sansio/blueprints.py:34-116",
    "top_score": 0.8247740864753723
  },
  {
    "id": "Q03",
    "category": "where_defined",
    "hit": false,
    "top_chunk": "src/flask/ctx.py:235-257",
    "top_score": 0.7476767301559448
  },
  {
    "id": "Q04",
    "category": "where_defined",
    "hit": false,
    "top_chunk": "src/flask/ctx.py:300-337",
    "top_score": 0.7304905652999878
  },
  {
    "id": "Q05",
    "category": "where_defined",
    "hit": true,
    "top_chunk": "src/flask/ctx.py:300-337",
    "top_score": 0.7365588545799255
  },
  {
    "id": "Q06",
    "category": "where_defined",
    "hit": false,
    "top_chunk": "src/flask/sansio/app.py:479-493",
    "top_score": 0.788173496723175
  },
  {
    "id": "Q07",
    "category": "where_defined",
    "hit": true,
    "top_chunk": "src/flask/sansio/scaffold.py:284-293",
    "top_score": 0.8083575963973999
  },
  {
    "id": "Q08",
    "category": "where_defined",
    "hit": true,
    "top_chunk": "src/flask/helpers.py:417-540",
    "top_score": 0.7907505631446838
  },
  {
    "id": "Q09",
    "category": "where_defined",
    "hit": true,
    "top_chunk": "src/flask/helpers.py:200-251",
    "top_score": 0.7727720737457275
  },
  {
    "id": "Q10",
    "category": "where_defined",
    "hit": true,
    "top_chunk": "src/flask/sessions.py:323-335",
    "top_score": 0.758975625038147
  },
  {
    "id": "Q11",
    "category": "how_works",
    "hit": false,
    "top_chunk": "src/flask/views.py:78-83",
    "top_score": 0.819145143032074
  },
  {
    "id": "Q12",
    "category": "how_works",
    "hit": true,
    "top_chunk": "src/flask/ctx.py:300-337",
    "top_score": 0.7715398073196411
  },
  {
    "id": "Q13",
    "category": "how_works",
    "hit": true,
    "top_chunk": "src/flask/blueprints.py:82-102",
    "top_score": 0.8213618993759155
  },
  {
    "id": "Q14",
    "category": "how_works",
    "hit": true,
    "top_chunk": "src/flask/sansio/scaffold.py:459-484",
    "top_score": 0.828369140625
  },
  {
    "id": "Q15",
    "category": "how_works",
    "hit": true,
    "top_chunk": "src/flask/json/__init__.py:138-170",
    "top_score": 0.8477450609207153
  },
  {
    "id": "Q16",
    "category": "how_works",
    "hit": true,
    "top_chunk": "src/flask/app.py:755-811",
    "top_score": 0.8578062057495117
  },
  {
    "id": "Q17",
    "category": "how_works",
    "hit": true,
    "top_chunk": "src/flask/sansio/blueprints.py:273-377",
    "top_score": 0.8361722230911255
  },
  {
    "id": "Q18",
    "category": "how_works",
    "hit": true,
    "top_chunk": "src/flask/sessions.py:323-335",
    "top_score": 0.8355519771575928
  },
  {
    "id": "Q19",
    "category": "how_works",
    "hit": true,
    "top_chunk": "src/flask/app.py:1102-1222",
    "top_score": 0.8778213858604431
  },
  {
    "id": "Q20",
    "category": "how_works",
    "hit": true,
    "top_chunk": "src/flask/config.py:126-185",
    "top_score": 0.805113673210144
  },
  {
    "id": "Q21",
    "category": "what_calls",
    "hit": true,
    "top_chunk": "src/flask/app.py:1366-1392",
    "top_score": 0.8059816360473633
  },
  {
    "id": "Q22",
    "category": "what_calls",
    "hit": true,
    "top_chunk": "src/flask/ctx.py:118-148",
    "top_score": 0.8222725987434387
  },
  {
    "id": "Q23",
    "category": "what_calls",
    "hit": true,
    "top_chunk": "src/flask/app.py:1618-1625",
    "top_score": 0.8208078145980835
  },
  {
    "id": "Q24",
    "category": "what_calls",
    "hit": true,
    "top_chunk": "src/flask/app.py:992-1019",
    "top_score": 0.8205741047859192
  },
  {
    "id": "Q25",
    "category": "what_calls",
    "hit": false,
    "top_chunk": "src/flask/helpers.py:151-197",
    "top_score": 0.871530294418335
  },
  {
    "id": "Q26",
    "category": "what_calls",
    "hit": false,
    "top_chunk": "src/flask/app.py:865-895",
    "top_score": 0.7567228078842163
  },
  {
    "id": "Q27",
    "category": "what_calls",
    "hit": true,
    "top_chunk": "src/flask/app.py:1394-1418",
    "top_score": 0.8056752681732178
  },
  {
    "id": "Q28",
    "category": "what_calls",
    "hit": false,
    "top_chunk": "src/flask/app.py:1420-1451",
    "top_score": 0.8466423749923706
  },
  {
    "id": "Q29",
    "category": "what_calls",
    "hit": true,
    "top_chunk": "src/flask/sessions.py:249-261",
    "top_score": 0.8398499488830566
  },
  {
    "id": "Q30",
    "category": "what_calls",
    "hit": true,
    "top_chunk": "src/flask/cli.py:999-1045",
    "top_score": 0.8085726499557495
  }
]
```

</details>
