Here’s a pack of ready‑to‑paste **Claude code prompts** that walk it through building the whole thing:

* Python + LangChain tool
* Uses **py-tree-sitter** with the **RPG Tree‑sitter grammar** you already have
* Uses **Anthropic Claude Opus 4.5** via `langchain_anthropic.ChatAnthropic`([LangChain Docs][1])
* Parses RPG, extracts dependencies/resources, then calls the LLM to explain.

You can use these sequentially in a single Claude chat (or in separate chats, if you paste the relevant context each time).

---

## Prompt 0 – Session setup (tell Claude who it is and what you want)

> **Prompt 0 – Context and goals**
>
> You are an expert:
>
> * Python engineer
> * LangChain and Anthropic Claude power‑user
> * Tree‑sitter and language tooling developer
> * IBM i / RPGLE (ILE RPG, free‑form) developer
>
> Goal: Build a **local Python CLI tool** that:
>
> 1. Uses **Tree‑sitter** with an **RPG grammar** (`tree-sitter-rpg`) to parse RPG free‑form code.
> 2. Walks the AST to detect:
>
>    * Procedures and subroutines
>    * DCL‑F file definitions (database / printer / work files)
>    * External calls (CALLP, prototypes with `extpgm`/`extproc`, etc.)
>    * `%xxxx` built‑ins that reference external resources if possible
> 3. Builds a structured JSON “program index”:
>
>    * `files`: list of RPG source files analyzed
>    * `procedures`: name, params, called procedures, external calls, referenced files
>    * `files_used`: DCL‑F entries with attributes
>    * `constants` / `data_structures` (just basic info)
> 4. Uses **LangChain + Anthropic Claude Opus 4.5** (`langchain_anthropic.ChatAnthropic`) to:
>
>    * Summarize what the program does
>    * Explain the call graph and dependencies
>    * Explain which external resources (files/programs) are used and how
>    * Produce a human‑readable architecture report.
>
> Constraints:
>
> * Code must run locally: a simple `main.py` CLI that accepts one or more `.rpgle` paths.
> * Use **py-tree-sitter** (`tree_sitter`) for parsing.([GitHub][2])
> * Use **LangChain’s Anthropic integration** (`langchain_anthropic.ChatAnthropic`) with an `ANTHROPIC_API_KEY` env var.([LangChain Docs][1])
> * Keep everything in a single repo, no Docker required.
>
> I will give you more specific prompts next; please respond “OK, ready” and wait.

---

## Prompt 1 – Project layout & dependencies

> **Prompt 1 – Create project skeleton and dependencies**
>
> Design a minimal but clean Python project layout for this tool.
>
> Requirements:
>
> * Use `src/` layout:
>
>   * `src/rpg_explainer/__init__.py`
>   * `src/rpg_explainer/parser.py`        → Tree‑sitter integration + AST index building
>   * `src/rpg_explainer/analysis.py`      → Higher‑level analysis helpers on top of AST
>   * `src/rpg_explainer/llm_client.py`    → LangChain + Claude Opus 4.5 integration
>   * `src/rpg_explainer/cli.py`           → Click / argparse CLI
>   * `src/rpg_explainer/prompts.py`       → Prompt templates for the LLM
> * At repo root:
>
>   * `pyproject.toml` **or** `requirements.txt` (your choice, but prefer `pyproject.toml`)
>   * `README.md`
>   * `build_rpg_language.py` (helper to compile the Tree‑sitter RPG grammar)
>
> Libraries to include:
>
> * `tree_sitter`
> * `langchain`
> * `langchain-anthropic`
> * `python-dotenv` (for loading `ANTHROPIC_API_KEY` from `.env`)
> * `click` or `typer` (whichever you prefer) for the CLI
>
> Please:
>
> 1. Output `pyproject.toml` (or `requirements.txt`) with appropriate dependencies and versions that work with the latest LangChain + langchain‑anthropic.
> 2. Output the folder structure as a tree.
> 3. Create a placeholder `README.md` describing the tool at a high level.
>
> DO NOT write the implementation files yet, just their names with 1–2 sentence descriptions.

