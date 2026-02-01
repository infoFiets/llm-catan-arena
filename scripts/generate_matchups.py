#!/usr/bin/env python3
"""
Generate balanced matchups for the full tournament.

Ensures each model plays roughly equally and all pairs eventually meet.
"""

import argparse
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


def generate_balanced_matchups(
    models: list[str],
    num_games: int,
    seed: int = None
) -> list[list[str]]:
    """
    Generate balanced 4-player matchups.

    Strategy: Track how many games each model has played and prioritize
    models with fewer games. Also track pair coverage to ensure diversity.
    """
    if seed is not None:
        random.seed(seed)

    games_per_model = defaultdict(int)
    pair_counts = defaultdict(int)
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


def print_stats(matchups: list[list[str]], models: list[str]):
    """Print statistics about the generated matchups."""
    games_per_model = defaultdict(int)
    pair_counts = defaultdict(int)

    for matchup in matchups:
        for model in matchup:
            games_per_model[model] += 1
        for pair in combinations(matchup, 2):
            pair_counts[tuple(sorted(pair))] += 1

    print("\n" + "=" * 60)
    print("MATCHUP STATISTICS")
    print("=" * 60)

    # Games per model
    games_list = sorted(games_per_model.items(), key=lambda x: -x[1])
    min_games = min(games_per_model.values()) if games_per_model else 0
    max_games = max(games_per_model.values()) if games_per_model else 0
    avg_games = sum(games_per_model.values()) / len(models) if models else 0

    print(f"\nGames per model: min={min_games}, max={max_games}, avg={avg_games:.1f}")
    print(f"Models with 0 games: {len(models) - len(games_per_model)}")

    # Pair coverage
    total_pairs = len(models) * (len(models) - 1) // 2
    covered_pairs = len(pair_counts)
    uncovered = total_pairs - covered_pairs

    print(f"\nPair coverage: {covered_pairs}/{total_pairs} ({100*covered_pairs/total_pairs:.1f}%)")
    print(f"Uncovered pairs: {uncovered}")

    # Distribution of pair meetings
    if pair_counts:
        pair_values = list(pair_counts.values())
        print(f"Pair meetings: min={min(pair_values)}, max={max(pair_values)}, avg={sum(pair_values)/len(pair_values):.1f}")


def main():
    parser = argparse.ArgumentParser(description="Generate balanced tournament matchups")
    parser.add_argument("--config", default="config_full_tournament.yaml", help="Config file with models")
    parser.add_argument("--games", type=int, default=50, help="Number of games to generate")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--format", choices=["commands", "batch", "json", "list"], default="commands",
                        help="Output format")
    parser.add_argument("--stats", action="store_true", help="Print statistics about matchups")
    parser.add_argument("--models", nargs="+", help="Specific models to use (overrides config)")

    args = parser.parse_args()

    # Load models
    if args.models:
        models = args.models
    else:
        config_path = Path(__file__).parent.parent / args.config
        models = load_models(config_path)

    print(f"# Generating {args.games} matchups from {len(models)} models", file=__import__('sys').stderr)

    # Generate matchups
    matchups = generate_balanced_matchups(models, args.games, args.seed)

    # Print matchups
    print_matchups(matchups, args.format)

    # Print stats if requested
    if args.stats:
        print_stats(matchups, models)


if __name__ == "__main__":
    main()
