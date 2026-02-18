#!/usr/bin/env python3
"""
Generate balanced matchups for the full tournament.

Ensures each model plays roughly equally and all pairs eventually meet.
Reads existing game history to prioritize underplayed models and pairs.
"""

import argparse
import json
import random
import yaml
from collections import defaultdict
from itertools import combinations
from pathlib import Path


def load_models(config_path: str) -> list[str]:
    """Load model keys from config file."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return list(config.get("models", {}).keys())


def load_existing_history(ratings_file: str) -> tuple[dict, dict]:
    """
    Load existing game history from Elo ratings file.

    Returns:
        Tuple of (games_per_model, pair_counts) from existing games
        Model keys are normalized (stripped of -text/-mcp suffix) to match config keys
    """
    games_per_model = defaultdict(int)
    pair_counts = defaultdict(int)

    path = Path(ratings_file)
    if not path.exists():
        return games_per_model, pair_counts

    try:
        with open(path) as f:
            data = json.load(f)

        history = data.get("history", [])

        for game in history:
            players = game.get("players", [])
            # Players are stored as strings like "gemini-3-pro-text"
            # Strip the -text/-mcp suffix to match config model keys
            model_keys = []
            for p in players:
                if isinstance(p, str):
                    # Strip -text or -mcp suffix to get base model key
                    base_key = p
                    if base_key.endswith("-text"):
                        base_key = base_key[:-5]
                    elif base_key.endswith("-mcp"):
                        base_key = base_key[:-4]
                    model_keys.append(base_key)

            # Count games per model
            for model in model_keys:
                games_per_model[model] += 1

            # Count pair meetings
            for pair in combinations(model_keys, 2):
                pair_counts[tuple(sorted(pair))] += 1

        return games_per_model, pair_counts

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not parse ratings file: {e}", file=__import__('sys').stderr)
        return games_per_model, pair_counts


def generate_balanced_matchups(
    models: list[str],
    num_games: int,
    seed: int = None,
    existing_games_per_model: dict = None,
    existing_pair_counts: dict = None
) -> list[list[str]]:
    """
    Generate balanced 4-player matchups.

    Strategy: Track how many games each model has played and prioritize
    models with fewer games. Also track pair coverage to ensure diversity.

    Args:
        models: List of model keys to include
        num_games: Number of matchups to generate
        seed: Random seed for reproducibility
        existing_games_per_model: Pre-existing game counts from history
        existing_pair_counts: Pre-existing pair counts from history
    """
    if seed is not None:
        random.seed(seed)

    # Start with existing counts or empty
    games_per_model = defaultdict(int)
    pair_counts = defaultdict(int)

    if existing_games_per_model:
        games_per_model.update(existing_games_per_model)
    if existing_pair_counts:
        pair_counts.update(existing_pair_counts)

    matchups = []

    for _ in range(num_games):
        # Sort models by games played (ascending) to prioritize underplayed models
        sorted_models = sorted(models, key=lambda m: (games_per_model[m], random.random()))

        # Take 4 models, preferring those with fewer games
        # But add some randomness to avoid always picking the same 4
        candidates = sorted_models[:16]  # Top 16 least-played
        random.shuffle(candidates)

        # Score candidates by pair novelty
        best_matchup = None
        best_score = float('inf')

        # Try several random combinations and pick the one with most novel pairs
        for _ in range(50):
            matchup = random.sample(candidates, 4)
            # Score = sum of pair counts (lower is better = more novel pairs)
            score = sum(pair_counts[tuple(sorted(pair))] for pair in combinations(matchup, 2))
            # Add penalty for models that have played a lot
            score += sum(games_per_model[m] for m in matchup) * 0.1

            if score < best_score:
                best_score = score
                best_matchup = matchup

        matchups.append(best_matchup)

        # Update counts
        for model in best_matchup:
            games_per_model[model] += 1
        for pair in combinations(best_matchup, 2):
            pair_counts[tuple(sorted(pair))] += 1

    return matchups


def print_matchups(matchups: list[list[str]], output_format: str = "commands"):
    """Print matchups in requested format."""
    if output_format == "commands":
        # Group into batches of 5 for parallel execution
        print("# Generated matchups - run these commands")
        print("# Each command runs 1 game with 4 models\n")

        for i, matchup in enumerate(matchups, 1):
            models_str = " ".join(matchup)
            print(f"# Game {i}")
            print(f"python scripts/run_tournament.py --single-game {models_str} --mode text --format toon --games 1 --config config_full_tournament.yaml")
            print()

    elif output_format == "batch":
        # Output as batch commands (multiple games in parallel)
        print("# Generated matchups - batch format")
        print("# Run multiple games in parallel\n")

        batch_size = 4
        for batch_start in range(0, len(matchups), batch_size):
            batch = matchups[batch_start:batch_start + batch_size]
            print(f"# Batch {batch_start // batch_size + 1} ({len(batch)} games)")

            for matchup in batch:
                models_str = " ".join(matchup)
                print(f"python scripts/run_tournament.py --single-game {models_str} --mode text --format toon --games 1 --config config_full_tournament.yaml &")
            print("wait")
            print()

    elif output_format == "json":
        import json
        print(json.dumps(matchups, indent=2))

    elif output_format == "list":
        for i, matchup in enumerate(matchups, 1):
            print(f"{i}. {' vs '.join(matchup)}")


def print_stats(matchups: list[list[str]], models: list[str],
                existing_games: dict = None, existing_pairs: dict = None):
    """Print statistics about the generated matchups."""
    # Calculate stats for NEW matchups only
    new_games_per_model = defaultdict(int)
    new_pair_counts = defaultdict(int)

    for matchup in matchups:
        for model in matchup:
            new_games_per_model[model] += 1
        for pair in combinations(matchup, 2):
            new_pair_counts[tuple(sorted(pair))] += 1

    # Calculate TOTAL stats (existing + new)
    total_games_per_model = defaultdict(int)
    total_pair_counts = defaultdict(int)

    if existing_games:
        total_games_per_model.update(existing_games)
    if existing_pairs:
        total_pair_counts.update(existing_pairs)

    for model, count in new_games_per_model.items():
        total_games_per_model[model] += count
    for pair, count in new_pair_counts.items():
        total_pair_counts[pair] += count

    print("\n" + "=" * 60)
    print("MATCHUP STATISTICS")
    print("=" * 60)

    # Existing games summary
    if existing_games:
        existing_total = sum(existing_games.values()) // 4
        existing_pairs_count = len(existing_pairs) if existing_pairs else 0
        print(f"\nExisting games: {existing_total} games, {existing_pairs_count} pairs covered")

    # New games per model
    if new_games_per_model:
        min_new = min(new_games_per_model.values())
        max_new = max(new_games_per_model.values())
        avg_new = sum(new_games_per_model.values()) / len(models) if models else 0
        print(f"\nNEW games per model: min={min_new}, max={max_new}, avg={avg_new:.1f}")

    # Total games per model
    models_with_games = [m for m in models if total_games_per_model.get(m, 0) > 0]
    if total_games_per_model:
        min_total = min(total_games_per_model[m] for m in models if m in total_games_per_model) if models_with_games else 0
        max_total = max(total_games_per_model.values())
        avg_total = sum(total_games_per_model[m] for m in models) / len(models) if models else 0
        print(f"TOTAL games per model: min={min_total}, max={max_total}, avg={avg_total:.1f}")

    models_with_zero = [m for m in models if total_games_per_model.get(m, 0) == 0]
    if models_with_zero:
        print(f"Models with 0 total games ({len(models_with_zero)}): {', '.join(models_with_zero[:5])}{'...' if len(models_with_zero) > 5 else ''}")

    # Pair coverage
    total_possible_pairs = len(models) * (len(models) - 1) // 2
    new_covered = len(new_pair_counts)
    total_covered = len(total_pair_counts)
    uncovered = total_possible_pairs - total_covered

    print(f"\nNEW pair coverage: {new_covered} pairs in this batch")
    print(f"TOTAL pair coverage: {total_covered}/{total_possible_pairs} ({100*total_covered/total_possible_pairs:.1f}%)")
    print(f"Uncovered pairs: {uncovered}")

    # Distribution of pair meetings
    if total_pair_counts:
        pair_values = list(total_pair_counts.values())
        print(f"Pair meetings (total): min={min(pair_values)}, max={max(pair_values)}, avg={sum(pair_values)/len(pair_values):.1f}")


def main():
    parser = argparse.ArgumentParser(description="Generate balanced tournament matchups")
    parser.add_argument("--config", default="config_full_tournament.yaml", help="Config file with models")
    parser.add_argument("--games", type=int, default=50, help="Number of games to generate")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--format", choices=["commands", "batch", "json", "list"], default="commands",
                        help="Output format")
    parser.add_argument("--stats", action="store_true", help="Print statistics about matchups")
    parser.add_argument("--models", nargs="+", help="Specific models to use (overrides config)")
    parser.add_argument("--ratings-file", default="data/elo_ratings.json",
                        help="Elo ratings file to read existing history from")
    parser.add_argument("--ignore-history", action="store_true",
                        help="Ignore existing game history (start fresh)")

    args = parser.parse_args()

    # Load models
    if args.models:
        models = args.models
    else:
        config_path = Path(__file__).parent.parent / args.config
        models = load_models(config_path)

    # Load existing history unless ignored
    existing_games = {}
    existing_pairs = {}
    if not args.ignore_history:
        ratings_path = Path(__file__).parent.parent / args.ratings_file
        existing_games, existing_pairs = load_existing_history(ratings_path)
        if existing_games:
            total_existing = sum(existing_games.values()) // 4  # 4 players per game
            print(f"# Found {total_existing} existing games in history", file=__import__('sys').stderr)

    print(f"# Generating {args.games} matchups from {len(models)} models", file=__import__('sys').stderr)

    # Generate matchups
    matchups = generate_balanced_matchups(
        models, args.games, args.seed,
        existing_games_per_model=existing_games,
        existing_pair_counts=existing_pairs
    )

    # Print matchups
    print_matchups(matchups, args.format)

    # Print stats if requested
    if args.stats:
        print_stats(matchups, models, existing_games, existing_pairs)


if __name__ == "__main__":
    main()
