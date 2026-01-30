#!/usr/bin/env python3
"""
Generate Insights for Blog Posts from Tournament Data.

Creates analysis, visualizations, and exportable data for:
- Blog posts
- LinkedIn posts
- Data visualizations

Usage:
    python scripts/generate_insights.py --input data/tournament
    python scripts/generate_insights.py --input data/tournament --output output/blog
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.elo import EloRating


def load_tournament_data(input_dir: Path) -> Dict[str, Any]:
    """Load all tournament data from directory."""
    data = {
        "results": [],
        "summary": None
    }

    # Load all result files
    for json_file in input_dir.glob("*_results.json"):
        with open(json_file) as f:
            results = json.load(f)
            data["results"].extend(results)

    # Load summary if exists
    summary_file = input_dir / "tournament_summary.json"
    if summary_file.exists():
        with open(summary_file) as f:
            data["summary"] = json.load(f)

    print(f"Loaded {len(data['results'])} game results")
    return data


# =============================================================================
# Insight 1: Format Comparison (TOON Analysis)
# =============================================================================

def analyze_format_comparison(results: List[Dict], output_dir: Path) -> Dict:
    """Analyze TOON vs JSON format performance."""
    format_stats = defaultdict(lambda: {
        "games": 0,
        "total_cost": 0,
        "total_tokens": 0,
        "wins": defaultdict(int)
    })

    for r in results:
        fmt = r.get("format", "unknown")
        format_stats[fmt]["games"] += 1
        format_stats[fmt]["total_cost"] += r.get("total_cost", 0)
        format_stats[fmt]["total_tokens"] += r.get("total_tokens", 0)

        winner = r.get("winner")
        if winner:
            format_stats[fmt]["wins"][winner] += 1

    # Calculate averages
    analysis = {}
    for fmt, stats in format_stats.items():
        if stats["games"] > 0:
            analysis[fmt] = {
                "games": stats["games"],
                "avg_cost": stats["total_cost"] / stats["games"],
                "avg_tokens": stats["total_tokens"] / stats["games"],
                "total_cost": stats["total_cost"],
                "wins": dict(stats["wins"])
            }

    # Calculate savings
    if "json" in analysis and "toon" in analysis:
        json_cost = analysis["json"]["avg_cost"]
        toon_cost = analysis["toon"]["avg_cost"]
        json_tokens = analysis["json"]["avg_tokens"]
        toon_tokens = analysis["toon"]["avg_tokens"]

        analysis["comparison"] = {
            "cost_savings_pct": ((json_cost - toon_cost) / json_cost * 100) if json_cost > 0 else 0,
            "token_savings_pct": ((json_tokens - toon_tokens) / json_tokens * 100) if json_tokens > 0 else 0,
            "cost_per_game_saved": json_cost - toon_cost,
            "tokens_per_game_saved": json_tokens - toon_tokens
        }

    # Create visualization
    if len(format_stats) > 1:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        formats = list(analysis.keys())
        formats = [f for f in formats if f != "comparison"]

        # Cost comparison
        costs = [analysis[f]["avg_cost"] for f in formats]
        axes[0].bar(formats, costs, color=['#3498db', '#e74c3c', '#27ae60'][:len(formats)])
        axes[0].set_title("Average Cost per Game by Format", fontsize=14)
        axes[0].set_ylabel("Cost ($)")
        for i, (f, c) in enumerate(zip(formats, costs)):
            axes[0].text(i, c + 0.001, f"${c:.4f}", ha='center')

        # Token comparison
        tokens = [analysis[f]["avg_tokens"] for f in formats]
        axes[1].bar(formats, tokens, color=['#3498db', '#e74c3c', '#27ae60'][:len(formats)])
        axes[1].set_title("Average Tokens per Game by Format", fontsize=14)
        axes[1].set_ylabel("Tokens")
        for i, (f, t) in enumerate(zip(formats, tokens)):
            axes[1].text(i, t + 100, f"{t:,.0f}", ha='center')

        plt.tight_layout()
        plt.savefig(output_dir / "format_comparison.png", dpi=300)
        plt.close()

    return analysis


# =============================================================================
# Insight 2: Mode Comparison (Tool-calling vs Text)
# =============================================================================

def analyze_mode_comparison(results: List[Dict], output_dir: Path) -> Dict:
    """Analyze tool-calling vs text mode performance."""
    # Group by player mode (from suffix)
    mode_wins = {"mcp": 0, "text": 0}
    mode_games = {"mcp": 0, "text": 0}
    mode_costs = {"mcp": [], "text": []}

    for r in results:
        winner = r.get("winner", "")
        specs = r.get("player_specs", [])

        for spec in specs:
            if "-mcp" in spec:
                mode_games["mcp"] += 1
                mode_costs["mcp"].append(r.get("total_cost", 0) / 4)
                if "-mcp" in winner:
                    mode_wins["mcp"] += 1
            elif "-text" in spec:
                mode_games["text"] += 1
                mode_costs["text"].append(r.get("total_cost", 0) / 4)
                if "-text" in winner:
                    mode_wins["text"] += 1

    analysis = {}
    for mode in ["mcp", "text"]:
        if mode_games[mode] > 0:
            analysis[mode] = {
                "games": mode_games[mode],
                "wins": mode_wins[mode],
                "win_rate": mode_wins[mode] / mode_games[mode] * 100,
                "avg_cost": sum(mode_costs[mode]) / len(mode_costs[mode]) if mode_costs[mode] else 0
            }

    # Create visualization
    if len(analysis) == 2:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        modes = list(analysis.keys())

        # Win rate comparison
        win_rates = [analysis[m]["win_rate"] for m in modes]
        colors = ['#9b59b6', '#f39c12']
        axes[0].bar(modes, win_rates, color=colors)
        axes[0].set_title("Win Rate by Mode", fontsize=14)
        axes[0].set_ylabel("Win Rate (%)")
        axes[0].set_ylim(0, 100)
        for i, (m, wr) in enumerate(zip(modes, win_rates)):
            axes[0].text(i, wr + 2, f"{wr:.1f}%", ha='center')

        # Cost comparison
        costs = [analysis[m]["avg_cost"] for m in modes]
        axes[1].bar(modes, costs, color=colors)
        axes[1].set_title("Average Cost per Player per Game", fontsize=14)
        axes[1].set_ylabel("Cost ($)")
        for i, (m, c) in enumerate(zip(modes, costs)):
            axes[1].text(i, c + 0.001, f"${c:.4f}", ha='center')

        plt.tight_layout()
        plt.savefig(output_dir / "mode_comparison.png", dpi=300)
        plt.close()

    return analysis


# =============================================================================
# Insight 3: Model Rankings
# =============================================================================

def analyze_model_rankings(results: List[Dict], output_dir: Path) -> Dict:
    """Analyze overall model performance and rankings."""
    # Get Elo ratings
    elo = EloRating()
    leaderboard = elo.get_leaderboard()

    # Calculate win rates from results
    model_stats = defaultdict(lambda: {"games": 0, "wins": 0, "cost": 0})

    for r in results:
        winner = r.get("winner", "")
        specs = r.get("player_specs", [])
        cost = r.get("total_cost", 0) / 4

        for spec in specs:
            # Normalize model name
            model = spec.replace("-mcp", "").replace("-text", "")
            model_stats[model]["games"] += 1
            model_stats[model]["cost"] += cost

            if model in winner:
                model_stats[model]["wins"] += 1

    # Combine with Elo
    analysis = {"models": {}}
    for model, stats in model_stats.items():
        if stats["games"] > 0:
            elo_data = next((e for e in leaderboard if model in e["player"]), None)

            analysis["models"][model] = {
                "games": stats["games"],
                "wins": stats["wins"],
                "win_rate": stats["wins"] / stats["games"] * 100,
                "avg_cost": stats["cost"] / stats["games"],
                "elo": elo_data["rating"] if elo_data else 1500,
                "elo_games": elo_data["games"] if elo_data else 0
            }

    # Sort by Elo
    analysis["ranking"] = sorted(
        analysis["models"].items(),
        key=lambda x: x[1]["elo"],
        reverse=True
    )

    # Create visualization
    if analysis["models"]:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        models = [m for m, _ in analysis["ranking"]]
        elos = [analysis["models"][m]["elo"] for m in models]
        win_rates = [analysis["models"][m]["win_rate"] for m in models]

        # Elo rankings
        colors = plt.cm.viridis([i/len(models) for i in range(len(models))])
        axes[0].barh(models, elos, color=colors)
        axes[0].set_title("Elo Ratings", fontsize=14)
        axes[0].set_xlabel("Elo Rating")
        axes[0].axvline(x=1500, color='red', linestyle='--', alpha=0.5, label='Starting Elo')
        for i, (m, e) in enumerate(zip(models, elos)):
            axes[0].text(e + 5, i, f"{e:.0f}", va='center')

        # Win rates
        axes[1].barh(models, win_rates, color=colors)
        axes[1].set_title("Win Rates", fontsize=14)
        axes[1].set_xlabel("Win Rate (%)")
        axes[1].set_xlim(0, 100)
        for i, (m, wr) in enumerate(zip(models, win_rates)):
            axes[1].text(wr + 1, i, f"{wr:.1f}%", va='center')

        plt.tight_layout()
        plt.savefig(output_dir / "model_rankings.png", dpi=300)
        plt.close()

    return analysis


# =============================================================================
# Insight 4: Cost Efficiency
# =============================================================================

def analyze_cost_efficiency(results: List[Dict], output_dir: Path) -> Dict:
    """Analyze cost per win and cost efficiency."""
    model_costs = defaultdict(lambda: {"total_cost": 0, "wins": 0, "games": 0})

    for r in results:
        winner = r.get("winner", "")
        specs = r.get("player_specs", [])
        cost = r.get("total_cost", 0) / 4

        for spec in specs:
            model = spec.replace("-mcp", "").replace("-text", "")
            model_costs[model]["total_cost"] += cost
            model_costs[model]["games"] += 1

            if model in winner:
                model_costs[model]["wins"] += 1

    analysis = {}
    for model, stats in model_costs.items():
        if stats["games"] > 0:
            cost_per_win = stats["total_cost"] / stats["wins"] if stats["wins"] > 0 else float('inf')
            analysis[model] = {
                "total_cost": stats["total_cost"],
                "wins": stats["wins"],
                "games": stats["games"],
                "cost_per_game": stats["total_cost"] / stats["games"],
                "cost_per_win": cost_per_win if cost_per_win != float('inf') else None,
                "win_rate": stats["wins"] / stats["games"] * 100
            }

    # Create visualization
    if analysis:
        fig, ax = plt.subplots(figsize=(10, 6))

        models = sorted(analysis.keys(), key=lambda m: analysis[m]["cost_per_game"])
        costs = [analysis[m]["cost_per_game"] for m in models]
        win_rates = [analysis[m]["win_rate"] for m in models]

        # Scatter plot: cost vs win rate
        scatter = ax.scatter(costs, win_rates, s=200, c=range(len(models)), cmap='viridis', alpha=0.7)
        ax.set_xlabel("Average Cost per Game ($)", fontsize=12)
        ax.set_ylabel("Win Rate (%)", fontsize=12)
        ax.set_title("Cost Efficiency: Cost vs Win Rate", fontsize=14)

        # Add labels
        for i, model in enumerate(models):
            ax.annotate(model, (costs[i], win_rates[i]), fontsize=10,
                       xytext=(5, 5), textcoords='offset points')

        plt.tight_layout()
        plt.savefig(output_dir / "cost_efficiency.png", dpi=300)
        plt.close()

    return analysis


# =============================================================================
# Generate Blog Content
# =============================================================================

def generate_blog_content(analyses: Dict, output_dir: Path):
    """Generate markdown content for blog posts."""

    # Main insights document
    content = f"""# LLM Catan Arena: Tournament Insights

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*

