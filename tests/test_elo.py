"""
Tests for Elo rating system.
"""

import pytest
import tempfile
import json
from pathlib import Path

from src.elo import EloRating, DEFAULT_ELO, DEFAULT_K_FACTOR


class TestEloRating:
    """Test cases for EloRating class."""

    @pytest.fixture
    def temp_ratings_file(self):
        """Create a temporary ratings file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            yield f.name
        # Cleanup handled by test

    @pytest.fixture
    def elo(self, temp_ratings_file):
        """Create an EloRating instance with temporary file."""
        return EloRating(ratings_file=temp_ratings_file)

    def test_initialization(self, elo):
        """Test that EloRating initializes correctly."""
        assert elo.k_factor == DEFAULT_K_FACTOR
        assert elo.default_elo == DEFAULT_ELO
        assert len(elo.ratings) == 0
        assert len(elo.history) == 0

    def test_default_rating(self, elo):
        """Test that new players get default rating."""
        assert elo.get_rating("new_player") == DEFAULT_ELO

    def test_expected_score_equal_ratings(self, elo):
        """Test expected score when ratings are equal."""
        expected = elo._expected_score(1500, 1500)
        assert expected == pytest.approx(0.5, abs=0.001)

    def test_expected_score_higher_rating(self, elo):
        """Test expected score when player has higher rating."""
        expected = elo._expected_score(1700, 1500)
        # Higher rated player should expect > 0.5
        assert expected > 0.5
        assert expected < 1.0

    def test_expected_score_lower_rating(self, elo):
        """Test expected score when player has lower rating."""
        expected = elo._expected_score(1300, 1500)
        # Lower rated player should expect < 0.5
        assert expected < 0.5
        assert expected > 0.0

    def test_actual_score_placements(self, elo):
        """Test actual score calculation for different placements."""
        assert elo._actual_score(1, 4) == pytest.approx(1.0)
        assert elo._actual_score(2, 4) == pytest.approx(0.667, abs=0.01)
        assert elo._actual_score(3, 4) == pytest.approx(0.333, abs=0.01)
        assert elo._actual_score(4, 4) == pytest.approx(0.0)

    def test_update_ratings_basic(self, elo):
        """Test basic rating update for a 4-player game."""
        game_result = {
            "scores": {
                "player_a": 10,  # 1st
                "player_b": 8,   # 2nd
                "player_c": 6,   # 3rd
                "player_d": 4    # 4th
            }
        }

        changes = elo.update_ratings(game_result)

        # All players should have ratings now
        assert len(elo.ratings) == 4

        # Winner should gain rating
        assert changes["player_a"]["change"] > 0
        # Last place should lose rating
        assert changes["player_d"]["change"] < 0

        # Middle players change depends on expected vs actual
        # With equal starting ratings, 2nd should gain slightly, 3rd should lose slightly

    def test_update_ratings_persistence(self, elo, temp_ratings_file):
        """Test that ratings are saved and can be loaded."""
        game_result = {
            "scores": {
                "player_a": 10,
                "player_b": 5
            }
        }

        elo.update_ratings(game_result)
        original_ratings = dict(elo.ratings)

        # Create new instance with same file
        elo2 = EloRating(ratings_file=temp_ratings_file)

        assert elo2.ratings == original_ratings

    def test_update_ratings_history(self, elo):
        """Test that game history is recorded."""
        game_result = {
            "scores": {"p1": 10, "p2": 5}
        }

        elo.update_ratings(game_result, session_id="test_session_123")

        assert len(elo.history) == 1
        assert elo.history[0]["session_id"] == "test_session_123"
        assert "p1" in elo.history[0]["placements"]

    def test_game_counts(self, elo):
        """Test that game counts are tracked."""
        game1 = {"scores": {"p1": 10, "p2": 5}}
        game2 = {"scores": {"p1": 8, "p3": 10}}

        elo.update_ratings(game1)
        elo.update_ratings(game2)

        assert elo.game_counts["p1"] == 2
        assert elo.game_counts["p2"] == 1
        assert elo.game_counts["p3"] == 1

    def test_leaderboard(self, elo):
        """Test leaderboard generation."""
        # Play some games
        elo.update_ratings({"scores": {"p1": 10, "p2": 5, "p3": 3, "p4": 2}})
        elo.update_ratings({"scores": {"p1": 10, "p2": 8, "p3": 6, "p4": 4}})

        leaderboard = elo.get_leaderboard()

        # Should be sorted by rating descending
        assert len(leaderboard) == 4
        assert leaderboard[0]["player_id"] == "p1"  # Winner should be on top
        assert leaderboard[0]["wins"] == 2

    def test_leaderboard_min_games(self, elo):
        """Test leaderboard with minimum games filter."""
        elo.update_ratings({"scores": {"p1": 10, "p2": 5}})
        elo.update_ratings({"scores": {"p1": 10, "p3": 5}})

        # p1 has 2 games, p2 and p3 have 1 each
        leaderboard = elo.get_leaderboard(min_games=2)

        assert len(leaderboard) == 1
        assert leaderboard[0]["player_id"] == "p1"

    def test_head_to_head(self, elo):
        """Test head-to-head statistics."""
        # Play 3 games between p1 and p2
        elo.update_ratings({"scores": {"p1": 10, "p2": 5}})  # p1 wins
        elo.update_ratings({"scores": {"p1": 10, "p2": 8}})  # p1 wins
        elo.update_ratings({"scores": {"p1": 5, "p2": 10}})  # p2 wins

        h2h = elo.get_head_to_head("p1", "p2")

        assert h2h["games_together"] == 3
        assert h2h["p1_wins"] == 2
        assert h2h["p2_wins"] == 1
        assert h2h["p1_better_placement_rate"] == pytest.approx(2/3, abs=0.01)

    def test_reset_ratings(self, elo):
        """Test rating reset."""
        elo.update_ratings({"scores": {"p1": 10, "p2": 5}})
        assert len(elo.ratings) > 0

        elo.reset_ratings(confirm=True)

        assert len(elo.ratings) == 0
        assert len(elo.history) == 0
        assert len(elo.game_counts) == 0

    def test_format_leaderboard(self, elo):
        """Test leaderboard string formatting."""
        elo.update_ratings({"scores": {"player_a": 10, "player_b": 5}})

        formatted = elo.format_leaderboard()

        assert "LEADERBOARD" in formatted
        assert "player_a" in formatted
        assert "player_b" in formatted

    def test_rating_convergence(self, elo):
        """Test that ratings converge over many games."""
        # Simulate p1 winning 80% of games against p2
        for i in range(20):
            if i % 5 == 0:
                elo.update_ratings({"scores": {"p1": 5, "p2": 10}})  # p2 wins 20%
            else:
                elo.update_ratings({"scores": {"p1": 10, "p2": 5}})  # p1 wins 80%

        # p1 should have significantly higher rating
        assert elo.get_rating("p1") > elo.get_rating("p2")
        assert elo.get_rating("p1") - elo.get_rating("p2") > 100

    def test_player_key_parsing(self, elo):
        """Test that player keys with colons are handled correctly."""
        game_result = {
            "scores": {
                "Claude Sonnet:RED": 10,
                "GPT-4:BLUE": 8,
                "Gemini:WHITE": 6,
                "Haiku:ORANGE": 4
            }
        }

        changes = elo.update_ratings(game_result)

        # Should extract just the model name part
        assert "Claude Sonnet" in elo.ratings
        assert "GPT-4" in elo.ratings
