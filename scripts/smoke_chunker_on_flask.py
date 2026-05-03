"""Smoke-test the AST chunker on real-world code (pallets/flask).

Run after `git clone --depth 1 https://github.com/pallets/flask.git data/flask`.
Prints summary statistics so we can spot pathological cases before building the
embedder. Not a unit test — a manual sanity check.

Usage:  .venv/Scripts/python scripts/smoke_chunker_on_flask.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from vishanti.chunker_ast import CodeChunk, chunk_python_file

REPO_ROOT = Path(__file__).resolve().parents[1]
FLASK_SRC = REPO_ROOT / "data" / "flask" / "src" / "flask"


def main() -> int:
    if not FLASK_SRC.exists():
        print(f"missing: {FLASK_SRC}")
        print("clone first: git clone --depth 1 https://github.com/pallets/flask.git data/flask")
        return 1

    py_files = sorted(FLASK_SRC.rglob("*.py"))
    all_chunks: list[CodeChunk] = []
    files_with_zero: list[Path] = []
    parse_errors: list[tuple[Path, str]] = []

    for path in py_files:
        try:
            chunks = chunk_python_file(str(path), path.read_text(encoding="utf-8"))
        except Exception as e:
            parse_errors.append((path, str(e)))
            continue
        if not chunks:
            files_with_zero.append(path)
        all_chunks.extend(chunks)

    by_kind: dict[str, int] = {}
    has_docstring = 0
    for c in all_chunks:
        by_kind[c.symbol_kind] = by_kind.get(c.symbol_kind, 0) + 1
        if c.docstring:
            has_docstring += 1

    sizes = [(c.end_line - c.start_line + 1, c) for c in all_chunks]
    sizes.sort(key=lambda pair: pair[0], reverse=True)

    print(f"{'=' * 60}")
    print(f"vishanti AST chunker - smoke test on pallets/flask")
    print(f"{'=' * 60}")
    print(f"Source dir:       {FLASK_SRC.relative_to(REPO_ROOT)}")
    print(f"Python files:     {len(py_files)}")
    print(f"Files w/ 0 chunks:{len(files_with_zero)}  (often __init__.py, py.typed)")
    print(f"Parse errors:     {len(parse_errors)}")
    print()
    print(f"Total chunks:     {len(all_chunks)}")
    plurals = {
        "module": "modules:",
        "function": "functions:",
        "class": "classes:",
        "method": "methods:",
    }
    for kind in ("module", "function", "class", "method"):
        if kind in by_kind:
            print(f"  {plurals[kind]:<14}{by_kind[kind]}")
    print(f"  with docstring: {has_docstring} ({100 * has_docstring // max(len(all_chunks), 1)}%)")
    print()
    print("Largest 5 chunks (lines):")
    for line_count, chunk in sizes[:5]:
        rel = Path(chunk.file_path).relative_to(REPO_ROOT)
        parent = f"  ({chunk.parent_class})" if chunk.parent_class else ""
        print(f"  {line_count:>4}  {chunk.symbol_kind:<8} {chunk.symbol_name:<30}  {rel}:{chunk.start_line}{parent}")
    print()
    print("Smallest 5 chunks (lines):")
    for line_count, chunk in sizes[-5:]:
        rel = Path(chunk.file_path).relative_to(REPO_ROOT)
        parent = f"  ({chunk.parent_class})" if chunk.parent_class else ""
        print(f"  {line_count:>4}  {chunk.symbol_kind:<8} {chunk.symbol_name:<30}  {rel}:{chunk.start_line}{parent}")

    if files_with_zero:
        print()
        print("Files with 0 chunks (verify these are reasonable):")
        for p in files_with_zero[:10]:
            print(f"  {p.relative_to(REPO_ROOT)}")

    if parse_errors:
        print()
        print("Parse errors (must be 0 for a clean smoke test):")
        for path, err in parse_errors:
            print(f"  {path.relative_to(REPO_ROOT)}: {err}")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
