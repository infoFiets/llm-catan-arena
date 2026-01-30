"""
Tool-calling LLM players for Settlers of Catan.

Players that use tool/function calling to query game state via structured tools.
Supports any model with tool calling capability through OpenRouter.
"""

from .base_mcp_player import BaseMCPPlayer
from .mcp_claude_player import MCPClaudePlayer
from .openrouter_tools_player import OpenRouterToolsPlayer

__all__ = [
    "BaseMCPPlayer",
    "MCPClaudePlayer",
    "OpenRouterToolsPlayer",
]
