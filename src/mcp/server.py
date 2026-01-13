"""
MCP Server for Catanatron Game State Access

Provides tool-based query interface to game state via function calls.
Server lifecycle is per-decision: context is set before each decide() call.
"""

from typing import Optional, Dict, Any
import json
import logging

from .game_wrapper import CatanatronGameWrapper
from .action_mapper import ActionMapper
from .tools import get_all_tools


class CatanatronMCPServer:
    """
    MCP server wrapping Catanatron game state.

    Provides three tools:
    - get_game_state: Query current game state
    - get_valid_actions: Get available actions with IDs
    - select_action: Mark an action as selected

    Lifecycle:
    - Created once per game (shared by all players)
    - Context set before each player's decide() call
    - Tools called during LLM decision process
    - Selected action retrieved after LLM finishes
    """

    def __init__(self, game_id: str = "catan_game"):
        """Initialize MCP server without game context."""
        self.game_id = game_id
        self.game_wrapper: Optional[CatanatronGameWrapper] = None
        self.action_mapper = ActionMapper(use_descriptive_ids=True)
        self.selected_action_id: Optional[str] = None
        self.log = logging.getLogger(f"MCPServer:{game_id}")

    def set_game_context(self, game, player_color: str, playable_actions: list):
        """
        Set current game context for this decision.
        Called by player before LLM query.

        Args:
            game: Catanatron game instance
            player_color: Color of player making decision
            playable_actions: List of valid Action objects
        """
        self.game_wrapper = CatanatronGameWrapper(game, player_color)
        self.action_mapper.set_actions(playable_actions)
        self.selected_action_id = None
        self.log.debug(
            f"Context set for {player_color}: "
            f"{len(playable_actions)} actions available"
        )

    def get_selected_action(self):
        """
        Retrieve selected action after LLM query.

        Returns:
            Action object or None
        """
        if self.selected_action_id:
            action = self.action_mapper.get_action(self.selected_action_id)
            self.log.debug(f"Retrieved selected action: {self.selected_action_id}")
            return action
        else:
            self.log.warning("No action selected")
            return None

    def get_tools(self) -> list:
        """Get tool definitions for LLM."""
        return get_all_tools()

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """
        Handle a tool call from LLM.

        Args:
            tool_name: Name of tool being called
            tool_input: Input parameters as dict

        Returns:
            JSON string with tool result
        """
        self.log.debug(f"Tool called: {tool_name} with input: {tool_input}")

        if not self.game_wrapper:
            return json.dumps({
                "error": "No game context set. Server not initialized for this decision."
            })

        if tool_name == "get_game_state":
            return self._handle_get_game_state(tool_input)
        elif tool_name == "get_valid_actions":
            return self._handle_get_valid_actions(tool_input)
        elif tool_name == "select_action":
            return self._handle_select_action(tool_input)
        else:
            return json.dumps({
                "error": f"Unknown tool: {tool_name}",
                "available_tools": ["get_game_state", "get_valid_actions", "select_action"]
            })

    def _handle_get_game_state(self, tool_input: dict) -> str:
        """Handle get_game_state tool call."""
        include_board = tool_input.get("include_board", False)
        include_history = tool_input.get("include_history", False)

        try:
            state = self.game_wrapper.get_state(
                include_board=include_board,
                include_history=include_history
            )
            return json.dumps(state, indent=2)
        except Exception as e:
            self.log.error(f"Error getting game state: {e}", exc_info=True)
            return json.dumps({
                "error": f"Failed to get game state: {str(e)}"
            })

    def _handle_get_valid_actions(self, tool_input: dict) -> str:
        """Handle get_valid_actions tool call."""
        try:
            actions = self.action_mapper.get_all_actions_with_ids()
            return json.dumps({
                "num_actions": len(actions),
                "actions": actions
            }, indent=2)
        except Exception as e:
            self.log.error(f"Error getting valid actions: {e}", exc_info=True)
            return json.dumps({
                "error": f"Failed to get valid actions: {str(e)}"
            })

    def _handle_select_action(self, tool_input: dict) -> str:
        """Handle select_action tool call (marks selection, doesn't execute)."""
        action_id = tool_input.get("action_id")

        if not action_id:
            return json.dumps({
                "error": "action_id is required",
                "example": {"action_id": "build_settlement_42"}
            })

        if not self.action_mapper.is_valid_action_id(action_id):
            return json.dumps({
                "error": f"Invalid action_id: {action_id}",
                "valid_action_ids": self.action_mapper.get_all_action_ids()
            })

        # Mark action as selected
        self.selected_action_id = action_id
        action = self.action_mapper.get_action(action_id)

        self.log.info(f"Action selected: {action_id}")

        return json.dumps({
            "success": True,
            "action_id": action_id,
            "action_description": self.action_mapper._safe_action_str(action),
            "message": "Action selected successfully. The game engine will execute it."
        }, indent=2)

    def clear_context(self):
        """Clear game context after decision is complete."""
        self.game_wrapper = None
        self.selected_action_id = None
        self.log.debug("Context cleared")
