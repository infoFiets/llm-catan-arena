#!/usr/bin/env python3
"""
Mode Comparison Tool for LLM Catan Arena.

Compare performance between text-based and MCP-based player modes,
and/or between different prompt formats (JSON, TOON).

Usage:
    # Compare text vs MCP modes
    python scripts/compare_modes.py --games 5

    # Compare prompt formats (TOON vs JSON)
    python scripts/compare_modes.py --games 5 --compare-formats json toon

    # Full comparison: modes and formats
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
    config_path: str = "config.yaml",
    modes: List[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run games in both text and MCP modes.

    Args:
        num_games: Number of games per mode
        matchup: List of 4 player model keys
        config_path: Path to config file
        modes: List of modes to compare (default: ["text", "mcp"])

    Returns:
        Dictionary with mode keys containing game results
    """
    if modes is None:
        modes = ["text", "mcp"]

    results = {mode: [] for mode in modes}

    for mode in modes:
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


def run_format_comparison_games(
    num_games: int,
    matchup: List[str],
    formats: List[str],
    config_path: str = "config.yaml",
    mode: str = "text"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run games comparing different prompt formats.

    Args:
        num_games: Number of games per format
        matchup: List of 4 player model keys
        formats: List of prompt formats to compare (e.g., ["json", "toon"])
        config_path: Path to config file
        mode: Player mode (default: "text")

    Returns:
        Dictionary with format keys containing game results
    """
    results = {fmt: [] for fmt in formats}

    for fmt in formats:
        print(f"\n{'='*60}")
        print(f"Running {num_games} games with {fmt.upper()} format")
        print(f"{'='*60}")

        try:
            runner = CatanGameRunner(config_path, mode=mode, prompt_format=fmt)

            for i in range(num_games):
                print(f"\n  Game {i + 1}/{num_games}...")
                try:
                    result = runner.run_game(matchup, game_id=f"{fmt}_{i+1}")
                    result["format"] = fmt
                    result["mode"] = mode
                    results[fmt].append(result)
                    print(f"    Winner: {result['winner']}")
                    print(f"    Cost: ${result['total_cost']:.4f}")
                    print(f"    Tokens: {result['total_tokens']}")
                except Exception as e:
                    print(f"    Error: {e}")
                    continue

        except Exception as e:
            print(f"Error initializing runner with {fmt} format: {e}")
            continue

    return results


def analyze_comparison(results: Dict[str, List[Dict[str, Any]]], comparison_type: str = "mode") -> Dict[str, Any]:
    """
    Analyze comparison results between modes or formats.

    Args:
        results: Dictionary with mode/format keys containing game results
        comparison_type: "mode" or "format" to customize analysis labels

    Returns:
        Analysis dictionary with metrics for each mode/format
    """
    analysis = {"_comparison_type": comparison_type}

    for key, games in results.items():
        if not games:
            analysis[key] = {"error": "No games completed"}
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

        analysis[key] = {
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
    comparison_type = analysis.get("_comparison_type", "mode")
    is_format_comparison = comparison_type == "format"

    lines = []
    lines.append("=" * 70)
    if is_format_comparison:
        lines.append("LLM CATAN ARENA - FORMAT COMPARISON REPORT")
    else:
        lines.append("LLM CATAN ARENA - MODE COMPARISON REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    # Get all keys except metadata
    keys = [k for k in analysis.keys() if not k.startswith("_")]

    for key in keys:
        data = analysis[key]
        if "error" in data:
            lines.append(f"\n{key.upper()}: {data['error']}")
            continue

        lines.append(f"\n{'-'*70}")
        if is_format_comparison:
            lines.append(f"{key.upper()} FORMAT RESULTS")
        else:
            lines.append(f"{key.upper()} MODE RESULTS")
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
    if len(keys) >= 2:
        # Get first two valid keys for comparison
        valid_keys = [k for k in keys if "error" not in analysis.get(k, {})]
        if len(valid_keys) >= 2:
            key1, key2 = valid_keys[0], valid_keys[1]
            data1 = analysis[key1]
            data2 = analysis[key2]

            lines.append(f"\n{'='*70}")
            lines.append("COMPARISON SUMMARY")
            lines.append(f"{'='*70}")

            cost_diff = data2["avg_cost_per_game"] - data1["avg_cost_per_game"]
            cost_pct = (cost_diff / data1["avg_cost_per_game"] * 100) if data1["avg_cost_per_game"] > 0 else 0

            token_diff = data2["avg_tokens_per_game"] - data1["avg_tokens_per_game"]
            token_pct = (token_diff / data1["avg_tokens_per_game"] * 100) if data1["avg_tokens_per_game"] > 0 else 0

            lines.append(f"")
            lines.append(f"Cost Difference ({key2.upper()} vs {key1.upper()}):")
            lines.append(f"  ${cost_diff:+.4f} per game ({cost_pct:+.1f}%)")

            lines.append(f"")
            lines.append(f"Token Difference ({key2.upper()} vs {key1.upper()}):")
            lines.append(f"  {token_diff:+,.0f} per game ({token_pct:+.1f}%)")

            lines.append(f"")
            if cost_diff < 0:
                lines.append(f"  -> {key2.upper()} is MORE cost efficient")
            elif cost_diff > 0:
                lines.append(f"  -> {key1.upper()} is MORE cost efficient")
            else:
                lines.append(f"  -> Both have similar cost efficiency")

            # Additional format-specific insights
            if is_format_comparison:
                lines.append(f"")
                savings_pct = abs(token_pct)
                if token_diff < 0:
                    lines.append(f"  Token Savings: {savings_pct:.1f}% fewer tokens with {key2.upper()}")
                elif token_diff > 0:
                    lines.append(f"  Token Savings: {savings_pct:.1f}% fewer tokens with {key1.upper()}")

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

    comparison_type = analysis.get("_comparison_type", "mode")
    is_format_comparison = comparison_type == "format"

    # Get all valid keys (skip metadata keys)
    keys = [k for k in analysis.keys() if not k.startswith("_") and "error" not in analysis.get(k, {})]
    if len(keys) < 2:
        print("Not enough data to generate comparison plots")
        return

    # Cost comparison bar chart
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Colors for different items
    colors = ["#3498db", "#e74c3c", "#27ae60", "#9b59b6"][:len(keys)]

    # Average cost
    costs = [analysis[k]["avg_cost_per_game"] for k in keys]
    axes[0].bar(keys, costs, color=colors)
    title_suffix = "Format" if is_format_comparison else "Mode"
    axes[0].set_title(f"Average Cost per Game by {title_suffix}")
    axes[0].set_ylabel("Cost ($)")
    for i, cost in enumerate(costs):
        axes[0].text(i, cost + 0.001, f"${cost:.4f}", ha="center")

    # Average tokens
    tokens = [analysis[k]["avg_tokens_per_game"] for k in keys]
    axes[1].bar(keys, tokens, color=colors)
    axes[1].set_title(f"Average Tokens per Game by {title_suffix}")
    axes[1].set_ylabel("Tokens")
    for i, tok in enumerate(tokens):
        axes[1].text(i, tok + 100, f"{tok:,.0f}", ha="center")

    plt.tight_layout()
    filename = "format_comparison.png" if is_format_comparison else "mode_comparison.png"
    plt.savefig(f"{output_dir}/{filename}", dpi=300)
    print(f"Saved comparison plot to {output_dir}/{filename}")
    plt.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare text vs MCP mode performance, or different prompt formats, in LLM Catan Arena"
    )

    parser.add_argument(
        "--games",
        type=int,
        default=3,
        help="Number of games to run per mode/format (default: 3)"
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

    parser.add_argument(
        "--compare-formats",
        nargs=2,
        metavar=("FORMAT1", "FORMAT2"),
        choices=["json", "json-minified", "toon"],
        help="Compare two prompt formats instead of modes (e.g., --compare-formats json toon)"
    )

    parser.add_argument(
        "--mode",
        choices=["text", "mcp"],
        default="text",
        help="Player mode to use for format comparison (default: text)"
    )

    args = parser.parse_args()

    print("=" * 70)
    if args.compare_formats:
        print("LLM CATAN ARENA - FORMAT COMPARISON TOOL")
        print("=" * 70)
        print(f"Comparing formats: {args.compare_formats[0]} vs {args.compare_formats[1]}")
        print(f"Games per format: {args.games}")
        print(f"Player mode: {args.mode}")
    else:
        print("LLM CATAN ARENA - MODE COMPARISON TOOL")
        print("=" * 70)
        print(f"Games per mode: {args.games}")
    print(f"Matchup: {args.matchup}")
    print(f"Config: {args.config}")
    print("=" * 70)

    # Run comparison games
    if args.compare_formats:
        results = run_format_comparison_games(
            num_games=args.games,
            matchup=args.matchup,
            formats=args.compare_formats,
            config_path=args.config,
            mode=args.mode
        )
        comparison_type = "format"
    else:
        results = run_comparison_games(
            num_games=args.games,
            matchup=args.matchup,
            config_path=args.config
        )
        comparison_type = "mode"

    # Save raw results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config_data = {
        "games_per_item": args.games,
        "matchup": args.matchup,
        "comparison_type": comparison_type
    }
    if args.compare_formats:
        config_data["formats"] = args.compare_formats
        config_data["mode"] = args.mode

    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": config_data,
            "results": results
        }, f, indent=2, default=str)

    print(f"\nRaw results saved to {output_path}")

    # Analyze results
    analysis = analyze_comparison(results, comparison_type=comparison_type)

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
