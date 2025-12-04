# RPG Explainer

A CLI tool that parses IBM ILE RPG (RPGLE) free-form programs using Tree-sitter and generates human-readable architecture reports using Claude LLM.

## Features

- **Tree-sitter parsing**: Uses a custom RPG grammar to parse free-form RPGLE code
- **Static analysis**: Extracts procedures, subroutines, file definitions, data structures, and call graphs
- **LLM-powered explanations**: Uses Claude Opus 4.5 via LangChain to generate detailed program explanations
- **Dependency detection**: Identifies internal and external calls, file usage, and resource dependencies

## Installation

### Prerequisites

- Python 3.10+
- Node.js (for building the Tree-sitter grammar)
- An Anthropic API key

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd rpg-explainer
   ```

2. Build the Tree-sitter RPG grammar:
   ```bash
   cd tree-sitter-rpg
   npm install
   npx tree-sitter generate
   cd ..
   python build_rpg_language.py
   ```

3. Install the Python package:
   ```bash
   pip install -e .
   ```

4. Set your Anthropic API key:
   ```bash
   export ANTHROPIC_API_KEY=your-api-key-here
   ```

## Usage

Analyze one or more RPG source files:

```bash
rpg-explain path/to/program.rpgle
```

Analyze multiple files:

```bash
rpg-explain src/module1.rpgle src/module2.rpgle
```

Save the report to a file:

```bash
rpg-explain program.rpgle --output report.md
```

## Project Structure

```
rpg-explainer/
├── src/
│   └── rpg_explainer/
│       ├── __init__.py
│       ├── parser.py         # Tree-sitter integration + AST index building
│       ├── analysis.py       # Higher-level analysis helpers
│       ├── llm_client.py     # LangChain + Claude integration
│       ├── cli.py            # CLI entry point
│       └── prompts.py        # LLM prompt templates
├── tree-sitter-rpg/          # Tree-sitter RPG grammar
│   ├── grammar.js
│   └── package.json
├── tests/
│   └── test_basic_analysis.py
├── build/                    # Compiled Tree-sitter library
├── build_rpg_language.py     # Script to compile the grammar
├── main.py                   # Alternative entry point
├── pyproject.toml
└── README.md
```

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (required for LLM features)
- `RPG_TREESITTER_LIB`: Custom path to the compiled Tree-sitter library (optional, defaults to `build/languages.so`)

## License

MIT
