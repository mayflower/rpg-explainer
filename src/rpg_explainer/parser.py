"""Tree-sitter integration for parsing RPG source files."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from tree_sitter import Language, Node, Parser, Tree


# Known node type names from the RPG grammar
NODE_TYPES = {
    # Top-level
    "source_file",
    "top_level_item",
    # Statements
    "statement",
    "expression_statement",
    "ctl_opt",
    "preprocessor_directive",
    # Definitions
    "definition",
    "dcl_s",
    "constant_definition",
    "data_structure_definition",
    "subfield_definition",
    "file_definition",
    "procedure_prototype",
    "procedure_interface",
    "parameter_definition",
    "type_spec",
    "attribute",
    # Procedures
    "procedure_definition",
    # Control flow
    "if_statement",
    "elseif_clause",
    "else_clause",
    "select_statement",
    "when_clause",
    "other_clause",
    "loop_statement",
    "dow_loop",
    "dou_loop",
    "do_loop",
    "for_loop",
    "monitor_statement",
    "on_error_clause",
    "return_statement",
    # Expressions
    "expression",
    "logical_or_expression",
    "logical_and_expression",
    "equality_expression",
    "relational_expression",
    "additive_expression",
    "multiplicative_expression",
    "unary_expression",
    "call_expression",
    "primary_expression",
    "parenthesized_expression",
    "qualified_identifier",
    "simple_identifier",
    # Tokens
    "identifier",
    "identifier_or_star",
    "special_identifier",
    "builtin_function",
    "number_literal",
    "string_literal",
    "comment",
}


@dataclass
class ParsedFile:
    """Represents a parsed RPG source file."""

    path: str
    tree: Tree
    source: str

    @property
    def root_node(self) -> Node:
        """Return the root node of the parse tree."""
        return self.tree.root_node

    @property
    def has_errors(self) -> bool:
        """Check if the parse tree contains any errors."""
        return self.tree.root_node.has_error


def node_text(node: Node, source: str | bytes) -> str:
    """Extract the text content of a node."""
    if isinstance(source, bytes):
        return source[node.start_byte : node.end_byte].decode("utf-8")
    return source[node.start_byte : node.end_byte]


def iter_nodes(
    node: Node, parent: Node | None = None
) -> Iterator[tuple[Node, Node | None]]:
    """Iterate over all nodes in the tree in pre-order.

    Yields:
        Tuples of (node, parent) for each node in the tree.
    """
    yield (node, parent)
    for child in node.children:
        yield from iter_nodes(child, node)


def find_nodes_by_type(node: Node, node_type: str) -> Iterator[Node]:
    """Find all descendant nodes of a specific type."""
    for child, _ in iter_nodes(node):
        if child.type == node_type:
            yield child


class RPGParser:
    """Parser for RPG source files using Tree-sitter."""

    def __init__(self, library_path: str | None = None):
        """Initialize the RPG parser.

        Args:
            library_path: Path to the compiled Tree-sitter library.
                Defaults to the RPG_TREESITTER_LIB env var or 'build/languages.so'.
        """
        from tree_sitter import Language, Parser

        if library_path is None:
            library_path = os.environ.get("RPG_TREESITTER_LIB")

        if library_path is None:
            # Default to build/languages.so relative to the project root
            project_root = Path(__file__).parent.parent.parent
            library_path = str(project_root / "build" / "languages.so")

        if not Path(library_path).exists():
            raise FileNotFoundError(
                f"Tree-sitter library not found: {library_path}\n"
                "Run 'python build_rpg_language.py' to build it."
            )

        self._language: Language = Language(library_path, "rpg")
        self._parser: Parser = Parser()
        self._parser.set_language(self._language)

    @property
    def language(self) -> Language:
        """Return the Tree-sitter language object."""
        return self._language

    @property
    def parser(self) -> Parser:
        """Return the Tree-sitter parser object."""
        return self._parser

    def parse_code(self, source: str, path: str | None = None) -> Tree:
        """Parse RPG source code.

        Args:
            source: The RPG source code as a string.
            path: Optional path to associate with the parse tree.

        Returns:
            The Tree-sitter parse tree.
        """
        return self._parser.parse(source.encode("utf-8"))

    def parse_file(self, path: str | Path) -> Tree:
        """Parse an RPG source file.

        Args:
            path: Path to the RPG source file.

        Returns:
            The Tree-sitter parse tree.
        """
        path = Path(path)
        source = path.read_text(encoding="utf-8")
        return self.parse_code(source, str(path))

    def parse_to_parsed_file(self, path: str | Path) -> ParsedFile:
        """Parse an RPG source file and return a ParsedFile object.

        Args:
            path: Path to the RPG source file.

        Returns:
            A ParsedFile containing the tree and source.
        """
        path = Path(path)
        source = path.read_text(encoding="utf-8")
        tree = self.parse_code(source, str(path))
        return ParsedFile(path=str(path), tree=tree, source=source)


def parse_files(
    paths: list[str | Path], parser: RPGParser | None = None
) -> list[ParsedFile]:
    """Parse multiple RPG source files.

    Args:
        paths: List of paths to RPG source files.
        parser: Optional RPGParser instance to use. Creates one if not provided.

    Returns:
        List of ParsedFile objects.
    """
    if parser is None:
        parser = RPGParser()

    result: list[ParsedFile] = []
    for path in paths:
        parsed = parser.parse_to_parsed_file(path)
        result.append(parsed)

    return result
