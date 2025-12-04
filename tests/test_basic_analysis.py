"""Basic tests for RPG parsing and analysis.

These tests verify that the parser and analyzer work correctly
without making any LLM API calls.
"""

import pytest


# Sample RPG free-form code for testing
SAMPLE_RPG_CODE = """
**FREE
// Sample RPG program for testing

ctl-opt option(*srcstmt:*nodebugio);

dcl-f CUSTFILE usage(*update) extfile('CUSTLIB/CUSTFILE');
dcl-f ORDRFILE usage(*input);
dcl-f RPTFILE printer;

dcl-c MAX_ITEMS 100;
dcl-c PI 3.14159;

dcl-ds CustomerRec qualified;
  dcl-subf id packed(7);
  dcl-subf name char(50);
  dcl-subf balance packed(11:2);
end-ds;

dcl-pr UpdateInventory extpgm('UPDTINV');
  dcl-parm itemNo char(15) const;
  dcl-parm quantity packed(5) const;
end-pr;

dcl-proc ProcessOrder export;
  dcl-pi *n ind;
    dcl-parm orderNum char(10) const;
    dcl-parm custId packed(7) const;
  end-pi;

  dcl-s result ind;
  dcl-s itemCount int(10);

  result = *off;
  itemCount = 0;

  // Read customer
  chain custId CUSTFILE;
  if %found(CUSTFILE);
    // Process order items
    dow itemCount < MAX_ITEMS;
      read ORDRFILE;
      if %eof(ORDRFILE);
        leave;
      endif;
      itemCount = itemCount + 1;
      UpdateInventory(%trim(orderNum) : itemCount);
    enddo;
    result = *on;
  endif;

  return result;
end-proc;

dcl-proc CalculateTotal;
  dcl-pi *n packed(11:2);
    dcl-parm qty packed(5) const;
    dcl-parm price packed(7:2) const;
  end-pi;

  return qty * price;
end-proc;

dcl-proc PrintReport;
  dcl-pi *n;
  end-pi;

  write RPTFILE;
  ProcessOrder('ORD001' : 12345);

end-proc;
"""


@pytest.fixture
def sample_rpg_file(tmp_path):
    """Create a temporary RPG file for testing."""
    rpg_file = tmp_path / "sample.rpgle"
    rpg_file.write_text(SAMPLE_RPG_CODE)
    return rpg_file


class TestRPGParser:
    """Tests for the RPG parser."""

    @pytest.fixture(autouse=True)
    def check_treesitter(self):
        """Skip tests if Tree-sitter library is not built."""
        from pathlib import Path

        lib_path = Path(__file__).parent.parent / "build" / "languages.so"
        if not lib_path.exists():
            pytest.skip(
                "Tree-sitter library not built. Run 'python build_rpg_language.py' first."
            )

    def test_parse_code(self, sample_rpg_file):
        """Test parsing RPG code from a string."""
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        tree = parser.parse_code(SAMPLE_RPG_CODE)

        assert tree is not None
        assert tree.root_node is not None
        assert tree.root_node.type == "source_file"

    def test_parse_file(self, sample_rpg_file):
        """Test parsing RPG code from a file."""
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        tree = parser.parse_file(sample_rpg_file)

        assert tree is not None
        assert tree.root_node.type == "source_file"

    def test_parse_to_parsed_file(self, sample_rpg_file):
        """Test parsing to a ParsedFile object."""
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        parsed = parser.parse_to_parsed_file(sample_rpg_file)

        assert parsed.path == str(sample_rpg_file)
        assert parsed.source == SAMPLE_RPG_CODE
        assert parsed.tree is not None

    def test_iter_nodes(self, sample_rpg_file):
        """Test iterating over nodes in the parse tree."""
        from rpg_explainer.parser import RPGParser, iter_nodes

        parser = RPGParser()
        tree = parser.parse_code(SAMPLE_RPG_CODE)

        nodes = list(iter_nodes(tree.root_node))
        assert len(nodes) > 0

        # First node should be the root
        first_node, first_parent = nodes[0]
        assert first_node.type == "source_file"
        assert first_parent is None

    def test_find_nodes_by_type(self, sample_rpg_file):
        """Test finding nodes by type."""
        from rpg_explainer.parser import RPGParser, find_nodes_by_type

        parser = RPGParser()
        tree = parser.parse_code(SAMPLE_RPG_CODE)

        # Should find procedure definitions
        procs = list(find_nodes_by_type(tree.root_node, "procedure_definition"))
        assert len(procs) >= 1

        # Should find file definitions
        files = list(find_nodes_by_type(tree.root_node, "file_definition"))
        assert len(files) >= 1


