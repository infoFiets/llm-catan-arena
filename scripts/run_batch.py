#!/usr/bin/env python3
"""
Run a batch of tournament games with balanced matchups in parallel.

This script generates balanced matchups and runs them concurrently,
making it easy to run the tournament in chunks.
"""

import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_matchups import load_models, generate_balanced_matchups

# Lock for thread-safe printing
print_lock = Lock()


def run_single_game(game_num: int, total_games: int, matchup: list[str], config: str) -> dict:
    """Run a single game and return the result."""
    models_str = " vs ".join(matchup)

    cmd = [
        "python", "scripts/run_tournament.py",
        "--single-game", *matchup,
        "--mode", "text",
        "--format", "toon",
        "--games", "1",
        "--config", config
    ]

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout per game
        )
        elapsed = time.time() - start_time

        if result.returncode == 0:
            return {
                "game_num": game_num,
                "matchup": models_str,
                "status": "success",
                "elapsed": elapsed,
                "output": result.stdout[-500:] if result.stdout else ""  # Last 500 chars
            }
        else:
            return {
                "game_num": game_num,
                "matchup": models_str,
                "status": "error",
                "elapsed": elapsed,
                "error": result.stderr[-500:] if result.stderr else "Unknown error"
            }
    except subprocess.TimeoutExpired:
        return {
            "game_num": game_num,
            "matchup": models_str,
            "status": "timeout",
            "elapsed": 1800,
            "error": "Game timed out after 30 minutes"
        }
    except Exception as e:
        return {
            "game_num": game_num,
            "matchup": models_str,
            "status": "error",
            "elapsed": time.time() - start_time,
            "error": str(e)
        }


def run_batch(
    config: str,
    num_games: int,
    parallel: int,
    seed: int = None,
    dry_run: bool = False,
    models: list[str] = None
):
    """Run a batch of tournament games in parallel."""
    # Load models from config
    if models:
        model_list = models
    else:
        config_path = Path(__file__).parent.parent / config
        model_list = load_models(config_path)

    print(f"Generating {num_games} balanced matchups from {len(model_list)} models...")
    print(f"Running {parallel} games in parallel\n")

    # Generate matchups
    matchups = generate_balanced_matchups(model_list, num_games, seed)

    if dry_run:
        print("DRY RUN - would run these matchups:\n")
        for i, matchup in enumerate(matchups, 1):
            print(f"  {i}. {' vs '.join(matchup)}")
        return

    # Track progress
    completed = 0
    successful = 0
    failed = 0
    total_time = 0
    start_time = time.time()

    print(f"{'='*70}")
    print(f"Starting {num_games} games with {parallel} parallel workers")
    print(f"{'='*70}\n")

    try:
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            # Submit all games
            futures = {
                executor.submit(run_single_game, i, num_games, matchup, config): i
                for i, matchup in enumerate(matchups, 1)
            }

            # Process results as they complete
            for future in as_completed(futures):
                result = future.result()
                completed += 1

                with print_lock:
                    if result["status"] == "success":
                        successful += 1
                        print(f"[{completed}/{num_games}] ✓ Game {result['game_num']}: {result['matchup']} ({result['elapsed']:.1f}s)")
                    else:
                        failed += 1
                        print(f"[{completed}/{num_games}] ✗ Game {result['game_num']}: {result['matchup']} - {result['status']}")
                        if result.get("error"):
                            print(f"    Error: {result['error'][:100]}")

                    total_time += result["elapsed"]

    except KeyboardInterrupt:
        print(f"\n\nInterrupted! Waiting for {parallel} in-progress games to finish...")
        print("(Press Ctrl+C again to force quit)")
        # ThreadPoolExecutor will wait for running tasks to complete

    elapsed_wall = time.time() - start_time

    print(f"\n{'='*70}")
    print(f"BATCH COMPLETE")
    print(f"{'='*70}")
    print(f"Games: {successful} successful, {failed} failed, {num_games - completed} cancelled")
    print(f"Wall time: {elapsed_wall/60:.1f} minutes")
    print(f"Total game time: {total_time/60:.1f} minutes")
    print(f"Parallelism efficiency: {total_time/elapsed_wall:.1f}x" if elapsed_wall > 0 else "")
    print(f"\nRun 'python scripts/tournament_stats.py' to see current standings.")


def main():
    parser = argparse.ArgumentParser(description="Run a batch of tournament games in parallel")
    parser.add_argument("--config", default="config_full_tournament.yaml", help="Config file")
    parser.add_argument("--games", type=int, default=10, help="Number of games to run")
    parser.add_argument("--parallel", type=int, default=10, help="Number of games to run simultaneously")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible matchups")
    parser.add_argument("--dry-run", action="store_true", help="Print matchups without running")
    parser.add_argument("--models", nargs="+", help="Specific models to use (overrides config)")

    args = parser.parse_args()

    run_batch(
        config=args.config,
        num_games=args.games,
        parallel=args.parallel,
        seed=args.seed,
        dry_run=args.dry_run,
        models=args.models
    )


if __name__ == "__main__":
    main()
