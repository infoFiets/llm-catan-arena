#!/usr/bin/env python3
"""
Rebuild Elo ratings from game files.

Scans all game JSON files and rebuilds Elo ratings from scratch.
Useful for recovering from race conditions or data corruption.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.elo import EloRating

# Alias mapping: old short names -> canonical full model names
# Based on config.yaml mappings used in early experiments
ALIAS_MAP = {
    "haiku": "claude-4.5-haiku",
    "deepseek": "deepseek-v3.2",
    "llama": "llama-4-maverick",
    "gemini-flash": "gemini-2.5-flash",
    "claude": "claude-4.5-sonnet",
    "gpt4": "gpt-4o",
}


def canonicalize_model_key(model_key: str) -> str:
    """Convert old alias to canonical model name if applicable."""
    return ALIAS_MAP.get(model_key, model_key)


def rebuild_from_games(games_dir: str, ratings_file: str, dry_run: bool = False):
    """Rebuild Elo from all game files."""
    games_path = Path(games_dir)

    if not games_path.exists():
        print(f"Games directory not found: {games_path}")
        return

    # Find all game files
    game_files = sorted(games_path.glob("*.json"))
    print(f"Found {len(game_files)} game files")

    # Initialize fresh Elo
    elo = EloRating(ratings_file)
    if not dry_run:
        elo.reset_ratings(confirm=True)

    processed = 0
    skipped = 0

    for game_file in game_files:
        try:
            with open(game_file) as f:
                data = json.load(f)

            # Get final scores
            final_scores = data.get("final_scores", {})
            winner = data.get("winner")
            session_id = data.get("session_id", game_file.stem)

            if not final_scores:
                print(f"  Skipping {game_file.name}: no final_scores")
                skipped += 1
                continue

            if winner == "Draw":
                print(f"  Skipping {game_file.name}: Draw")
                skipped += 1
                continue

            # Convert scores to expected format
            # final_scores uses display names: {"Model Name:COLOR": VP, ...}
            # players uses model keys: ["model-key:COLOR", ...]
            # We need to map display names to model keys

            players = data.get("players", [])
            if isinstance(players, dict):
                players = list(players.keys())

            # Build mapping from color to model key
            color_to_key = {}
            for p in players:
                if ":" in p:
                    key, color = p.rsplit(":", 1)
                    color_to_key[color] = key

            # Convert final_scores to use model keys with mode suffix
            # All games so far are text mode, so append -text to all players
            # Also apply alias mapping for old short names
            converted_scores = {}
            for display_key, vp in final_scores.items():
                if ":" in display_key:
                    _, color = display_key.rsplit(":", 1)
                    if color in color_to_key:
                        # Apply alias mapping and append -text suffix
                        raw_key = color_to_key[color]
                        canonical_key = canonicalize_model_key(raw_key)
                        model_key = f"{canonical_key}-text:{color}"
                        converted_scores[model_key] = vp
                    else:
                        converted_scores[display_key] = vp
                else:
                    converted_scores[display_key] = vp

            game_result = {"scores": converted_scores}

            if dry_run:
                print(f"  Would process: {game_file.name}")
                print(f"    Scores: {final_scores}")
            else:
                elo.update_ratings(game_result, session_id)
                processed += 1
                print(f"  Processed: {game_file.name} - Winner: {winner}")

        except Exception as e:
            print(f"  Error processing {game_file.name}: {e}")
            skipped += 1

    print(f"\n{'DRY RUN - ' if dry_run else ''}Rebuild complete:")
    print(f"  Processed: {processed}")
    print(f"  Skipped: {skipped}")

    if not dry_run:
        print(f"\nNew leaderboard:")
        print(elo.format_leaderboard())


def main():
    parser = argparse.ArgumentParser(description="Rebuild Elo from game files")
    parser.add_argument("--games-dir", default="data/games", help="Directory with game JSON files")
    parser.add_argument("--ratings-file", default="data/elo_ratings.json", help="Output ratings file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without changing anything")

    args = parser.parse_args()

    rebuild_from_games(args.games_dir, args.ratings_file, args.dry_run)


if __name__ == "__main__":
    main()
