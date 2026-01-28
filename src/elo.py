"""
Elo Rating System for LLM Catan Arena.

Implements multiplayer Elo for 4-player Catan games.
Supports persistent ratings across sessions.
"""

import json
import math
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict


# Default starting Elo
DEFAULT_ELO = 1500
# K-factor controls how much ratings change per game
DEFAULT_K_FACTOR = 32


class EloRating:
    """
    Multiplayer Elo rating system for 4-player games.

    Uses the "average opponent" method:
    - Each player's expected score is calculated against the average rating of opponents
    - Actual score is based on placement (1st=1.0, 2nd=0.67, 3rd=0.33, 4th=0.0)
    """

    def __init__(
        self,
        ratings_file: str = "data/elo_ratings.json",
        k_factor: float = DEFAULT_K_FACTOR,
        default_elo: float = DEFAULT_ELO
    ):
        """
        Initialize Elo rating system.

        Args:
            ratings_file: Path to persist ratings
            k_factor: How much ratings change per game (higher = more volatile)
            default_elo: Starting rating for new players
        """
        self.ratings_file = Path(ratings_file)
        self.k_factor = k_factor
        self.default_elo = default_elo
        self.log = logging.getLogger(__name__)

        # Load existing ratings or start fresh
        self.ratings: Dict[str, float] = {}
        self.history: List[Dict[str, Any]] = []
        self.game_counts: Dict[str, int] = defaultdict(int)

        self._load_ratings()

    def _load_ratings(self):
        """Load ratings from file if exists."""
        if self.ratings_file.exists():
            try:
                with open(self.ratings_file, 'r') as f:
                    data = json.load(f)
                    self.ratings = data.get("ratings", {})
                    self.history = data.get("history", [])
                    self.game_counts = defaultdict(int, data.get("game_counts", {}))
                    self.log.info(f"Loaded {len(self.ratings)} player ratings")
            except Exception as e:
                self.log.error(f"Error loading ratings: {e}")
                self.ratings = {}
                self.history = []
                self.game_counts = defaultdict(int)
        else:
            self.log.info("No existing ratings file, starting fresh")

    def _save_ratings(self):
        """Save ratings to file."""
        self.ratings_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "ratings": self.ratings,
            "history": self.history,
            "game_counts": dict(self.game_counts),
            "last_updated": datetime.now().isoformat()
        }

        with open(self.ratings_file, 'w') as f:
            json.dump(data, f, indent=2)

        self.log.debug(f"Saved ratings to {self.ratings_file}")

    def get_rating(self, player_id: str) -> float:
        """
        Get current rating for a player.

        Args:
            player_id: Unique player identifier (e.g., "claude-mcp", "gpt4-text")

        Returns:
            Current Elo rating
        """
        return self.ratings.get(player_id, self.default_elo)

    def get_all_ratings(self) -> Dict[str, float]:
        """Get all player ratings sorted by rating descending."""
        return dict(sorted(self.ratings.items(), key=lambda x: -x[1]))

    def _expected_score(self, player_rating: float, opponent_avg: float) -> float:
        """
        Calculate expected score against average opponent.

        Uses standard Elo formula:
        E = 1 / (1 + 10^((opponent - player) / 400))

        Args:
            player_rating: Player's current rating
            opponent_avg: Average rating of opponents

        Returns:
            Expected score between 0 and 1
        """
        return 1.0 / (1.0 + math.pow(10, (opponent_avg - player_rating) / 400))

    def _actual_score(self, placement: int, num_players: int = 4) -> float:
        """
        Convert placement to actual score.

        For 4 players:
        - 1st place: 1.0
        - 2nd place: 0.67
        - 3rd place: 0.33
        - 4th place: 0.0

        Args:
            placement: 1-indexed placement (1 = winner)
            num_players: Total players in game

        Returns:
            Score between 0 and 1
        """
        if num_players <= 1:
            return 0.5

        # Linear interpolation from 1.0 (1st) to 0.0 (last)
        return 1.0 - (placement - 1) / (num_players - 1)

    def update_ratings(
        self,
        game_result: Dict[str, Any],
        session_id: str = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Update ratings based on a game result.

        Args:
            game_result: Dict with 'scores' mapping player_id to victory points
                        e.g., {"claude-mcp:RED": 10, "gpt4-text:BLUE": 7, ...}
            session_id: Optional session ID for tracking

        Returns:
            Dict mapping player_id to {"old": X, "new": Y, "change": Z}
        """
        # Extract player IDs and their scores
        player_scores = {}
        for player_key, vp in game_result.get("scores", {}).items():
            # player_key format: "ModelName:COLOR" or "model-mode:COLOR"
            # We want just the model identifier
            player_id = player_key.rsplit(":", 1)[0] if ":" in player_key else player_key
            player_scores[player_id] = vp

        if len(player_scores) < 2:
            self.log.warning("Need at least 2 players to update ratings")
            return {}

        # Sort by score to get placements
        sorted_players = sorted(player_scores.items(), key=lambda x: -x[1])
        placements = {player: i + 1 for i, (player, _) in enumerate(sorted_players)}

        # Get current ratings (or default for new players)
        current_ratings = {p: self.get_rating(p) for p in player_scores}

        # Calculate rating changes
        rating_changes = {}
        num_players = len(player_scores)

        for player_id in player_scores:
            old_rating = current_ratings[player_id]

            # Calculate average opponent rating
            opponents = [r for p, r in current_ratings.items() if p != player_id]
            opponent_avg = sum(opponents) / len(opponents) if opponents else self.default_elo

            # Expected vs actual score
            expected = self._expected_score(old_rating, opponent_avg)
            actual = self._actual_score(placements[player_id], num_players)

            # Calculate new rating
            change = self.k_factor * (actual - expected)
            new_rating = old_rating + change

            # Update stored rating
            self.ratings[player_id] = new_rating
            self.game_counts[player_id] += 1

            rating_changes[player_id] = {
                "old": old_rating,
                "new": new_rating,
                "change": change,
                "placement": placements[player_id],
                "expected": expected,
                "actual": actual
            }

        # Record in history
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "players": list(player_scores.keys()),
            "scores": player_scores,
            "placements": placements,
            "rating_changes": rating_changes
        })

        # Save to file
        self._save_ratings()

        return rating_changes

    def get_leaderboard(self, min_games: int = 0) -> List[Dict[str, Any]]:
        """
        Get leaderboard sorted by rating.

        Args:
            min_games: Minimum games played to be included

        Returns:
            List of dicts with player stats
        """
        leaderboard = []

        for player_id, rating in sorted(self.ratings.items(), key=lambda x: -x[1]):
            games = self.game_counts.get(player_id, 0)

            if games >= min_games:
                # Calculate win rate from history
                wins = sum(
                    1 for h in self.history
                    if player_id in h.get("placements", {})
                    and h["placements"][player_id] == 1
                )

                leaderboard.append({
                    "player_id": player_id,
                    "rating": round(rating, 1),
                    "games": games,
                    "wins": wins,
                    "win_rate": wins / games if games > 0 else 0
                })

        return leaderboard

    def format_leaderboard(self, min_games: int = 0) -> str:
        """
        Format leaderboard as readable string.

        Args:
            min_games: Minimum games to be included

        Returns:
            Formatted leaderboard string
        """
        leaderboard = self.get_leaderboard(min_games)

        if not leaderboard:
            return "No players with enough games yet."

        lines = []
        lines.append("=" * 70)
        lines.append("ELO LEADERBOARD")
        lines.append("=" * 70)
        lines.append(f"{'Rank':<6} {'Player':<25} {'Rating':<10} {'Games':<8} {'Win %':<8}")
        lines.append("-" * 70)

        for i, entry in enumerate(leaderboard, 1):
            lines.append(
                f"{i:<6} {entry['player_id']:<25} {entry['rating']:<10.1f} "
                f"{entry['games']:<8} {entry['win_rate']*100:<7.1f}%"
            )

        lines.append("=" * 70)

        return "\n".join(lines)

    def get_head_to_head(self, player_a: str, player_b: str) -> Dict[str, Any]:
        """
        Get head-to-head stats between two players.

        Args:
            player_a: First player ID
            player_b: Second player ID

        Returns:
            Dict with head-to-head statistics
        """
        games_together = 0
        a_wins = 0
        b_wins = 0
        a_better_placement = 0

        for game in self.history:
            placements = game.get("placements", {})

            if player_a in placements and player_b in placements:
                games_together += 1

                if placements[player_a] == 1:
                    a_wins += 1
                if placements[player_b] == 1:
                    b_wins += 1

                if placements[player_a] < placements[player_b]:
                    a_better_placement += 1

        return {
            "games_together": games_together,
            f"{player_a}_wins": a_wins,
            f"{player_b}_wins": b_wins,
            f"{player_a}_better_placement_rate": a_better_placement / games_together if games_together > 0 else 0,
            f"{player_a}_rating": self.get_rating(player_a),
            f"{player_b}_rating": self.get_rating(player_b),
            "rating_difference": self.get_rating(player_a) - self.get_rating(player_b)
        }

    def reset_ratings(self, confirm: bool = False):
        """
        Reset all ratings to default.

        Args:
            confirm: Must be True to actually reset
        """
        if not confirm:
            self.log.warning("Reset not confirmed. Pass confirm=True to reset.")
            return

        self.ratings = {}
        self.history = []
        self.game_counts = defaultdict(int)
        self._save_ratings()
        self.log.info("All ratings reset")


def update_elo_from_game_result(
    game_result: Dict[str, Any],
    ratings_file: str = "data/elo_ratings.json"
) -> Dict[str, Dict[str, float]]:
    """
    Convenience function to update Elo from a game result.

    Args:
        game_result: Game result dict with 'scores' key
        ratings_file: Path to ratings file

    Returns:
        Rating changes dict
    """
    elo = EloRating(ratings_file)
    return elo.update_ratings(game_result, game_result.get("session_id"))


def print_leaderboard(ratings_file: str = "data/elo_ratings.json", min_games: int = 0):
    """
    Print current leaderboard.

    Args:
        ratings_file: Path to ratings file
        min_games: Minimum games to be included
    """
    elo = EloRating(ratings_file)
    print(elo.format_leaderboard(min_games))
