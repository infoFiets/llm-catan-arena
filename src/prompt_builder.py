"""
Prompt Builder for Catan Game State.

Converts Catanatron game state into clear, structured prompts for LLM players.
Keeps prompts concise but informative, formatted as multiple choice questions.
"""

from typing import List, Dict, Any
from llm_game_utils import PromptFormatter


class CatanPromptBuilder:
    """Builds prompts for LLM players in Settlers of Catan."""

    def __init__(self):
        """Initialize the prompt builder with PromptFormatter."""
        self.formatter = PromptFormatter()

    def build_action_prompt(
        self,
        game_state: Any,
        player_state: Dict[str, Any],
        available_actions: List[Any],
        recent_moves: List[str] = None
    ) -> str:
        """
        Build a prompt for an LLM to choose an action in Catan.

        Args:
            game_state: Catanatron game state object
            player_state: Dictionary with player's current state
            available_actions: List of available Catanatron actions
            recent_moves: Optional list of recent moves for context

        Returns:
            Formatted prompt string ready for LLM
        """
        # Extract and format game state
        state_dict = self._extract_state_dict(game_state, player_state)

        # Format available actions as readable choices
        action_choices = self._format_actions(available_actions)

        # Build context from recent moves
        context = self._build_context(recent_moves, player_state)

        # Use PromptFormatter to create structured prompt
        prompt = self.formatter.format_game_state(
            game_name="Settlers of Catan",
            current_state=state_dict,
            available_actions=action_choices,
            additional_context=context
        )

        return prompt

    def _extract_state_dict(self, game_state: Any, player_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant state information into a clean dictionary.

        Args:
            game_state: Catanatron game state object
            player_state: Player-specific state information

        Returns:
            Dictionary with formatted game state
        """
        state = {
            "your_resources": player_state.get("resources", {}),
            "your_victory_points": player_state.get("victory_points", 0),
            "your_buildings": {
                "settlements": player_state.get("settlements", 0),
                "cities": player_state.get("cities", 0),
                "roads": player_state.get("roads", 0)
            },
            "your_development_cards": player_state.get("dev_cards", []),
        }

        # Add opponent information (limited to avoid prompt bloat)
        if "opponents" in player_state:
            state["opponents"] = player_state["opponents"]

        # Add board state summary if available
        if "board_summary" in player_state:
            state["board_state"] = player_state["board_summary"]

        return state

    def _format_actions(self, available_actions: List[Any]) -> List[str]:
        """
        Format Catanatron action objects into readable strings.

        Args:
            available_actions: List of Catanatron action objects

        Returns:
            List of human-readable action descriptions
        """
        formatted_actions = []

        for action in available_actions:
            # Convert action to readable string
            # This will need to be customized based on Catanatron's action format
            action_str = self._action_to_string(action)
            formatted_actions.append(action_str)

        return formatted_actions

    def _action_to_string(self, action: Any) -> str:
        """
        Convert a single Catanatron action to a readable string.

        Args:
            action: Catanatron action object

        Returns:
            Human-readable action description
        """
        try:
            # Try to use Catanatron's string representation
            if hasattr(action, '__str__'):
                return str(action)
        except AttributeError:
            # Catanatron 3.x has a bug where action_repr tries to call .value on string colors
            pass

        # Fallback: construct a basic description
        try:
            action_type = str(type(action).__name__)

            # Handle different action types
            if hasattr(action, 'action_type'):
                action_type = str(action.action_type)

            # Try to get color if available
            color_str = ""
            if hasattr(action, 'color'):
                color_str = f" for {action.color}"

            return f"{action_type}{color_str}"
        except Exception:
            return "Action"

    def _build_context(self, recent_moves: List[str] = None, player_state: Dict[str, Any] = None) -> str:
        """
        Build contextual information to help the LLM make better decisions.

        Args:
            recent_moves: List of recent game moves
            player_state: Current player state

        Returns:
            Context string
        """
        context_parts = []

        # Add recent moves context
        if recent_moves and len(recent_moves) > 0:
            recent_context = "Recent moves: " + ", ".join(recent_moves[-3:])
            context_parts.append(recent_context)

        # Add strategic context based on game state
        if player_state:
            vp = player_state.get("victory_points", 0)
            if vp >= 8:
                context_parts.append("You're close to winning! Focus on reaching 10 victory points.")
            elif vp <= 2:
                context_parts.append("Early game - focus on expansion and resource generation.")

        # Combine context
        if context_parts:
            return " ".join(context_parts)

        return "Choose your action carefully to maximize your chances of winning."

    def build_trade_prompt(
        self,
        player_state: Dict[str, Any],
        trade_options: List[Dict[str, Any]]
    ) -> str:
        """
        Build a prompt specifically for trading decisions.

        Args:
            player_state: Current player state with resources
            trade_options: List of possible trades

        Returns:
            Formatted trading prompt
        """
        resources = player_state.get("resources", {})

        prompt = f"""Trading Decision in Settlers of Catan

Your current resources: {self._format_resources(resources)}

Available trade options:
"""
        for i, trade in enumerate(trade_options, 1):
            give = trade.get("give", {})
            receive = trade.get("receive", {})
            prompt += f"\n{i}. Give: {self._format_resources(give)} → Receive: {self._format_resources(receive)}"

        prompt += "\n\nWhich trade would you like to make? Choose the number or 'none' to skip trading."

        return prompt

    def _format_resources(self, resources: Dict[str, int]) -> str:
        """
        Format resource dictionary into readable string.

        Args:
            resources: Dictionary of resource name to count

        Returns:
            Formatted resource string
        """
        if not resources:
            return "none"

        formatted = []
        for resource, count in resources.items():
            if count > 0:
                formatted.append(f"{count} {resource}")

        return ", ".join(formatted) if formatted else "none"