---

## Prompt 2 – Tree-sitter integration for RPG

> **Prompt 2 – Implement Tree‑sitter RPG parser (`parser.py` + build helper)**
>
> Assume I already have a `tree-sitter-rpg` grammar repo on disk that contains `grammar.js` for free‑form ILE RPG. (You don’t need to regenerate it; just assume it exists and works.)
>
> Use **py-tree-sitter** as documented here (you don’t need to browse, just follow standard usage):([tree-sitter.github.io][3])
>
> * `Language.build_library("build/my-languages.so", [...])`
> * `Language("build/my-languages.so", "rpg")`
> * `Parser().set_language(...)`
>
> Implement:
>
> 1. `build_rpg_language.py`
>
>    * Script that:
>
>      * Uses `tree_sitter.Language.build_library` to build `build/languages.so` from the local `tree-sitter-rpg` directory.
>      * Prints a clear success message or errors.
>      * Is idempotent (rebuilds the library if sources changed).
>    * Assume the grammar’s language name is `"rpg"`.
> 2. `src/rpg_explainer/parser.py`
>    Implement a class `RPGParser` that:
>
>    * In `__init__`, loads the compiled language library:
>
>      * Default path: `build/languages.so`
>      * Environment variable override: `RPG_TREESITTER_LIB`
>    * Exposes:
>
>      * `parse_code(source: str, path: str | None = None) -> tree_sitter.Tree`
>      * `parse_file(path: str) -> tree_sitter.Tree`
>    * Adds a small utility:
>
>      * `iter_nodes(tree)` – generator that yields nodes in pre‑order with `(node, parent)` (or similar).
> 3. Define **known node type names** based on the RPG grammar (you can hardcode these strings, they come from the grammar):
>
>    * `program`, `control_options`, `file_definition`
>    * `dcl_s`, `constant_definition`, `dcl_ds`, `subfield_definition`, `type_spec`
>    * `procedure`, `procedure_interface`, `parameter_definition`
>    * `call_statement`, `assignment`, `eval_statement`
>    * `if_statement`, `dow_statement`, `for_statement`, `select_statement`, `monitor_statement`, `begsr_statement`
>    * `identifier`, `number_literal`, `string_literal`, `special_value`, `builtin_function`, `qualified_name`, `array_access`
>
> Implement `parser.py` with:
>
> * A small `ParsedFile` dataclass:
>
>   * `path: str`
>   * `tree: Tree`
>   * `source: str`
> * High‑level helper:
>
>   * `parse_files(paths: list[str]) -> list[ParsedFile]`
>
> Please output full code for `build_rpg_language.py` and `src/rpg_explainer/parser.py`.

---

## Prompt 3 – Static analysis: build a “program index”

