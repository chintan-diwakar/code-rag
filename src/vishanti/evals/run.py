"""Run the eval set against the current pipeline. Writes evals/REPORT.md.

Usage:
    .venv/Scripts/python -m vishanti.evals.run

Pipeline (week-1 baseline):
    1. AST-chunk every .py in data/flask/src/flask
    2. Embed all chunk.code with bge-small-en-v1.5 (in-memory cosine retriever)
    3. For each of the 30 questions: embed the question, retrieve top-5
    4. A hit = retrieved chunk overlaps any ground-truth span (file_path + line range)
    5. Report recall@5 overall and per category, plus latency stats and sample misses
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from vishanti.chunker_ast import CodeChunk, chunk_python_file
from vishanti.embedder import DEFAULT_MODEL, Embedder
from vishanti.evals.types import EvalQuestion, GroundTruthSpan, load_dataset
from vishanti.retriever import InMemoryRetriever, RetrievalHit

REPO_ROOT = Path(__file__).resolve().parents[3]
FLASK_SRC = REPO_ROOT / "data" / "flask" / "src" / "flask"
DATASET_PATH = REPO_ROOT / "evals" / "dataset.json"
REPORT_PATH = REPO_ROOT / "evals" / "REPORT.md"
K = 5


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

    retriever = InMemoryRetriever(chunk_vectors, chunks)

    print("Step 4: loading eval set...")
    dataset = load_dataset(DATASET_PATH)
    print(f"  {len(dataset.questions)} questions")

    print(f"Step 5: running retrieval (k={K}) for each question...")
    t0 = time.perf_counter()
    question_vectors = embedder.encode([q.question for q in dataset.questions])
    embed_time = time.perf_counter() - t0

    per_query_latency: list[float] = []
    rows: list[QueryResult] = []
    for question, qv in zip(dataset.questions, question_vectors, strict=True):
        ts = time.perf_counter()
        hits = retriever.search(qv, k=K)
        per_query_latency.append((time.perf_counter() - ts) * 1000.0)
        rows.append(QueryResult(question=question, hits=hits, hit=_is_hit(question, hits)))

    print(f"  embedded {len(dataset.questions)} questions in {embed_time:.2f}s")
    print(
        f"  retrieval p50={statistics.median(per_query_latency):.2f}ms, "
        f"p95={_p95(per_query_latency):.2f}ms"
    )

    overall, by_category = _compute_recall(rows)
    print(f"\nrecall@{K} = {overall:.3f} ({sum(r.hit for r in rows)}/{len(rows)})")
    for cat, score in sorted(by_category.items()):
        cat_count = sum(1 for r in rows if r.question.category == cat)
        cat_hits = sum(1 for r in rows if r.question.category == cat and r.hit)
        print(f"  {cat:<14} {score:.3f}  ({cat_hits}/{cat_count})")

    print(f"\nWriting report to {REPORT_PATH.relative_to(REPO_ROOT)}")
    _write_report(
        report_path=REPORT_PATH,
        config={
            "model": DEFAULT_MODEL,
            "k": K,
            "chunks": len(chunks),
            "questions": len(dataset.questions),
            "retriever": "in-memory cosine",
            "chunker": "AST (tree-sitter), MAX_CLASS_LINES=100",
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        overall=overall,
        by_category=by_category,
        rows=rows,
        latency_ms=per_query_latency,
    )
    print("done.")
    return 0


# ---------------------------------------------------------------------------


class QueryResult:
    __slots__ = ("question", "hits", "hit")

    def __init__(self, question: EvalQuestion, hits: list[RetrievalHit], hit: bool) -> None:
        self.question = question
        self.hits = hits
        self.hit = hit


def _chunk_repo(src_dir: Path) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for path in sorted(src_dir.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        # Store the file_path on each chunk relative to the repo root, matching
        # the eval dataset's ground-truth file_path format.
        rel = path.relative_to(src_dir.parents[1])  # data/flask -> "src/flask/..."
        for c in chunk_python_file(str(rel).replace("\\", "/"), text):
            chunks.append(c)
    return chunks


def _is_hit(question: EvalQuestion, hits: list[RetrievalHit]) -> bool:
    for hit in hits:
        for span in question.ground_truth:
            if span.overlaps(hit.chunk.file_path, hit.chunk.start_line, hit.chunk.end_line):
                return True
    return False


def _compute_recall(rows: list[QueryResult]) -> tuple[float, dict[str, float]]:
    overall = sum(r.hit for r in rows) / max(len(rows), 1)
    by_cat: dict[str, list[bool]] = {}
    for r in rows:
        by_cat.setdefault(r.question.category, []).append(r.hit)
    return overall, {cat: sum(v) / len(v) for cat, v in by_cat.items()}


def _p95(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[min(int(len(s) * 0.95), len(s) - 1)]


def _write_report(
    *,
    report_path: Path,
    config: dict,
    overall: float,
    by_category: dict[str, float],
    rows: list[QueryResult],
    latency_ms: list[float],
) -> None:
    misses = [r for r in rows if not r.hit]
    lines: list[str] = []
    lines.append("# Eval report")
    lines.append("")
    lines.append(f"_Generated {config['ts']}_")
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append(f"- **Model:** `{config['model']}`")
    lines.append(f"- **Retriever:** {config['retriever']}")
    lines.append(f"- **Chunker:** {config['chunker']}")
    lines.append(f"- **Chunks indexed:** {config['chunks']}")
    lines.append(f"- **Questions:** {config['questions']}")
    lines.append(f"- **k:** {config['k']}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Slice | recall@5 | hits / total |")
    lines.append("|---|---|---|")
    lines.append(f"| **Overall** | **{overall:.3f}** | {sum(r.hit for r in rows)}/{len(rows)} |")
    for cat in ("where_defined", "how_works", "what_calls"):
        score = by_category.get(cat, 0.0)
        cat_total = sum(1 for r in rows if r.question.category == cat)
        cat_hits = sum(1 for r in rows if r.question.category == cat and r.hit)
        lines.append(f"| {cat} | {score:.3f} | {cat_hits}/{cat_total} |")
    lines.append("")
    lines.append("## Retrieval latency")
    lines.append("")
    lines.append(f"- p50: {statistics.median(latency_ms):.2f} ms")
    lines.append(f"- p95: {_p95(latency_ms):.2f} ms")
    lines.append(f"- max: {max(latency_ms):.2f} ms")
    lines.append("")
    if misses:
        lines.append(f"## Sample misses (showing first {min(5, len(misses))} of {len(misses)})")
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
                    f"- {hit.score:.3f}  `{hit.chunk.file_path}:{hit.chunk.start_line}-{hit.chunk.end_line}`  "
                    f"{hit.chunk.symbol_kind} `{hit.chunk.symbol_name}`{parent}"
                )
            lines.append("")

    lines.append("## Raw results (JSON)")
    lines.append("")
    lines.append("<details><summary>per-question</summary>")
    lines.append("")
    lines.append("```json")
    lines.append(
        json.dumps(
            [
                {
                    "id": r.question.id,
                    "category": r.question.category,
                    "hit": r.hit,
                    "top_chunk": (
                        f"{r.hits[0].chunk.file_path}:"
                        f"{r.hits[0].chunk.start_line}-{r.hits[0].chunk.end_line}"
                        if r.hits
                        else None
                    ),
                    "top_score": r.hits[0].score if r.hits else None,
                }
                for r in rows
            ],
            indent=2,
        )
    )
    lines.append("```")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
