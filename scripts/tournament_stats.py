#!/usr/bin/env python3
"""
Tournament statistics and significance checker.

Analyzes current tournament state:
- Games per model
- Pair coverage
- Elo confidence intervals
- Statistical significance of rankings
"""

import argparse
import json
import math
from collections import defaultdict
from itertools import combinations
from pathlib import Path


def load_elo_ratings(ratings_file: str) -> dict:
    """Load Elo ratings from file."""
    path = Path(ratings_file)
    if not path.exists():
        return {"ratings": {}, "history": []}

    with open(path) as f:
        return json.load(f)


def calculate_confidence_interval(games: int, elo: float, k: int = 32) -> tuple[float, float]:
    """
    Estimate 95% confidence interval for Elo rating.

    Based on the approximation that Elo standard error decreases with sqrt(games).
    Initial uncertainty ~200 points, decreases with more games.
    """
    if games == 0:
        return (elo - 400, elo + 400)

    # Standard error approximation
    # After n games, SE ≈ initial_uncertainty / sqrt(n)
    initial_uncertainty = 200
    se = initial_uncertainty / math.sqrt(games)

    # 95% CI = 1.96 * SE
    margin = 1.96 * se

    return (elo - margin, elo + margin)


def analyze_tournament(ratings_data: dict, min_games: int = 5) -> dict:
    """Analyze tournament state."""
    ratings = ratings_data.get("ratings", {})
    history = ratings_data.get("history", [])

    # Count games per model
    games_per_model = defaultdict(int)
    for game in history:
        for player in game.get("players", []):
            model_key = player.get("model_key", "")
            if model_key:
                games_per_model[model_key] += 1

    # Count pair meetings
    pair_counts = defaultdict(int)
    for game in history:
        players = [p.get("model_key", "") for p in game.get("players", [])]
        players = [p for p in players if p]  # Filter empty
        for pair in combinations(players, 2):
            pair_counts[tuple(sorted(pair))] += 1

    # Calculate confidence intervals
    model_stats = []
    for model, data in ratings.items():
        elo = data.get("elo", 1500)
        games = data.get("games", 0)
        wins = data.get("wins", 0)
        ci_low, ci_high = calculate_confidence_interval(games, elo)

        model_stats.append({
            "model": model,
            "elo": elo,
            "games": games,
            "wins": wins,
            "win_rate": wins / games if games > 0 else 0,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "ci_width": ci_high - ci_low
        })

    # Sort by Elo
    model_stats.sort(key=lambda x: -x["elo"])

    # Add rank
    for i, stat in enumerate(model_stats):
        stat["rank"] = i + 1

    # Check for significant differences between adjacent ranks
    for i in range(len(model_stats) - 1):
        current = model_stats[i]
        next_model = model_stats[i + 1]
        # Rankings are significantly different if CIs don't overlap
        current["sig_diff_from_next"] = current["ci_low"] > next_model["ci_high"]

    return {
        "total_games": len(history),
        "total_models": len(ratings),
        "games_per_model": dict(games_per_model),
        "pair_counts": {f"{p[0]} vs {p[1]}": c for p, c in pair_counts.items()},
        "model_stats": model_stats
    }


