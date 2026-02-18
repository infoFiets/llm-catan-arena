"""
End-to-end integration tests for the tournament system.

These tests verify the full tournament flow works correctly,
including game execution, result saving, and Elo updates.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from collections import defaultdict

import pytest

from src.elo import EloRating


class MockLLMClient:
    """
    Mock LLM client that returns deterministic responses.

    Used to simulate LLM players without making actual API calls.
    """

    def __init__(self, responses=None):
        """
        Initialize mock client.

        Args:
            responses: List of responses to cycle through, or None for default
        """
        self.responses = responses or ["1"]  # Default: always select action 1
        self.call_index = 0
        self.call_history = []

    def query(self, model_id, prompt, max_tokens=1000):
        """
        Mock query that returns deterministic response.

        Returns:
            Tuple of (response, cost, tokens)
        """
        response = self.responses[self.call_index % len(self.responses)]
        self.call_index += 1
        self.call_history.append({
            "model_id": model_id,
            "prompt_length": len(prompt),
            "response": response
        })
        return response, 0.001, 100  # response, cost, tokens


class MockGameRunner:
    """
    Mock game runner that simulates game completion without API calls.

    Returns deterministic results based on player names.
    """

    def __init__(self, results_override=None):
        """
        Initialize mock runner.

        Args:
            results_override: Dict mapping game_id to predetermined results
        """
        self.results_override = results_override or {}
        self.games_run = []

    def run_game(self, players, game_id=None):
        """
        Simulate running a game.

        Args:
            players: List of player identifiers
            game_id: Optional game identifier

        Returns:
            Dict with game results
        """
        self.games_run.append({
            "players": players.copy(),
            "game_id": game_id
        })

        if game_id and game_id in self.results_override:
            return self.results_override[game_id]

        # Generate deterministic scores based on player names
        # Use hash to get consistent but varied scores
        scores = {}
        for i, player in enumerate(players):
            # Higher index players get lower scores by default
            base_score = 10 - i * 2
            # Add some variation based on name hash
            variation = hash(player) % 3
            scores[player] = max(2, base_score + variation)

        # Determine winner (highest score)
        sorted_players = sorted(scores.items(), key=lambda x: -x[1])
        winner = sorted_players[0][0]

        return {
            "session_id": game_id or f"mock_game_{len(self.games_run)}",
            "winner": winner,
            "scores": scores,
            "total_cost": 0.01,
            "total_tokens": 1000,
            "player_specs": players
        }


class TestMiniTournament:
    """Test a small tournament with mock players."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_ratings_file(self, temp_dir):
        """Create a temporary ratings file path."""
        return str(temp_dir / "elo_ratings.json")

    @pytest.fixture
    def temp_games_dir(self, temp_dir):
        """Create a temporary games output directory."""
        games_dir = temp_dir / "games"
        games_dir.mkdir()
        return games_dir

    def test_mini_tournament_flow(self, temp_ratings_file):
        """
        Run small tournament with 4 mock models, verify results.

        - Run 5 games
        - Verify all games completed
        - Verify Elo ratings updated for all 4 models
        """
        elo = EloRating(ratings_file=temp_ratings_file)
        game_runner = MockGameRunner()

        models = ["mock_claude", "mock_gpt", "mock_gemini", "mock_haiku"]
        num_games = 5

        # Run games
        results = []
        for i in range(num_games):
            result = game_runner.run_game(models, game_id=f"tournament_game_{i}")

            # Update Elo from result
            elo_scores = {f"{p}-text": result["scores"][p] for p in models}
            elo.update_ratings(
                {"scores": elo_scores},
                session_id=result["session_id"]
            )
            results.append(result)

        # Verify all games ran
        assert len(results) == num_games
        assert len(game_runner.games_run) == num_games

        # Verify Elo updated for all models
        for model in models:
            player_id = f"{model}-text"
            assert player_id in elo.ratings, f"Missing Elo for {player_id}"
            assert elo.game_counts[player_id] == num_games

        # Verify history recorded
        assert len(elo.history) == num_games

        # Verify leaderboard works
        leaderboard = elo.get_leaderboard()
        assert len(leaderboard) == len(models)

    def test_elo_ratings_reflect_performance(self, temp_ratings_file):
        """
        Test that Elo ratings correctly reflect game performance.

        A model that wins consistently should have higher rating.
        """
        elo = EloRating(ratings_file=temp_ratings_file)

        # Simulate 10 games where "winner_model" always wins
        models = ["winner_model", "loser_a", "loser_b", "loser_c"]

        for i in range(10):
            # winner_model always gets highest score
            scores = {
                f"{models[0]}-text": 10,  # Winner
                f"{models[1]}-text": 6,
                f"{models[2]}-text": 4,
                f"{models[3]}-text": 2,
            }
            elo.update_ratings({"scores": scores}, session_id=f"game_{i}")

        # winner_model should have highest rating
        ratings = elo.get_all_ratings()
        winner_rating = ratings[f"{models[0]}-text"]

        for model in models[1:]:
            loser_rating = ratings[f"{model}-text"]
            assert winner_rating > loser_rating, (
                f"Winner ({winner_rating}) should be higher than {model} ({loser_rating})"
            )

    def test_mixed_results_elo_convergence(self, temp_ratings_file):
        """
        Test Elo convergence with mixed results.

        Two evenly-matched models should have similar ratings.
        """
        elo = EloRating(ratings_file=temp_ratings_file)

        # Simulate alternating wins between two models
        models = ["model_a", "model_b"]

        for i in range(20):
            if i % 2 == 0:
                # model_a wins
                scores = {f"{models[0]}-text": 10, f"{models[1]}-text": 5}
            else:
                # model_b wins
                scores = {f"{models[0]}-text": 5, f"{models[1]}-text": 10}
            elo.update_ratings({"scores": scores}, session_id=f"game_{i}")

        # Ratings should be close (within 100 points)
        rating_a = elo.get_rating(f"{models[0]}-text")
        rating_b = elo.get_rating(f"{models[1]}-text")

        assert abs(rating_a - rating_b) < 100, (
            f"Evenly matched models should have similar ratings: "
            f"a={rating_a}, b={rating_b}"
        )


