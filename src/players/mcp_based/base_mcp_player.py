"""
Base MCP Player for Settlers of Catan.

Abstract base class for LLM players using MCP (Model Context Protocol)
to query game state via structured tools.
"""

import logging
import random
from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional

from catanatron.models.player import Player
from llm_game_utils import GameResultLogger

from ...mcp.server import CatanatronMCPServer


class BaseMCPPlayer(Player, ABC):
    """
    Abstract base class for MCP-enabled LLM players.

    Flow in decide() method:
    1. Set game context in MCP server
    2. Query LLM (LLM uses MCP tools to explore state)
    3. LLM calls select_action tool
    4. Retrieve selected action from server
    5. Return action to Catanatron
    """

    def __init__(
        self,
        color,
        model_name: str,
        session_id: str = None,
        logger: GameResultLogger = None,
        mcp_server: CatanatronMCPServer = None,
        is_bot: bool = True
    ):
        """
        Initialize base MCP player.

        Args:
            color: Catanatron color string
            model_name: Name of LLM model
            session_id: Session ID for logging
            logger: GameResultLogger instance
            mcp_server: Shared MCP server instance (or None to create new)
            is_bot: Whether this is a bot player
        """
        super().__init__(color, is_bot)
        self.model_name = model_name
        self.session_id = session_id
        self.logger = logger
        self.mcp_server = mcp_server or CatanatronMCPServer(f"catan_{color}")
        self.recent_moves = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.move_count = 0

        self.log = logging.getLogger(f"{self.__class__.__name__}:{color}")

    @abstractmethod
    def query_llm_with_mcp(
        self,
        system_prompt: str,
        mcp_server: CatanatronMCPServer
    ) -> tuple[str, float, int]:
        """
        Query LLM with MCP tools available.

        Subclasses implement this to:
        1. Connect LLM API to MCP tools
        2. Send system prompt
        3. Let LLM explore via MCP
        4. Return response, cost, tokens

        Args:
            system_prompt: Initial instructions for LLM
            mcp_server: MCP server with tools

        Returns:
            Tuple of (response_text, cost, tokens_used)
        """
        pass

    def decide(self, game, playable_actions):
        """
        Main decision method called by Catanatron.

        Args:
            game: Complete game state
            playable_actions: List of valid actions

        Returns:
            Selected action from playable_actions
        """
        try:
            # Set game context in MCP server
            self.mcp_server.set_game_context(game, self.color, playable_actions)

            # Build system prompt
            system_prompt = self._build_system_prompt(game)

            # Query LLM with MCP tools
            self.log.debug("Querying LLM with MCP tools")
            response, cost, tokens = self.query_llm_with_mcp(system_prompt, self.mcp_server)

            # Update stats
            self.total_cost += cost
            self.total_tokens += tokens
            self.move_count += 1

            # Get selected action from MCP server
            selected_action = self.mcp_server.get_selected_action()

            if not selected_action:
                self.log.warning("LLM did not select action via MCP, falling back")
                selected_action = self._fallback_action(playable_actions)

            # Log the move
            if self.logger and self.session_id:
                self.logger.log_move(
                    session_id=self.session_id,
                    player=str(self.color),
                    move_data={
                        "action": self._safe_action_str(selected_action),
                        "response": response[:200],  # First 200 chars
                        "cost": cost,
                        "tokens": tokens,
                        "mode": "mcp"
                    },
                    turn_number=self.move_count
                )

            # Track for context
            self.recent_moves.append(self._safe_action_str(selected_action))
            if len(self.recent_moves) > 5:
                self.recent_moves = self.recent_moves[-5:]

            # Clear context for next decision
            self.mcp_server.clear_context()

            return selected_action

        except Exception as e:
            self.log.error(f"Error in decide(): {e}", exc_info=True)
            return self._fallback_action(playable_actions)

    def _build_system_prompt(self, game) -> str:
        """
        Build system prompt for LLM.

        Args:
            game: Catanatron game instance

        Returns:
            System prompt string
        """
        recent_context = ""
        if self.recent_moves:
            recent_context = f"\n\nYour recent moves: {', '.join(self.recent_moves[-3:])}"

        return f"""You are an expert Settlers of Catan player playing as {self.color}.

Your goal is to win the game by reaching 10 victory points.

You have access to MCP (Model Context Protocol) tools to explore the game state:
1. **get_game_state** - View your resources, buildings, victory points, and opponent info
2. **get_valid_actions** - See all actions you can take right now
3. **select_action** - Choose an action by its action_id

Process:
1. Call get_game_state to understand the current situation
2. Call get_valid_actions to see what you can do
3. Analyze the options strategically
4. Call select_action with your chosen action_id

Strategy tips:
- Focus on reaching 10 victory points efficiently
- Manage resources carefully - build when you can
- Consider opponent positions and threats
- Longest road and largest army give bonus points
- Settlements are worth 1 VP, cities 2 VP
- Development cards can provide VPs and strategic advantages{recent_context}

Make your decision now by using the MCP tools."""

    def _safe_action_str(self, action: Any) -> str:
        """Safely convert action to string."""
        try:
            return str(action)
        except:
            return "Action"

    def _fallback_action(self, playable_actions: List[Any]) -> Any:
        """Fallback to random action."""
        self.log.warning("Using fallback random action")
        return random.choice(playable_actions)

    def reset_state(self):
        """Reset state between games."""
        self.recent_moves = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.move_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get player statistics."""
        return {
            "model": self.model_name,
            "color": self.color,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "move_count": self.move_count,
            "avg_cost_per_move": self.total_cost / self.move_count if self.move_count > 0 else 0,
            "mode": "mcp"
        }
