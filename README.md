# vishanti

Code RAG with AST-aware chunking and a measured eval harness.

## What this is

A retrieval-augmented question answering system over a public OSS codebase. The differentiator from a generic "chat with your docs" RAG is three things:

1. **AST-aware chunking** via tree-sitter. One chunk per function or class, with cross-file symbol metadata.
2. **Hybrid retrieval** (BM25 + vector + reciprocal rank fusion) followed by a cross-encoder reranker.
3. **A real eval harness** with a hand-curated 30-question set, measuring recall@5, MRR, faithfulness, and an ablation study comparing embedding models and reranker on/off.

## Status

Week 1 in progress. Currently shipped:
- AST chunker (`src/vishanti/chunker_ast.py`) — Python only, tree-sitter based.

Coming next:
- Eval set fixtures
- Embedder + retriever
- FastAPI + HTMX UI
- Deploy

## Quickstart

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
# source .venv/bin/activate  # Unix
pip install -e ".[dev]"
pytest
```