## Executive Summary

This tournament compared multiple LLM models playing Settlers of Catan to evaluate:
- Strategic reasoning capabilities
- Cost efficiency
- Impact of prompt formats (TOON vs JSON)
- Tool-calling vs text-based interactions

---

## Key Findings

### 1. Format Comparison (TOON vs JSON)
"""

    if "format" in analyses:
        fmt = analyses["format"]
        if "comparison" in fmt:
            comp = fmt["comparison"]
            content += f"""
**Token Savings:** TOON format reduces tokens by **{comp['token_savings_pct']:.1f}%** compared to standard JSON.

**Cost Savings:** This translates to **{comp['cost_savings_pct']:.1f}%** cost reduction per game.

| Format | Avg Cost/Game | Avg Tokens/Game |
|--------|---------------|-----------------|
"""
            for f in ["json", "json-minified", "toon"]:
                if f in fmt:
                    content += f"| {f} | ${fmt[f]['avg_cost']:.4f} | {fmt[f]['avg_tokens']:,.0f} |\n"

    content += """
### 2. Mode Comparison (Tool-calling vs Text)
"""

    if "mode" in analyses:
        mode = analyses["mode"]
        if "mcp" in mode and "text" in mode:
            content += f"""
| Mode | Win Rate | Avg Cost |
|------|----------|----------|
| Tool-calling (MCP) | {mode['mcp']['win_rate']:.1f}% | ${mode['mcp']['avg_cost']:.4f} |
| Text | {mode['text']['win_rate']:.1f}% | ${mode['text']['avg_cost']:.4f} |
"""

    content += """
