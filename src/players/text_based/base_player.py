"""
Base LLM Player for Settlers of Catan.

Abstract base class that wraps Catanatron's Player interface for LLM-based players.
Handles prompt generation, response parsing, and error handling.
"""

import logging
import random
import re
import time
from abc import ABC, abstractmethod
from typing import List, Any, Dict

from catanatron.models.player import Player
from llm_game_utils import GameResultLogger

from ...prompt_builder import CatanPromptBuilder

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds

# Enhanced system prompt with Catan rules and strategy
CATAN_SYSTEM_PROMPT = """You are an expert Settlers of Catan player. Your goal is to be the first to reach the victory point target.

VICTORY POINTS:
- Settlement = 1 VP (max 5)
- City = 2 VP (max 4)
- Longest Road (5+ roads) = 2 VP
- Largest Army (3+ knights played) = 2 VP
- Victory Point dev cards = 1 VP each

BUILDING COSTS:
- Road: 1 wood + 1 brick
- Settlement: 1 wood + 1 brick + 1 wheat + 1 sheep
- City: 3 wheat + 2 ore (upgrades a settlement)
- Dev Card: 1 wheat + 1 sheep + 1 ore

CRITICAL END-GAME STRATEGY (when at 7+ VP):
⚠️ CLOSE OUT THE GAME - Don't stall! If you can gain VP this turn, DO IT:
1. Have 3 wheat + 2 ore? → BUILD CITY NOW (instant +1 VP)
2. Have wood+brick+wheat+sheep? → BUILD SETTLEMENT NOW
3. One road from longest road? → BUILD THAT ROAD
4. Have knight card + would give largest army? → PLAY IT NOW
5. Have VP dev cards + enough to win? → You've won!

DON'T end your turn with resources that could become VP!
DON'T buy dev cards when you could build something for VP!
Trade aggressively (even 4:1) to get resources you need to close out.

Respond with ONLY the action number and a brief explanation."""


class BaseLLMPlayer(Player, ABC):
    """
    Abstract base class for LLM players in Catan.

    Extends Catanatron's Player class and provides:
    - Prompt generation from game state
    - LLM query infrastructure
    - Response parsing and validation
    - Error handling with retries
    - Game logging
    """

    def __init__(
        self,
        color,
        model_name: str,
        session_id: str = None,
        logger: GameResultLogger = None,
        is_bot: bool = True,
        prompt_format: str = "toon",
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        mode: str = "text"
    ):
        """
        Initialize base LLM player.

        Args:
            color: Catanatron color enum
            model_name: Name of the LLM model (for logging)
            session_id: Optional session ID for logging
            logger: Optional GameResultLogger instance
            is_bot: Whether this is a bot player
            prompt_format: Prompt format - "json", "json-minified", or "toon"
            max_retries: Maximum number of retries on API failure
            retry_delay: Delay between retries in seconds
            mode: Player mode - "text" or "mcp" (for display purposes)
        """
        super().__init__(color, is_bot)
        self.model_name = model_name
        self.mode = mode
        self.session_id = session_id
        self.logger = logger
        self.prompt_format = prompt_format
        self.prompt_builder = CatanPromptBuilder(prompt_format=prompt_format)
        self.recent_moves = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.move_count = 0
        self.error_count = 0
        self.max_retries = max_retries
        self.retry_delay = retry_delay

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

        Raises:
            Exception: If the API call fails (will be retried by query_llm_with_retry)
        """
        pass

    def query_llm_with_retry(self, prompt: str) -> tuple[str, float, int, bool]:
        """
        Query LLM with automatic retry on failure.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Tuple of (response_text, cost, tokens_used, was_error)
            was_error is True if all retries failed and we're returning a fallback
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response, cost, tokens = self.query_llm(prompt)
                return (response, cost, tokens, False)
            except Exception as e:
                last_error = e
                self.error_count += 1
                self.log.warning(
                    f"API call failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff

        # All retries failed
        self.log.error(f"All {self.max_retries} API attempts failed: {last_error}")
        # Return fallback with flag indicating error
        return ("1", 0.0, 0, True)

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

            # Query LLM with retry
            self.log.debug(f"Querying LLM with prompt (len={len(prompt)})")
            response, cost, tokens, was_error = self.query_llm_with_retry(prompt)

            # Update stats
            self.total_cost += cost
            self.total_tokens += tokens
            self.move_count += 1

            # Log game progress
            self._log_game_progress(game)

            # If API failed, use random action instead of parsing "1"
            if was_error:
                selected_action = self._fallback_action(playable_actions)
            else:
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
                        "response": response[:200] if not was_error else "[API_ERROR]",
                        "cost": cost,
                        "tokens": tokens,
                        "api_error": was_error
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
            response_text = response.strip()
            num_actions = len(playable_actions)

            # Pattern 1: Look for "Action: N", "Action N", "**Action: N**", etc.
            action_pattern = re.search(r'\*{0,2}[Aa]ction[:\s]*(\d+)\*{0,2}', response_text)
            if action_pattern:
                action_num = int(action_pattern.group(1))
                if 1 <= action_num <= num_actions:
                    return playable_actions[action_num - 1]

            # Pattern 2: Look for standalone number at start of response or after newline
            # Matches "1.", "1)", "1:", "1 -", or just "1" at line start
            line_start_pattern = re.search(r'(?:^|\n)\s*(\d+)[\.\)\:\s\-]', response_text)
            if line_start_pattern:
                action_num = int(line_start_pattern.group(1))
                if 1 <= action_num <= num_actions:
                    return playable_actions[action_num - 1]

            # Pattern 3: Find first standalone number in reasonable range
            all_numbers = re.findall(r'\b(\d+)\b', response_text[:500])  # Check first 500 chars
            for num_str in all_numbers:
                num = int(num_str)
                if 1 <= num <= num_actions:
                    return playable_actions[num - 1]

            # Pattern 4: Try to match action description keywords
            response_lower = response_text.lower()
            for i, action in enumerate(playable_actions):
                action_str = self._safe_action_str(action).lower()
                # Check for key parts of action description
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

    def _log_game_progress(self, game) -> None:
        """
        Log current game progress with all players' VPs and running cost.

        Args:
            game: Catanatron game object
        """
        try:
            turn_num = game.state.num_turns

            # Build VP string for all players
            vp_parts = []
            for color, player_index in game.state.color_to_index.items():
                vp = game.state.player_state.get(f"P{player_index}_ACTUAL_VICTORY_POINTS", 0)
                vp_parts.append(f"{color}:{vp}vp")

            vp_str = " ".join(vp_parts)

            # Format current player info with mode
            mode_str = f" ({self.mode.upper()})" if hasattr(self, 'mode') else ""
            player_info = f"{self.color}{mode_str} moving"

            # Log the progress line (flush for immediate output when piped)
            print(f"[Turn {turn_num}] {vp_str} | {player_info} | ${self.total_cost:.2f}", flush=True)

        except Exception as e:
            # Don't let logging errors break the game
            self.log.debug(f"Error logging game progress: {e}")

    def reset_state(self):
        """Reset state between games."""
        self.recent_moves = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.move_count = 0
        self.error_count = 0

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
            "error_count": self.error_count,
            "avg_cost_per_move": self.total_cost / self.move_count if self.move_count > 0 else 0
        }

    def __repr__(self):
        return f"{self.__class__.__name__}({self.model_name}):{self.color}"
