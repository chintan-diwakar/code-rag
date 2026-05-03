"""Run the eval set against vector / bm25 / hybrid pipelines.

Usage:
    .venv/Scripts/python -m vishanti.evals.run

Writes evals/REPORT.md (hybrid headline) and evals/ABLATION.md (3-way diff).

Pipeline:
    1. AST-chunk every .py in data/flask/src/flask
    2. Embed all chunk.code with bge-small-en-v1.5
    3. Build a VectorRetriever, a BM25Retriever, and a HybridRetriever
    4. For each of the 30 questions, run all three retrievers
    5. A hit = retrieved chunk overlaps any ground-truth span
    6. Report recall@5 overall and per category for each retriever
"""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from vishanti.chunker_ast import CodeChunk, chunk_python_file
from vishanti.embedder import DEFAULT_MODEL, Embedder
from vishanti.evals.types import EvalQuestion, load_dataset
from vishanti.retriever import (
    BM25Retriever,
    HybridRetriever,
    RetrievalHit,
    VectorRetriever,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FLASK_SRC = REPO_ROOT / "data" / "flask" / "src" / "flask"
DATASET_PATH = REPO_ROOT / "evals" / "dataset.json"
REPORT_PATH = REPO_ROOT / "evals" / "REPORT.md"
ABLATION_PATH = REPO_ROOT / "evals" / "ABLATION.md"
K = 5
HEADLINE_MODE = "hybrid"


@dataclass
class QueryResult:
    question: EvalQuestion
    hits: list[RetrievalHit]
    hit: bool


@dataclass
class ModeResult:
    mode: str
    overall_recall: float
    by_category: dict[str, float] = field(default_factory=dict)
    rows: list[QueryResult] = field(default_factory=list)
    latency_ms: list[float] = field(default_factory=list)


def main() -> int:
    if not FLASK_SRC.exists():
        print(f"missing: {FLASK_SRC}\nrun: git clone --depth 1 https://github.com/pallets/flask.git data/flask")
        return 1

    print("Step 1: chunking flask source...")
    t0 = time.perf_counter()
    chunks = _chunk_repo(FLASK_SRC)
    print(f"  {len(chunks)} chunks in {time.perf_counter() - t0:.2f}s")

    print(f"Step 2: loading embedder ({DEFAULT_MODEL})...")
    t0 = time.perf_counter()
    embedder = Embedder()
    print(f"  embedder ready (dim={embedder.dim}) in {time.perf_counter() - t0:.2f}s")

    print(f"Step 3: embedding {len(chunks)} chunks...")
    t0 = time.perf_counter()
    chunk_vectors = embedder.encode([c.code for c in chunks])
    print(f"  done in {time.perf_counter() - t0:.2f}s")

    print("Step 4: building retrievers...")
    vector_retriever = VectorRetriever(chunk_vectors, chunks)
    bm25_retriever = BM25Retriever(chunks)
    hybrid_retriever = HybridRetriever(vector_retriever, bm25_retriever)

    print("Step 5: loading eval set + embedding questions...")
    dataset = load_dataset(DATASET_PATH)
    question_vectors = embedder.encode([q.question for q in dataset.questions])
    print(f"  {len(dataset.questions)} questions")

    print("\nStep 6: running retrieval for each mode...")

    runs: list[ModeResult] = []
    runs.append(_run_mode("vector", lambda q, qv: vector_retriever.search(qv, K), dataset, question_vectors))
    runs.append(_run_mode("bm25", lambda q, qv: bm25_retriever.search(q.question, K), dataset, question_vectors))
    runs.append(_run_mode("hybrid", lambda q, qv: hybrid_retriever.search(q.question, qv, K), dataset, question_vectors))

    for r in runs:
        print(
            f"  {r.mode:<8}  recall@{K}={r.overall_recall:.3f}   "
            f"p50={statistics.median(r.latency_ms):.2f}ms   "
            f"p95={_p95(r.latency_ms):.2f}ms"
        )

    headline = next(r for r in runs if r.mode == HEADLINE_MODE)
    config = {
        "model": DEFAULT_MODEL,
        "k": K,
        "chunks": len(chunks),
        "questions": len(dataset.questions),
        "chunker": "AST (tree-sitter), MAX_CLASS_LINES=100",
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    print(f"\nWriting report to {REPORT_PATH.relative_to(REPO_ROOT)} (mode={HEADLINE_MODE})")
    _write_report(REPORT_PATH, config, headline)
    print(f"Writing ablation to {ABLATION_PATH.relative_to(REPO_ROOT)}")
    _write_ablation(ABLATION_PATH, config, runs)
    print("done.")
    return 0


# ---------------------------------------------------------------------------


def _run_mode(mode, do_search, dataset, question_vectors):
    rows: list[QueryResult] = []
    latency: list[float] = []
    for question, qv in zip(dataset.questions, question_vectors, strict=True):
        ts = time.perf_counter()
        hits = do_search(question, qv)
        latency.append((time.perf_counter() - ts) * 1000.0)
        rows.append(QueryResult(question=question, hits=hits, hit=_is_hit(question, hits)))

    overall = sum(r.hit for r in rows) / max(len(rows), 1)
    by_cat: dict[str, list[bool]] = {}
    for r in rows:
        by_cat.setdefault(r.question.category, []).append(r.hit)
    return ModeResult(
        mode=mode,
        overall_recall=overall,
        by_category={cat: sum(v) / len(v) for cat, v in by_cat.items()},
        rows=rows,
        latency_ms=latency,
    )


def _chunk_repo(src_dir: Path) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for path in sorted(src_dir.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(src_dir.parents[1])
        for c in chunk_python_file(str(rel).replace("\\", "/"), text):
            chunks.append(c)
    return chunks


def _is_hit(question: EvalQuestion, hits: list[RetrievalHit]) -> bool:
    for hit in hits:
        for span in question.ground_truth:
            if span.overlaps(hit.chunk.file_path, hit.chunk.start_line, hit.chunk.end_line):
                return True
    return False


def _p95(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[min(int(len(s) * 0.95), len(s) - 1)]


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------


def _write_report(path: Path, config: dict, run: ModeResult) -> None:
    lines: list[str] = []
    lines.append(f"# Eval report ({run.mode})")
    lines.append("")
    lines.append(f"_Generated {config['ts']}_")
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append(f"- **Mode:** `{run.mode}` (headline)")
    lines.append(f"- **Embedder:** `{config['model']}`")
    lines.append(f"- **Chunker:** {config['chunker']}")
    lines.append(f"- **Chunks indexed:** {config['chunks']}")
    lines.append(f"- **Questions:** {config['questions']}")
    lines.append(f"- **k:** {config['k']}")
    lines.append("")
    lines.append("See `ABLATION.md` for the comparison across vector / bm25 / hybrid.")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Slice | recall@5 | hits / total |")
    lines.append("|---|---|---|")
    lines.append(
        f"| **Overall** | **{run.overall_recall:.3f}** | "
        f"{sum(r.hit for r in run.rows)}/{len(run.rows)} |"
    )
    for cat in ("where_defined", "how_works", "what_calls"):
        score = run.by_category.get(cat, 0.0)
        cat_total = sum(1 for r in run.rows if r.question.category == cat)
        cat_hits = sum(1 for r in run.rows if r.question.category == cat and r.hit)
        lines.append(f"| {cat} | {score:.3f} | {cat_hits}/{cat_total} |")
    lines.append("")
    lines.append("## Retrieval latency")
    lines.append("")
    lines.append(f"- p50: {statistics.median(run.latency_ms):.2f} ms")
    lines.append(f"- p95: {_p95(run.latency_ms):.2f} ms")
    lines.append(f"- max: {max(run.latency_ms):.2f} ms")
    lines.append("")

    misses = [r for r in run.rows if not r.hit]
    if misses:
        lines.append(f"## Sample misses (first {min(5, len(misses))} of {len(misses)})")
        lines.append("")
        for r in misses[:5]:
            lines.append(f"### {r.question.id} [{r.question.category}]")
            lines.append(f"_{r.question.question}_")
            lines.append("")
            lines.append("Ground truth:")
            for span in r.question.ground_truth:
                lines.append(f"- `{span.file_path}:{span.start_line}-{span.end_line}`")
            lines.append("")
            lines.append("Top-5 retrieved (none overlapped):")
            for hit in r.hits:
                parent = f" ({hit.chunk.parent_class})" if hit.chunk.parent_class else ""
                lines.append(
                    f"- {hit.score:.3f}  `{hit.chunk.file_path}:"
                    f"{hit.chunk.start_line}-{hit.chunk.end_line}`  "
                    f"{hit.chunk.symbol_kind} `{hit.chunk.symbol_name}`{parent}"
                )
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _write_ablation(path: Path, config: dict, runs: list[ModeResult]) -> None:
    lines: list[str] = []
    lines.append("# Ablation: vector vs bm25 vs hybrid")
    lines.append("")
    lines.append(f"_Generated {config['ts']}_")
    lines.append("")
    lines.append("## Setup")
    lines.append("")
    lines.append(f"- **Embedder:** `{config['model']}`")
    lines.append(f"- **Chunker:** {config['chunker']}")
    lines.append(f"- **Chunks indexed:** {config['chunks']}")
    lines.append(f"- **Questions:** {config['questions']}")
    lines.append(f"- **k:** {config['k']}")
    lines.append("")
    lines.append("## Recall@5 by mode and category")
    lines.append("")
    headers = ["Mode"] + ["overall", "where_defined", "how_works", "what_calls"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in runs:
        row = [
            f"**{r.mode}**",
            f"{r.overall_recall:.3f}",
            f"{r.by_category.get('where_defined', 0):.3f}",
            f"{r.by_category.get('how_works', 0):.3f}",
            f"{r.by_category.get('what_calls', 0):.3f}",
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("## Latency (ms per query)")
    lines.append("")
    lines.append("| Mode | p50 | p95 | max |")
    lines.append("|---|---|---|---|")
    for r in runs:
        lines.append(
            f"| {r.mode} | {statistics.median(r.latency_ms):.2f} | "
            f"{_p95(r.latency_ms):.2f} | {max(r.latency_ms):.2f} |"
        )
    lines.append("")

    # Per-question table — useful for spotting where each mode wins/loses
    lines.append("## Per-question hits")
    lines.append("")
    lines.append("| Q | category | " + " | ".join(r.mode for r in runs) + " |")
    lines.append("|" + "|".join(["---"] * (2 + len(runs))) + "|")
    questions = runs[0].rows
    for i, _ in enumerate(questions):
        q = questions[i].question
        cells = []
        for r in runs:
            cells.append("OK" if r.rows[i].hit else "miss")
        lines.append(f"| {q.id} | {q.category} | " + " | ".join(cells) + " |")
    lines.append("")

    # Wins added by hybrid over vector and bm25 alone
    vector_run = next(r for r in runs if r.mode == "vector")
    bm25_run = next(r for r in runs if r.mode == "bm25")
    hybrid_run = next(r for r in runs if r.mode == "hybrid")
    hybrid_only_wins = [
        i
        for i in range(len(hybrid_run.rows))
        if hybrid_run.rows[i].hit
        and not vector_run.rows[i].hit
        and not bm25_run.rows[i].hit
    ]
    union_misses = [
        i
        for i in range(len(hybrid_run.rows))
        if not hybrid_run.rows[i].hit
        and not vector_run.rows[i].hit
        and not bm25_run.rows[i].hit
    ]
    lines.append("## Diagnostics")
    lines.append("")
    lines.append(
        f"- Questions hybrid retrieves that NEITHER single mode does: "
        f"{len(hybrid_only_wins)}  "
        f"(`{', '.join(hybrid_run.rows[i].question.id for i in hybrid_only_wins) or 'none'}`)"
    )
    lines.append(
        f"- Questions all 3 modes miss (chunker / dataset issues): "
        f"{len(union_misses)}  "
        f"(`{', '.join(hybrid_run.rows[i].question.id for i in union_misses) or 'none'}`)"
    )
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- Vector is bge-small-en-v1.5 cosine over L2-normalized embeddings.")
    lines.append("- BM25 uses code-aware tokenization (camelCase + snake_case split, lowercased).")
    lines.append("- Hybrid uses Reciprocal Rank Fusion (c=60, fetch_k=20 per retriever).")
    lines.append("")

    lines.append("## Raw results (JSON)")
    lines.append("")
    lines.append("<details><summary>per-question per-mode</summary>")
    lines.append("")
    raw = [
        {
            "id": runs[0].rows[i].question.id,
            "category": runs[0].rows[i].question.category,
            **{r.mode: r.rows[i].hit for r in runs},
        }
        for i in range(len(runs[0].rows))
    ]
    lines.append("```json")
    lines.append(json.dumps(raw, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
