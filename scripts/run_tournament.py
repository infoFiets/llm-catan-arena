#!/usr/bin/env python3
"""
Tournament Runner for LLM Catan Arena.

Run multiple Catan games with different LLM player combinations
and analyze the results.

Usage:
    python scripts/run_tournament.py --games 5
    python scripts/run_tournament.py --single-game claude gpt4 gemini haiku
    python scripts/run_tournament.py --analyze
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.game_runner import CatanGameRunner
from src.analysis import CatanAnalyzer

# Load environment variables
load_dotenv()


def run_tournament(num_games: int = None, config_path: str = "config.yaml"):
    """
    Run a full tournament using configuration file.

    Args:
        num_games: Number of times to run each matchup
        config_path: Path to configuration file
    """
    print("=" * 60)
    print("LLM CATAN ARENA - TOURNAMENT MODE")
    print("=" * 60)

    runner = CatanGameRunner(config_path)
    results = runner.run_tournament(num_games=num_games)

    print("\n" + "=" * 60)
    print(f"Tournament Complete: {len(results)} games played")
    print("=" * 60)

    # Run analysis
    print("\nGenerating analysis...")
    analyzer = CatanAnalyzer()
    analyzer.print_report(results)


def run_single_game(players: list, config_path: str = "config.yaml"):
    """
    Run a single game with specified players.

    Args:
        players: List of 4 model keys (e.g., ['claude', 'gpt4', 'gemini', 'haiku'])
        config_path: Path to configuration file
    """
    if len(players) != 4:
        print("Error: Exactly 4 players required!")
        print("Example: python scripts/run_tournament.py --single-game claude gpt4 gemini haiku")
        sys.exit(1)

    print("=" * 60)
    print("LLM CATAN ARENA - SINGLE GAME MODE")
    print("=" * 60)
    print(f"Players: {players}\n")

    runner = CatanGameRunner(config_path)
    result = runner.run_game(players)

    print("\n" + "=" * 60)
    print("GAME RESULTS")
    print("=" * 60)
    print(f"Winner: {result['winner']}")
    print(f"Scores: {result['scores']}")
    print(f"Total Cost: ${result['total_cost']:.4f}")
    print(f"Total Tokens: {result['total_tokens']}")
    print("=" * 60)


def run_analysis():
    """Analyze existing results without running new games."""
    print("=" * 60)
    print("LLM CATAN ARENA - ANALYSIS MODE")
    print("=" * 60)

    analyzer = CatanAnalyzer()
    analyzer.print_report()

    # Optionally generate plots
    print("\nGenerate plots? (y/n): ", end='')
    if input().lower() == 'y':
        results = analyzer.load_results()
        if results:
            win_stats = analyzer.calculate_win_rates(results)
            cost_stats = analyzer.calculate_cost_stats(results)

            analyzer.plot_win_rates(win_stats, "data/win_rates.png")
            analyzer.plot_cost_comparison(cost_stats, "data/cost_comparison.png")
            print("Plots saved to data/ directory")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run LLM Catan Arena tournaments and games"
    )

    parser.add_argument(
        '--games',
        type=int,
        help='Number of games to run in tournament mode'
    )

    parser.add_argument(
        '--single-game',
        nargs=4,
        metavar=('PLAYER1', 'PLAYER2', 'PLAYER3', 'PLAYER4'),
        help='Run a single game with specified players (e.g., claude gpt4 gemini haiku)'
    )

    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analyze existing results without running new games'
    )

    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    args = parser.parse_args()

    # Determine mode
    if args.analyze:
        run_analysis()
    elif args.single_game:
        run_single_game(args.single_game, args.config)
    else:
        # Tournament mode
        num_games = args.games
        run_tournament(num_games, args.config)


if __name__ == "__main__":
    main()
