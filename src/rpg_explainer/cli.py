"""Command-line interface for the RPG Explainer tool."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__


def check_treesitter_library() -> bool:
    """Check if the Tree-sitter library is built."""
    project_root = Path(__file__).parent.parent.parent
    lib_path = project_root / "build" / "languages.so"
    return lib_path.exists()


def print_progress(message: str) -> None:
    """Print a progress message."""
    click.echo(click.style(f">> {message}", fg="cyan"), err=True)


def print_error(message: str) -> None:
    """Print an error message."""
    click.echo(click.style(f"Error: {message}", fg="red"), err=True)


def print_warning(message: str) -> None:
    """Print a warning message."""
    click.echo(click.style(f"Warning: {message}", fg="yellow"), err=True)


@click.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Write the report to a file instead of stdout.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output the raw program index as JSON instead of LLM explanation.",
)
@click.option(
    "--no-llm",
    is_flag=True,
    help="Skip the LLM explanation (useful for testing parsing only).",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="Override the Claude model to use.",
)
@click.version_option(version=__version__)
def main(
    paths: tuple[str, ...],
    output: str | None,
    output_json: bool,
    no_llm: bool,
    model: str | None,
) -> None:
    """Analyze and explain RPG source files.

    Parses one or more RPG source files, extracts structural information,
    and uses Claude LLM to generate a human-readable explanation.

    Examples:

        rpg-explain program.rpgle

        rpg-explain src/module1.rpgle src/module2.rpgle --output report.md

        rpg-explain program.rpgle --json > index.json
    """
    # Check if Tree-sitter library is built
    if not check_treesitter_library():
        print_error("Tree-sitter RPG library not found.")
        print_error("Please build it first:")
        print_error("  cd tree-sitter-rpg && npm install && npx tree-sitter generate")
        print_error("  python build_rpg_language.py")
        sys.exit(1)

    # Import here to avoid issues if tree-sitter isn't installed
    from .analysis import RPGAnalyzer
    from .parser import RPGParser

    # Parse files
    print_progress("Parsing RPG source files...")
    parse_errors: list[tuple[str, str]] = []
    parsed_files = []

    try:
        parser = RPGParser()
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)

    for path in paths:
        try:
            parsed = parser.parse_to_parsed_file(path)
            parsed_files.append(parsed)
            if parsed.has_errors:
                parse_errors.append((path, "Parse tree contains errors"))
        except Exception as e:
            parse_errors.append((path, str(e)))
            print_warning(f"Failed to parse {path}: {e}")

    if not parsed_files:
        print_error("No files were successfully parsed.")
        sys.exit(1)

    # Analyze
    print_progress("Analyzing dependencies and structure...")
    analyzer = RPGAnalyzer()
    index = analyzer.build_index(parsed_files)

    # Add parse errors to output if any
    if parse_errors:
        print_warning(f"{len(parse_errors)} file(s) had parse issues.")

    # Output JSON if requested
    if output_json:
        result = index.to_json(indent=2)
        if output:
            Path(output).write_text(result)
            print_progress(f"JSON index written to {output}")
        else:
            click.echo(result)
        return

    # Skip LLM if requested
    if no_llm:
        # Just output basic stats
        total_procs = sum(len(f.procedures) for f in index.files)
        total_files = sum(len(f.file_defs) for f in index.files)
        click.echo(f"Analyzed {len(index.files)} source file(s)")
        click.echo(f"  Procedures: {total_procs}")
        click.echo(f"  File definitions: {total_files}")

        if parse_errors:
            click.echo("\nParse Issues:")
            for path, error in parse_errors:
                click.echo(f"  - {path}: {error}")
        return

    # Generate LLM explanation
    print_progress("Calling Claude LLM for explanation...")

    # Collect source files for the LLM
    source_files = {pf.path: pf.source for pf in parsed_files}

    try:
        from .llm_client import RPGExplainerLLM

        llm = RPGExplainerLLM(model=model)
        report = llm.explain_program(index, source_files=source_files)
    except ValueError as e:
        print_error(str(e))
        sys.exit(1)
    except Exception as e:
        print_error(f"LLM call failed: {e}")
        sys.exit(1)

    # Add parse issues section if any
    if parse_errors:
        report += "\n\n## Parse Issues\n\n"
        report += "The following files had parsing issues:\n\n"
        for path, error in parse_errors:
            report += f"- **{path}**: {error}\n"

    # Output report
    if output:
        Path(output).write_text(report)
        print_progress(f"Report written to {output}")
    else:
        click.echo(report)


if __name__ == "__main__":
    main()
