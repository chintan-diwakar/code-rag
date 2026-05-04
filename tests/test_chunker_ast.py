from pathlib import Path

import pytest

from code_rag.chunker_ast import CodeChunk, chunk_python_file

FIXTURE = Path(__file__).parent / "fixtures" / "sample.py"


@pytest.fixture(scope="module")
def chunks() -> list[CodeChunk]:
    return chunk_python_file(str(FIXTURE), FIXTURE.read_text(encoding="utf-8"))


def test_emits_expected_symbols(chunks: list[CodeChunk]) -> None:
    # Order: module preamble first, then top-level defs/classes by line.
    names = [c.symbol_name for c in chunks]
    assert names == [
        "sample",  # module-preamble chunk (filename stem)
        "plain_function",
        "no_docstring",
        "decorated_function",
        "Empty",
        "Greeter",
        "WithDecorator",
        "async_thing",
    ]


def test_kinds_include_module_function_class(chunks: list[CodeChunk]) -> None:
    kinds = {c.symbol_kind for c in chunks}
    assert kinds == {"module", "function", "class"}
    assert all(c.symbol_name != "__main__" for c in chunks)


def test_module_preamble_captures_leading_statements(chunks: list[CodeChunk]) -> None:
    module = next(c for c in chunks if c.symbol_kind == "module")
    assert module.symbol_name == "sample"
    # Preamble = top-level statements BEFORE the first def/class.
    # In the fixture: module docstring, `import os`, `from typing import Any`,
    # `CONSTANT = 42`, then `def plain_function` (stop here).
    assert "import os" in module.code
    assert "from typing import Any" in module.code
    assert "CONSTANT = 42" in module.code
    # The `if __name__ == "__main__":` block at the bottom comes AFTER defs and
    # is NOT in the preamble — that's the correct behavior. Including it would
    # bloat the line range and produce false-positive overlap matches.
    assert "__main__" not in module.code
    # And the line range should be tight — ending at or before the first def.
    plain = next(c for c in chunks if c.symbol_name == "plain_function")
    assert module.end_line < plain.start_line


def test_kind_classification(chunks: list[CodeChunk]) -> None:
    by_name = {c.symbol_name: c.symbol_kind for c in chunks if c.symbol_kind != "module"}
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
# Module-preamble (new in this iteration)
# ---------------------------------------------------------------------------


def test_module_preamble_omitted_when_file_has_only_defs() -> None:
    src = "def alpha():\n    pass\n\nclass Beta:\n    pass\n"
    chunks = chunk_python_file("only_defs.py", src)
    kinds = {c.symbol_kind for c in chunks}
    assert "module" not in kinds


def test_module_preamble_uses_filename_stem_as_symbol() -> None:
    src = "import os\nVALUE = 1\n\ndef f():\n    pass\n"
    chunks = chunk_python_file("globals.py", src)
    module = next(c for c in chunks if c.symbol_kind == "module")
    assert module.symbol_name == "globals"


def test_module_preamble_captures_proxy_assignment_pattern() -> None:
    # Mirrors flask/globals.py shape — what unblocks Q03/Q04/Q05.
    src = (
        "from contextvars import ContextVar\n"
        "from werkzeug.local import LocalProxy\n"
        "\n"
        "_cv_app = ContextVar('flask.app_ctx')\n"
        "current_app = LocalProxy(_cv_app, 'app')\n"
        "request = LocalProxy(_cv_app, 'request')\n"
    )
    chunks = chunk_python_file("globals.py", src)
    module = next(c for c in chunks if c.symbol_kind == "module")
    assert "current_app = LocalProxy" in module.code
    assert "request = LocalProxy" in module.code


# ---------------------------------------------------------------------------
# Class-header chunks on split (new in this iteration)
# ---------------------------------------------------------------------------


def test_small_class_stays_whole_under_default_threshold(chunks: list[CodeChunk]) -> None:
    # Greeter is small, single class chunk, no parent_class.
    by_name = {c.symbol_name: c for c in chunks if c.symbol_kind != "module"}
    assert by_name["Greeter"].symbol_kind == "class"
    assert by_name["Greeter"].parent_class is None


def test_oversized_class_emits_header_plus_methods() -> None:
    src = (
        "class Big:\n"
        '    """Greets people."""\n'
        "\n"
        "    PREFIX: str = 'Hello'\n"
        "\n"
        "    def __init__(self):\n"
        "        self.greeted = 0\n"
        "\n"
        "    def greet(self, name):\n"
        "        return f'{self.PREFIX}, {name}!'\n"
    )
    chunks = chunk_python_file("inline.py", src, max_class_lines=2)
    by_kind = {(c.symbol_kind, c.symbol_name): c for c in chunks}

    # Class-header chunk exists with kind="class"
    assert ("class", "Big") in by_kind
    header = by_kind[("class", "Big")]
    assert header.docstring == "Greets people."
    assert "PREFIX" in header.code
    assert "def __init__" not in header.code  # header stops before first method
    assert "def greet" not in header.code

    # Method chunks
    init_chunk = by_kind[("method", "__init__")]
    greet_chunk = by_kind[("method", "greet")]
    assert init_chunk.parent_class == "Big"
    assert greet_chunk.parent_class == "Big"


def test_split_preserves_method_decorators() -> None:
    src = (
        "class Big:\n"
        '    """A class big enough to force split."""\n'
        "\n"
        "    @property\n"
        "    def x(self):\n"
        "        return 1\n"
        "\n"
        "    @staticmethod\n"
        "    def y():\n"
        "        return 2\n"
    )
    chunks = chunk_python_file("inline.py", src, max_class_lines=2)
    by_name = {(c.symbol_kind, c.symbol_name): c for c in chunks}
    assert by_name[("method", "x")].decorators == ["property"]
    assert by_name[("method", "y")].decorators == ["staticmethod"]
    assert by_name[("method", "x")].parent_class == "Big"


def test_class_header_includes_class_decorators() -> None:
    src = (
        "@dataclass\n"
        "class Big:\n"
        '    """A frozen-dataclass-style class."""\n'
        "\n"
        "    name: str\n"
        "    age: int\n"
        "\n"
        "    def greet(self):\n"
        "        return self.name\n"
    )
    chunks = chunk_python_file("inline.py", src, max_class_lines=2)
    header = next(c for c in chunks if c.symbol_kind == "class" and c.symbol_name == "Big")
    assert header.decorators == ["dataclass"]
    # Decorator and class signature both in the header code
    assert "@dataclass" in header.code
    assert "class Big" in header.code
    # Class-level fields are kept in the header
    assert "name: str" in header.code
    # Methods are NOT in the header
    assert "def greet" not in header.code


def test_top_level_function_not_affected_by_class_threshold() -> None:
    src = "def alpha():\n    return 1\n\nclass C:\n    def m(self):\n        pass\n"
    chunks = chunk_python_file("inline.py", src, max_class_lines=1)
    plain = next(c for c in chunks if c.symbol_name == "alpha")
    assert plain.symbol_kind == "function"
    assert plain.parent_class is None
