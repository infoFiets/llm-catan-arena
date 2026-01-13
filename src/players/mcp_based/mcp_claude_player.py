"""
Claude MCP Player for Settlers of Catan.

Uses Claude API with native tool calling for game state exploration.
"""

import os
import json
import logging
from typing import Dict, Any, Tuple
from llm_game_utils import GameResultLogger

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base_mcp_player import BaseMCPPlayer
from ...mcp.server import CatanatronMCPServer


class MCPClaudePlayer(BaseMCPPlayer):
    """
    Catan player powered by Claude with MCP tools.

    Uses Anthropic's native tool calling with MCP server.
    """

    def __init__(
        self,
        color,
        model_config: dict,
        session_id: str = None,
        logger: GameResultLogger = None,
        mcp_server: CatanatronMCPServer = None,
        anthropic_api_key: str = None
    ):
        """
        Initialize Claude MCP player.

        Args:
            color: Catanatron color string
            model_config: Dict with model_id, name, etc.
            session_id: Session ID for logging
            logger: GameResultLogger instance
            mcp_server: Shared MCP server
            anthropic_api_key: Anthropic API key (or None to use env var)
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package required for MCPClaudePlayer. "
                "Install with: pip install anthropic"
            )

        model_name = model_config.get("name", "Claude")
        super().__init__(color, model_name, session_id, logger, mcp_server)

        # Initialize Anthropic client
        api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY must be provided or set in environment"
            )

        self.client = Anthropic(api_key=api_key)
        self.model_id = model_config["model_id"]
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 4000)

        # Pricing (per million tokens)
        self.input_cost_per_million = model_config.get("input_cost", 3.0) * 1000  # Convert to per million
        self.output_cost_per_million = model_config.get("output_cost", 15.0) * 1000

    def query_llm_with_mcp(
        self,
        system_prompt: str,
        mcp_server: CatanatronMCPServer
    ) -> Tuple[str, float, int]:
        """
        Query Claude with MCP tools.

        Uses Anthropic's native tool calling format.
        """
        try:
            # Convert MCP tools to Anthropic format
            tools = self._convert_mcp_tools_to_anthropic()

            messages = [{"role": "user", "content": "Make your move in the game."}]

            # Multi-turn conversation for tool use
            max_turns = 10  # Prevent infinite loops
            total_input_tokens = 0
            total_output_tokens = 0
            final_response_text = ""

            for turn in range(max_turns):
                self.log.debug(f"Turn {turn + 1}/{max_turns}")

                response = self.client.messages.create(
                    model=self.model_id,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=messages,
                    tools=tools
                )

                # Track tokens
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens

                # Check if Claude wants to use tools
                if response.stop_reason == "tool_use":
                    # Execute tool calls via MCP server
                    tool_results = []
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            self.log.debug(f"Tool call: {content_block.name}")
                            result = mcp_server.handle_tool_call(
                                content_block.name,
                                content_block.input
                            )
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": result
                            })

                            # Check if select_action was called
                            if content_block.name == "select_action":
                                # Extract final text from response
                                final_response_text = self._extract_text_from_response(response)
                                # Calculate cost and return
                                cost = self._calculate_cost(total_input_tokens, total_output_tokens)
                                total_tokens = total_input_tokens + total_output_tokens
                                return (final_response_text, cost, total_tokens)

                    # Add assistant response and tool results to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})

                elif response.stop_reason == "end_turn":
                    # Claude finished without more tool calls
                    self.log.warning("Claude ended turn without selecting action")
                    break
                else:
                    # Some other stop reason
                    self.log.warning(f"Unexpected stop reason: {response.stop_reason}")
                    break

            # If we got here, Claude didn't select an action
            final_response_text = self._extract_text_from_response(response)
            cost = self._calculate_cost(total_input_tokens, total_output_tokens)
            total_tokens = total_input_tokens + total_output_tokens

            self.log.warning(
                f"Claude completed {turn + 1} turns without selecting action"
            )

            return (final_response_text, cost, total_tokens)

        except Exception as e:
            self.log.error(f"Error querying Claude with MCP: {e}", exc_info=True)
            return (f"Error: {str(e)}", 0.0, 0)

    def _convert_mcp_tools_to_anthropic(self) -> list:
        """Convert MCP tool definitions to Anthropic format."""
        mcp_tools = self.mcp_server.get_tools()
        anthropic_tools = []

        for tool in mcp_tools:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            })

        return anthropic_tools

    def _extract_text_from_response(self, response) -> str:
        """Extract text content from response."""
        texts = []
        for block in response.content:
            if hasattr(block, 'type') and block.type == "text":
                texts.append(block.text)
        return "\n".join(texts) if texts else "No text response"

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate API cost.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in dollars
        """
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million
        return input_cost + output_cost
