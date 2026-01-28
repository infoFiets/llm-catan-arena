#!/usr/bin/env python3
"""
Mode Comparison Tool for LLM Catan Arena.

Compare performance between text-based and MCP-based player modes.
Runs identical matchups in both modes and generates comparison reports.

Usage:
    python scripts/compare_modes.py --games 5
    python scripts/compare_modes.py --games 10 --output comparison_results.json
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt

from src.game_runner import CatanGameRunner

# Load environment variables
load_dotenv()


def run_comparison_games(
    num_games: int,
    matchup: List[str],
    config_path: str = "config.yaml"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run games in both text and MCP modes.

    Args:
        num_games: Number of games per mode
        matchup: List of 4 player model keys
        config_path: Path to config file

    Returns:
        Dictionary with 'text' and 'mcp' keys containing game results
    """
    results = {"text": [], "mcp": []}

    for mode in ["text", "mcp"]:
        print(f"\n{'='*60}")
        print(f"Running {num_games} games in {mode.upper()} mode")
        print(f"{'='*60}")

        try:
            runner = CatanGameRunner(config_path, mode=mode)

            for i in range(num_games):
                print(f"\n  Game {i + 1}/{num_games}...")
                try:
                    result = runner.run_game(matchup, game_id=f"{mode}_{i+1}")
                    result["mode"] = mode
                    results[mode].append(result)
                    print(f"    Winner: {result['winner']}")
                    print(f"    Cost: ${result['total_cost']:.4f}")
                except Exception as e:
                    print(f"    Error: {e}")
                    continue

        except Exception as e:
            print(f"Error initializing {mode} mode runner: {e}")
            continue

    return results


