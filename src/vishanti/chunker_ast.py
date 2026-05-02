"""AST-aware chunker for Python source files.

Emits one chunk per top-level function or class. Decorators are included in the
chunk span. Docstrings are extracted as a separate field for retrieval-time
weighting later. Methods stay inside their parent class chunk in this version;
splitting oversized classes is a follow-up.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

_PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_PY_LANGUAGE)

_DEF_TYPES = ("function_definition", "class_definition")


@dataclass
class CodeChunk:
    file_path: str
    symbol_name: str
    symbol_kind: str  # "function" or "class"
    start_line: int  # 1-indexed, inclusive (includes decorator lines)
    end_line: int  # 1-indexed, inclusive
    code: str
    docstring: str | None = None
    parent_class: str | None = None
    decorators: list[str] = field(default_factory=list)


def chunk_python_file(file_path: str, source: str | bytes) -> list[CodeChunk]:
    """Parse `source` as Python and return one chunk per top-level def/class."""
    source_bytes = source.encode("utf-8") if isinstance(source, str) else source
    tree = _PARSER.parse(source_bytes)

    chunks: list[CodeChunk] = []
    for node in tree.root_node.children:
        chunk = _node_to_chunk(node, source_bytes, file_path)
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def _node_to_chunk(node: Node, source_bytes: bytes, file_path: str) -> CodeChunk | None:
    decorators: list[str] = []
    target = node

    if node.type == "decorated_definition":
        for child in node.children:
            if child.type == "decorator":
                deco_text = _slice(source_bytes, child).lstrip("@").strip()
                decorators.append(deco_text)
            elif child.type in _DEF_TYPES:
                target = child

    if target.type not in _DEF_TYPES:
        return None

    name_node = target.child_by_field_name("name")
    if name_node is None:
        return None

    return CodeChunk(
        file_path=file_path,
        symbol_name=_slice(source_bytes, name_node),
        symbol_kind="function" if target.type == "function_definition" else "class",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code=_slice(source_bytes, node),
        docstring=_extract_docstring(target, source_bytes),
        decorators=decorators,
    )


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
        if child.type in ("comment",):
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
