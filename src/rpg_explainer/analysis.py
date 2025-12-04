"""Static analysis for RPG programs - extracts procedures, calls, and resources."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from .parser import ParsedFile, find_nodes_by_type, iter_nodes, node_text


if TYPE_CHECKING:
    from tree_sitter import Node


@dataclass
class RPGParameter:
    """Represents a procedure/subroutine parameter."""

    name: str
    type: str | None = None
    attributes: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class RPGFileDef:
    """Represents a DCL-F file definition."""

    name: str
    keywords: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class RPGConstant:
    """Represents a DCL-C constant definition."""

    name: str
    value_preview: str = ""


@dataclass
class RPGDataStructure:
    """Represents a DCL-DS data structure definition."""

    name: str
    subfields: list[str] = field(default_factory=list)


@dataclass
class RPGSubroutine:
    """Represents a BEGSR subroutine."""

    name: str
    calls_internal: list[str] = field(default_factory=list)
    calls_external: list[str] = field(default_factory=list)
    uses_files: list[str] = field(default_factory=list)


@dataclass
class RPGProcedure:
    """Represents a DCL-PROC procedure."""

    name: str
    params: list[RPGParameter] = field(default_factory=list)
    returns: str | None = None
    calls_internal: list[str] = field(default_factory=list)
    calls_external: list[str] = field(default_factory=list)
    uses_files: list[str] = field(default_factory=list)


@dataclass
class RPGFixedSpec:
    """Represents a fixed-form specification line."""

    spec_type: str  # H, F, D, C, P, or *
    raw_line: str
    # Parsed fields (populated by spec-specific parsing)
    name: str | None = None
    keywords: dict[str, str] = field(default_factory=dict)


@dataclass
class RPGFile:
    """Represents a parsed RPG source file with extracted information."""

    path: str
    procedures: list[RPGProcedure] = field(default_factory=list)
    subroutines: list[RPGSubroutine] = field(default_factory=list)
    file_defs: list[RPGFileDef] = field(default_factory=list)
    constants: list[RPGConstant] = field(default_factory=list)
    data_structures: list[RPGDataStructure] = field(default_factory=list)
    prototypes: list[str] = field(default_factory=list)
    # Fixed-form specs (for programs with fixed-form code)
    fixed_h_specs: list[RPGFixedSpec] = field(default_factory=list)
    fixed_f_specs: list[RPGFixedSpec] = field(default_factory=list)
    fixed_d_specs: list[RPGFixedSpec] = field(default_factory=list)
    fixed_c_specs: list[RPGFixedSpec] = field(default_factory=list)
    fixed_p_specs: list[RPGFixedSpec] = field(default_factory=list)


@dataclass
class ProgramIndex:
    """Index of all analyzed RPG files."""

    files: list[RPGFile] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to a dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def _get_identifier_name(node: Node, source: str) -> str | None:
    """Extract the identifier name from a node."""
    # Check if the node itself is an identifier
    if node.type in ("identifier", "special_identifier"):
        return node_text(node, source)

    # Look for a 'name' field
    name_node = node.child_by_field_name("name")
    if name_node:
        return node_text(name_node, source)

    # Look for first identifier child
    for child in node.children:
        if child.type in ("identifier", "special_identifier", "identifier_or_star"):
            if child.type == "identifier_or_star":
                # Recurse into identifier_or_star
                return _get_identifier_name(child, source)
            return node_text(child, source)

    return None


def _extract_type_spec(node: Node, source: str) -> str | None:
    """Extract type specification from a type_spec node."""
    for child, _ in iter_nodes(node):
        if child.type == "type_spec":
            return node_text(child, source)
    return None


def _extract_attributes(node: Node, source: str) -> dict[str, list[str]]:
    """Extract keyword attributes from a node."""
    attrs: dict[str, list[str]] = {}

    for child in node.children:
        if child.type == "attribute":
            attr_name = None
            attr_args: list[str] = []

            for attr_child in child.children:
                if attr_child.type in ("identifier", "special_identifier"):
                    if attr_name is None:
                        attr_name = node_text(attr_child, source).lower()
                elif attr_child.type not in ("(", ")", ",", ":"):
                    # Collect arguments
                    arg_text = node_text(attr_child, source)
                    if arg_text:
                        attr_args.append(arg_text)

            if attr_name:
                attrs[attr_name] = attr_args

    return attrs


def _extract_parameters(proc_node: Node, source: str) -> list[RPGParameter]:
    """Extract parameters from a procedure interface."""
    params: list[RPGParameter] = []

    for pi_node in find_nodes_by_type(proc_node, "procedure_interface"):
        for param_node in find_nodes_by_type(pi_node, "parameter_definition"):
            name = _get_identifier_name(param_node, source)
            if name:
                type_spec = _extract_type_spec(param_node, source)
                attrs = _extract_attributes(param_node, source)
                params.append(RPGParameter(name=name, type=type_spec, attributes=attrs))

    return params


def _extract_return_type(proc_node: Node, source: str) -> str | None:
    """Extract return type from a procedure interface."""
    for pi_node in find_nodes_by_type(proc_node, "procedure_interface"):
        for child in pi_node.children:
            if child.type == "type_spec":
                return node_text(child, source)
    return None


def _find_call_targets(node: Node, source: str) -> Iterator[str]:
    """Find all call targets (procedure/function names) in a node.

    In the simplified grammar, calls are represented as identifier followed
    by paren_group. We look for this pattern.
    """
    prev_node: Node | None = None

    for child, _ in iter_nodes(node):
        if child.type == "paren_group" and prev_node is not None:
            # Check if the previous node was an identifier (potential call target)
            if prev_node.type == "identifier":
                name = node_text(prev_node, source)
                # Skip built-in functions (they start with %)
                if not name.startswith("%"):
                    yield name
        prev_node = child


def _find_file_references(node: Node, source: str, file_names: set[str]) -> list[str]:
    """Find references to file names within a node."""
    refs: list[str] = []
    file_names_lower = {f.lower() for f in file_names}

    for child, _ in iter_nodes(node):
        if child.type == "identifier":
            name = node_text(child, source)
            if name.lower() in file_names_lower:
                if name not in refs:
                    refs.append(name)

    return refs


class RPGAnalyzer:
    """Analyzer for extracting structured information from parsed RPG files."""

    def build_index(self, parsed_files: list[ParsedFile]) -> ProgramIndex:
        """Build a program index from parsed files.

        Args:
            parsed_files: List of ParsedFile objects to analyze.

        Returns:
            A ProgramIndex containing structured information about all files.
        """
        index = ProgramIndex()

        for parsed in parsed_files:
            rpg_file = self._analyze_file(parsed)
            index.files.append(rpg_file)

        # Second pass: categorize calls as internal or external
        self._categorize_calls(index)

        return index

    def _analyze_file(self, parsed: ParsedFile) -> RPGFile:
        """Analyze a single parsed file."""
        rpg_file = RPGFile(path=parsed.path)
        source = parsed.source
        root = parsed.root_node

        # Extract file definitions first (we need these for reference tracking)
        for file_def_node in find_nodes_by_type(root, "file_definition"):
            file_def = self._extract_file_def(file_def_node, source)
            if file_def:
                rpg_file.file_defs.append(file_def)

        file_names = {f.name for f in rpg_file.file_defs}

        # Extract constants
        for const_node in find_nodes_by_type(root, "constant_definition"):
            const = self._extract_constant(const_node, source)
            if const:
                rpg_file.constants.append(const)

        # Extract data structures
        for ds_node in find_nodes_by_type(root, "data_structure_definition"):
            ds = self._extract_data_structure(ds_node, source)
            if ds:
                rpg_file.data_structures.append(ds)

        # Extract procedure prototypes (for external call detection)
        for proto_node in find_nodes_by_type(root, "procedure_prototype"):
            name = _get_identifier_name(proto_node, source)
            if name:
                rpg_file.prototypes.append(name)

        # Extract procedures
        for proc_node in find_nodes_by_type(root, "procedure_definition"):
            proc = self._extract_procedure(proc_node, source, file_names)
            if proc:
                rpg_file.procedures.append(proc)

        # Extract fixed-form specs
        self._extract_fixed_form_specs(rpg_file, root, source)

        return rpg_file

    def _extract_fixed_form_specs(
        self, rpg_file: RPGFile, root: Node, source: str
    ) -> None:
        """Extract fixed-form specification lines."""
        # H specs (Header/Control)
        for node in find_nodes_by_type(root, "fixed_h_spec"):
            spec = self._parse_fixed_spec("H", node, source)
            if spec:
                rpg_file.fixed_h_specs.append(spec)

        # F specs (File)
        for node in find_nodes_by_type(root, "fixed_f_spec"):
            spec = self._parse_fixed_f_spec(node, source)
            if spec:
                rpg_file.fixed_f_specs.append(spec)
                # Also add to file_defs for consistency
                if spec.name:
                    rpg_file.file_defs.append(
                        RPGFileDef(name=spec.name, keywords=spec.keywords)
                    )

        # D specs (Definition)
        for node in find_nodes_by_type(root, "fixed_d_spec"):
            spec = self._parse_fixed_d_spec(node, source)
            if spec:
                rpg_file.fixed_d_specs.append(spec)

        # C specs (Calculation)
        for node in find_nodes_by_type(root, "fixed_c_spec"):
            spec = self._parse_fixed_c_spec(node, source)
            if spec:
                rpg_file.fixed_c_specs.append(spec)

        # P specs (Procedure)
        for node in find_nodes_by_type(root, "fixed_p_spec"):
            spec = self._parse_fixed_spec("P", node, source)
            if spec:
                rpg_file.fixed_p_specs.append(spec)

    def _parse_fixed_spec(
        self, spec_type: str, node: Node, source: str
    ) -> RPGFixedSpec | None:
        """Parse a basic fixed-form spec line."""
        raw_line = node_text(node, source)
        if not raw_line:
            return None
        return RPGFixedSpec(spec_type=spec_type, raw_line=raw_line)

    def _parse_fixed_f_spec(self, node: Node, source: str) -> RPGFixedSpec | None:
        """Parse a fixed-form F (File) specification.

        F spec layout (columns 1-80):
        - Col 6: F (spec type)
        - Col 7-16: File name (10 chars)
        - Col 17: File type (I/O/U/C)
        - Col 18: File designation
        - Col 19-20: End of file (E or blank)
        - Col 21: File addition (A or blank)
        - Col 22: Sequence (A/D/blank)
        - Col 23-27: Record length
        - Col 28-32: Limits processing
        - Col 33-34: Length of key or record address
        - Col 35: Record address type
        - Col 36-42: File organization/device
        - Col 43-80: Keywords
        """
        raw_line = node_text(node, source)
        if not raw_line or len(raw_line) < 17:
            return None

        # Extract file name (columns 7-16, 0-indexed: 6-15)
        name = raw_line[6:16].strip() if len(raw_line) > 6 else None

        # Skip comment lines
        if name and name.startswith("*"):
            return RPGFixedSpec(spec_type="F", raw_line=raw_line, name=None)

        return RPGFixedSpec(spec_type="F", raw_line=raw_line, name=name)

    def _parse_fixed_d_spec(self, node: Node, source: str) -> RPGFixedSpec | None:
        """Parse a fixed-form D (Definition) specification.

        D spec layout (columns 1-80):
        - Col 6: D (spec type)
        - Col 7-21: Name (15 chars)
        - Col 22: External description (E or blank)
        - Col 23: Data structure type (DS, S, C, etc.)
        - Col 24-25: Definition type
        - Col 26-32: From position
        - Col 33-39: To position / length
        - Col 40-41: Data type
        - Col 42-44: Decimal positions
        - Col 45-80: Keywords
        """
        raw_line = node_text(node, source)
        if not raw_line or len(raw_line) < 22:
            return None

        # Extract name (columns 7-21, 0-indexed: 6-20)
        name = raw_line[6:21].strip() if len(raw_line) > 6 else None

        # Skip comment lines
        if name and name.startswith("*"):
            return RPGFixedSpec(spec_type="D", raw_line=raw_line, name=None)

        return RPGFixedSpec(spec_type="D", raw_line=raw_line, name=name)

    def _parse_fixed_c_spec(self, node: Node, source: str) -> RPGFixedSpec | None:
        """Parse a fixed-form C (Calculation) specification.

        C spec layout (columns 1-80):
        - Col 6: C (spec type)
        - Col 7-8: Control level (01-99, LR, etc.)
        - Col 9-11: Indicators
        - Col 12-25: Factor 1 (14 chars)
        - Col 26-35: Operation code (10 chars)
        - Col 36-49: Factor 2 (14 chars)
        - Col 50-63: Result field (14 chars)
        - Col 64-68: Field length
        - Col 69-70: Decimal positions
        - Col 71-76: Resulting indicators
        - Col 77-80: Comments
        """
        raw_line = node_text(node, source)
        if not raw_line or len(raw_line) < 7:
            return None

        # Skip comment lines (C* in column 6-7)
        if len(raw_line) > 6 and raw_line[6] == "*":
            return RPGFixedSpec(spec_type="C", raw_line=raw_line, name=None)

        # Extract operation code (columns 26-35, 0-indexed: 25-34)
        opcode = ""
        if len(raw_line) > 25:
            opcode = (
                raw_line[25:35].strip().upper()
                if len(raw_line) > 34
                else raw_line[25:].strip().upper()
            )

        # For lines without explicit opcode, check Factor 2 for operations like DSPLY
        # Factor 2 is columns 36-49 (0-indexed: 35-48)
        factor2 = ""
        if len(raw_line) > 35:
            factor2 = (
                raw_line[35:49].strip() if len(raw_line) > 48 else raw_line[35:].strip()
            )

        # If no opcode but factor2 contains something like 'dsply', it's likely the operation
        if not opcode and factor2:
            # Check if factor2 looks like an operation (all alpha)
            if factor2.isalpha():
                opcode = factor2.upper()

        # The "name" for C specs is the operation code
        return RPGFixedSpec(
            spec_type="C",
            raw_line=raw_line,
            name=opcode if opcode else None,
            keywords={"opcode": opcode} if opcode else {},
        )

    def _extract_file_def(self, node: Node, source: str) -> RPGFileDef | None:
        """Extract a file definition."""
        name = _get_identifier_name(node, source)
        if not name:
            return None

        keywords = _extract_attributes(node, source)
        return RPGFileDef(name=name, keywords=keywords)

    def _extract_constant(self, node: Node, source: str) -> RPGConstant | None:
        """Extract a constant definition."""
        name = _get_identifier_name(node, source)
        if not name:
            return None

        # Get the value field
        value_node = node.child_by_field_name("value")
        value_preview = ""
        if value_node:
            value_preview = node_text(value_node, source)[:50]

        return RPGConstant(name=name, value_preview=value_preview)

    def _extract_data_structure(
        self, node: Node, source: str
    ) -> RPGDataStructure | None:
        """Extract a data structure definition."""
        name = _get_identifier_name(node, source)
        if not name:
            return None

        subfields: list[str] = []
        for subfield_node in find_nodes_by_type(node, "subfield_definition"):
            subfield_name = _get_identifier_name(subfield_node, source)
            if subfield_name:
                subfields.append(subfield_name)

        return RPGDataStructure(name=name, subfields=subfields)

    def _extract_procedure(
        self, node: Node, source: str, file_names: set[str]
    ) -> RPGProcedure | None:
        """Extract a procedure definition."""
        name = _get_identifier_name(node, source)
        if not name:
            return None

        params = _extract_parameters(node, source)
        returns = _extract_return_type(node, source)

        # Find all call targets
        call_targets = list(_find_call_targets(node, source))

        # Find file references
        uses_files = _find_file_references(node, source, file_names)

        return RPGProcedure(
            name=name,
            params=params,
            returns=returns,
            calls_internal=call_targets,  # Will be categorized later
            calls_external=[],
            uses_files=uses_files,
        )

    def _categorize_calls(self, index: ProgramIndex) -> None:
        """Categorize calls as internal or external based on defined procedures."""
        # Collect all procedure names and prototypes
        all_procs: set[str] = set()
        external_procs: set[str] = set()

        for rpg_file in index.files:
            for proc in rpg_file.procedures:
                all_procs.add(proc.name.lower())
            for proto in rpg_file.prototypes:
                external_procs.add(proto.lower())

        # Now categorize calls
        for rpg_file in index.files:
            for proc in rpg_file.procedures:
                internal: list[str] = []
                external: list[str] = []

                for call in proc.calls_internal:
                    call_lower = call.lower()
                    if call_lower in external_procs:
                        external.append(call)
                    elif call_lower in all_procs:
                        internal.append(call)
                    else:
                        # Unknown - treat as external
                        external.append(call)

                proc.calls_internal = internal
                proc.calls_external = external
