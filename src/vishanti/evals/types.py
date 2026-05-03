"""Schema for the eval dataset.

The dataset is a JSON file shipped at `evals/dataset.json`. Each question has:
- An id (Q01..QN)
- A natural-language question
- A category (where_defined | how_works | what_calls)
- One or more ground_truth spans: {file_path, start_line, end_line, rationale}
- expected_keywords: tokens that should appear in a good answer
- confidence: "high" | "medium" — flags questions for human review

Recall metric: a retrieved chunk counts as a hit if its [start_line, end_line]
range overlaps any ground-truth span on the same file_path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Category = Literal["where_defined", "how_works", "what_calls"]
Confidence = Literal["high", "medium"]


@dataclass
class GroundTruthSpan:
    file_path: str  # repo-relative, e.g. "src/flask/app.py"
    start_line: int
    end_line: int  # 1-indexed, inclusive
    rationale: str = ""

    def overlaps(self, other_file: str, other_start: int, other_end: int) -> bool:
        if self.file_path != other_file:
            return False
        return not (other_end < self.start_line or other_start > self.end_line)


@dataclass
class EvalQuestion:
    id: str
    category: Category
    question: str
    ground_truth: list[GroundTruthSpan]
    expected_keywords: list[str] = field(default_factory=list)
    confidence: Confidence = "high"
    notes: str = ""


@dataclass
class EvalDataset:
    version: str
    repo: str
    questions: list[EvalQuestion]


def load_dataset(path: str | Path) -> EvalDataset:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    questions = [
        EvalQuestion(
            id=q["id"],
            category=q["category"],
            question=q["question"],
            ground_truth=[
                GroundTruthSpan(
                    file_path=g["file_path"],
                    start_line=g["start_line"],
                    end_line=g["end_line"],
                    rationale=g.get("rationale", ""),
                )
                for g in q["ground_truth"]
            ],
            expected_keywords=q.get("expected_keywords", []),
            confidence=q.get("confidence", "high"),
            notes=q.get("notes", ""),
        )
        for q in raw["questions"]
    ]
    return EvalDataset(version=raw["version"], repo=raw["repo"], questions=questions)
