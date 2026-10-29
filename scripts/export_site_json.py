#!/usr/bin/env python3
"""
Export the arena's results as one static JSON file for mcgrathtrading.com/benchmarks.

Reads what the tournament already wrote and recomputes nothing it does not have to:

- Elo, games and wins come from data/elo_ratings.json, exactly as
  EloRating.get_leaderboard() counts them (a win is first place in a game's
  history entry), so the numbers match data/leaderboard.csv.
- Cost, tokens and duration come from data/games/*.json. Cost is recorded per
  move, and every move names the seat (colour) that made it, so cost is summed
  per player, not split from a per-game total. Only games that are in the Elo
  history count, so cost per win divides like by like.
- Model versions (the exact OpenRouter id) come from config_full_tournament.yaml.

Usage:
    python scripts/export_site_json.py --out catan.json
    python scripts/export_site_json.py --data-dir ../llm-catan-arena/data --out catan.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent

# The Elo ids carry the player mode ("-text" or "-mcp"); the site shows the model.
MODE_SUFFIXES = ("-text", "-mcp")


def _strip_mode(player_id: str) -> tuple[str, str]:
    for suffix in MODE_SUFFIXES:
        if player_id.endswith(suffix):
            return player_id[: -len(suffix)], ("tool" if suffix == "-mcp" else "text")
    return player_id, "text"


def _session_key(session_id: str) -> str:
    # Older logs used spaces in the session id, newer ones underscores.
    return session_id.replace(" ", "_")


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def load_model_ids(config_path: Path) -> Dict[str, Dict[str, str]]:
    """Alias -> {model_id, name} from the tournament config, or {} without one."""
    if not config_path.exists():
        return {}
    try:
        import yaml
    except ImportError:  # pragma: no cover, yaml is a project dependency
        return {}
    data = yaml.safe_load(config_path.read_text()) or {}
    out = {}
    for alias, spec in (data.get("models") or {}).items():
        if isinstance(spec, dict) and spec.get("model_id"):
            out[alias] = {"model_id": spec["model_id"], "name": spec.get("name", alias)}
    return out


def _seat_map(game: Dict[str, Any], history_players: List[str]) -> Dict[str, str]:
    """Colour -> Elo player id for one game.

    The game log lists seats as "alias:COLOUR" in the same order the Elo history
    lists players. Early games used short aliases ("haiku", "claude") that the
    Elo rebuild resolved to full ids, so the mapping is by position, not by name.
    When one model held two seats the history has fewer players; then each seat
    is matched by name against the history, falling back to the alias seen in
    the other seats.
    """
    seats = [p.rsplit(":", 1) for p in game.get("players", []) if ":" in p]
    if len(seats) == len(history_players):
        return {colour: history_players[i] for i, (_, colour) in enumerate(seats)}
    by_base = {_strip_mode(p)[0]: p for p in history_players}
    mapping = {}
    unused = list(history_players)
    for alias, colour in seats:
        if alias in by_base:
            mapping[colour] = by_base[alias]
            if by_base[alias] in unused:
                unused.remove(by_base[alias])
    # Whatever is left (an alias the history renamed) goes to the unused ids in order;
    # a repeated alias reuses the id its first seat got.
    alias_to_id: Dict[str, str] = {}
    for alias, colour in seats:
        if colour in mapping:
            alias_to_id.setdefault(alias, mapping[colour])
            continue
        if alias in alias_to_id:
            mapping[colour] = alias_to_id[alias]
        elif unused:
            mapping[colour] = alias_to_id[alias] = unused.pop(0)
    return mapping


def _git_commit(path: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def build(data_dir: Path, config_path: Path, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    ratings_doc = json.loads((data_dir / "elo_ratings.json").read_text())
    ratings: Dict[str, float] = ratings_doc.get("ratings", {})
    history: List[Dict[str, Any]] = ratings_doc.get("history", [])
    counts: Dict[str, int] = ratings_doc.get("game_counts", {})
    model_ids = load_model_ids(config_path)

    by_session = {_session_key(h["session_id"]): h for h in history if h.get("session_id")}

    stats: Dict[str, Dict[str, float]] = {
        pid: {"cost": 0.0, "tokens": 0, "moves": 0, "errors": 0, "minutes": 0.0, "timed_games": 0, "cost_games": 0}
        for pid in ratings
    }
    victory_points, turn_limits = set(), set()
    last_game: Optional[datetime] = None
    first_game: Optional[datetime] = None
    logged = 0

    for path in sorted((data_dir / "games").glob("*.json")):
        try:
            game = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        entry = by_session.get(_session_key(game.get("session_id", "")))
        if entry is None:
            continue  # not rated (an error, a draw or a self-play test), so not counted
        logged += 1
        cfg = game.get("game_config", {})
        if cfg.get("victory_points"):
            victory_points.add(cfg["victory_points"])
        if cfg.get("max_turns"):
            turn_limits.add(cfg["max_turns"])
        start, end = _parse_time(game.get("start_time")), _parse_time(game.get("end_time"))
        if end and (last_game is None or end > last_game):
            last_game = end
        if start and (first_game is None or start < first_game):
            first_game = start

        seats = _seat_map(game, entry.get("players", []))
        seen = set()
        for move in game.get("moves", []):
            pid = seats.get(move.get("player"))
            data = move.get("move_data", {})
            if pid not in stats:
                continue
            if data.get("api_error"):
                stats[pid]["errors"] += 1
                continue
            stats[pid]["cost"] += float(data.get("cost") or 0.0)
            stats[pid]["tokens"] += int(data.get("tokens") or 0)
            stats[pid]["moves"] += 1
            seen.add(pid)
        for pid in seen:
            stats[pid]["cost_games"] += 1
        if start and end:
            for pid in set(seats.values()):
                if pid in stats:
                    stats[pid]["minutes"] += (end - start).total_seconds() / 60
                    stats[pid]["timed_games"] += 1

    models = []
    for pid, rating in sorted(ratings.items(), key=lambda kv: -kv[1]):
        base, mode = _strip_mode(pid)
        games = int(counts.get(pid, 0))
        wins = sum(1 for h in history if h.get("placements", {}).get(pid) == 1)
        s = stats[pid]
        cost = round(s["cost"], 4) if s["cost_games"] else None
        info = model_ids.get(base, {})
        models.append({
            "model": base,
            "name": info.get("name", base),
            "model_id": info.get("model_id"),
            "mode": mode,
            "elo": round(rating),
            "games": games,
            "wins": wins,
            "win_rate": round(wins / games, 4) if games else None,
            "cost_usd_total": cost,
            "cost_per_win": round(cost / wins, 4) if cost is not None and wins else None,
            "tokens_per_move": round(s["tokens"] / s["moves"]) if s["moves"] else None,
            "answered_moves": int(s["moves"]),
            "api_errors": int(s["errors"]),
            "mean_duration_min": round(s["minutes"] / s["timed_games"], 1) if s["timed_games"] else None,
        })

    vp = "/".join(str(v) for v in sorted(victory_points)) or "10"
    turns = sorted(turn_limits)
    turn_text = f"{turns[0]} to {turns[-1]}" if len(turns) > 1 else (str(turns[0]) if turns else "a fixed number of")
    method = (
        "Four-player games of Settlers of Catan on the Catanatron engine, every seat an LLM "
        "called through OpenRouter in text mode: the model reads the game state in a prompt "
        f"and picks one of the legal actions. First to {vp} victory points wins (both targets "
        f"were used across the tournament), with a limit of {turn_text} turns; at the limit "
        "the player with the most points places first. Ratings are multiplayer Elo: everyone "
        "starts at 1500, each player's expected score is taken against the average rating of "
        "its opponents, the actual score runs from 1.0 for first place to 0.0 for last, and "
        "K is 32. A win is a first place. Cost is what OpenRouter reported for each move, "
        "summed per player; tokens per move counts moves that returned an answer. A move "
        "whose API call failed after retries is played as a random legal action and counted under API errors."
    )

    return {
        "benchmark": "llm-catan-arena",
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "source_commit": _git_commit(data_dir),
        "ratings_updated": ratings_doc.get("last_updated"),
        "first_game_at": first_game.isoformat(timespec="seconds") if first_game else None,
        "last_game_at": last_game.isoformat(timespec="seconds") if last_game else None,
        "n_games": len(history),
        "n_games_with_logs": logged,
        "method": method,
        "models": models,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--data-dir", type=Path, default=REPO / "data")
    ap.add_argument("--config", type=Path, default=REPO / "config_full_tournament.yaml")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    doc = build(args.data_dir, args.config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {args.out}: {len(doc['models'])} models, {doc['n_games']} games, last {doc['last_game_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
