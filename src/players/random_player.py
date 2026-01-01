"""
Random Player for Settlers of Catan.

Simple baseline player that makes random decisions.
Useful for comparison with LLM players.
"""

import random
from catanatron.models.player import Player


class RandomPlayer(Player):
    """
    Simple random player for baseline comparison.

    Makes random choices from available actions without any strategy.
    """

    def __init__(self, color):
        """
        Initialize random player.

        Args:
            color: Catanatron color string
        """
        super().__init__(color, is_bot=True)
        self.model_name = "Random"
        self.move_count = 0

    def decide(self, game, playable_actions):
        """
        Choose a random action from available actions.

        Args:
            game: Complete game state (unused)
            playable_actions: List of valid actions

        Returns:
            Randomly selected action
        """
        self.move_count += 1
        return random.choice(playable_actions)

    def reset_state(self):
        """Reset state between games."""
        self.move_count = 0

    def get_stats(self):
        """
        Get player statistics.

        Returns:
            Dictionary with player stats
        """
        return {
            "model": "Random",
            "color": self.color,
            "total_cost": 0.0,
            "total_tokens": 0,
            "move_count": self.move_count,
            "avg_cost_per_move": 0.0
        }

    def __repr__(self):
        return f"RandomPlayer:{self.color}"