### 3. Model Rankings
"""

    if "rankings" in analyses:
        content += """
| Rank | Model | Elo Rating | Win Rate | Avg Cost |
|------|-------|------------|----------|----------|
"""
        for i, (model, stats) in enumerate(analyses["rankings"]["ranking"][:10], 1):
            content += f"| {i} | {model} | {stats['elo']:.0f} | {stats['win_rate']:.1f}% | ${stats['avg_cost']:.4f} |\n"

    content += """
### 4. Cost Efficiency

The most cost-efficient models (lowest cost per win):
"""

    if "efficiency" in analyses:
        sorted_eff = sorted(
            [(m, s) for m, s in analyses["efficiency"].items() if s.get("cost_per_win")],
            key=lambda x: x[1]["cost_per_win"]
        )[:5]

        content += """
| Model | Cost per Win | Win Rate |
|-------|--------------|----------|
"""
        for model, stats in sorted_eff:
            content += f"| {model} | ${stats['cost_per_win']:.4f} | {stats['win_rate']:.1f}% |\n"

    content += """
---

## Visualizations

- `format_comparison.png` - Token and cost savings by format
- `mode_comparison.png` - Tool-calling vs text performance
- `model_rankings.png` - Elo ratings and win rates
- `cost_efficiency.png` - Cost vs performance scatter plot

