"""AST-aware chunker for Python source files.

Top-level functions/classes become one chunk each. Classes that exceed
`max_class_lines` are split into one chunk per method (`symbol_kind="method"`,
`parent_class` set) so retrieval works on per-method granularity for huge
classes like flask.app.Flask (1500+ lines).

Limitations (intentional, deferred):
- When a class is split, its class-level decorators, docstring, and bare
  attribute assignments are not re-emitted as a "class header" chunk yet.
  The class name is still preserved via `parent_class` on each method.
- Nested classes inside an oversized class are skipped during splitting.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

_PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_PY_LANGUAGE)

_DEF_TYPES = ("function_definition", "class_definition")

DEFAULT_MAX_CLASS_LINES = 100


@dataclass
class CodeChunk:
    file_path: str
    symbol_name: str
    symbol_kind: str  # "function" | "class" | "method"
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
    """Parse `source` as Python and return chunks.

    Top-level functions and small classes become one chunk. Classes whose
    line span exceeds `max_class_lines` become one chunk per method.
    """
    source_bytes = source.encode("utf-8") if isinstance(source, str) else source
    tree = _PARSER.parse(source_bytes)

    chunks: list[CodeChunk] = []
    for node in tree.root_node.children:
        chunks.extend(_node_to_chunks(node, source_bytes, file_path, max_class_lines))
    return chunks


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

    chunk = CodeChunk(
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
        return [chunk]

    # Class: split if oversized
    if chunk.end_line - chunk.start_line + 1 <= max_class_lines:
        return [chunk]
    return _split_class_into_methods(target, source_bytes, file_path, symbol_name)


def _split_class_into_methods(
    class_node: Node, source_bytes: bytes, file_path: str, parent_class: str
) -> list[CodeChunk]:
    body = class_node.child_by_field_name("body")
    if body is None:
        return []

    chunks: list[CodeChunk] = []
    for child in body.children:
        method_target, method_decorators = _unwrap_decorated(child, source_bytes)
        if method_target is None or method_target.type != "function_definition":
            continue
        name_node = method_target.child_by_field_name("name")
        if name_node is None:
            continue
        chunks.append(
            CodeChunk(
                file_path=file_path,
                symbol_name=_slice(source_bytes, name_node),
                symbol_kind="method",
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                code=_slice(source_bytes, child),
                docstring=_extract_docstring(method_target, source_bytes),
                decorators=method_decorators,
                parent_class=parent_class,
            )
        )
    return chunks


def _unwrap_decorated(node: Node, source_bytes: bytes) -> tuple[Node | None, list[str]]:
    """Return (inner_def_node, decorators). For non-decorated nodes, returns (node, [])."""
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