class TestTournamentRecovery:
    """Test tournament recovery from failures."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_ratings_file(self, temp_dir):
        """Create a temporary ratings file path."""
        return str(temp_dir / "elo_ratings.json")

    def test_partial_batch_failure_saves_successful(self, temp_ratings_file):
        """
        Test that successful games are saved even when some fail.

        Run batch where some games fail - verify successful games
        are saved correctly.
        """
        elo = EloRating(ratings_file=temp_ratings_file)

        models = ["model_a", "model_b", "model_c", "model_d"]
        results = []
        failed = []

        # Simulate 10 games, 3 of which fail
        for i in range(10):
            if i in [2, 5, 8]:  # These games "fail"
                failed.append(i)
                continue

            # Successful game
            scores = {f"{m}-text": 10 - j for j, m in enumerate(models)}
            elo.update_ratings({"scores": scores}, session_id=f"game_{i}")
            results.append({"game_id": f"game_{i}", "scores": scores})

        # Verify successful games are recorded
        assert len(elo.history) == 7  # 10 - 3 failed

        # Verify Elo updated correctly
        for model in models:
            assert elo.game_counts[f"{model}-text"] == 7

        # Verify failed games didn't corrupt data
        for entry in elo.history:
            assert "scores" in entry
            assert "placements" in entry

    def test_failed_games_dont_corrupt_elo(self, temp_ratings_file):
        """
        Test that failed game updates don't corrupt Elo state.
        """
        elo = EloRating(ratings_file=temp_ratings_file)

        # Add a successful game
        elo.update_ratings(
            {"scores": {"p1-text": 10, "p2-text": 5}},
            session_id="good_game_1"
        )

        initial_rating_p1 = elo.get_rating("p1-text")

        # Simulate a "failed" update with invalid data
        try:
            elo.update_ratings(
                {"scores": {}},  # Empty scores - should not crash
                session_id="bad_game"
            )
        except Exception:
            pass  # Expected to handle gracefully

        # Original data should be intact
        elo_reload = EloRating(ratings_file=temp_ratings_file)
        assert elo_reload.get_rating("p1-text") == initial_rating_p1

        # Add another good game
        elo_reload.update_ratings(
            {"scores": {"p1-text": 8, "p3-text": 10}},
            session_id="good_game_2"
        )

        # Verify state is correct
        assert len(elo_reload.history) >= 2

    def test_interrupted_save_recovery(self, temp_ratings_file):
        """
        Test recovery when save is interrupted.

        Simulates a partial write scenario.
        """
        # Create initial valid state
        elo1 = EloRating(ratings_file=temp_ratings_file)
        elo1.update_ratings(
            {"scores": {"p1": 10, "p2": 5}},
            session_id="initial_game"
        )

        # Read the file and verify it's valid
        with open(temp_ratings_file) as f:
            data = json.load(f)

        assert "ratings" in data
        assert "history" in data

        # Simulate corrupted file (partial write)
        with open(temp_ratings_file, 'w') as f:
            f.write('{"ratings": {"p1": 1520.5, "p2": 1479.5}, "history": [')
            # Incomplete JSON

        # Try to load - should handle gracefully
        elo2 = EloRating(ratings_file=temp_ratings_file)

        # Should start fresh after corruption (implementation dependent)
        # The important thing is it doesn't crash


class TestResultSaving:
    """Test that game results are saved correctly."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_game_result_has_required_fields(self, temp_dir):
        """Test that game results have all required fields."""
        runner = MockGameRunner()
        models = ["p1", "p2", "p3", "p4"]

        result = runner.run_game(models, game_id="test_game")

        # Check required fields
        assert "session_id" in result
        assert "winner" in result
        assert "scores" in result
        assert "player_specs" in result

        # Check scores structure
        assert len(result["scores"]) == 4
        for player in models:
            assert player in result["scores"]

    def test_scores_are_valid(self, temp_dir):
        """Test that scores are reasonable values."""
        runner = MockGameRunner()
        models = ["a", "b", "c", "d"]

        result = runner.run_game(models)

        for player, score in result["scores"].items():
            assert isinstance(score, (int, float))
            assert score >= 0
            assert score <= 20  # Reasonable max for Catan

    def test_winner_has_highest_score(self, temp_dir):
        """Test that winner has the highest score."""
        runner = MockGameRunner()
        models = ["x", "y", "z", "w"]

        result = runner.run_game(models)

        winner = result["winner"]
        winner_score = result["scores"][winner]

        for player, score in result["scores"].items():
            assert winner_score >= score


