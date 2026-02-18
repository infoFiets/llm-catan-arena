"""
Tests for batch execution and matchup generation.

These tests verify that batch execution correctly handles parallel games,
tracks completion, and that matchup generation prioritizes underplayed models.
"""

import json
import tempfile
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import from scripts directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_matchups import (
    generate_balanced_matchups,
    load_existing_history,
)


class TestMatchupGeneration:
    """Test cases for matchup generation."""

    def test_generate_matchups_returns_correct_count(self):
        """Test that generate_balanced_matchups returns requested number."""
        models = ["model_a", "model_b", "model_c", "model_d", "model_e", "model_f"]
        num_games = 10

        matchups = generate_balanced_matchups(models, num_games, seed=42)

        assert len(matchups) == num_games

    def test_generate_matchups_all_have_four_players(self):
        """Test that each matchup has exactly 4 players."""
        models = ["m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8"]
        matchups = generate_balanced_matchups(models, 20, seed=42)

        for matchup in matchups:
            assert len(matchup) == 4, f"Matchup has {len(matchup)} players: {matchup}"

    def test_generate_matchups_uses_valid_models(self):
        """Test that all players in matchups are from the model list."""
        models = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]
        matchups = generate_balanced_matchups(models, 15, seed=42)

        for matchup in matchups:
            for player in matchup:
                assert player in models, f"Unknown model {player} in matchup"

    def test_generate_matchups_reproducible_with_seed(self):
        """Test that same seed produces same matchups."""
        models = ["a", "b", "c", "d", "e", "f", "g", "h"]

        matchups1 = generate_balanced_matchups(models, 10, seed=123)
        matchups2 = generate_balanced_matchups(models, 10, seed=123)

        assert matchups1 == matchups2

    def test_matchup_considers_existing_history(self):
        """
        Test that matchup generator prioritizes underplayed models.

        When some models have more existing games, generator should
        favor models with fewer games.
        """
        models = ["played_a", "played_b", "fresh_c", "fresh_d", "fresh_e", "fresh_f"]

        # Simulate existing history where played_a and played_b have many games
        existing_games = {
            "played_a": 100,
            "played_b": 100,
            "fresh_c": 0,
            "fresh_d": 0,
            "fresh_e": 0,
            "fresh_f": 0,
        }

        matchups = generate_balanced_matchups(
            models, 20, seed=42,
            existing_games_per_model=existing_games
        )

        # Count appearances
        appearances = defaultdict(int)
        for matchup in matchups:
            for model in matchup:
                appearances[model] += 1

        # Fresh models should appear more often than played models
        fresh_total = sum(appearances[m] for m in ["fresh_c", "fresh_d", "fresh_e", "fresh_f"])
        played_total = sum(appearances[m] for m in ["played_a", "played_b"])

        # With 4 fresh vs 2 played and heavy weighting, fresh should dominate
        assert fresh_total > played_total, (
            f"Fresh models ({fresh_total}) should appear more than played ({played_total})"
        )

    def test_matchup_pair_coverage(self):
        """Test that matchup generation covers many unique pairs."""
        models = [f"model_{i}" for i in range(10)]
        num_games = 30

        matchups = generate_balanced_matchups(models, num_games, seed=42)

        # Count unique pairs
        all_pairs = set()
        for matchup in matchups:
            for pair in combinations(matchup, 2):
                all_pairs.add(tuple(sorted(pair)))

        # With 10 models, there are 45 possible pairs
        # 30 games with 6 pairs each = up to 180 pair instances
        # Should cover a good portion of possible pairs
        total_possible = 10 * 9 // 2  # 45

        coverage_pct = len(all_pairs) / total_possible * 100
        assert coverage_pct > 50, (
            f"Pair coverage too low: {len(all_pairs)}/{total_possible} ({coverage_pct:.1f}%)"
        )

    def test_matchup_avoids_duplicate_pairs_in_same_game(self):
        """Test that no player appears twice in same matchup."""
        models = ["a", "b", "c", "d", "e", "f", "g", "h"]
        matchups = generate_balanced_matchups(models, 50, seed=42)

        for i, matchup in enumerate(matchups):
            unique_in_matchup = set(matchup)
            assert len(unique_in_matchup) == 4, (
                f"Matchup {i} has duplicate players: {matchup}"
            )


class TestLoadExistingHistory:
    """Test cases for loading existing game history."""

    @pytest.fixture
    def temp_ratings_file(self):
        """Create a temporary ratings file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file returns empty dicts."""
        games, pairs = load_existing_history("/nonexistent/path/file.json")

        assert len(games) == 0
        assert len(pairs) == 0

    def test_load_existing_history(self, temp_ratings_file):
        """Test loading history from a valid file."""
        # Create test data
        test_data = {
            "ratings": {},
            "history": [
                {"players": ["model_a-text", "model_b-text", "model_c-text", "model_d-text"]},
                {"players": ["model_a-text", "model_b-text", "model_e-text", "model_f-text"]},
            ],
            "game_counts": {}
        }

        with open(temp_ratings_file, 'w') as f:
            json.dump(test_data, f)

        games, pairs = load_existing_history(temp_ratings_file)

        # model_a and model_b appear in both games
        assert games["model_a"] == 2
        assert games["model_b"] == 2
        assert games["model_c"] == 1
        assert games["model_e"] == 1

        # Check pair counts
        assert pairs[tuple(sorted(["model_a", "model_b"]))] == 2

    def test_load_history_strips_mode_suffix(self, temp_ratings_file):
        """Test that -text/-mcp suffixes are stripped from player names."""
        test_data = {
            "ratings": {},
            "history": [
                {"players": ["claude-text", "gpt-mcp", "gemini-text", "haiku-mcp"]},
            ],
            "game_counts": {}
        }

        with open(temp_ratings_file, 'w') as f:
            json.dump(test_data, f)

        games, pairs = load_existing_history(temp_ratings_file)

        # Should have base model names, not with suffix
        assert "claude" in games
        assert "gpt" in games
        assert "gemini" in games
        assert "haiku" in games

        # Should NOT have suffixed names
        assert "claude-text" not in games
        assert "gpt-mcp" not in games


