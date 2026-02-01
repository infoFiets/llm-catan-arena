#!/usr/bin/env python3
"""
Tournament Runner for LLM Catan Arena.

Run multiple Catan games with different LLM player combinations
and analyze the results.

Supports mixed-mode games where MCP and text players compete in the same game.
Use mode suffixes (-mcp, -text) to specify per-player mode.

Usage:
    python scripts/run_tournament.py --games 5
    python scripts/run_tournament.py --single-game claude gpt4 gemini haiku
    python scripts/run_tournament.py --single-game claude-mcp claude-text gpt4-text gemini-text
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
from src.elo import EloRating

# Load environment variables
load_dotenv()


def run_tournament(num_games: int = None, config_path: str = "config.yaml", mode: str = "text", prompt_format: str = "json", parallel: int = 1):
    """
    Run a full tournament using configuration file.

    Args:
        num_games: Number of times to run each matchup
        config_path: Path to configuration file
        mode: Player mode ("text" or "mcp")
        prompt_format: Prompt format - "json", "json-minified", or "toon"
        parallel: Number of parallel games to run
    """
    print("=" * 60)
    print(f"LLM CATAN ARENA - TOURNAMENT MODE ({mode.upper()}, format={prompt_format})")
    if parallel > 1:
        print(f"Running {parallel} games in parallel")
    print("=" * 60)

    runner = CatanGameRunner(config_path, mode=mode, prompt_format=prompt_format)
    results = runner.run_tournament(num_games=num_games, parallel=parallel)

    print("\n" + "=" * 60)
    print(f"Tournament Complete: {len(results)} games played")
    print("=" * 60)

    # Run analysis
    print("\nGenerating analysis...")
    analyzer = CatanAnalyzer()
    analyzer.print_report(results)

    # Show Elo leaderboard
    print("\n")
    elo = EloRating()
    print(elo.format_leaderboard())


def run_single_game(players: list, config_path: str = "config.yaml", mode: str = "text", prompt_format: str = "json", num_games: int = 1, parallel: int = 1):
    """
    Run one or more games with specified players.

    Args:
        players: List of 4 player specs with optional mode suffix
                 (e.g., ['claude-mcp', 'claude-text', 'gpt4', 'gemini'])
        config_path: Path to configuration file
        mode: Default player mode ("text" or "mcp"), overridden by suffixes
        prompt_format: Prompt format - "json", "json-minified", or "toon"
        num_games: Number of games to run with this matchup
        parallel: Number of games to run in parallel
    """
    if len(players) != 4:
        print("Error: Exactly 4 players required!")
        print("Example: python scripts/run_tournament.py --single-game claude-mcp claude-text gpt4-text gemini-text")
        sys.exit(1)

    # Check if any player has explicit mode suffix
    has_mode_suffix = any(p.endswith('-mcp') or p.endswith('-text') for p in players)
    mode_info = "mixed-mode" if has_mode_suffix else f"default={mode.upper()}"

    runner = CatanGameRunner(config_path, mode=mode, prompt_format=prompt_format)

    # If running multiple games, use tournament infrastructure
    if num_games > 1:
        print("=" * 60)
        print(f"LLM CATAN ARENA - {num_games} GAMES ({mode_info}, format={prompt_format})")
        if parallel > 1:
            print(f"Running {parallel} games in parallel")
        print("=" * 60)
        print(f"Matchup: {players}\n", flush=True)

        # Use run_tournament with single matchup
        results = runner.run_tournament(matchups=[players], num_games=num_games, parallel=parallel)

        print("\n" + "=" * 60)
        print(f"RESULTS: {len(results)} games completed")
        print("=" * 60)

        # Aggregate stats
        total_cost = sum(r.get('total_cost', 0) for r in results)
        total_tokens = sum(r.get('total_tokens', 0) for r in results)

        # Count wins
        win_counts = {}
        for r in results:
            winner = r.get('winner', 'N/A')
            win_counts[winner] = win_counts.get(winner, 0) + 1

        print("Win counts:")
        for player, wins in sorted(win_counts.items(), key=lambda x: -x[1]):
            print(f"  {player}: {wins} wins")

        print(f"\nTotal Cost: ${total_cost:.4f}")
        print(f"Total Tokens: {total_tokens}")
        print(f"Avg Cost/Game: ${total_cost/len(results):.4f}")

        # Show Elo leaderboard
        print("\n")
        elo = EloRating()
        print(elo.format_leaderboard())

        print("=" * 60)
        return

    # Single game mode
    print("=" * 60)
    print(f"LLM CATAN ARENA - SINGLE GAME ({mode_info}, format={prompt_format})")
    print("=" * 60)
    print(f"Players: {players}\n", flush=True)

    result = runner.run_game(players)

    print("\n" + "=" * 60)
    print("GAME RESULTS")
    print("=" * 60)
    print(f"Winner: {result['winner']}")
    print(f"Scores: {result['scores']}")
    print(f"Total Cost: ${result['total_cost']:.4f}")
    print(f"Total Tokens: {result['total_tokens']}")

    # Show Elo changes if available
    if "elo_changes" in result and result["elo_changes"]:
        print("\nElo Rating Changes:")
        for player_id, change in sorted(result["elo_changes"].items(), key=lambda x: -x[1]["new"]):
            change_str = f"+{change['change']:.1f}" if change['change'] >= 0 else f"{change['change']:.1f}"
            print(f"  {player_id}: {change['old']:.0f} -> {change['new']:.0f} ({change_str})")

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
        help='Run a single game with specified players. Use mode suffix for mixed-mode games '
             '(e.g., "claude-mcp claude-text gpt4-text gemini-text" for direct MCP vs text comparison)'
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

    parser.add_argument(
        '--mode',
        choices=['text', 'mcp'],
        default='text',
        help='Default player mode: text (prompt/response) or mcp (tool calling). '
             'Override per-player with suffixes like "claude-mcp" or "gpt4-text"'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'json-minified', 'toon'],
        default='json',
        help='Prompt format: json (standard), json-minified (~33%% token reduction), toon (~53%% token reduction)'
    )

    parser.add_argument(
        '--parallel',
        type=int,
        default=1,
        help='Number of games to run in parallel (default: 1). Recommended: 2-4 to avoid rate limits.'
    )

    args = parser.parse_args()

    # Determine mode
    if args.analyze:
        run_analysis()
    elif args.single_game:
        num_games = args.games if args.games else 1
        run_single_game(args.single_game, args.config, args.mode, args.format, num_games, args.parallel)
    else:
        # Tournament mode
        num_games = args.games
        run_tournament(num_games, args.config, args.mode, args.format, args.parallel)


if __name__ == "__main__":
    main()