class TestRPGAnalyzer:
    """Tests for the RPG analyzer."""

    @pytest.fixture(autouse=True)
    def check_treesitter(self):
        """Skip tests if Tree-sitter library is not built."""
        from pathlib import Path

        lib_path = Path(__file__).parent.parent / "build" / "languages.so"
        if not lib_path.exists():
            pytest.skip(
                "Tree-sitter library not built. Run 'python build_rpg_language.py' first."
            )

    def test_build_index(self, sample_rpg_file):
        """Test building a program index."""
        from rpg_explainer.analysis import RPGAnalyzer
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        parsed = parser.parse_to_parsed_file(sample_rpg_file)

        analyzer = RPGAnalyzer()
        index = analyzer.build_index([parsed])

        assert len(index.files) == 1
        rpg_file = index.files[0]
        assert rpg_file.path == str(sample_rpg_file)

    def test_detects_file_definitions(self, sample_rpg_file):
        """Test that file definitions (DCL-F) are detected."""
        from rpg_explainer.analysis import RPGAnalyzer
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        parsed = parser.parse_to_parsed_file(sample_rpg_file)

        analyzer = RPGAnalyzer()
        index = analyzer.build_index([parsed])

        rpg_file = index.files[0]

        # Should detect at least one file definition
        assert len(rpg_file.file_defs) >= 1

        # Check for specific files
        file_names = {f.name for f in rpg_file.file_defs}
        assert "CUSTFILE" in file_names or "custfile" in file_names.union(
            {n.lower() for n in file_names}
        )

    def test_detects_procedures(self, sample_rpg_file):
        """Test that procedures are detected."""
        from rpg_explainer.analysis import RPGAnalyzer
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        parsed = parser.parse_to_parsed_file(sample_rpg_file)

        analyzer = RPGAnalyzer()
        index = analyzer.build_index([parsed])

        rpg_file = index.files[0]

        # Should detect at least one procedure
        assert len(rpg_file.procedures) >= 1

        # Check for specific procedures
        proc_names = {p.name for p in rpg_file.procedures}
        assert any(
            "ProcessOrder" in n or "processorder" in n.lower() for n in proc_names
        )

    def test_detects_calls(self, sample_rpg_file):
        """Test that internal and external calls are detected."""
        from rpg_explainer.analysis import RPGAnalyzer
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        parsed = parser.parse_to_parsed_file(sample_rpg_file)

        analyzer = RPGAnalyzer()
        index = analyzer.build_index([parsed])

        rpg_file = index.files[0]

        # Check that some procedure has calls
        all_internal = []
        all_external = []
        for proc in rpg_file.procedures:
            all_internal.extend(proc.calls_internal)
            all_external.extend(proc.calls_external)

        # Should detect at least one internal or external call
        assert len(all_internal) + len(all_external) >= 1

    def test_detects_constants(self, sample_rpg_file):
        """Test that constants are detected."""
        from rpg_explainer.analysis import RPGAnalyzer
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        parsed = parser.parse_to_parsed_file(sample_rpg_file)

        analyzer = RPGAnalyzer()
        index = analyzer.build_index([parsed])

        rpg_file = index.files[0]

        # Should detect at least one constant
        assert len(rpg_file.constants) >= 1

        const_names = {c.name for c in rpg_file.constants}
        assert any("MAX_ITEMS" in n or "max_items" in n.lower() for n in const_names)

    def test_detects_data_structures(self, sample_rpg_file):
        """Test that data structures are detected."""
        from rpg_explainer.analysis import RPGAnalyzer
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        parsed = parser.parse_to_parsed_file(sample_rpg_file)

        analyzer = RPGAnalyzer()
        index = analyzer.build_index([parsed])

        rpg_file = index.files[0]

        # Should detect at least one data structure
        assert len(rpg_file.data_structures) >= 1

    def test_index_to_json(self, sample_rpg_file):
        """Test that the index can be serialized to JSON."""
        import json

        from rpg_explainer.analysis import RPGAnalyzer
        from rpg_explainer.parser import RPGParser

        parser = RPGParser()
        parsed = parser.parse_to_parsed_file(sample_rpg_file)

        analyzer = RPGAnalyzer()
        index = analyzer.build_index([parsed])

        # Should serialize without errors
        json_str = index.to_json()
        assert json_str is not None

        # Should be valid JSON
        data = json.loads(json_str)
        assert "files" in data
        assert len(data["files"]) == 1
