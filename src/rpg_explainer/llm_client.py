"""LangChain + Anthropic Claude integration for RPG program explanation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .prompts import PROCEDURE_FOCUS_PROMPT, QUICK_SUMMARY_PROMPT, SUMMARY_PROMPT


if TYPE_CHECKING:
    from .analysis import ProgramIndex, RPGProcedure

# Default model - Claude Opus 4.5
DEFAULT_MODEL = "claude-opus-4-5-20251101"


class RPGExplainerLLM:
    """LLM client for explaining RPG programs using Claude."""

    def __init__(self, model: str | None = None, temperature: float = 0.2):
        """Initialize the LLM client.

        Args:
            model: The Claude model ID to use. Defaults to Claude Opus 4.5.
            temperature: Sampling temperature (0.0-1.0). Lower = more deterministic.

        Raises:
            ValueError: If ANTHROPIC_API_KEY environment variable is not set.
        """
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it to your Anthropic API key."
            )

        self.model = model or DEFAULT_MODEL
        self.temperature = temperature

        self._llm = ChatAnthropic(
            model=self.model,
            temperature=self.temperature,
            max_tokens=8192,
        )

    def explain_program(
        self, index: ProgramIndex, source_files: dict[str, str] | None = None
    ) -> str:
        """Generate a comprehensive explanation of an RPG program.

        Args:
            index: The ProgramIndex containing analyzed program information.
            source_files: Optional dict mapping file paths to their source code.

        Returns:
            A markdown-formatted explanation of the program.
        """
        program_json = index.to_json(indent=2)

        # Build source code section if provided
        source_section = ""
        if source_files:
            source_section = "\n\n## Raw Source Code\n\n"
            for path, source in source_files.items():
                source_section += f"### {path}\n\n```rpgle\n{source}\n```\n\n"

        # Build the prompt
        prompt = SUMMARY_PROMPT.format(
            program_index_json=program_json,
            source_code_section=source_section,
        )

        # Create messages
        messages = [
            SystemMessage(
                content="You are a senior IBM i / RPGLE architect. "
                "Provide clear, technical explanations."
            ),
            HumanMessage(content=prompt),
        ]

        # Invoke the LLM
        response = self._llm.invoke(messages)

        return str(response.content)

    def explain_procedure(
        self,
        procedure: RPGProcedure,
        source_code: str,
    ) -> str:
        """Generate a detailed explanation of a specific procedure.

        Args:
            procedure: The RPGProcedure to explain.
            source_code: The raw source code of the procedure.

        Returns:
            A markdown-formatted explanation of the procedure.
        """
        # Format parameters
        params_str = ", ".join(f"{p.name}: {p.type or 'unknown'}" for p in procedure.params)
        if not params_str:
            params_str = "None"

        # Build the prompt
        prompt = PROCEDURE_FOCUS_PROMPT.format(
            procedure_name=procedure.name,
            parameters=params_str,
            return_type=procedure.returns or "None",
            internal_calls=", ".join(procedure.calls_internal) or "None",
            external_calls=", ".join(procedure.calls_external) or "None",
            files_used=", ".join(procedure.uses_files) or "None",
            source_code=source_code,
        )

        messages = [
            SystemMessage(
                content="You are a senior IBM i / RPGLE architect. "
                "Provide detailed technical analysis."
            ),
            HumanMessage(content=prompt),
        ]

        response = self._llm.invoke(messages)

        return str(response.content)

    def quick_summary(self, index: ProgramIndex) -> str:
        """Generate a brief summary of the program.

        Args:
            index: The ProgramIndex containing analyzed program information.

        Returns:
            A brief 2-3 sentence summary.
        """
        program_json = index.to_json(indent=2)

        prompt = QUICK_SUMMARY_PROMPT.format(program_index_json=program_json)

        messages = [HumanMessage(content=prompt)]

        response = self._llm.invoke(messages)

        return str(response.content)
