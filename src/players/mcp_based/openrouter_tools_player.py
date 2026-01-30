"""
OpenRouter Tool-Calling Player for Settlers of Catan.

Generic player that uses OpenRouter's tool calling API.
Works with any model that supports function/tool calling (Claude, GPT, etc.).
"""

import os
import json
import logging
import time
from typing import Dict, Any, Tuple, List, Optional

import httpx
from llm_game_utils import GameResultLogger

from .base_mcp_player import BaseMCPPlayer
from ...mcp.server import CatanatronMCPServer


class OpenRouterToolsPlayer(BaseMCPPlayer):
    """
    Catan player using OpenRouter's tool calling API.

    This player works with any model that supports tool calling through OpenRouter,
    including Claude, GPT-4, Gemini, and others.
    """

    # Models known to support tool calling well
    TOOL_CALLING_MODELS = {
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-haiku",
        "anthropic/claude-3-opus",
        "openai/gpt-4-turbo",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "google/gemini-pro",
        "google/gemini-1.5-pro",
        "google/gemini-1.5-flash",
    }

    def __init__(
        self,
        color,
        model_config: dict,
        session_id: str = None,
        logger: GameResultLogger = None,
        mcp_server: CatanatronMCPServer = None,
        api_key: str = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize OpenRouter tool-calling player.

        Args:
            color: Catanatron color string
            model_config: Dict with model_id, name, input_cost, output_cost, etc.
            session_id: Session ID for logging
            logger: GameResultLogger instance
            mcp_server: Shared MCP server
            api_key: OpenRouter API key (or None to use env var)
            max_retries: Max retries on API failure
            retry_delay: Base delay between retries
        """
        model_name = model_config.get("name", "LLM")
        super().__init__(color, model_name, session_id, logger, mcp_server)

        # API setup
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY must be provided or set in environment"
            )

        self.model_id = model_config["model_id"]
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 4000)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Pricing (per 1K tokens)
        self.input_cost_per_k = model_config.get("input_cost", 0.001)
        self.output_cost_per_k = model_config.get("output_cost", 0.002)

        # HTTP client
        self.http_client = httpx.Client(
            timeout=120,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/infoFiets/llm-catan-arena",
                "X-Title": "LLM Catan Arena",
                "Content-Type": "application/json"
            }
        )

        # Warn if model might not support tool calling
        if self.model_id not in self.TOOL_CALLING_MODELS:
            self.log.warning(
                f"Model {self.model_id} may not support tool calling. "
                f"Known supported models: {', '.join(sorted(self.TOOL_CALLING_MODELS))}"
            )

    def query_llm_with_mcp(
        self,
        system_prompt: str,
        mcp_server: CatanatronMCPServer
    ) -> Tuple[str, float, int]:
        """
        Query LLM with tool calling via OpenRouter.

        Uses OpenRouter's tool calling format (OpenAI-compatible).
        """
        try:
            # Convert MCP tools to OpenAI/OpenRouter format
            tools = self._convert_tools_to_openai_format()

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Make your move in the game."}
            ]

            # Multi-turn conversation for tool use
            max_turns = 10
            total_input_tokens = 0
            total_output_tokens = 0
            final_response_text = ""

            for turn in range(max_turns):
                self.log.debug(f"Turn {turn + 1}/{max_turns}")

                # Make API call with retry
                response_data = self._make_request_with_retry(messages, tools)

                if response_data is None:
                    # All retries failed
                    self.log.error("All API retries failed")
                    return ("API Error", 0.0, 0)

                # Track tokens
                usage = response_data.get("usage", {})
                total_input_tokens += usage.get("prompt_tokens", 0)
                total_output_tokens += usage.get("completion_tokens", 0)

                # Get the response message
                choice = response_data.get("choices", [{}])[0]
                message = choice.get("message", {})
                finish_reason = choice.get("finish_reason", "")

                # Check for tool calls
                tool_calls = message.get("tool_calls", [])

                if tool_calls:
                    # Add assistant message with tool calls to history
                    messages.append(message)

                    # Process each tool call
                    for tool_call in tool_calls:
                        tool_name = tool_call.get("function", {}).get("name", "")
                        tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
                        tool_call_id = tool_call.get("id", "")

                        try:
                            tool_args = json.loads(tool_args_str)
                        except json.JSONDecodeError:
                            tool_args = {}

                        self.log.debug(f"Tool call: {tool_name}({tool_args})")

                        # Execute tool via MCP server
                        result = mcp_server.handle_tool_call(tool_name, tool_args)

                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result if isinstance(result, str) else json.dumps(result)
                        })

                        # Check if select_action was called - we're done
                        if tool_name == "select_action":
                            final_response_text = message.get("content", "") or "Action selected"
                            cost = self._calculate_cost(total_input_tokens, total_output_tokens)
                            return (final_response_text, cost, total_input_tokens + total_output_tokens)

                elif finish_reason == "stop" or not tool_calls:
                    # Model finished without more tool calls
                    final_response_text = message.get("content", "No response")
                    self.log.warning("LLM ended turn without selecting action")
                    break

            # If we got here, LLM didn't select an action within max turns
            self.log.warning(f"LLM completed {turn + 1} turns without selecting action")
            cost = self._calculate_cost(total_input_tokens, total_output_tokens)
            return (final_response_text, cost, total_input_tokens + total_output_tokens)

        except Exception as e:
            self.log.error(f"Error in query_llm_with_mcp: {e}", exc_info=True)
            return (f"Error: {str(e)}", 0.0, 0)

    def _make_request_with_retry(
        self,
        messages: List[Dict],
        tools: List[Dict]
    ) -> Optional[Dict]:
        """Make API request with retry logic."""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.http_client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={
                        "model": self.model_id,
                        "messages": messages,
                        "tools": tools,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens
                    }
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                self.log.warning(
                    f"HTTP error (attempt {attempt + 1}/{self.max_retries}): "
                    f"{e.response.status_code} - {e.response.text[:200]}"
                )
            except Exception as e:
                last_error = e
                self.log.warning(
                    f"Request error (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

            if attempt < self.max_retries - 1:
                sleep_time = self.retry_delay * (attempt + 1)
                time.sleep(sleep_time)

        self.log.error(f"All {self.max_retries} attempts failed: {last_error}")
        return None

    def _convert_tools_to_openai_format(self) -> List[Dict]:
        """Convert MCP tools to OpenAI/OpenRouter function calling format."""
        mcp_tools = self.mcp_server.get_tools()
        openai_tools = []

        for tool in mcp_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            })

        return openai_tools

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost based on token usage."""
        input_cost = (input_tokens / 1000) * self.input_cost_per_k
        output_cost = (output_tokens / 1000) * self.output_cost_per_k
        return input_cost + output_cost

    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'http_client'):
            self.http_client.close()
