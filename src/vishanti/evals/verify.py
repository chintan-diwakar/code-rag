"""Sanity-check the eval dataset against the cloned source.

Verifies:
- Every ground-truth file_path exists in the repo.
- Every (start_line, end_line) is in bounds for the file.
- start_line <= end_line.
- Every ID is unique and matches Q\\d+.
- Each question has at least one ground-truth span.
- Categories are valid.
- expected_keywords appear in the ground-truth span (best-effort heuristic;
  reports rather than fails to allow keyword loosening over time).

Exit 0 = all checks pass. Exit 1 = at least one structural error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from vishanti.evals.types import EvalDataset, load_dataset

VALID_CATEGORIES = {"where_defined", "how_works", "what_calls"}
VALID_CONFIDENCE = {"high", "medium"}
ID_PATTERN = re.compile(r"^Q\d+$")


def verify(dataset_path: Path, repo_root: Path) -> int:
    dataset: EvalDataset = load_dataset(dataset_path)

    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    by_category: dict[str, int] = {}

    for q in dataset.questions:
        # ID structure
        if not ID_PATTERN.match(q.id):
            errors.append(f"{q.id}: id does not match Q\\d+ pattern")
        if q.id in seen_ids:
            errors.append(f"{q.id}: duplicate id")
        seen_ids.add(q.id)

        # Category
        if q.category not in VALID_CATEGORIES:
            errors.append(f"{q.id}: invalid category '{q.category}'")
        else:
            by_category[q.category] = by_category.get(q.category, 0) + 1

        # Confidence
        if q.confidence not in VALID_CONFIDENCE:
            errors.append(f"{q.id}: invalid confidence '{q.confidence}'")

        # Ground truth presence
        if not q.ground_truth:
            errors.append(f"{q.id}: no ground_truth spans")
            continue

        # Per-span validation
        for i, span in enumerate(q.ground_truth):
            tag = f"{q.id}.gt[{i}]"
            full = repo_root / span.file_path
            if not full.exists():
                errors.append(f"{tag}: file not found: {span.file_path}")
                continue
            try:
                line_count = sum(1 for _ in full.open(encoding="utf-8"))
            except UnicodeDecodeError as e:
                errors.append(f"{tag}: cannot read {span.file_path}: {e}")
                continue
            if span.start_line < 1:
                errors.append(f"{tag}: start_line {span.start_line} < 1")
            if span.end_line < span.start_line:
                errors.append(f"{tag}: end_line {span.end_line} < start_line {span.start_line}")
            if span.start_line > line_count:
                errors.append(f"{tag}: start_line {span.start_line} > file length {line_count}")
            if span.end_line > line_count:
                errors.append(
                    f"{tag}: end_line {span.end_line} > file length {line_count}"
                )

            # Best-effort: at least one expected_keyword should appear in the span
            if q.expected_keywords:
                text = "\n".join(
                    full.read_text(encoding="utf-8").splitlines()[
                        max(span.start_line - 1, 0) : span.end_line
                    ]
                )
                missing = [k for k in q.expected_keywords if k not in text]
                if len(missing) == len(q.expected_keywords):
                    warnings.append(
                        f"{tag}: NONE of expected_keywords found in span: {q.expected_keywords}"
                    )

    # Summary
    print(f"Dataset: {dataset_path}")
    print(f"Repo root: {repo_root}")
    print(f"Version: {dataset.version}, repo: {dataset.repo}")
    print(f"Questions: {len(dataset.questions)}")
    for cat in sorted(VALID_CATEGORIES):
        print(f"  {cat}: {by_category.get(cat, 0)}")

    print()
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ! {w}")
        print()

    if errors:
        print(f"FAIL - {len(errors)} error(s):")
        for e in errors:
            print(f"  X {e}")
        return 1

    print("OK - all structural checks passed.")
    return 0


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[3] / "data" / "flask"
    dataset_path = Path(__file__).resolve().parents[3] / "evals" / "dataset.json"
    sys.exit(verify(dataset_path, repo_root))
