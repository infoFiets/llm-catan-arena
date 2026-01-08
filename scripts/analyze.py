#!/usr/bin/env python3
"""
Command-line interface for LLM Catan Arena analysis.

Usage:
    python scripts/analyze.py --summary
    python scripts/analyze.py --charts
    python scripts/analyze.py --highlights
    python scripts/analyze.py --export-report
    python scripts/analyze.py --game-details game_001
    python scripts/analyze.py --all
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis import (
    load_all_games,
    calculate_win_rates,
    calculate_costs,
    calculate_game_stats,
    head_to_head_matrix,
    export_summary_report,
)
from src.visualizations import generate_all_visualizations
from src.highlight_finder import (
    find_interesting_moments,
    generate_highlights_report,
    export_interesting_game_details,
    get_game_details,
)


def print_summary(games):
    """Print summary statistics to console."""
    print("\n" + "=" * 70)
    print("LLM CATAN ARENA - QUICK SUMMARY")
    print("=" * 70)

    stats = calculate_game_stats(games)
    print(f"\n📊 OVERALL STATISTICS")
    print(f"   Total Games: {stats['total_games']}")
    print(f"   Avg Game Length: {stats['avg_turns']:.1f} turns")
    print(f"   Avg Duration: {stats['avg_duration_minutes']:.1f} minutes")
    print(f"   Avg Winning Score: {stats['avg_winning_score']:.1f} VP")

    print(f"\n🏆 WIN RATES")
    win_rates = calculate_win_rates(games)
    for _, row in win_rates.iterrows():
        print(f"   {row['model']:.<40} {row['win_rate']:>6.1%}  ({row['wins']}/{row['games']})")

    print(f"\n💰 COST ANALYSIS")
    costs = calculate_costs(games)
    for _, row in costs.iterrows():
        cost_per_win = f"${row['cost_per_win']:.4f}" if row['cost_per_win'] != float('inf') else "N/A"
        print(f"   {row['model']:.<40} ${row['avg_cost_per_game']:.4f}/game  {cost_per_win}/win")

    print("\n" + "=" * 70 + "\n")


def print_highlights(games):
    """Print interesting moments to console."""
    print("\n" + "=" * 70)
    print("INTERESTING MOMENTS")
    print("=" * 70)

    highlights = find_interesting_moments(games)

    for category, game_ids in highlights.items():
        if game_ids:
            category_name = category.replace("_", " ").title()
            print(f"\n{category_name}: {len(game_ids)} games")
            for game_id in game_ids[:3]:  # Show top 3
                details = get_game_details(games, game_id)
                if details:
                    print(f"  • {game_id}")
                    print(f"    Winner: {details['winner']} ({details['winner_score']} VP, "
                          f"margin: {details['victory_margin']})")

    print("\n" + "=" * 70 + "\n")


def show_game_details(games, game_id):
    """Show detailed information about a specific game."""
    details = get_game_details(games, game_id)

    if not details:
        print(f"❌ Game '{game_id}' not found")
        print("\nAvailable games:")
        for game in games[:10]:  # Show first 10
            print(f"  • {game.get('session_id')}")
        return

    print("\n" + "=" * 70)
    print(f"GAME DETAILS: {game_id}")
    print("=" * 70)
    print(f"\n🏆 Winner: {details['winner']} ({details['winner_score']} VP)")
    print(f"📊 Victory Margin: {details['victory_margin']} VP")
    print(f"🎲 Game Length: {details['total_turns']} turns")
    print(f"⏱️  Duration: {details['duration_minutes']:.1f} minutes")
    print(f"💵 Total Cost: ${details['total_cost']:.4f}")

    print(f"\n📋 Final Scores:")
    for player, score in sorted(details['final_scores'].items(),
                                key=lambda x: x[1], reverse=True):
        winner_mark = "👑" if player.endswith(details['winner'].split(":")[-1]) else "  "
        print(f"   {winner_mark} {player}: {score} VP")

    print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze LLM Catan Arena game results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/analyze.py --summary                    # Print summary stats
  python scripts/analyze.py --charts                     # Generate all charts
  python scripts/analyze.py --highlights                 # Find interesting moments
  python scripts/analyze.py --export-report              # Generate full markdown report
  python scripts/analyze.py --game-details GAME_ID       # Show details of specific game
  python scripts/analyze.py --all                        # Do everything
        """
    )

    parser.add_argument('--data-dir', type=str, default='data/games',
                       help='Directory containing game JSON files (default: data/games)')
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory for reports and charts (default: output)')

    # Actions
    parser.add_argument('--summary', action='store_true',
                       help='Print summary statistics')
    parser.add_argument('--charts', action='store_true',
                       help='Generate all visualization charts')
    parser.add_argument('--highlights', action='store_true',
                       help='Find and display interesting moments')
    parser.add_argument('--export-report', action='store_true',
                       help='Generate full markdown summary report')
    parser.add_argument('--export-highlights', action='store_true',
                       help='Generate highlights markdown report')
    parser.add_argument('--game-details', type=str, metavar='GAME_ID',
                       help='Show detailed information about a specific game')
    parser.add_argument('--all', action='store_true',
                       help='Run all analysis and generate all outputs')

    args = parser.parse_args()

    # Load games
    print(f"📂 Loading games from {args.data_dir}...")
    games = load_all_games(args.data_dir)

    if not games:
        print(f"❌ No games found in {args.data_dir}")
        return 1

    print(f"✅ Loaded {len(games)} games\n")

    # Determine what to do
    if args.all:
        # Do everything
        print_summary(games)
        print("\n📈 Generating all visualizations...")
        generate_all_visualizations(games, f"{args.output_dir}/charts")
        print("\n📝 Generating summary report...")
        export_summary_report(games, f"{args.output_dir}/summary_report.md")
        print("\n🎯 Generating highlights report...")
        generate_highlights_report(games, f"{args.output_dir}/highlights_report.md")
        print("\n✅ All analysis complete!")

    else:
        # Run requested actions
        if args.summary:
            print_summary(games)

        if args.charts:
            print("\n📈 Generating all visualizations...")
            generate_all_visualizations(games, f"{args.output_dir}/charts")

        if args.highlights:
            print_highlights(games)

        if args.export_report:
            print("\n📝 Generating summary report...")
            export_summary_report(games, f"{args.output_dir}/summary_report.md")

        if args.export_highlights:
            print("\n🎯 Generating highlights report...")
            generate_highlights_report(games, f"{args.output_dir}/highlights_report.md")

        if args.game_details:
            show_game_details(games, args.game_details)

        # If no actions specified, show help
        if not any([args.summary, args.charts, args.highlights,
                   args.export_report, args.export_highlights, args.game_details]):
            parser.print_help()
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