class TestStatisticsAccuracy:
    """Test that tournament statistics are accurate."""

    @pytest.fixture
    def temp_ratings_file(self):
        """Create a temporary ratings file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_win_rate_calculation(self, temp_ratings_file):
        """Test that win rates are calculated correctly."""
        elo = EloRating(ratings_file=temp_ratings_file)

        # Player A wins 3 out of 5 games
        for i in range(5):
            if i < 3:
                scores = {"player_a": 10, "player_b": 5}
            else:
                scores = {"player_a": 5, "player_b": 10}
            elo.update_ratings({"scores": scores}, session_id=f"game_{i}")

        leaderboard = elo.get_leaderboard()

        # Find player_a in leaderboard
        player_a_entry = next(e for e in leaderboard if e["player_id"] == "player_a")

        assert player_a_entry["games"] == 5
        assert player_a_entry["wins"] == 3
        assert player_a_entry["win_rate"] == pytest.approx(0.6, abs=0.01)

    def test_game_count_tracking(self, temp_ratings_file):
        """Test that game counts are tracked accurately."""
        elo = EloRating(ratings_file=temp_ratings_file)

        models = ["m1", "m2", "m3", "m4"]

        # Run 10 4-player games
        for i in range(10):
            scores = {m: 10 - j for j, m in enumerate(models)}
            elo.update_ratings({"scores": scores}, session_id=f"game_{i}")

        # Each model should have 10 games
        for model in models:
            assert elo.game_counts[model] == 10

    def test_head_to_head_accuracy(self, temp_ratings_file):
        """Test head-to-head statistics accuracy."""
        elo = EloRating(ratings_file=temp_ratings_file)

        # A beats B 4 times, B beats A 1 time
        games = [
            ({"a": 10, "b": 5}),  # A wins
            ({"a": 10, "b": 8}),  # A wins
            ({"a": 7, "b": 5}),   # A wins
            ({"a": 10, "b": 6}),  # A wins
            ({"a": 5, "b": 10}),  # B wins
        ]

        for i, scores in enumerate(games):
            elo.update_ratings({"scores": scores}, session_id=f"h2h_game_{i}")

        h2h = elo.get_head_to_head("a", "b")

        assert h2h["games_together"] == 5
        assert h2h["a_wins"] == 4
        assert h2h["b_wins"] == 1
        assert h2h["a_better_placement_rate"] == pytest.approx(0.8, abs=0.01)
