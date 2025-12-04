"""Tests for fixed-form RPG parsing and analysis."""

import pytest
from rpg_explainer.analysis import RPGAnalyzer
from rpg_explainer.parser import RPGParser


@pytest.fixture
def parser():
    """Create a parser instance."""
    return RPGParser()


@pytest.fixture
def analyzer():
    """Create an analyzer instance."""
    return RPGAnalyzer()


class TestFixedFormParsing:
    """Tests for parsing fixed-form RPG code."""

    def test_parse_h_spec(self, parser):
        """Test parsing H (Header) specifications."""
        code = "     H option(*nodebugio) datfmt(*iso)"
        tree = parser.parser.parse(bytes(code, "utf-8"))
        root = tree.root_node

        assert root.type == "source_file"
        assert len(root.children) == 1
        assert root.children[0].type == "fixed_h_spec"

    def test_parse_d_spec(self, parser):
        """Test parsing D (Definition) specifications."""
        code = "     D myVar          s             10a"
        tree = parser.parser.parse(bytes(code, "utf-8"))
        root = tree.root_node

        assert root.type == "source_file"
        assert len(root.children) == 1
        assert root.children[0].type == "fixed_d_spec"

    def test_parse_c_spec(self, parser):
        """Test parsing C (Calculation) specifications."""
        code = "     C                   eval      *inlr = *on"
        tree = parser.parser.parse(bytes(code, "utf-8"))
        root = tree.root_node

        assert root.type == "source_file"
        assert len(root.children) == 1
        assert root.children[0].type == "fixed_c_spec"

    def test_parse_comment_line(self, parser):
        """Test parsing fixed-form comment lines."""
        code = "     D* This is a comment"
        tree = parser.parser.parse(bytes(code, "utf-8"))
        root = tree.root_node

        assert root.type == "source_file"
        assert len(root.children) == 1
        # D* is still a D spec line, just a comment variant
        assert root.children[0].type == "fixed_d_spec"

    def test_parse_multiple_specs(self, parser):
        """Test parsing multiple fixed-form specifications."""
        code = """     H option(*nodebugio)
     D myVar          s             10a
     D myVar2         s             20a
     C                   eval      *inlr = *on"""

        tree = parser.parser.parse(bytes(code, "utf-8"))
        root = tree.root_node

        assert root.type == "source_file"
        # Should have 4 specs: 1 H, 2 D, 1 C
        assert len(root.children) == 4

        types = [child.type for child in root.children]
        assert types == ["fixed_h_spec", "fixed_d_spec", "fixed_d_spec", "fixed_c_spec"]


class TestFreeDirective:
    """Tests for **FREE directive handling."""

    def test_parse_free_directive(self, parser):
        """Test that **FREE is recognized."""
        code = """**free
dsply 'Hello';
*inlr = *on;"""

        tree = parser.parser.parse(bytes(code, "utf-8"))
        root = tree.root_node

        assert root.type == "source_file"
        # First child should be the free directive
        assert root.children[0].type == "free_directive"

    def test_mixed_format(self, parser):
        """Test mixed fixed-form and free-form code."""
        code = """     H option(*nodebugio)
     D myVar          s             10a
**FREE
dcl-s anotherVar char(20);
*inlr = *on;"""

        tree = parser.parser.parse(bytes(code, "utf-8"))
        root = tree.root_node

        types = [child.type for child in root.children]

        # First two should be fixed-form
        assert types[0] == "fixed_h_spec"
        assert types[1] == "fixed_d_spec"
        # Then free directive
        assert types[2] == "free_directive"
        # Then free-form code
        assert "variable_definition" in types or "simple_statement" in types


class TestFixedFormAnalysis:
    """Tests for analyzing fixed-form RPG code."""

    def test_analyze_h_spec(self, parser, analyzer):
        """Test analysis of H specifications."""
        code = "     H option(*nodebugio) datfmt(*iso)"

        parsed = parser.parse_to_parsed_file_from_string(code, "test.rpgle")
        index = analyzer.build_index([parsed])

        assert len(index.files) == 1
        assert len(index.files[0].fixed_h_specs) == 1

        h_spec = index.files[0].fixed_h_specs[0]
        assert h_spec.spec_type == "H"
        assert "option" in h_spec.raw_line

    def test_analyze_d_spec_variable(self, parser, analyzer):
        """Test analysis of D specifications for variables."""
        code = "     D myVar          s             10a"

        parsed = parser.parse_to_parsed_file_from_string(code, "test.rpgle")
        index = analyzer.build_index([parsed])

        assert len(index.files[0].fixed_d_specs) == 1

        d_spec = index.files[0].fixed_d_specs[0]
        assert d_spec.spec_type == "D"
        assert d_spec.name == "myVar"

    def test_analyze_c_spec_eval(self, parser, analyzer):
        """Test analysis of C specifications with EVAL operation."""
        code = "     C                   eval      *inlr = *on"

        parsed = parser.parse_to_parsed_file_from_string(code, "test.rpgle")
        index = analyzer.build_index([parsed])

        assert len(index.files[0].fixed_c_specs) == 1

        c_spec = index.files[0].fixed_c_specs[0]
        assert c_spec.spec_type == "C"
        assert c_spec.name == "EVAL"
        assert c_spec.keywords.get("opcode") == "EVAL"

    def test_analyze_c_spec_dsply(self, parser, analyzer):
        """Test analysis of C specifications with DSPLY operation."""
        code = "     C     'Hello'       dsply"

        parsed = parser.parse_to_parsed_file_from_string(code, "test.rpgle")
        index = analyzer.build_index([parsed])

        assert len(index.files[0].fixed_c_specs) == 1

        c_spec = index.files[0].fixed_c_specs[0]
        assert c_spec.spec_type == "C"
        assert c_spec.name == "DSPLY"

    def test_analyze_comment_lines(self, parser, analyzer):
        """Test that comment lines are identified."""
        code = """     D* This is a D comment
     D myVar          s             10a
     C* This is a C comment"""

        parsed = parser.parse_to_parsed_file_from_string(code, "test.rpgle")
        index = analyzer.build_index([parsed])

        # Comments have name = None
        d_specs = index.files[0].fixed_d_specs
        assert len(d_specs) == 2
        assert d_specs[0].name is None  # Comment
        assert d_specs[1].name == "myVar"  # Variable

        c_specs = index.files[0].fixed_c_specs
        assert len(c_specs) == 1
        assert c_specs[0].name is None  # Comment


# Add helper method to parser for testing
def _add_parse_from_string_method():
    """Add parse_to_parsed_file_from_string method to RPGParser for testing."""
    from rpg_explainer.parser import ParsedFile

    def parse_to_parsed_file_from_string(self, source: str, path: str) -> ParsedFile:
        """Parse source code string and return a ParsedFile object."""
        tree = self.parser.parse(bytes(source, "utf-8"))
        return ParsedFile(path=path, tree=tree, source=source)

    RPGParser.parse_to_parsed_file_from_string = parse_to_parsed_file_from_string


# Apply the monkey patch
_add_parse_from_string_method()