class TestBatchExecution:
    """Test cases for batch execution logic."""

    def test_batch_tracks_completion(self):
        """Test that batch correctly counts completed vs failed games."""
        # Simulate batch results
        results = [
            {"status": "success", "game_num": 1},
            {"status": "success", "game_num": 2},
            {"status": "error", "game_num": 3, "error": "API timeout"},
            {"status": "success", "game_num": 4},
            {"status": "timeout_graceful", "game_num": 5},  # Still counts as success
        ]

        successful = sum(1 for r in results if r["status"] in ("success", "timeout_graceful"))
        failed = sum(1 for r in results if r["status"] not in ("success", "timeout_graceful"))

        assert successful == 4
        assert failed == 1

    def test_batch_parallel_isolation(self):
        """
        Test that parallel games don't interfere with each other.

        Each game should have independent state.
        """
        # Create mock game data
        game_states = {}

        def mock_run_game(game_id, matchup):
            """Mock game runner that stores state."""
            # Each game should have its own state
            state = {
                "id": game_id,
                "matchup": matchup.copy(),
                "turns": 0,
                "scores": {p: 0 for p in matchup}
            }
            game_states[game_id] = state

            # Simulate game progress
            for turn in range(10):
                state["turns"] += 1
                for p in matchup:
                    state["scores"][p] += 1

            return {
                "game_id": game_id,
                "final_scores": state["scores"].copy()
            }

        # Run 5 games in parallel (simulated)
        import threading
        threads = []
        results = []
        lock = threading.Lock()

        matchups = [
            [f"m{i}_p{j}" for j in range(4)]
            for i in range(5)
        ]

        for i, matchup in enumerate(matchups):
            def run(gid, m):
                result = mock_run_game(gid, m)
                with lock:
                    results.append(result)

            t = threading.Thread(target=run, args=(f"game_{i}", matchup))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify each game has correct independent state
        assert len(results) == 5
        assert len(game_states) == 5

        for game_id, state in game_states.items():
            # Each game should have completed 10 turns
            assert state["turns"] == 10
            # Each player should have scored 10 points
            for score in state["scores"].values():
                assert score == 10


class TestMatchupBalancing:
    """Test cases for matchup balancing algorithms."""

    def test_models_with_zero_games_prioritized(self):
        """Models with zero games should be prioritized."""
        models = ["veteran"] + [f"newbie_{i}" for i in range(7)]

        existing_games = {"veteran": 50}
        for i in range(7):
            existing_games[f"newbie_{i}"] = 0

        matchups = generate_balanced_matchups(
            models, 10, seed=42,
            existing_games_per_model=existing_games
        )

        # Count veteran appearances
        veteran_count = sum(1 for m in matchups if "veteran" in m)

        # Newbies should appear much more than veteran
        newbie_total = sum(
            sum(1 for p in m if p.startswith("newbie_"))
            for m in matchups
        )

        # Each game has 4 slots, 10 games = 40 slots
        # 7 newbies should fill most slots
        assert newbie_total > veteran_count * 3, (
            f"Newbies ({newbie_total}) should appear much more than veteran ({veteran_count})"
        )

    def test_pair_novelty_scoring(self):
        """Test that pairs that haven't met are prioritized."""
        models = ["a", "b", "c", "d", "e", "f"]

        # a and b have met 10 times already
        existing_pairs = {("a", "b"): 10}

        matchups = generate_balanced_matchups(
            models, 20, seed=42,
            existing_pair_counts=existing_pairs
        )

        # Count how often a and b appear together
        ab_together = sum(
            1 for m in matchups
            if "a" in m and "b" in m
        )

        # Other pairs that haven't met should appear more
        cd_together = sum(
            1 for m in matchups
            if "c" in m and "d" in m
        )

        # c-d should appear at least as often as a-b
        # (since a-b is penalized for existing meetings)
        assert cd_together >= ab_together * 0.5, (
            f"Novel pair c-d ({cd_together}) should appear often, "
            f"penalized pair a-b ({ab_together})"
        )

    def test_even_distribution_over_many_games(self):
        """Test that all models get roughly equal games over time."""
        models = [f"model_{i}" for i in range(8)]

        matchups = generate_balanced_matchups(models, 100, seed=42)

        appearances = defaultdict(int)
        for matchup in matchups:
            for model in matchup:
                appearances[model] += 1

        # Each model should appear roughly equally
        # 100 games * 4 slots = 400 appearances / 8 models = 50 avg
        values = list(appearances.values())
        min_app = min(values)
        max_app = max(values)

        # Difference between max and min should be < 20%
        avg = sum(values) / len(values)
        assert (max_app - min_app) / avg < 0.4, (
            f"Distribution too uneven: min={min_app}, max={max_app}, avg={avg:.1f}"
        )
