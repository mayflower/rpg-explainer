#!/usr/bin/env python3
"""Build the Tree-sitter RPG language library.

This script compiles the Tree-sitter RPG grammar into a shared library
that can be loaded by the Python tree-sitter bindings.
"""

import sys
from pathlib import Path


def build_language() -> Path:
    """Build the Tree-sitter RPG language library.

    Returns:
        Path to the compiled library.

    Raises:
        RuntimeError: If the build fails.
    """
    try:
        from tree_sitter import Language
    except ImportError:
        print("Error: tree-sitter Python package not installed.", file=sys.stderr)
        print("Install with: pip install tree-sitter", file=sys.stderr)
        sys.exit(1)

    # Determine paths
    script_dir = Path(__file__).parent.resolve()
    grammar_dir = script_dir / "tree-sitter-rpg"
    build_dir = script_dir / "build"
    output_path = build_dir / "languages.so"

    # Check grammar directory exists
    if not grammar_dir.exists():
        print(f"Error: Grammar directory not found: {grammar_dir}", file=sys.stderr)
        print("Make sure tree-sitter-rpg/ exists with grammar.js", file=sys.stderr)
        sys.exit(1)

    grammar_file = grammar_dir / "grammar.js"
    if not grammar_file.exists():
        print(f"Error: grammar.js not found in {grammar_dir}", file=sys.stderr)
        sys.exit(1)

    # Check if tree-sitter generate has been run
    src_dir = grammar_dir / "src"
    parser_c = src_dir / "parser.c"

    if not parser_c.exists():
        print("Tree-sitter parser not generated yet.", file=sys.stderr)
        print("Please run the following commands first:", file=sys.stderr)
        print(f"  cd {grammar_dir}", file=sys.stderr)
        print("  npm install", file=sys.stderr)
        print("  npx tree-sitter generate", file=sys.stderr)
        sys.exit(1)

    # Create build directory
    build_dir.mkdir(exist_ok=True)

    # Build the language library using the new tree-sitter API
    print("Building Tree-sitter RPG language library...")
    print(f"  Grammar: {grammar_dir}")
    print(f"  Output: {output_path}")

    try:
        Language.build_library(str(output_path), [str(grammar_dir)])
        print(f"Successfully built: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error building language library: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    output = build_language()
    print(f"\nLanguage library ready: {output}")
    print("\nYou can now use the RPG parser:")
    print("  from rpg_explainer.parser import RPGParser")
    print("  parser = RPGParser()")


if __name__ == "__main__":
    main()
