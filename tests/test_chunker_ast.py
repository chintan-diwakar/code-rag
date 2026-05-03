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


# ---------------------------------------------------------------------------
# Oversized class splitting
# ---------------------------------------------------------------------------


def test_small_class_stays_whole_under_default_threshold(chunks: list[CodeChunk]) -> None:
    by_name = {c.symbol_name: c for c in chunks}
    assert by_name["Greeter"].symbol_kind == "class"
    assert by_name["Greeter"].parent_class is None


def test_oversized_class_splits_into_methods() -> None:
    # Force-split Greeter by lowering the threshold below its line span.
    forced = chunk_python_file(str(FIXTURE), FIXTURE.read_text(encoding="utf-8"), max_class_lines=3)
    by_name = {(c.symbol_kind, c.symbol_name): c for c in forced}

    # Greeter no longer appears as a class chunk
    assert ("class", "Greeter") not in by_name
    # __init__ and greet appear as method chunks with parent_class set
    init = by_name[("method", "__init__")]
    greet = by_name[("method", "greet")]
    assert init.parent_class == "Greeter"
    assert greet.parent_class == "Greeter"
    assert greet.docstring == "Return a greeting."
    assert "def greet" in greet.code


def test_split_preserves_method_decorators() -> None:
    src = '''
class Big:
    """A class big enough to force split."""

    @property
    def x(self):
        return 1

    @staticmethod
    def y():
        return 2
'''
    forced = chunk_python_file("inline.py", src, max_class_lines=2)
    by_name = {c.symbol_name: c for c in forced}
    assert by_name["x"].decorators == ["property"]
    assert by_name["y"].decorators == ["staticmethod"]
    assert by_name["x"].symbol_kind == "method"
    assert by_name["x"].parent_class == "Big"


def test_top_level_function_not_affected_by_class_threshold() -> None:
    # Even with a tiny threshold, top-level functions remain "function" kind.
    forced = chunk_python_file(str(FIXTURE), FIXTURE.read_text(encoding="utf-8"), max_class_lines=1)
    plain = next(c for c in forced if c.symbol_name == "plain_function")
    assert plain.symbol_kind == "function"
    assert plain.parent_class is None