> **Prompt 3 – Implement static analysis (`analysis.py`)**
>
> Now use the Tree‑sitter AST to build a **program index** capturing procedures, calls, and resources.
>
> Implement `src/rpg_explainer/analysis.py` with:
>
> ### Data models
>
> Use `dataclasses` and `typing`:
>
> ```python
> @dataclass
> class RPGFile:
>     path: str
>     procedures: list["RPGProcedure"]
>     subroutines: list["RPGSubroutine"]
>     file_defs: list["RPGFileDef"]
>     constants: list["RPGConstant"]
>     data_structures: list["RPGDataStructure"]
>
> @dataclass
> class RPGProcedure:
>     name: str
>     params: list["RPGParameter"]
>     returns: str | None
>     calls_internal: list[str]        # names of procedures/subroutines in same program
>     calls_external: list[str]        # external programs / procedures
>     uses_files: list[str]            # logical file names from DCL-F
>
> @dataclass
> class RPGSubroutine:
>     name: str
>     calls_internal: list[str]
>     calls_external: list[str]
>     uses_files: list[str]
>
> @dataclass
> class RPGFileDef:
>     name: str
>     keywords: dict[str, list[str]]   # e.g. usage(*update) → {"usage": ["*update"]}
>
> @dataclass
> class RPGParameter:
>     name: str
>     type: str | None
>     attributes: dict[str, list[str]]
>
> @dataclass
> class RPGConstant:
>     name: str
>     value_preview: str
>
> @dataclass
> class RPGDataStructure:
>     name: str
>     subfields: list[str]
>
> @dataclass
> class ProgramIndex:
>     files: list[RPGFile]
> ```
>
> ### Analysis logic
>
> Implement a class `RPGAnalyzer` with methods:
>
> * `build_index(parsed_files: list[ParsedFile]) -> ProgramIndex`
> * Internally:
>
>   * Walk each file’s AST and:
>
>     * For `file_definition` nodes:
>
>       * Extract the identifier name.
>       * Extract keyword attributes (child `typed_keyword` nodes, treat keyword name as `identifier`, args as list of normalized strings).
>     * For `procedure` nodes:
>
>       * Extract the procedure name.
>       * From `procedure_interface` → parameters and optional return type (from `type_spec` node).
>       * Within the procedure body:
>
>         * Collect `call_statement` nodes:
>
>           * Distinguish between:
>
>             * Calls to procedures defined in the same file (internal) → by identifier match.
>             * Calls to external programs (e.g. `callp SomeProg` with no matching local procedure).
>         * Track file usage:
>
>           * If the procedure mentions identifiers corresponding to `RPGFileDef.name`, add to `uses_files`.
>     * For `begsr_statement` nodes (subroutines):
>
>       * Treat similarly to procedures but no parameters.
>     * For `constant_definition`, `dcl_ds`:
>
>       * Fill `RPGConstant` and `RPGDataStructure` with basic info (just enough for explanation).
>
> The implementation does not have to understand every RPG feature; it just needs to be **reasonably robust**:
>
> * If something is ambiguous, put it in `calls_external` or `uses_files` conservatively.
> * Use helper functions like `node_text(node, source)` to extract identifier names.
>
> At the end, `ProgramIndex` should be serializable to JSON (e.g. via `dataclasses.asdict`).
>
> Please output full code for `src/rpg_explainer/analysis.py`, updating imports from `parser.py` as needed.

---

## Prompt 4 – LangChain + Claude Opus 4.5 integration (`llm_client.py` + prompts)

> **Prompt 4 – Wire up LangChain & Anthropic Claude Opus 4.5**
>
> Now integrate **LangChain** with **Anthropic Claude Opus 4.5** via `langchain_anthropic.ChatAnthropic`.([LangChain Docs][1])
>
> Assumptions:
>
> * The user has `ANTHROPIC_API_KEY` set, and `langchain-anthropic` installed.
> * The correct model ID for Claude Opus 4.5 will follow Anthropic’s standard naming scheme (`"claude-opus-4-5-YYYYMMDD"`). Use a clearly marked placeholder like `"claude-opus-4-5-YYYYMMDD"` and comment that the user must replace it with the actual ID from Claude docs.
>
> ### `src/rpg_explainer/prompts.py`
>
> Create a module that defines string templates (or LangChain `PromptTemplate`s) for:
>
> 1. `SUMMARY_PROMPT`
>
>    * System style: “You are a senior IBM i / RPGLE architect…”
>    * Input variables:
>
>      * `program_index_json` (JSON of `ProgramIndex`)
>      * Optional `raw_snippets` for tricky procedures (can be left unused for now).
>    * Ask the model to:
>
>      * Summarize overall program purpose.
>      * Describe major procedures and their roles.
>      * Explain call graph and external dependencies (programs and files).
>      * Highlight risky operations (file updates, deletes, external calls).
> 2. `PROCEDURE_FOCUS_PROMPT`
>
>    * For drilling into a single procedure with its local context and raw code.
>
> Keep these as plain Python string templates or LangChain `PromptTemplate` objects.
>
> ### `src/rpg_explainer/llm_client.py`
>
> Implement:
>
> ```python
> class RPGExplainerLLM:
>     def __init__(self, model: str | None = None, temperature: float = 0.2):
>         ...
>
>     def explain_program(self, index: ProgramIndex) -> str:
>         """Returns a markdown explanation of the RPG program."""
> ```
>
> Behavior:
>
> * In `__init__`:
>
>   * Create a `ChatAnthropic` instance using the given model or default placeholder `"claude-opus-4-5-YYYYMMDD"`.
>   * Use low temperature, e.g. `0.2`.
> * In `explain_program`:
>
>   * Convert `ProgramIndex` to JSON (pretty‑printed, but not insanely large).
>   * Build a LangChain chain:
>
>     * System/content: `SUMMARY_PROMPT` (or proper LC template) plus the JSON.
>   * Call `.invoke(...)` on the chain.
>   * Return a markdown string.
>
> Be explicit about:
>
> * How you import `ChatAnthropic` (`from langchain_anthropic import ChatAnthropic`).
> * How the environment variable `ANTHROPIC_API_KEY` is used (no custom code needed; LangChain picks it up).
>
> Please output full code for `src/rpg_explainer/prompts.py` and `src/rpg_explainer/llm_client.py`.