def analyze_comparison(results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Analyze comparison results between modes.

    Args:
        results: Dictionary with 'text' and 'mcp' game results

    Returns:
        Analysis dictionary with metrics for each mode
    """
    analysis = {}

    for mode, games in results.items():
        if not games:
            analysis[mode] = {"error": "No games completed"}
            continue

        # Calculate metrics
        total_games = len(games)
        wins_by_model = {}
        total_costs = []
        total_tokens = []

        for game in games:
            winner = game.get("winner")
            if winner:
                wins_by_model[winner] = wins_by_model.get(winner, 0) + 1

            total_costs.append(game.get("total_cost", 0))
            total_tokens.append(game.get("total_tokens", 0))

        # Calculate averages
        avg_cost = sum(total_costs) / total_games if total_games > 0 else 0
        avg_tokens = sum(total_tokens) / total_games if total_games > 0 else 0

        # Win rates
        win_rates = {
            model: wins / total_games
            for model, wins in wins_by_model.items()
        }

        analysis[mode] = {
            "total_games": total_games,
            "wins_by_model": wins_by_model,
            "win_rates": win_rates,
            "avg_cost_per_game": avg_cost,
            "total_cost": sum(total_costs),
            "avg_tokens_per_game": avg_tokens,
            "total_tokens": sum(total_tokens),
            "min_cost": min(total_costs) if total_costs else 0,
            "max_cost": max(total_costs) if total_costs else 0,
        }

    return analysis


def generate_comparison_report(analysis: Dict[str, Any]) -> str:
    """
    Generate text comparison report.

    Args:
        analysis: Analysis dictionary from analyze_comparison()

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 70)
    lines.append("LLM CATAN ARENA - MODE COMPARISON REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    for mode in ["text", "mcp"]:
        if mode not in analysis:
            continue

        data = analysis[mode]
        if "error" in data:
            lines.append(f"\n{mode.upper()} MODE: {data['error']}")
            continue

        lines.append(f"\n{'-'*70}")
        lines.append(f"{mode.upper()} MODE RESULTS")
        lines.append(f"{'-'*70}")
        lines.append(f"Total Games: {data['total_games']}")
        lines.append(f"")
        lines.append("Win Rates:")
        for model, rate in sorted(data["win_rates"].items(), key=lambda x: -x[1]):
            wins = data["wins_by_model"][model]
            lines.append(f"  {model:.<30} {rate:>6.1%} ({wins} wins)")

        lines.append(f"")
        lines.append("Cost Analysis:")
        lines.append(f"  Average Cost per Game: ${data['avg_cost_per_game']:.4f}")
        lines.append(f"  Total Cost: ${data['total_cost']:.4f}")
        lines.append(f"  Min Game Cost: ${data['min_cost']:.4f}")
        lines.append(f"  Max Game Cost: ${data['max_cost']:.4f}")

        lines.append(f"")
        lines.append("Token Usage:")
        lines.append(f"  Average Tokens per Game: {data['avg_tokens_per_game']:,.0f}")
        lines.append(f"  Total Tokens: {data['total_tokens']:,}")

    # Comparison summary
    if "text" in analysis and "mcp" in analysis:
        text_data = analysis["text"]
        mcp_data = analysis["mcp"]

        if "error" not in text_data and "error" not in mcp_data:
            lines.append(f"\n{'='*70}")
            lines.append("COMPARISON SUMMARY")
            lines.append(f"{'='*70}")

            cost_diff = mcp_data["avg_cost_per_game"] - text_data["avg_cost_per_game"]
            cost_pct = (cost_diff / text_data["avg_cost_per_game"] * 100) if text_data["avg_cost_per_game"] > 0 else 0

            token_diff = mcp_data["avg_tokens_per_game"] - text_data["avg_tokens_per_game"]
            token_pct = (token_diff / text_data["avg_tokens_per_game"] * 100) if text_data["avg_tokens_per_game"] > 0 else 0

            lines.append(f"")
            lines.append(f"Cost Difference (MCP vs Text):")
            lines.append(f"  ${cost_diff:+.4f} per game ({cost_pct:+.1f}%)")

            lines.append(f"")
            lines.append(f"Token Difference (MCP vs Text):")
            lines.append(f"  {token_diff:+,.0f} per game ({token_pct:+.1f}%)")

            lines.append(f"")
            if cost_diff < 0:
                lines.append("  -> MCP mode is MORE cost efficient")
            elif cost_diff > 0:
                lines.append("  -> Text mode is MORE cost efficient")
            else:
                lines.append("  -> Both modes have similar cost efficiency")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def plot_comparison(analysis: Dict[str, Any], output_dir: str = "output"):
    """
    Generate comparison plots.

    Args:
        analysis: Analysis dictionary from analyze_comparison()
        output_dir: Directory to save plots
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    modes = [m for m in ["text", "mcp"] if m in analysis and "error" not in analysis[m]]
    if len(modes) < 2:
        print("Not enough data to generate comparison plots")
        return

    # Cost comparison bar chart
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Average cost
    costs = [analysis[m]["avg_cost_per_game"] for m in modes]
    axes[0].bar(modes, costs, color=["#3498db", "#e74c3c"])
    axes[0].set_title("Average Cost per Game by Mode")
    axes[0].set_ylabel("Cost ($)")
    for i, cost in enumerate(costs):
        axes[0].text(i, cost + 0.001, f"${cost:.4f}", ha="center")

    # Average tokens
    tokens = [analysis[m]["avg_tokens_per_game"] for m in modes]
    axes[1].bar(modes, tokens, color=["#3498db", "#e74c3c"])
    axes[1].set_title("Average Tokens per Game by Mode")
    axes[1].set_ylabel("Tokens")
    for i, tok in enumerate(tokens):
        axes[1].text(i, tok + 100, f"{tok:,.0f}", ha="center")

    plt.tight_layout()
    plt.savefig(f"{output_dir}/mode_comparison.png", dpi=300)
    print(f"Saved comparison plot to {output_dir}/mode_comparison.png")
    plt.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare text vs MCP mode performance in LLM Catan Arena"
    )

    parser.add_argument(
        "--games",
        type=int,
        default=3,
        help="Number of games to run per mode (default: 3)"
    )

    parser.add_argument(
        "--matchup",
        nargs=4,
        metavar=("P1", "P2", "P3", "P4"),
        default=["claude", "claude", "claude", "claude"],
        help="Player models for matchup (default: all claude)"
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )

    parser.add_argument(
        "--output",
        default="output/comparison_results.json",
        help="Output file for raw results (default: output/comparison_results.json)"
    )

    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip generating comparison plots"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("LLM CATAN ARENA - MODE COMPARISON TOOL")
    print("=" * 70)
    print(f"Games per mode: {args.games}")
    print(f"Matchup: {args.matchup}")
    print(f"Config: {args.config}")
    print("=" * 70)

    # Run comparison games
    results = run_comparison_games(
        num_games=args.games,
        matchup=args.matchup,
        config_path=args.config
    )

    # Save raw results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": {
                "games_per_mode": args.games,
                "matchup": args.matchup
            },
            "results": results
        }, f, indent=2, default=str)

    print(f"\nRaw results saved to {output_path}")

    # Analyze results
    analysis = analyze_comparison(results)

    # Generate report
    report = generate_comparison_report(analysis)
    print("\n" + report)

    # Save report
    report_path = output_path.with_suffix(".txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Report saved to {report_path}")

    # Generate plots
    if not args.no_plots:
        try:
            plot_comparison(analysis, str(output_path.parent))
        except Exception as e:
            print(f"Error generating plots: {e}")


if __name__ == "__main__":
    main()
