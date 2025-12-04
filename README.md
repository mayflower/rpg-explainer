# RPG Explainer

A CLI tool that parses IBM ILE RPG (RPGLE) programs using Tree-sitter and generates human-readable architecture reports with Mermaid diagrams using Claude LLM.

## Features

- **Tree-sitter parsing**: Uses a custom RPG grammar to parse both **free-form** and **fixed-form** RPGLE code (RPG III/IV)
- **Mixed format support**: Automatically detects `**FREE` directive and handles mixed-format files
- **Static analysis**: Extracts procedures, subroutines, file definitions, data structures, and call graphs
- **LLM-powered explanations**: Uses Claude via LangChain to generate detailed program explanations
- **Mermaid diagrams**: Generates flowcharts, sequence diagrams, ER diagrams, and state diagrams for visualization
- **Dependency detection**: Identifies internal and external calls, file usage, and resource dependencies

## Example Output

The tool generates comprehensive analysis reports including:

- Executive summary
- Program architecture with flowcharts
- File dependencies with ER diagrams
- Processing flow with sequence diagrams
- Business logic analysis
- Modernization recommendations

See [examples.md](examples.md) for complete analysis examples.

## Installation

### Prerequisites

- Python 3.10+
- Node.js (for building the Tree-sitter grammar)
- An Anthropic API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/rpg-explainer.git
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

Use a different Claude model:

```bash
rpg-explain program.rpgle --model claude-sonnet-4-20250514
```

## Supported RPG Formats

### Free-Form RPG (RPG IV Free)
```rpgle
**free
ctl-opt dftactgrp(*no);

dcl-s myVar char(10);

dcl-proc myProcedure;
  // procedure code
end-proc;
```

### Fixed-Form RPG (RPG III/IV)
```rpgle
     H option(*nodebugio)
     Fmyfile    if   e           k disk
     D myVar          s             10a
     C                   eval      *inlr = *on
```

### Mixed Format
Files starting with `**FREE` are parsed as free-form; others are parsed as fixed-form with column-position awareness.

## Project Structure

```
rpg-explainer/
├── src/
│   └── rpg_explainer/
│       ├── __init__.py
│       ├── parser.py         # Tree-sitter integration + AST parsing
│       ├── analysis.py       # Static analysis and index building
│       ├── llm_client.py     # LangChain + Claude integration
│       ├── cli.py            # CLI entry point
│       └── prompts.py        # LLM prompt templates
├── tree-sitter-rpg/          # Tree-sitter RPG grammar
│   ├── grammar.js            # Grammar definition
│   ├── src/scanner.c         # External scanner for fixed-form
│   └── package.json
├── tests/
│   ├── test_basic_analysis.py
│   └── test_fixed_form.py
├── examples/                  # Example RPG programs
├── examples.md               # Analysis examples with output
├── build_rpg_language.py     # Script to compile the grammar
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

Run tests with coverage:

```bash
pytest --cov=rpg_explainer
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Yes |
| `RPG_TREESITTER_LIB` | Custom path to compiled Tree-sitter library | No (defaults to `build/languages.so`) |

## How It Works

1. **Parsing**: The Tree-sitter grammar parses RPG source code into an AST
2. **Analysis**: The analyzer extracts procedures, files, data structures, and call relationships
3. **Indexing**: A `ProgramIndex` is built containing all program metadata as JSON
4. **LLM Processing**: Claude receives both the structured JSON and raw source code
5. **Report Generation**: Claude generates a comprehensive markdown report with Mermaid diagrams

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
