"""
MCP-based LLM players for Settlers of Catan.

Players that use Model Context Protocol tools to query game state.
"""

from .base_mcp_player import BaseMCPPlayer
from .mcp_claude_player import MCPClaudePlayer

__all__ = [
    "BaseMCPPlayer",
    "MCPClaudePlayer",
]
