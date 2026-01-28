#!/usr/bin/env python3
"""
Elo Rating Manager for LLM Catan Arena.

View leaderboards, compare players, and manage ratings.

Usage:
    python scripts/elo_ratings.py                    # Show leaderboard
    python scripts/elo_ratings.py --min-games 5     # Min 5 games to show
    python scripts/elo_ratings.py --compare claude-mcp claude-text
    python scripts/elo_ratings.py --history 10       # Last 10 games
    python scripts/elo_ratings.py --reset            # Reset all ratings
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.elo import EloRating


def show_leaderboard(elo: EloRating, min_games: int = 0):
    """Display the current leaderboard."""
    print(elo.format_leaderboard(min_games))


def show_history(elo: EloRating, num_games: int = 10):
    """Show recent game history with rating changes."""
    history = elo.history[-num_games:] if num_games > 0 else elo.history

    if not history:
        print("No game history yet.")
        return

    print("=" * 80)
    print(f"RECENT GAMES (last {len(history)})")
    print("=" * 80)

    for i, game in enumerate(reversed(history), 1):
        print(f"\nGame {i}: {game.get('timestamp', 'Unknown')[:19]}")
        print("-" * 40)

        # Sort by placement
        placements = game.get("placements", {})
        changes = game.get("rating_changes", {})
        scores = game.get("scores", {})

        sorted_players = sorted(placements.items(), key=lambda x: x[1])

        for player, placement in sorted_players:
            change = changes.get(player, {})
            vp = scores.get(player, "?")
            rating_change = change.get("change", 0)
            new_rating = change.get("new", elo.get_rating(player))

            change_str = f"+{rating_change:.1f}" if rating_change >= 0 else f"{rating_change:.1f}"
            place_emoji = ["🥇", "🥈", "🥉", "4️⃣"][placement - 1] if placement <= 4 else f"{placement}."

            print(f"  {place_emoji} {player:<25} {vp:>2} VP  {new_rating:>6.1f} ({change_str})")


def compare_players(elo: EloRating, player_a: str, player_b: str):
    """Show head-to-head comparison between two players."""
    h2h = elo.get_head_to_head(player_a, player_b)

    print("=" * 60)
    print(f"HEAD-TO-HEAD: {player_a} vs {player_b}")
    print("=" * 60)

    if h2h["games_together"] == 0:
        print("No games played together yet.")
        return

    print(f"\nGames played together: {h2h['games_together']}")
    print(f"\n{player_a}:")
    print(f"  Rating: {h2h[f'{player_a}_rating']:.1f}")
    print(f"  Wins: {h2h[f'{player_a}_wins']}")
    print(f"  Better placement rate: {h2h[f'{player_a}_better_placement_rate']*100:.1f}%")

    print(f"\n{player_b}:")
    print(f"  Rating: {h2h[f'{player_b}_rating']:.1f}")
    print(f"  Wins: {h2h[f'{player_b}_wins']}")
    print(f"  Better placement rate: {(1-h2h[f'{player_a}_better_placement_rate'])*100:.1f}%")

    print(f"\nRating difference: {h2h['rating_difference']:+.1f} (in favor of {player_a if h2h['rating_difference'] > 0 else player_b})")


def reset_ratings(elo: EloRating, confirm: bool = False):
    """Reset all ratings."""
    if not confirm:
        print("Are you sure you want to reset all ratings?")
        print("This will delete all rating history.")
        response = input("Type 'yes' to confirm: ")
        confirm = response.lower() == 'yes'

    if confirm:
        elo.reset_ratings(confirm=True)
        print("All ratings have been reset.")
    else:
        print("Reset cancelled.")


def main():
    parser = argparse.ArgumentParser(
        description="Manage Elo ratings for LLM Catan Arena"
    )

    parser.add_argument(
        "--min-games",
        type=int,
        default=0,
        help="Minimum games played to appear on leaderboard"
    )

    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("PLAYER_A", "PLAYER_B"),
        help="Compare two players head-to-head"
    )

    parser.add_argument(
        "--history",
        type=int,
        nargs="?",
        const=10,
        metavar="N",
        help="Show last N games (default: 10)"
    )

    parser.add_argument(
        "--ratings-file",
        default="data/elo_ratings.json",
        help="Path to ratings file"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all ratings (requires confirmation)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    # Initialize Elo system
    elo = EloRating(args.ratings_file)

    if args.reset:
        reset_ratings(elo)
    elif args.compare:
        compare_players(elo, args.compare[0], args.compare[1])
    elif args.history is not None:
        show_history(elo, args.history)
    elif args.json:
        import json
        data = {
            "leaderboard": elo.get_leaderboard(args.min_games),
            "total_games": len(elo.history)
        }
        print(json.dumps(data, indent=2))
    else:
        show_leaderboard(elo, args.min_games)


if __name__ == "__main__":
    main()
