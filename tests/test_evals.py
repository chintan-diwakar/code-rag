"""Tests for the eval dataset loader and schema."""

from pathlib import Path

import pytest

from vishanti.evals import EvalQuestion, GroundTruthSpan, load_dataset

DATASET = Path(__file__).resolve().parents[1] / "evals" / "dataset.json"


@pytest.fixture(scope="module")
def dataset():
    return load_dataset(DATASET)


def test_loads_30_questions(dataset) -> None:
    assert len(dataset.questions) == 30


def test_ten_per_category(dataset) -> None:
    counts: dict[str, int] = {}
    for q in dataset.questions:
        counts[q.category] = counts.get(q.category, 0) + 1
    assert counts == {"where_defined": 10, "how_works": 10, "what_calls": 10}


def test_ids_are_unique_and_sequential(dataset) -> None:
    ids = [q.id for q in dataset.questions]
    assert len(set(ids)) == len(ids), "duplicate ids"
    expected = [f"Q{i:02d}" for i in range(1, 31)]
    assert ids == expected


def test_every_question_has_ground_truth(dataset) -> None:
    for q in dataset.questions:
        assert len(q.ground_truth) >= 1, f"{q.id} has no ground_truth"


def test_ground_truth_line_ranges_are_sane(dataset) -> None:
    for q in dataset.questions:
        for span in q.ground_truth:
            assert span.start_line >= 1, f"{q.id}: start_line < 1"
            assert span.end_line >= span.start_line, f"{q.id}: end_line < start_line"


def test_overlap_helper_self_overlap() -> None:
    span = GroundTruthSpan(file_path="x.py", start_line=10, end_line=20)
    assert span.overlaps("x.py", 5, 15)
    assert span.overlaps("x.py", 15, 25)
    assert span.overlaps("x.py", 12, 18)
    assert not span.overlaps("x.py", 0, 9)
    assert not span.overlaps("x.py", 21, 30)
    assert not span.overlaps("y.py", 10, 20)


def test_question_dataclass_roundtrips_keywords() -> None:
    q = EvalQuestion(
        id="Q99",
        category="how_works",
        question="?",
        ground_truth=[GroundTruthSpan("a.py", 1, 2)],
        expected_keywords=["foo", "bar"],
    )
    assert q.expected_keywords == ["foo", "bar"]
    assert q.confidence == "high"
