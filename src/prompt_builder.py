"""
Prompt Builder for Catan Game State.

Converts Catanatron game state into clear, structured prompts for LLM players.
Keeps prompts concise but informative, formatted as multiple choice questions.

Supports multiple formats for token efficiency:
- json: Standard JSON with indentation (default)
- json-minified: Minified JSON without whitespace
- toon: TOON-style format (Token-Oriented Object Notation) for ~53% token reduction
"""

import json
from typing import List, Dict, Any, Literal, Optional
from llm_game_utils import PromptFormatter

# Type alias for format options
PromptFormat = Literal["json", "json-minified", "toon"]


class CatanPromptBuilder:
    """Builds prompts for LLM players in Settlers of Catan."""

    def __init__(self, prompt_format: PromptFormat = "json"):
        """
        Initialize the prompt builder with PromptFormatter.

        Args:
            prompt_format: Prompt format - "json", "json-minified", or "toon"
        """
        self.formatter = PromptFormatter()
        self.prompt_format = prompt_format

    def build_action_prompt(
        self,
        game_state: Any,
        player_state: Dict[str, Any],
        available_actions: List[Any],
        recent_moves: List[str] = None,
        prompt_format: Optional[PromptFormat] = None
    ) -> str:
        """
        Build a prompt for an LLM to choose an action in Catan.

        Args:
            game_state: Catanatron game state object
            player_state: Dictionary with player's current state
            available_actions: List of available Catanatron actions
            recent_moves: Optional list of recent moves for context
            prompt_format: Override format for this call (uses instance default if None)

        Returns:
            Formatted prompt string ready for LLM
        """
        # Use provided format or fall back to instance default
        active_format = prompt_format or self.prompt_format

        # Extract and format game state
        state_dict = self._extract_state_dict(game_state, player_state)

        # Format available actions as readable choices
        action_choices = self._format_actions(available_actions)

        # Build context from recent moves
        context = self._build_context(recent_moves, player_state)

        # Route to appropriate formatter based on format
        if active_format == "toon":
            return self._format_toon_style(game_state, player_state, action_choices, context)
        elif active_format == "json-minified":
            return self._format_json_minified(state_dict, action_choices, context)
        else:
            # Default: standard JSON format
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

    def _format_toon_style(
        self,
        game_state: Any,
        player_state: Dict[str, Any],
        action_choices: List[str],
        context: str
    ) -> str:
        """
        Format prompt using TOON-style (Token-Oriented Object Notation).

        TOON format reduces tokens by ~53% compared to standard JSON by using:
        - Header declarations with schema
        - Tabular data with commas
        - Length guards for arrays

        Args:
            game_state: Catanatron game state object
            player_state: Dictionary with player's current state
            action_choices: List of formatted action strings
            context: Strategic context string

        Returns:
            TOON-formatted prompt string
        """
        # Get turn number from game state (it's in game_state.state.num_turns)
        turn = 0
        if game_state:
            if hasattr(game_state, 'state') and hasattr(game_state.state, 'num_turns'):
                turn = game_state.state.num_turns
            elif hasattr(game_state, 'num_turns'):
                turn = game_state.num_turns

        # Extract resources with consistent ordering
        res = player_state.get("resources", {})
        wood = res.get("wood", 0)
        brick = res.get("brick", 0)
        sheep = res.get("sheep", 0)
        wheat = res.get("wheat", 0)
        ore = res.get("ore", 0)

        # Extract buildings
        settlements = player_state.get("settlements", 0)
        cities = player_state.get("cities", 0)
        roads = player_state.get("roads", 0)

        # Get victory points and dev cards
        vp = player_state.get("victory_points", 0)
        dev_cards = player_state.get("dev_cards", [])

        # Get opponents
        opponents = player_state.get("opponents", [])

        # Build TOON-style prompt
        prompt = f"""SETTLERS OF CATAN - Choose your action

Turn: {turn} | You: {player_state.get('color', 'UNKNOWN')}

Resources{{wood, brick, sheep, wheat, ore}}:
{wood}, {brick}, {sheep}, {wheat}, {ore}

Buildings{{settlements, cities, roads}}:
{settlements}, {cities}, {roads}

VP: {vp}
Dev Cards[{len(dev_cards)}]: {', '.join(dev_cards) if dev_cards else 'none'}

Opponents[{len(opponents)}]{{color, vp, cards}}:
"""
        # Add opponents
        for opp in opponents:
            prompt += f"{opp.get('color', '?')}, {opp.get('victory_points', 0)}, {opp.get('resource_count', 0)}\n"

        # Add actions
        prompt += f"\nActions[{len(action_choices)}]:\n"
        for i, action in enumerate(action_choices, 1):
            prompt += f"{i}. {action}\n"

        # Add context/instructions
        prompt += f"""
{context}

Reply with the action number and brief reasoning."""

        return prompt

    def _format_json_minified(
        self,
        state_dict: Dict[str, Any],
        action_choices: List[str],
        context: str
    ) -> str:
        """
        Format prompt using minified JSON (no whitespace).

        Reduces tokens by ~33% compared to standard JSON.

        Args:
            state_dict: Dictionary with game state
            action_choices: List of formatted action strings
            context: Strategic context string

        Returns:
            JSON-minified prompt string
        """
        # Build complete state for minification
        full_state = {
            "game": "Settlers of Catan",
            "state": state_dict,
            "actions": {str(i+1): action for i, action in enumerate(action_choices)}
        }

        # Minify JSON
        minified = json.dumps(full_state, separators=(',', ':'))

        prompt = f"""{minified}

{context}

Reply with the action number and brief reasoning."""

        return prompt