def print_summary(analysis: dict, verbose: bool = False):
    """Print tournament summary."""
    print("=" * 70)
    print("TOURNAMENT STATUS")
    print("=" * 70)

    print(f"\nTotal games played: {analysis['total_games']}")
    print(f"Models with ratings: {analysis['total_models']}")

    # Games per model distribution
    games = list(analysis['games_per_model'].values())
    if games:
        print(f"\nGames per model: min={min(games)}, max={max(games)}, avg={sum(games)/len(games):.1f}")

        # Models with few games
        few_games = [m for m, g in analysis['games_per_model'].items() if g < 10]
        if few_games:
            print(f"Models with <10 games ({len(few_games)}): {', '.join(few_games[:5])}{'...' if len(few_games) > 5 else ''}")

    # Pair coverage
    pair_counts = analysis['pair_counts']
    total_models = analysis['total_models']
    total_possible_pairs = total_models * (total_models - 1) // 2
    covered_pairs = len(pair_counts)

    print(f"\nPair coverage: {covered_pairs}/{total_possible_pairs} ({100*covered_pairs/total_possible_pairs:.1f}%)" if total_possible_pairs > 0 else "")

    print("\n" + "=" * 70)
    print("LEADERBOARD (with 95% confidence intervals)")
    print("=" * 70)
    print(f"{'Rank':<5} {'Model':<30} {'Elo':>6} {'Games':>6} {'Win%':>6} {'95% CI':>15} {'Sig'}")
    print("-" * 70)

    for stat in analysis['model_stats'][:20]:  # Top 20
        sig = "***" if stat.get('sig_diff_from_next', False) else ""
        print(f"{stat['rank']:<5} {stat['model']:<30} {stat['elo']:>6.0f} {stat['games']:>6} {stat['win_rate']*100:>5.1f}% {stat['ci_low']:>6.0f}-{stat['ci_high']:<6.0f} {sig}")

    if len(analysis['model_stats']) > 20:
        print(f"... and {len(analysis['model_stats']) - 20} more models")

    # Significance summary
    sig_count = sum(1 for s in analysis['model_stats'][:-1] if s.get('sig_diff_from_next', False))
    print(f"\n*** = Significantly different from next rank (non-overlapping 95% CIs)")
    print(f"Significant ranking gaps: {sig_count}/{len(analysis['model_stats'])-1}")

    # Recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    if analysis['total_games'] < 50:
        print("- Need more games for meaningful rankings (target: 50+ games)")
    elif analysis['total_games'] < 100:
        print("- Rankings starting to stabilize, but more games recommended (target: 100+)")
    elif analysis['total_games'] < 200:
        print("- Good sample size. Check pair coverage and CI widths.")
    else:
        print("- Large sample size. Rankings should be stable.")

    avg_ci_width = sum(s['ci_width'] for s in analysis['model_stats']) / len(analysis['model_stats']) if analysis['model_stats'] else 0
    if avg_ci_width > 150:
        print(f"- Average CI width is {avg_ci_width:.0f} points - need more games to tighten")
    elif avg_ci_width > 100:
        print(f"- Average CI width is {avg_ci_width:.0f} points - moderate uncertainty")
    else:
        print(f"- Average CI width is {avg_ci_width:.0f} points - good precision")

    if covered_pairs < total_possible_pairs * 0.5:
        print(f"- Low pair coverage ({100*covered_pairs/total_possible_pairs:.0f}%) - consider more diverse matchups")


def print_verbose(analysis: dict):
    """Print verbose statistics."""
    print("\n" + "=" * 70)
    print("DETAILED STATISTICS")
    print("=" * 70)

    print("\nAll models by games played:")
    by_games = sorted(analysis['games_per_model'].items(), key=lambda x: -x[1])
    for model, games in by_games:
        print(f"  {model}: {games} games")


def main():
    parser = argparse.ArgumentParser(description="Analyze tournament statistics")
    parser.add_argument("--ratings-file", default="data/elo_ratings.json", help="Elo ratings file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed statistics")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--min-games", type=int, default=5, help="Minimum games for significance")

    args = parser.parse_args()

    # Load ratings
    ratings_data = load_elo_ratings(args.ratings_file)

    if not ratings_data.get("ratings"):
        print("No ratings data found. Run some games first!")
        return

    # Analyze
    analysis = analyze_tournament(ratings_data, args.min_games)

    if args.json:
        # Remove non-serializable data
        output = {
            "total_games": analysis["total_games"],
            "total_models": analysis["total_models"],
            "model_stats": analysis["model_stats"]
        }
        print(json.dumps(output, indent=2))
    else:
        print_summary(analysis, args.verbose)
        if args.verbose:
            print_verbose(analysis)


if __name__ == "__main__":
    main()
