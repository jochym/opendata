import logging
import re
import yaml
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path
from opendata.models import Metadata, AIAnalysis, FileSuggestion, ProjectFingerprint
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.agents.tools import handle_external_tools
from opendata.utils import FullTextReader, PromptManager

logger = logging.getLogger("opendata.agents.engine")


class AnalysisEngine:
    """Engine for AI interactions and tool execution."""

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager

    def generate_ai_prompt(
        self,
        mode: str,
        metadata: Metadata,
        fingerprint: Optional[ProjectFingerprint],
        effective_protocol: dict,
    ) -> str:
        """Generates the system prompt for the AI based on current state and protocols."""
        if not fingerprint:
            return "No project scanned."

        fingerprint_summary = fingerprint.model_dump_json(indent=2)
        current_data = yaml.dump(
            metadata.model_dump(exclude_unset=True), allow_unicode=True
        )

        protocols_str = ""
        # Legacy prompts
        if effective_protocol.get("prompts"):
            protocols_str += "ACTIVE PROTOCOLS & USER RULES:\n" + "\n".join(
                [f"{i}. {p}" for i, p in enumerate(effective_protocol["prompts"], 1)]
            )

        # Mode-specific prompts
        mode_prompts = effective_protocol.get(
            "metadata_prompts" if mode == "metadata" else "curator_prompts", []
        )
        if mode_prompts:
            if protocols_str:
                protocols_str += "\n\n"
            protocols_str += f"SPECIFIC {mode.upper()} INSTRUCTIONS:\n" + "\n".join(
                [f"{i}. {p}" for i, p in enumerate(mode_prompts, 1)]
            )

        primary_file_info = ""
        if fingerprint and fingerprint.primary_file:
            primary_file_info = (
                f"PRIMARY PUBLICATION FILE: {fingerprint.primary_file}\n"
            )

        template = (
            "system_prompt_metadata" if mode == "metadata" else "system_prompt_curator"
        )

        return self.prompt_manager.render(
            template,
            {
                "fingerprint": fingerprint_summary,
                "metadata": current_data,
                "protocols": protocols_str,
                "primary_file": primary_file_info,
            },
        )

    def run_ai_loop(
        self,
        ai_service: Any,
        user_input: str,
        chat_history: list[tuple[str, str]],
        current_metadata: Metadata,
        fingerprint: Optional[ProjectFingerprint],
        effective_protocol: dict,
        mode: str = "metadata",
        on_update: Optional[Callable[[], None]] = None,
        on_system_msg: Optional[Callable[[str], None]] = None,
        stop_event: Optional[Any] = None,
    ) -> Tuple[str, Optional[AIAnalysis], Metadata]:
        """Main iterative loop with Context Persistence and Tool recognition."""

        enhanced_input = handle_external_tools(user_input, ai_service) or user_input

        max_tool_iterations = 5
        for iteration in range(max_tool_iterations):
            if stop_event and stop_event.is_set():
                return "🛑 **Analysis cancelled by user.**", None, current_metadata

            context = self.generate_ai_prompt(
                mode, current_metadata, fingerprint, effective_protocol
            )

            # Use only a window of history for context
            history_str = "\n".join([f"{role}: {m}" for role, m in chat_history[-15:]])

            full_prompt = self.prompt_manager.render(
                "chat_wrapper",
                {
                    "history": history_str,
                    "user_input": enhanced_input,
                    "context": context,
                },
            )

            def status_callback(msg: str):
                if on_system_msg:
                    on_system_msg(msg)
                if on_update:
                    on_update()

            try:
                ai_response = ai_service.ask_agent(
                    full_prompt, on_status=status_callback
                )
            except Exception as e:
                logger.error(f"AI Error: {e}", exc_info=True)
                return (
                    f"❌ **AI Communication Error:** {str(e)}",
                    None,
                    current_metadata,
                )

            # Check for AI errors returned as text
            if ai_response.startswith("AI Error:") or ai_response.startswith(
                "AI not authenticated"
            ):
                return f"❌ **{ai_response}**", None, current_metadata

            # Ensure ai_response starts with JSON context if it looks like JSON
            if (
                ai_response.strip().startswith("{")
                and "METADATA" not in ai_response
                and "ANALYSIS" not in ai_response
            ):
                ai_response = f"METADATA:\n{ai_response}"
            elif "METADATA:" not in ai_response and "ANALYSIS" not in ai_response:
                json_match = re.search(r"({.*})", ai_response, re.DOTALL)
                if json_match:
                    ai_response = f"METADATA:\n{ai_response}"

            # Check for READ_FILE command
            read_match = re.search(r"READ_FILE:\s*(.+)", ai_response)
            if read_match and fingerprint:
                file_paths_str = read_match.group(1).strip()
                requested_files = [f.strip() for f in file_paths_str.split(",")]
                project_dir_to_use = Path(fingerprint.root_path)

                tool_output = []
                visible_files = []
                for rf in requested_files:
                    p = project_dir_to_use / rf
                    if p.exists() and p.is_file():
                        content = FullTextReader.read_full_text(p)
                        tool_output.append(f"--- FILE CONTENT: {rf} ---\n{content}")
                        visible_files.append(f"`{rf}`")
                    else:
                        tool_output.append(f"--- FILE NOT FOUND: {rf} ---")
                        visible_files.append(f"`{rf}` (not found)")

                if on_system_msg:
                    on_system_msg(
                        f"AI requested content of: {', '.join(visible_files)}"
                    )

                enhanced_input = "[System] READ_FILE Tool Results:\n\n" + "\n\n".join(
                    tool_output
                )

                if on_update:
                    on_update()
                continue  # Next iteration of the loop

            # If no READ_FILE, finish
            wrapped_response = (
                f"METADATA:\n{ai_response}"
                if "METADATA:" not in ai_response
                else ai_response
            )

            clean_msg, analysis, metadata = extract_metadata_from_ai_response(
                wrapped_response, current_metadata
            )

            # --- GLOB EXPANSION FOR FILE SUGGESTIONS ---
            if analysis and analysis.file_suggestions and fingerprint:
                project_dir = Path(fingerprint.root_path)
                expanded_suggestions = []
                seen_paths = set()

                for sug in analysis.file_suggestions:
                    if any(x in sug.path for x in ["*", "?", "["]):
                        found = list(project_dir.glob(sug.path))
                        if not found and not sug.path.startswith("**/"):
                            found = list(project_dir.glob(f"**/{sug.path}"))

                        for p in found:
                            if p.is_file():
                                rel_p = str(p.relative_to(project_dir))
                                if rel_p not in seen_paths:
                                    expanded_suggestions.append(
                                        FileSuggestion(
                                            path=rel_p,
                                            reason=f"[Pattern match: {sug.path}] {sug.reason}",
                                        )
                                    )
                                    seen_paths.add(rel_p)
                    else:
                        if sug.path not in seen_paths:
                            expanded_suggestions.append(sug)
                            seen_paths.add(sug.path)

                analysis.file_suggestions = expanded_suggestions

            return clean_msg, analysis, metadata

        return "Tool loop exceeded maximum iterations.", None, current_metadata
