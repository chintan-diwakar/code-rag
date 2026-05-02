from pathlib import Path

import pytest

from vishanti.chunker_ast import CodeChunk, chunk_python_file

FIXTURE = Path(__file__).parent / "fixtures" / "sample.py"


@pytest.fixture(scope="module")
def chunks() -> list[CodeChunk]:
    return chunk_python_file(str(FIXTURE), FIXTURE.read_text(encoding="utf-8"))


def test_emits_expected_top_level_symbols(chunks: list[CodeChunk]) -> None:
    names = [c.symbol_name for c in chunks]
    assert names == [
        "plain_function",
        "no_docstring",
        "decorated_function",
        "Empty",
        "Greeter",
        "WithDecorator",
        "async_thing",
    ]


def test_skips_imports_constants_and_main_guard(chunks: list[CodeChunk]) -> None:
    # Module docstring, import, CONSTANT assignment, and `if __name__` block
    # must NOT be emitted as chunks.
    kinds = {c.symbol_kind for c in chunks}
    assert kinds == {"function", "class"}
    assert all(c.symbol_name != "__main__" for c in chunks)


def test_kind_classification(chunks: list[CodeChunk]) -> None:
    by_name = {c.symbol_name: c.symbol_kind for c in chunks}
    assert by_name["plain_function"] == "function"
    assert by_name["async_thing"] == "function"
    assert by_name["Empty"] == "class"
    assert by_name["Greeter"] == "class"
    assert by_name["WithDecorator"] == "class"


def test_docstring_extraction(chunks: list[CodeChunk]) -> None:
    by_name = {c.symbol_name: c for c in chunks}
    assert by_name["plain_function"].docstring == "Add one to x."
    assert by_name["no_docstring"].docstring is None
    assert by_name["decorated_function"].docstring == "Decorated and documented."
    assert by_name["Empty"].docstring == "Just a docstring."
    assert by_name["Greeter"].docstring == "Greets people by name."


def test_decorators_captured(chunks: list[CodeChunk]) -> None:
    by_name = {c.symbol_name: c for c in chunks}
    assert by_name["plain_function"].decorators == []
    assert by_name["decorated_function"].decorators == ["staticmethod"]
    assert by_name["WithDecorator"].decorators == ["dataclass"]


def test_decorator_lines_included_in_chunk(chunks: list[CodeChunk]) -> None:
    by_name = {c.symbol_name: c for c in chunks}
    # decorator + def together on consecutive lines
    chunk = by_name["decorated_function"]
    assert chunk.code.lstrip().startswith("@staticmethod")
    assert "def decorated_function" in chunk.code


def test_class_chunk_includes_methods(chunks: list[CodeChunk]) -> None:
    by_name = {c.symbol_name: c for c in chunks}
    greeter = by_name["Greeter"]
    assert "def __init__" in greeter.code
    assert "def greet" in greeter.code


def test_line_ranges_are_one_indexed_and_ordered(chunks: list[CodeChunk]) -> None:
    for c in chunks:
        assert c.start_line >= 1
        assert c.end_line >= c.start_line
    starts = [c.start_line for c in chunks]
    assert starts == sorted(starts)


def test_file_path_propagated(chunks: list[CodeChunk]) -> None:
    for c in chunks:
        assert c.file_path == str(FIXTURE)