---

## Prompt 5 – CLI entrypoint (`cli.py` + `main.py`)

> **Prompt 5 – Build CLI that ties everything together**
>
> Now implement:
>
> 1. `src/rpg_explainer/cli.py`
>
>    * Use `click` or `typer`.
>    * Provide a command:
>
>      * `rpg-explain PATH [PATH ...]`
>    * Behavior:
>
>      * Ensure the Tree‑sitter library is built:
>
>        * If `build/languages.so` is missing, call `build_rpg_language.py` (document that the user may need to run it manually the first time).
>      * Use `RPGParser` to parse all paths.
>      * Use `RPGAnalyzer` to build `ProgramIndex`.
>      * Use `RPGExplainerLLM` to produce a markdown report.
>      * Print the report to stdout.
>      * Optionally accept `--output` to write the report to a file.
> 2. `main.py` at repo root:
>
>    * Small shim that calls the CLI (so user can run `python -m rpg_explainer` or `python main.py`).
>
> Add nice touches:
>
> * Progress messages: “Parsing files…”, “Analyzing dependencies…”, “Calling Claude Opus 4.5…”.
> * Basic error handling for:
>
>   * Missing `ANTHROPIC_API_KEY`
>   * Failed build of Tree‑sitter library
>   * Parse errors (collect but don’t crash; include in the report under a “Parse issues” section).
>
> Please output full code for `src/rpg_explainer/cli.py` and `main.py`.

---

## Prompt 6 – Optional: tests & example usage

> **Prompt 6 – Add a small test and examples**
>
> Finally:
>
> 1. Add a `tests/` folder with at least one example RPG free‑form program (as a string or file) and a pytest that:
>
>    * Parses it with `RPGParser`.
>    * Builds a `ProgramIndex`.
>    * Asserts that:
>
>      * At least one `RPGFileDef` is detected.
>      * At least one `RPGProcedure` is detected.
>      * At least one internal or external call is detected.
>    * The test should **not** call the LLM (no API calls in tests).
> 2. Update `README.md` with:
>
>    * Install instructions (`pip install -e .`)
>    * How to build the Tree‑sitter RPG library
>    * How to run:
>
>      * `export ANTHROPIC_API_KEY=...`
>      * `rpg-explain src/myprog.rpgle`
>
> Please output:
>
> * `tests/test_basic_analysis.py`
> * Updated `README.md` (only the changed version, not a diff).

---

If you run through these prompts with Claude, you should end up with:

* A local CLI that parses RPG via Tree‑sitter
* Builds a structured dependency/resource index
* And uses Claude Opus 4.5 through LangChain to explain what the program does and how everything is wired together.

[1]: https://langchain-5e9cc07a.mintlify.app/oss/python/integrations/chat/anthropic?utm_source=chatgpt.com "ChatAnthropic - Docs by LangChain"
[2]: https://github.com/tree-sitter/py-tree-sitter?utm_source=chatgpt.com "Python bindings to the Tree-sitter parsing library"
[3]: https://tree-sitter.github.io/py-tree-sitter/?utm_source=chatgpt.com "py-tree-sitter 0.25.2 documentation"