---

## Methodology

- **Game Engine:** Catanatron (Settlers of Catan simulation)
- **Player Types:** LLM-based strategic decision making
- **Elo System:** Multiplayer Elo with K=32
- **API Provider:** OpenRouter (unified access to multiple models)

---

*Data and code available at: [GitHub Repository URL]*
"""

    # Save blog content
    blog_file = output_dir / "blog_insights.md"
    with open(blog_file, "w") as f:
        f.write(content)

    print(f"Blog content saved to {blog_file}")

    # Generate LinkedIn snippets
    linkedin_content = f"""# LinkedIn Post Snippets

## Post 1: Main Results
🎮 Just ran a tournament of {analyses.get('total_games', 'X')} games pitting AI models against each other in Settlers of Catan!

Key findings:
• [Top model] emerged as the strategic champion
• TOON format reduces costs by ~{analyses.get('format', {}).get('comparison', {}).get('cost_savings_pct', 'X'):.0f}% vs JSON
• Tool-calling mode shows [X]% improvement over text mode

Full analysis: [link]

#AI #LLM #GameTheory #MachineLearning

---

## Post 2: Cost Efficiency
💰 Which AI is the best bang for your buck at strategic games?

I tested [models] playing Settlers of Catan.

Surprising finding: The most expensive model isn't always the best!

[Chart showing cost vs performance]

#AI #CostOptimization #LLM

---

## Post 3: TOON Format
📉 Reduced my AI API costs by {analyses.get('format', {}).get('comparison', {}).get('cost_savings_pct', 'X'):.0f}% with one simple change.

TOON (Token-Oriented Object Notation) compresses prompts while maintaining accuracy.

Before: Standard JSON = $X per game
After: TOON format = $Y per game

Same performance, lower cost. Details in comments.

#AI #CostReduction #Efficiency
"""

    linkedin_file = output_dir / "linkedin_snippets.md"
    with open(linkedin_file, "w") as f:
        f.write(linkedin_content)

    print(f"LinkedIn snippets saved to {linkedin_file}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate insights from tournament data")
    parser.add_argument("--input", "-i", default="data/tournament",
                       help="Input directory with tournament results")
    parser.add_argument("--output", "-o", default="output/insights",
                       help="Output directory for analysis")

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        print(f"Error: Input directory {input_dir} does not exist")
        print("Run a tournament first: python scripts/run_full_tournament.py --all")
        return

    # Load data
    data = load_tournament_data(input_dir)
    if not data["results"]:
        print("No results found. Run a tournament first.")
        return

    print(f"\nAnalyzing {len(data['results'])} game results...")

    # Run analyses
    analyses = {
        "total_games": len(data["results"])
    }

    print("\n1. Analyzing format comparison...")
    analyses["format"] = analyze_format_comparison(data["results"], output_dir)

    print("2. Analyzing mode comparison...")
    analyses["mode"] = analyze_mode_comparison(data["results"], output_dir)

    print("3. Analyzing model rankings...")
    analyses["rankings"] = analyze_model_rankings(data["results"], output_dir)

    print("4. Analyzing cost efficiency...")
    analyses["efficiency"] = analyze_cost_efficiency(data["results"], output_dir)

    # Save full analysis
    analysis_file = output_dir / "full_analysis.json"
    with open(analysis_file, "w") as f:
        json.dump(analyses, f, indent=2, default=str)
    print(f"\nFull analysis saved to {analysis_file}")

    # Generate blog content
    print("\nGenerating blog content...")
    generate_blog_content(analyses, output_dir)

    print("\n" + "="*70)
    print("INSIGHTS GENERATED")
    print("="*70)
    print(f"\nOutput files in {output_dir}:")
    for f in output_dir.glob("*"):
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()
