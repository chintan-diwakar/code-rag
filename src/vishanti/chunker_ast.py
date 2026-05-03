"""AST-aware chunker for Python source files.

Emits four kinds of chunks:

- `function`: top-level function definitions (incl. async, incl. decorators).
- `class`: top-level class definitions whose line span <= max_class_lines, OR
  the *header* of an oversized class (signature + decorators + docstring +
  class-level statements before the first method).
- `method`: when an oversized class is split, each method becomes its own
  `method` chunk with `parent_class` set.
- `module`: per-file chunk capturing top-level non-def/class statements
  (imports, module docstring, module-level assignments, `if TYPE_CHECKING:`,
  `if __name__ == "__main__":`). Lets retrieval find module-level constants
  and proxy definitions like `flask.globals.current_app`.

Limitations (intentional, deferred):
- Nested classes inside an oversized class are skipped during splitting.
- Module-preamble chunk concatenates statements with newlines, dropping any
  intervening def/class bodies and blank lines. Line range covers first to
  last preamble statement (may span large files).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

_PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_PY_LANGUAGE)

_DEF_TYPES = ("function_definition", "class_definition")

# Top-level statement node types that belong in the module preamble chunk.
_PREAMBLE_TYPES = frozenset(
    {
        "expression_statement",  # module docstring, calls
        "import_statement",
        "import_from_statement",
        "future_import_statement",
        "assignment",
        "augmented_assignment",
        "type_alias_statement",
        "if_statement",  # if TYPE_CHECKING / if __name__ == "__main__"
        "try_statement",  # try: import X / except ImportError: import Y
        "with_statement",
        "global_statement",
        "nonlocal_statement",
    }
)

DEFAULT_MAX_CLASS_LINES = 100


@dataclass
class CodeChunk:
    file_path: str
    symbol_name: str
    symbol_kind: str  # "function" | "class" | "method" | "module"
    start_line: int  # 1-indexed, inclusive
    end_line: int  # 1-indexed, inclusive
    code: str
    docstring: str | None = None
    parent_class: str | None = None
    decorators: list[str] = field(default_factory=list)


def chunk_python_file(
    file_path: str,
    source: str | bytes,
    *,
    max_class_lines: int = DEFAULT_MAX_CLASS_LINES,
) -> list[CodeChunk]:
    """Parse `source` as Python and return all chunks for the file."""
    source_bytes = source.encode("utf-8") if isinstance(source, str) else source
    tree = _PARSER.parse(source_bytes)
    root = tree.root_node

    chunks: list[CodeChunk] = []

    # 1. One module-preamble chunk if there are top-level non-def/class statements.
    preamble = _collect_module_preamble(root, source_bytes, file_path)
    if preamble is not None:
        chunks.append(preamble)

    # 2. Per-symbol chunks (functions, classes, split-class methods).
    for node in root.children:
        chunks.extend(_node_to_chunks(node, source_bytes, file_path, max_class_lines))

    # Stable order: by start_line.
    chunks.sort(key=lambda c: (c.start_line, c.end_line))
    return chunks


# ---------------------------------------------------------------------------
# Per-node chunking
# ---------------------------------------------------------------------------


def _node_to_chunks(
    node: Node, source_bytes: bytes, file_path: str, max_class_lines: int
) -> list[CodeChunk]:
    target, decorators = _unwrap_decorated(node, source_bytes)
    if target is None or target.type not in _DEF_TYPES:
        return []

    name_node = target.child_by_field_name("name")
    if name_node is None:
        return []

    symbol_name = _slice(source_bytes, name_node)
    symbol_kind = "function" if target.type == "function_definition" else "class"

    full_chunk = CodeChunk(
        file_path=file_path,
        symbol_name=symbol_name,
        symbol_kind=symbol_kind,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code=_slice(source_bytes, node),
        docstring=_extract_docstring(target, source_bytes),
        decorators=decorators,
    )

    if symbol_kind == "function":
        return [full_chunk]

    # Class within threshold — single chunk.
    if full_chunk.end_line - full_chunk.start_line + 1 <= max_class_lines:
        return [full_chunk]

    # Oversized class — header chunk + per-method chunks.
    return _split_oversized_class(node, target, decorators, source_bytes, file_path, symbol_name)


def _split_oversized_class(
    outer_node: Node,
    class_node: Node,
    decorators: list[str],
    source_bytes: bytes,
    file_path: str,
    name: str,
) -> list[CodeChunk]:
    body = class_node.child_by_field_name("body")
    if body is None:
        return []

    # Find the first method (or decorated method) in the body — header ends just before it.
    first_method_node: Node | None = None
    for child in body.children:
        method_target, _ = _unwrap_decorated(child, source_bytes)
        if method_target is not None and method_target.type == "function_definition":
            first_method_node = child
            break

    chunks: list[CodeChunk] = []

    # Header: from outer_node start (includes decorators) to just before first method.
    header_start_byte = outer_node.start_byte
    header_end_byte = (
        first_method_node.start_byte if first_method_node is not None else outer_node.end_byte
    )
    header_code = source_bytes[header_start_byte:header_end_byte].decode("utf-8").rstrip()
    header_start_line = outer_node.start_point[0] + 1
    header_end_line = (
        first_method_node.start_point[0]  # 0-indexed row of first method = line just BEFORE it
        if first_method_node is not None
        else outer_node.end_point[0] + 1
    )
    if header_code.strip():
        chunks.append(
            CodeChunk(
                file_path=file_path,
                symbol_name=name,
                symbol_kind="class",
                start_line=header_start_line,
                end_line=max(header_end_line, header_start_line),
                code=header_code,
                docstring=_extract_docstring(class_node, source_bytes),
                decorators=decorators,
            )
        )

    # Methods.
    for child in body.children:
        method_target, method_decorators = _unwrap_decorated(child, source_bytes)
        if method_target is None or method_target.type != "function_definition":
            continue
        method_name_node = method_target.child_by_field_name("name")
        if method_name_node is None:
            continue
        chunks.append(
            CodeChunk(
                file_path=file_path,
                symbol_name=_slice(source_bytes, method_name_node),
                symbol_kind="method",
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                code=_slice(source_bytes, child),
                docstring=_extract_docstring(method_target, source_bytes),
                decorators=method_decorators,
                parent_class=name,
            )
        )
    return chunks


# ---------------------------------------------------------------------------
# Module preamble
# ---------------------------------------------------------------------------


def _collect_module_preamble(
    root: Node, source_bytes: bytes, file_path: str
) -> CodeChunk | None:
    """Capture the file's leading preamble: all module-level statements that
    appear BEFORE the first top-level def/class.

    Stopping at the first def/class keeps the chunk's line range tight and
    prevents the recall metric (which checks line-range overlap) from
    spuriously matching ground-truth spans deep inside the file. If a file
    has *no* top-level defs/classes at all (re-export modules, type aliases),
    every preamble statement is included.
    """
    preamble_nodes: list[Node] = []
    for child in root.children:
        if child.type in _DEF_TYPES or child.type == "decorated_definition":
            break
        if child.type in _PREAMBLE_TYPES:
            preamble_nodes.append(child)

    if not preamble_nodes:
        return None

    parts = [_slice(source_bytes, n) for n in preamble_nodes]
    code = "\n".join(p.rstrip() for p in parts).strip()
    if not code:
        return None

    base = os.path.basename(file_path)
    symbol_name = os.path.splitext(base)[0] or base

    return CodeChunk(
        file_path=file_path,
        symbol_name=symbol_name,
        symbol_kind="module",
        start_line=preamble_nodes[0].start_point[0] + 1,
        end_line=preamble_nodes[-1].end_point[0] + 1,
        code=code,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unwrap_decorated(node: Node, source_bytes: bytes) -> tuple[Node | None, list[str]]:
    if node.type != "decorated_definition":
        return node, []
    decorators: list[str] = []
    inner: Node | None = None
    for child in node.children:
        if child.type == "decorator":
            decorators.append(_slice(source_bytes, child).lstrip("@").strip())
        elif child.type in _DEF_TYPES:
            inner = child
    return inner, decorators


def _extract_docstring(target: Node, source_bytes: bytes) -> str | None:
    body = target.child_by_field_name("body")
    if body is None:
        return None
    for child in body.children:
        if child.type == "expression_statement":
            inner = child.children[0] if child.children else None
            if inner is not None and inner.type == "string":
                return _unquote_string(_slice(source_bytes, inner))
            return None
        if child.type == "comment":
            continue
        return None
    return None


def _slice(source_bytes: bytes, node: Node) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8")


def _unquote_string(raw: str) -> str:
    s = raw.strip()
    for prefix in ("r", "R", "b", "B", "u", "U", "f", "F"):
        if s.startswith(prefix):
            s = s[1:]
            break
    for quote in ('"""', "'''", '"', "'"):
        if s.startswith(quote) and s.endswith(quote) and len(s) >= 2 * len(quote):
            return s[len(quote) : -len(quote)]
    return s
