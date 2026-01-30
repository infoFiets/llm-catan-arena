#!/usr/bin/env python3
"""
Full Tournament Runner for LLM Catan Arena.

Runs a comprehensive tournament designed to generate insights for:
1. Format comparison (JSON vs TOON)
2. Mode comparison (Text vs Tool-calling)
3. Model rankings
4. Model evolution analysis

Usage:
    # Estimate costs first
    python scripts/run_full_tournament.py --estimate-only

    # Run specific phase
    python scripts/run_full_tournament.py --phase format
    python scripts/run_full_tournament.py --phase mode
    python scripts/run_full_tournament.py --phase ranking
    python scripts/run_full_tournament.py --phase evolution

    # Run everything
    python scripts/run_full_tournament.py --all

    # Quick test run (fewer games)
    python scripts/run_full_tournament.py --all --quick
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.game_runner import CatanGameRunner
from src.elo import EloRating

# =============================================================================
# Tournament Configuration
# =============================================================================

# Models to include (must match config_full_tournament.yaml)
MODELS = {
    "claude": "anthropic/claude-4.5-sonnet-20250929",
    "claude-opus": "anthropic/claude-4.5-opus-20251124",
    "haiku": "anthropic/claude-4.5-haiku-20251001",
    "gpt5": "openai/gpt-5.2-20251211",
    "gemini": "google/gemini-2.5-pro",
}

# Extended models for evolution analysis
EXTENDED_MODELS = {
    "gpt5-mini": "openai/gpt-5-mini-2025-08-07",
    "gpt4o": "openai/gpt-4o",
    "gemini-flash": "google/gemini-2.5-flash",
    "gemini-3": "google/gemini-3-pro-preview-20251117",
    "llama4": "meta-llama/llama-4-maverick-17b-128e-instruct",
    "deepseek": "deepseek/deepseek-v3.2-20251201",
}

# Cost estimates per game (rough, in USD)
COST_PER_GAME = {
    "claude": 0.10,
    "claude-opus": 0.40,
    "haiku": 0.01,
    "gpt5": 0.20,
    "gpt5-mini": 0.02,
    "gpt4o": 0.08,
    "gemini": 0.05,
    "gemini-flash": 0.01,
    "gemini-3": 0.05,
    "llama4": 0.02,
    "deepseek": 0.01,
}

# =============================================================================
# Tournament Phases
# =============================================================================

def get_format_comparison_config(quick: bool = False) -> Dict:
    """Phase 1: Compare JSON vs TOON formats."""
    games_per_format = 5 if quick else 25

    return {
        "name": "Format Comparison",
        "description": "Compare token efficiency formats (JSON vs TOON) on same model",
        "experiments": [
            {
                "name": "claude_json",
                "matchup": ["claude", "claude", "claude", "claude"],
                "mode": "text",
                "format": "json",
                "games": games_per_format
            },
            {
                "name": "claude_json_minified",
                "matchup": ["claude", "claude", "claude", "claude"],
                "mode": "text",
                "format": "json-minified",
                "games": games_per_format
            },
            {
                "name": "claude_toon",
                "matchup": ["claude", "claude", "claude", "claude"],
                "mode": "text",
                "format": "toon",
                "games": games_per_format
            },
        ]
    }


def get_mode_comparison_config(quick: bool = False) -> Dict:
    """Phase 2: Compare Text vs Tool-calling modes."""
    games = 10 if quick else 40

    return {
        "name": "Mode Comparison",
        "description": "Compare text mode vs tool-calling mode",
        "experiments": [
            {
                "name": "claude_mode_comparison",
                "matchup": ["claude-mcp", "claude-text", "claude-mcp", "claude-text"],
                "mode": "text",  # Default, overridden by suffix
                "format": "json",
                "games": games
            },
            {
                "name": "gpt5_mode_comparison",
                "matchup": ["gpt5-mcp", "gpt5-text", "gpt5-mcp", "gpt5-text"],
                "mode": "text",
                "format": "json",
                "games": games
            },
            {
                "name": "cross_model_mode",
                "matchup": ["claude-mcp", "claude-text", "gpt5-mcp", "gpt5-text"],
                "mode": "text",
                "format": "json",
                "games": games
            },
        ]
    }


def get_ranking_config(quick: bool = False) -> Dict:
    """Phase 3: Full model rankings."""
    games_per_matchup = 5 if quick else 30

    # Generate round-robin style matchups
    models = ["claude", "gpt5", "gemini", "haiku"]
    matchups = []

    # Each model plays against combinations of others
    matchups.append({
        "name": "mixed_all",
        "matchup": ["claude", "gpt5", "gemini", "haiku"],
        "mode": "text",
        "format": "json",
        "games": games_per_matchup * 2  # More games for main comparison
    })

    # Pairwise comparisons (2 of each model)
    for i, m1 in enumerate(models):
        for m2 in models[i+1:]:
            matchups.append({
                "name": f"{m1}_vs_{m2}",
                "matchup": [m1, m1, m2, m2],
                "mode": "text",
                "format": "json",
                "games": games_per_matchup
            })

    return {
        "name": "Model Rankings",
        "description": "Round-robin tournament for Elo rankings",
        "experiments": matchups
    }


def get_evolution_config(quick: bool = False) -> Dict:
    """Phase 4: Model evolution analysis."""
    games = 5 if quick else 20

    return {
        "name": "Model Evolution",
        "description": "Compare model versions within same provider",
        "note": "Requires extended models in config_full_tournament.yaml",
        "experiments": [
            # GPT evolution (GPT-4o vs GPT-5 series)
            {
                "name": "gpt_evolution",
                "matchup": ["gpt4o", "gpt5", "gpt5-mini", "gpt4o"],
                "mode": "text",
                "format": "json",
                "games": games,
                "optional": True  # Skip if models not configured
            },
            # Claude tiers (Opus vs Sonnet vs Haiku)
            {
                "name": "claude_tiers",
                "matchup": ["claude-opus", "claude", "haiku", "haiku"],
                "mode": "text",
                "format": "json",
                "games": games
            },
            # Gemini evolution
            {
                "name": "gemini_evolution",
                "matchup": ["gemini-3", "gemini", "gemini-flash", "gemini-flash"],
                "mode": "text",
                "format": "json",
                "games": games,
                "optional": True
            },
            # Open source comparison
            {
                "name": "open_source_battle",
                "matchup": ["llama4", "deepseek", "llama4", "deepseek"],
                "mode": "text",
                "format": "json",
                "games": games,
                "optional": True
            },
        ]
    }


# =============================================================================
# Tournament Runner
# =============================================================================

def estimate_costs(phases: List[Dict]) -> Dict:
    """Estimate total tournament costs."""
    total_games = 0
    total_cost = 0.0
    phase_costs = []

    for phase in phases:
        phase_games = 0
        phase_cost = 0.0

        for exp in phase.get("experiments", []):
            games = exp.get("games", 0)
            matchup = exp.get("matchup", [])

            # Estimate cost per game based on models
            game_cost = sum(COST_PER_GAME.get(m.replace("-mcp", "").replace("-text", ""), 0.10)
                          for m in matchup) / 4  # Average per player

            exp_cost = games * game_cost * 4  # 4 players per game
            phase_games += games
            phase_cost += exp_cost

        phase_costs.append({
            "name": phase["name"],
            "games": phase_games,
            "estimated_cost": phase_cost
        })

        total_games += phase_games
        total_cost += phase_cost

    return {
        "phases": phase_costs,
        "total_games": total_games,
        "total_estimated_cost": total_cost,
        "note": "Costs are rough estimates. Actual costs depend on game length and token usage."
    }


def run_phase(phase_config: Dict, output_dir: Path) -> List[Dict]:
    """Run a single tournament phase."""
    results = []
    phase_name = phase_config["name"]

    print(f"\n{'='*70}")
    print(f"PHASE: {phase_name}")
    print(f"{'='*70}")
    print(f"Description: {phase_config.get('description', '')}\n")

    for exp in phase_config.get("experiments", []):
        exp_name = exp["name"]
        matchup = exp["matchup"]
        mode = exp.get("mode", "text")
        fmt = exp.get("format", "json")
        games = exp.get("games", 10)
        optional = exp.get("optional", False)

        print(f"\n--- Experiment: {exp_name} ---")
        print(f"Matchup: {matchup}")
        print(f"Mode: {mode}, Format: {fmt}, Games: {games}")

        try:
            runner = CatanGameRunner(mode=mode, prompt_format=fmt)

            exp_results = []
            for i in range(games):
                print(f"  Game {i+1}/{games}...", end=" ", flush=True)
                try:
                    result = runner.run_game(matchup, game_id=f"{exp_name}_{i+1}")
                    result["experiment"] = exp_name
                    result["phase"] = phase_name
                    result["format"] = fmt
                    result["mode"] = mode
                    exp_results.append(result)
                    print(f"Winner: {result.get('winner', 'N/A')}, Cost: ${result.get('total_cost', 0):.4f}")
                except Exception as e:
                    print(f"ERROR: {e}")
                    continue

            results.extend(exp_results)

            # Save intermediate results
            exp_file = output_dir / f"{exp_name}_results.json"
            with open(exp_file, "w") as f:
                json.dump(exp_results, f, indent=2, default=str)
            print(f"  Saved {len(exp_results)} results to {exp_file}")

        except Exception as e:
            if optional:
                print(f"  Skipping optional experiment (models not configured): {e}")
            else:
                print(f"  ERROR in experiment: {e}")
                raise

    return results


def generate_summary(all_results: List[Dict], output_dir: Path):
    """Generate summary statistics and save."""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_games": len(all_results),
        "phases": {},
        "by_experiment": {},
        "by_model": {},
        "by_format": {},
        "by_mode": {}
    }

    # Aggregate by various dimensions
    for result in all_results:
        phase = result.get("phase", "unknown")
        exp = result.get("experiment", "unknown")
        fmt = result.get("format", "unknown")
        mode = result.get("mode", "unknown")
        winner = result.get("winner", "unknown")
        cost = result.get("total_cost", 0)
        tokens = result.get("total_tokens", 0)

        # By phase
        if phase not in summary["phases"]:
            summary["phases"][phase] = {"games": 0, "cost": 0, "tokens": 0}
        summary["phases"][phase]["games"] += 1
        summary["phases"][phase]["cost"] += cost
        summary["phases"][phase]["tokens"] += tokens

        # By experiment
        if exp not in summary["by_experiment"]:
            summary["by_experiment"][exp] = {"games": 0, "wins": {}, "cost": 0, "tokens": 0}
        summary["by_experiment"][exp]["games"] += 1
        summary["by_experiment"][exp]["cost"] += cost
        summary["by_experiment"][exp]["tokens"] += tokens
        if winner:
            winner_key = winner.replace("-mcp", "").replace("-text", "")
            summary["by_experiment"][exp]["wins"][winner_key] = \
                summary["by_experiment"][exp]["wins"].get(winner_key, 0) + 1

        # By format
        if fmt not in summary["by_format"]:
            summary["by_format"][fmt] = {"games": 0, "cost": 0, "tokens": 0}
        summary["by_format"][fmt]["games"] += 1
        summary["by_format"][fmt]["cost"] += cost
        summary["by_format"][fmt]["tokens"] += tokens

        # By mode
        if mode not in summary["by_mode"]:
            summary["by_mode"][mode] = {"games": 0, "cost": 0, "tokens": 0}
        summary["by_mode"][mode]["games"] += 1
        summary["by_mode"][mode]["cost"] += cost
        summary["by_mode"][mode]["tokens"] += tokens

    # Calculate averages
    for key in ["phases", "by_experiment", "by_format", "by_mode"]:
        for name, data in summary[key].items():
            if data["games"] > 0:
                data["avg_cost"] = data["cost"] / data["games"]
                data["avg_tokens"] = data["tokens"] / data["games"]

    # Save summary
    summary_file = output_dir / "tournament_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to {summary_file}")

    # Print summary
    print("\n" + "="*70)
    print("TOURNAMENT SUMMARY")
    print("="*70)
    print(f"Total games: {summary['total_games']}")
    print(f"Total cost: ${sum(p['cost'] for p in summary['phases'].values()):.2f}")

    print("\nBy Format:")
    for fmt, data in summary["by_format"].items():
        print(f"  {fmt}: {data['games']} games, ${data['avg_cost']:.4f}/game, {data['avg_tokens']:.0f} tokens/game")

    print("\nElo Leaderboard:")
    elo = EloRating()
    print(elo.format_leaderboard())

    return summary


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Run full LLM Catan tournament")

    parser.add_argument("--phase", choices=["format", "mode", "ranking", "evolution"],
                       help="Run specific phase only")
    parser.add_argument("--all", action="store_true", help="Run all phases")
    parser.add_argument("--quick", action="store_true",
                       help="Quick test run with fewer games")
    parser.add_argument("--estimate-only", action="store_true",
                       help="Only estimate costs, don't run games")
    parser.add_argument("--output-dir", default="data/tournament",
                       help="Output directory for results")

    args = parser.parse_args()

    # Build phase configs
    quick = args.quick
    phases = []

    if args.phase == "format" or args.all:
        phases.append(get_format_comparison_config(quick))
    if args.phase == "mode" or args.all:
        phases.append(get_mode_comparison_config(quick))
    if args.phase == "ranking" or args.all:
        phases.append(get_ranking_config(quick))
    if args.phase == "evolution" or args.all:
        phases.append(get_evolution_config(quick))

    if not phases:
        print("No phases selected. Use --phase <name> or --all")
        parser.print_help()
        return

    # Cost estimation
    estimates = estimate_costs(phases)

    print("="*70)
    print("LLM CATAN ARENA - FULL TOURNAMENT")
    print("="*70)
    print(f"\nPhases to run: {len(phases)}")
    print(f"Total games: {estimates['total_games']}")
    print(f"Estimated cost: ${estimates['total_estimated_cost']:.2f}")
    print(f"\nCost breakdown:")
    for phase in estimates["phases"]:
        print(f"  {phase['name']}: {phase['games']} games, ~${phase['estimated_cost']:.2f}")

    if args.estimate_only:
        print("\n[Estimate only - not running games]")
        return

    # Confirm before running
    print(f"\n{'='*70}")
    response = input("Proceed with tournament? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        return

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run phases
    all_results = []
    for phase_config in phases:
        phase_results = run_phase(phase_config, output_dir)
        all_results.extend(phase_results)

    # Save all results
    all_results_file = output_dir / "all_results.json"
    with open(all_results_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nAll results saved to {all_results_file}")

    # Generate summary
    generate_summary(all_results, output_dir)

    print("\n" + "="*70)
    print("TOURNAMENT COMPLETE")
    print("="*70)
    print(f"\nResults in: {output_dir}")
    print("\nNext steps:")
    print("  1. python scripts/elo_ratings.py  # View rankings")
    print("  2. Review data/tournament/*.json for detailed analysis")
    print("  3. Generate visualizations with src/analysis.py")


if __name__ == "__main__":
    main()
