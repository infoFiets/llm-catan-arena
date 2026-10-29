"""
Tests for scripts/export_site_json.py, the JSON behind mcgrathtrading.com/benchmarks.

A three-game fixture written into tmp_path: the Elo history and leaderboard.csv as the
tournament writes them, plus the per-game logs the cost comes from.
"""

import csv
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "export_site_json.py"
spec = importlib.util.spec_from_file_location("export_site_json", SCRIPT)
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


def _move(colour, cost, tokens, error=False):
    return {"player": colour, "turn_number": 1,
            "move_data": {"action": "ActionType.ROLL", "cost": cost, "tokens": tokens, "api_error": error}}


def _game(session, seats, moves, start="2026-02-01T10:00:00", end="2026-02-01T10:30:00"):
    return {
        "session_id": session,
        "players": [f"{alias}:{colour}" for alias, colour in seats],
        "game_config": {"max_turns": 200, "victory_points": 8},
        "start_time": start, "end_time": end,
        "moves": moves, "winner": "", "final_scores": {},
    }


def _history(session, placements):
    return {"timestamp": "2026-02-04T13:00:00", "session_id": session,
            "players": list(placements), "placements": placements}


@pytest.fixture
def data_dir(tmp_path):
    data = tmp_path / "data"
    (data / "games").mkdir(parents=True)
    a, b, c, d = "alpha-text", "beta-text", "gamma-text", "delta-text"
    history = [
        # Game 1 logs short aliases, as the early games did ("a" for alpha and so on).
        _history("Settlers of Catan_20260201_100000", {a: 1, b: 2, c: 3, d: 4}),
        _history("Settlers_of_Catan_20260202_100000_ab", {b: 1, a: 2, c: 3, d: 4}),
        _history("Settlers_of_Catan_20260203_100000_cd", {a: 1, c: 2, b: 3, d: 4}),
    ]
    ratings = {a: 1540.4, b: 1510.2, c: 1490.6, d: 1458.8}
    (data / "elo_ratings.json").write_text(json.dumps({
        "ratings": ratings, "history": history,
        "game_counts": {a: 3, b: 3, c: 3, d: 3}, "last_updated": "2026-02-04T13:09:57",
    }))
    seats = [("RED", "BLUE", "WHITE", "ORANGE")]
    games = [
        _game("Settlers of Catan_20260201_100000", list(zip(["a", "b", "c", "d"], *seats)),
              [_move("RED", 0.10, 100), _move("BLUE", 0.20, 200), _move("WHITE", 0.0, 0, error=True)]),
        _game("Settlers_of_Catan_20260202_100000_ab", list(zip(["beta", "alpha", "gamma", "delta"], *seats)),
              [_move("RED", 0.50, 300), _move("BLUE", 0.05, 50)],
              start="2026-02-02T10:00:00", end="2026-02-02T11:00:00"),
        _game("Settlers_of_Catan_20260203_100000_cd", list(zip(["alpha", "gamma", "beta", "delta"], *seats)),
              [_move("RED", 0.15, 150), _move("BLUE", 0.01, 10)],
              start="2026-02-03T10:00:00", end="2026-02-03T10:45:00"),
        # Not in the Elo history: an errored game. Its cost must not count.
        _game("Settlers_of_Catan_20260204_100000_xx", list(zip(["alpha", "beta", "gamma", "delta"], *seats)),
              [_move("RED", 9.99, 999)], start="2026-02-04T10:00:00", end="2026-02-04T23:00:00"),
    ]
    for g in games:
        (data / "games" / f"{g['session_id']}.json").write_text(json.dumps(g))
    # leaderboard.csv as EloRating.get_leaderboard + the CSV writer produce it.
    with open(data / "leaderboard.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "model", "elo", "games", "wins", "win_rate"])
        for rank, pid in enumerate(sorted(ratings, key=lambda p: -ratings[p]), 1):
            wins = sum(1 for h in history if h["placements"][pid] == 1)
            w.writerow([rank, pid[:-5], round(ratings[pid]), 3, wins, round(100 * wins / 3, 1)])
    return data


@pytest.fixture
def doc(data_dir, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("models:\n  alpha:\n    model_id: \"vendor/alpha-2026\"\n    name: \"Alpha\"\n")
    return export.build(data_dir, config)


def _by_model(doc):
    return {m["model"]: m for m in doc["models"]}


def test_elo_games_and_wins_match_leaderboard_csv(doc, data_dir):
    models = _by_model(doc)
    with open(data_dir / "leaderboard.csv") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(models)
    for row in rows:
        m = models[row["model"]]
        assert m["elo"] == int(row["elo"])
        assert m["games"] == int(row["games"])
        assert m["wins"] == int(row["wins"])


def test_cost_is_summed_per_seat_and_only_for_rated_games(doc):
    models = _by_model(doc)
    # alpha sat RED in game 1, BLUE in game 2, RED in game 3; the unrated game is ignored.
    assert models["alpha"]["cost_usd_total"] == pytest.approx(0.10 + 0.05 + 0.15)
    assert models["beta"]["cost_usd_total"] == pytest.approx(0.20 + 0.50)
    assert models["alpha"]["tokens_per_move"] == round((100 + 50 + 150) / 3)


def test_cost_per_win_is_cost_over_wins_and_null_at_zero_wins(doc):
    models = _by_model(doc)
    alpha = models["alpha"]
    assert alpha["wins"] == 2
    assert alpha["cost_per_win"] == pytest.approx(alpha["cost_usd_total"] / 2)
    assert models["delta"]["wins"] == 0
    assert models["delta"]["cost_per_win"] is None


def test_api_errors_are_counted_not_answered(doc):
    gamma = _by_model(doc)["gamma"]
    assert gamma["api_errors"] == 1
    assert gamma["answered_moves"] == 1
    assert gamma["tokens_per_move"] == 10


def test_a_model_with_no_logged_moves_has_null_cost(doc):
    assert _by_model(doc)["delta"]["cost_usd_total"] is None
    assert _by_model(doc)["delta"]["tokens_per_move"] is None


def test_provenance_fields_are_present(doc):
    assert doc["generated_at"]
    assert "source_commit" in doc
    assert doc["n_games"] == 3
    assert doc["n_games_with_logs"] == 3
    assert doc["last_game_at"] == "2026-02-03T10:45:00"
    assert doc["ratings_updated"] == "2026-02-04T13:09:57"
    assert "first place" in doc["method"]


def test_model_version_comes_from_config(doc):
    models = _by_model(doc)
    assert models["alpha"]["model_id"] == "vendor/alpha-2026"
    assert models["alpha"]["name"] == "Alpha"
    assert models["beta"]["model_id"] is None


def test_mean_duration_uses_each_models_games(doc):
    # alpha played 30, 60 and 45 minutes.
    assert _by_model(doc)["alpha"]["mean_duration_min"] == 45.0


def test_cli_writes_json(data_dir, tmp_path):
    out = tmp_path / "out" / "catan.json"
    assert export.main(["--data-dir", str(data_dir), "--config", str(tmp_path / "none.yaml"),
                        "--out", str(out)]) == 0
    assert json.loads(out.read_text())["n_games"] == 3


def test_repeated_alias_maps_both_seats_to_one_model():
    game = {"players": ["claude:RED", "gpt4:BLUE", "haiku:WHITE", "haiku:ORANGE"]}
    seats = export._seat_map(game, ["claude-4.5-sonnet-text", "gpt-4o-text", "claude-4.5-haiku-text"])
    assert seats["WHITE"] == seats["ORANGE"] == "claude-4.5-haiku-text"
    assert seats["RED"] == "claude-4.5-sonnet-text"
