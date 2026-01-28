"""
Base LLM Player for Settlers of Catan.

Abstract base class that wraps Catanatron's Player interface for LLM-based players.
Handles prompt generation, response parsing, and error handling.
"""

import logging
import random
from abc import ABC, abstractmethod
from typing import List, Any, Dict

from catanatron.models.player import Player
from llm_game_utils import GameResultLogger

from ...prompt_builder import CatanPromptBuilder


class BaseLLMPlayer(Player, ABC):
    """
    Abstract base class for LLM players in Catan.

    Extends Catanatron's Player class and provides:
    - Prompt generation from game state
    - LLM query infrastructure
    - Response parsing and validation
    - Error handling and fallback logic
    - Game logging
    """

    def __init__(
        self,
        color,
        model_name: str,
        session_id: str = None,
        logger: GameResultLogger = None,
        is_bot: bool = True
    ):
        """
        Initialize base LLM player.

        Args:
            color: Catanatron color enum
            model_name: Name of the LLM model (for logging)
            session_id: Optional session ID for logging
            logger: Optional GameResultLogger instance
            is_bot: Whether this is a bot player
        """
        super().__init__(color, is_bot)
        self.model_name = model_name
        self.session_id = session_id
        self.logger = logger
        self.prompt_builder = CatanPromptBuilder()
        self.recent_moves = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.move_count = 0

        # Set up logging
        self.log = logging.getLogger(f"{self.__class__.__name__}:{color}")

    @abstractmethod
    def query_llm(self, prompt: str) -> tuple[str, float, int]:
        """
        Query the LLM with a prompt.

        Must be implemented by subclasses to call their specific LLM.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Tuple of (response_text, cost, tokens_used)
        """
        pass

    def decide(self, game, playable_actions):
        """
        Main decision method called by Catanatron.

        Args:
            game: Complete game state (read-only)
            playable_actions: List of valid actions at this moment

        Returns:
            One action from playable_actions
        """
        try:
            # Extract player state from game
            player_state = self._extract_player_state(game)

            # Build prompt
            prompt = self.prompt_builder.build_action_prompt(
                game_state=game,
                player_state=player_state,
                available_actions=playable_actions,
                recent_moves=self.recent_moves[-5:]  # Last 5 moves for context
            )

            # Query LLM
            self.log.debug(f"Querying LLM with prompt (len={len(prompt)})")
            response, cost, tokens = self.query_llm(prompt)

            # Update stats
            self.total_cost += cost
            self.total_tokens += tokens
            self.move_count += 1

            # Parse response to select action
            selected_action = self._parse_response(response, playable_actions)

            # Log the move
            if self.logger and self.session_id:
                self.logger.log_move(
                    session_id=self.session_id,
                    player=str(self.color),
                    move_data={
                        "action": self._safe_action_str(selected_action),
                        "prompt_length": len(prompt),
                        "response": response[:200],  # Truncate for storage
                        "cost": cost,
                        "tokens": tokens
                    },
                    turn_number=self.move_count
                )

            # Track move for context
            self.recent_moves.append(self._safe_action_str(selected_action))

            return selected_action

        except Exception as e:
            self.log.error(f"Error in decide(): {e}", exc_info=True)
            # Fallback to random action
            return self._fallback_action(playable_actions)

    def _safe_action_str(self, action: Any) -> str:
        """
        Safely convert action to string, handling Catanatron 3.x bug.

        Catanatron 3.x has a bug in action_repr that calls .value on string colors.
        This method wraps the conversion in a try/except to provide a fallback.

        Args:
            action: Action object to convert

        Returns:
            String representation of the action
        """
        try:
            return str(action)
        except (AttributeError, TypeError):
            # Fallback if Catanatron's action_repr fails
            try:
                action_type = str(type(action).__name__)
                if hasattr(action, 'action_type'):
                    action_type = str(action.action_type)
                return f"{action_type}"
            except:
                return "Action"

    def _extract_player_state(self, game) -> Dict[str, Any]:
        """
        Extract relevant player state from game object.

        Args:
            game: Catanatron game object

        Returns:
            Dictionary with player state information
        """
        try:
            # Get player index from color (Catanatron 3.x uses indexed player_state)
            player_index = game.state.color_to_index[self.color]
            prefix = f"P{player_index}_"

            # Get resources from flattened player_state dict
            resources = {
                "wood": game.state.player_state.get(f"{prefix}WOOD_IN_HAND", 0),
                "brick": game.state.player_state.get(f"{prefix}BRICK_IN_HAND", 0),
                "sheep": game.state.player_state.get(f"{prefix}SHEEP_IN_HAND", 0),
                "wheat": game.state.player_state.get(f"{prefix}WHEAT_IN_HAND", 0),
                "ore": game.state.player_state.get(f"{prefix}ORE_IN_HAND", 0)
            }

            # Get victory points
            victory_points = game.state.player_state.get(f"{prefix}ACTUAL_VICTORY_POINTS", 0)

            # Get buildings (count available vs. total to get built count)
            settlements_available = game.state.player_state.get(f"{prefix}SETTLEMENTS_AVAILABLE", 5)
            settlements = 5 - settlements_available

            cities_available = game.state.player_state.get(f"{prefix}CITIES_AVAILABLE", 4)
            cities = 4 - cities_available

            roads_available = game.state.player_state.get(f"{prefix}ROADS_AVAILABLE", 15)
            roads = 15 - roads_available

            # Get development cards
            dev_cards = []
            knight_count = game.state.player_state.get(f"{prefix}KNIGHT_IN_HAND", 0)
            yop_count = game.state.player_state.get(f"{prefix}YEAR_OF_PLENTY_IN_HAND", 0)
            monopoly_count = game.state.player_state.get(f"{prefix}MONOPOLY_IN_HAND", 0)
            road_building_count = game.state.player_state.get(f"{prefix}ROAD_BUILDING_IN_HAND", 0)
            vp_count = game.state.player_state.get(f"{prefix}VICTORY_POINT_IN_HAND", 0)

            dev_cards.extend(["KNIGHT"] * knight_count)
            dev_cards.extend(["YEAR_OF_PLENTY"] * yop_count)
            dev_cards.extend(["MONOPOLY"] * monopoly_count)
            dev_cards.extend(["ROAD_BUILDING"] * road_building_count)
            dev_cards.extend(["VICTORY_POINT"] * vp_count)

            # Get opponent info (simplified)
            opponents = []
            for opp_color, opp_index in game.state.color_to_index.items():
                if opp_color != self.color:
                    opp_prefix = f"P{opp_index}_"
                    opp_vp = game.state.player_state.get(f"{opp_prefix}ACTUAL_VICTORY_POINTS", 0)
                    opp_resources = sum([
                        game.state.player_state.get(f"{opp_prefix}WOOD_IN_HAND", 0),
                        game.state.player_state.get(f"{opp_prefix}BRICK_IN_HAND", 0),
                        game.state.player_state.get(f"{opp_prefix}SHEEP_IN_HAND", 0),
                        game.state.player_state.get(f"{opp_prefix}WHEAT_IN_HAND", 0),
                        game.state.player_state.get(f"{opp_prefix}ORE_IN_HAND", 0)
                    ])
                    opponents.append({
                        "color": opp_color,
                        "victory_points": opp_vp,
                        "resource_count": opp_resources
                    })

            return {
                "resources": resources,
                "victory_points": victory_points,
                "settlements": settlements,
                "cities": cities,
                "roads": roads,
                "dev_cards": dev_cards,
                "opponents": opponents
            }

        except Exception as e:
            self.log.error(f"Error extracting player state: {e}", exc_info=True)
            return {"resources": {}, "victory_points": 0}

    def _parse_response(self, response: str, playable_actions: List[Any]) -> Any:
        """
        Parse LLM response to select an action.

        Args:
            response: LLM response text
            playable_actions: List of valid actions

        Returns:
            Selected action from playable_actions
        """
        try:
            # Try to extract number from response (1-indexed in prompt)
            response_lower = response.lower().strip()

            # Look for number in response
            for i, _ in enumerate(playable_actions):
                # Check for "1", "1.", "option 1", etc.
                if f"{i+1}" in response_lower.split()[0:3]:  # Check first few words
                    return playable_actions[i]

            # If no clear number, try to match action description
            for i, action in enumerate(playable_actions):
                action_str = self._safe_action_str(action).lower()
                if action_str in response_lower:
                    return playable_actions[i]

            # Default to first action if parsing fails
            self.log.warning(f"Could not parse response, defaulting to first action. Response: {response[:100]}")
            return playable_actions[0]

        except Exception as e:
            self.log.error(f"Error parsing response: {e}")
            return playable_actions[0]

    def _fallback_action(self, playable_actions: List[Any]) -> Any:
        """
        Fallback to random action when LLM fails.

        Args:
            playable_actions: List of valid actions

        Returns:
            Randomly selected action
        """
        self.log.warning("Using fallback random action")
        return random.choice(playable_actions)

    def reset_state(self):
        """Reset state between games."""
        self.recent_moves = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.move_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get player statistics.

        Returns:
            Dictionary with player stats
        """
        return {
            "model": self.model_name,
            "color": self.color,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "move_count": self.move_count,
            "avg_cost_per_move": self.total_cost / self.move_count if self.move_count > 0 else 0
        }

    def __repr__(self):
        return f"{self.__class__.__name__}({self.model_name}):{self.color}"
