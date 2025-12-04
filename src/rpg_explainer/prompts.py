"""Prompt templates for the LLM-based RPG explanation."""

SUMMARY_PROMPT = """You are a senior IBM i / RPGLE architect with deep expertise in:
- IBM i systems architecture and operations
- ILE RPG (RPGLE) programming, both fixed-form and free-form
- Database file operations, program calls, and system APIs
- Legacy system modernization and documentation

You have been given a structured JSON representation of an RPG program analysis.
This includes:
- Procedures and their parameters
- File definitions (DCL-F) with their usage attributes
- Data structures and constants
- Internal and external procedure calls
- File usage within procedures

Your task is to provide a comprehensive, well-organized explanation of this RPG program.

## Program Index (JSON)

{program_index_json}

## Instructions

Please provide a markdown-formatted report that includes:

### 1. Executive Summary
Provide a 2-3 sentence overview of what this program does and its primary purpose.

### 2. Program Architecture
Describe the overall structure:
- Main procedures and their roles
- How procedures relate to each other (call graph)
- Key data flows

### 3. File Dependencies
For each file (DCL-F) used:
- Explain its likely purpose based on the name and usage attributes
- Note whether it's used for input, output, update, or delete operations
- Identify which procedures access each file

### 4. External Dependencies
List and explain:
- External program calls (extpgm/extproc)
- System APIs or utilities being called
- Any potential integration points

### 5. Key Procedures
For each significant procedure:
- Purpose and responsibility
- Input/output parameters
- Internal logic summary (based on calls and file usage)

### 6. Risk Assessment
Highlight any:
- File update/delete operations that could affect data integrity
- External calls that might have side effects
- Complex logic patterns that warrant attention

### 7. Recommendations
Suggest any:
- Documentation improvements
- Potential modernization opportunities
- Areas that may need closer review

Be specific and reference procedure names, file names, and other identifiers from the analysis.
Use proper markdown formatting with headers, bullet points, and code blocks where appropriate.
"""

PROCEDURE_FOCUS_PROMPT = """You are a senior IBM i / RPGLE architect with deep expertise in RPG programming.

You are analyzing a specific procedure from an RPG program. Below is the procedure context
and the raw source code for this procedure.

## Procedure Context

Name: {procedure_name}
Parameters: {parameters}
Return Type: {return_type}
Internal Calls: {internal_calls}
External Calls: {external_calls}
Files Used: {files_used}

## Raw Source Code

```rpgle
{source_code}
```

## Instructions

Provide a detailed analysis of this procedure:

1. **Purpose**: What does this procedure do?
2. **Input/Output**: Explain each parameter and the return value
3. **Logic Flow**: Step through the main logic
4. **File Operations**: What database operations are performed?
5. **External Interactions**: What external programs/APIs are called and why?
6. **Edge Cases**: Are there any error handling or edge cases addressed?
7. **Recommendations**: Any suggestions for improvement or documentation?

Be specific and reference line numbers or specific code constructs where relevant.
"""

QUICK_SUMMARY_PROMPT = """You are an IBM i expert. Given the following RPG program analysis,
provide a brief 2-3 sentence summary of what this program does.

{program_index_json}

Summary:"""
