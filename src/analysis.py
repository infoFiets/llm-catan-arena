"""
Analysis Module for LLM Catan Arena.

Load game results, calculate statistics, and generate comparison charts.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


class CatanAnalyzer:
    """
    Analyzes results from Catan games.

    Provides:
    - Win rate calculations by model
    - Cost analysis
    - Performance statistics
    - Visualization generation
    """

    def __init__(self, results_dir: str = "data/games"):
        """
        Initialize analyzer.

        Args:
            results_dir: Directory containing game result JSON files
        """
        self.results_dir = Path(results_dir)
        self.log = logging.getLogger(__name__)

    def load_results(self) -> List[Dict[str, Any]]:
        """
        Load all game results from JSON files.

        Returns:
            List of game result dictionaries
        """
        results = []

        if not self.results_dir.exists():
            self.log.warning(f"Results directory not found: {self.results_dir}")
            return results

        for json_file in self.results_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    results.append(data)
            except Exception as e:
                self.log.error(f"Error loading {json_file}: {e}")

        self.log.info(f"Loaded {len(results)} game results")
        return results

    def calculate_win_rates(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Calculate win rates for each model.

        Args:
            results: List of game results

        Returns:
            DataFrame with win statistics by model
        """
        stats = defaultdict(lambda: {"games": 0, "wins": 0})

        for result in results:
            winner = result.get("winner")
            players = result.get("players", [])

            for player in players:
                # Extract model name (before colon)
                model = player.split(":")[0] if ":" in player else player
                stats[model]["games"] += 1

                if winner and model in winner:
                    stats[model]["wins"] += 1

        # Convert to DataFrame
        df_data = []
        for model, model_stats in stats.items():
            win_rate = model_stats["wins"] / model_stats["games"] if model_stats["games"] > 0 else 0
            df_data.append({
                "model": model,
                "games": model_stats["games"],
                "wins": model_stats["wins"],
                "win_rate": win_rate
            })

        df = pd.DataFrame(df_data)
        df = df.sort_values("win_rate", ascending=False)

        return df

    def calculate_cost_stats(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Calculate cost statistics by model.

        Args:
            results: List of game results

        Returns:
            DataFrame with cost statistics
        """
        costs = defaultdict(list)

        for result in results:
            # Extract costs from result
            if "total_cost" in result:
                # This is a tournament result format
                for player in result.get("players", []):
                    model = player.split(":")[0] if ":" in player else player
                    cost_per_player = result["total_cost"] / len(result.get("players", [4]))
                    costs[model].append(cost_per_player)

        # Convert to DataFrame
        df_data = []
        for model, model_costs in costs.items():
            if model_costs:
                df_data.append({
                    "model": model,
                    "avg_cost": sum(model_costs) / len(model_costs),
                    "total_cost": sum(model_costs),
                    "min_cost": min(model_costs),
                    "max_cost": max(model_costs),
                    "games": len(model_costs)
                })

        df = pd.DataFrame(df_data)
        df = df.sort_values("avg_cost")

        return df

    def plot_win_rates(self, win_stats: pd.DataFrame, output_path: str = None):
        """
        Create bar chart of win rates.

        Args:
            win_stats: DataFrame from calculate_win_rates()
            output_path: Optional path to save figure
        """
        plt.figure(figsize=(10, 6))
        sns.barplot(data=win_stats, x="model", y="win_rate")
        plt.title("Win Rates by Model", fontsize=16)
        plt.xlabel("Model", fontsize=12)
        plt.ylabel("Win Rate", fontsize=12)
        plt.xticks(rotation=45)
        plt.ylim(0, 1)

        # Add value labels on bars
        for i, row in win_stats.iterrows():
            plt.text(
                i, row["win_rate"] + 0.02,
                f"{row['win_rate']:.1%}\n({row['wins']}/{row['games']})",
                ha='center'
            )

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300)
            print(f"Saved plot to {output_path}")
        else:
            plt.show()

    def plot_cost_comparison(self, cost_stats: pd.DataFrame, output_path: str = None):
        """
        Create bar chart comparing costs.

        Args:
            cost_stats: DataFrame from calculate_cost_stats()
            output_path: Optional path to save figure
        """
        plt.figure(figsize=(10, 6))
        sns.barplot(data=cost_stats, x="model", y="avg_cost")
        plt.title("Average Cost per Game by Model", fontsize=16)
        plt.xlabel("Model", fontsize=12)
        plt.ylabel("Average Cost ($)", fontsize=12)
        plt.xticks(rotation=45)

        # Add value labels
        for i, row in cost_stats.iterrows():
            plt.text(
                i, row["avg_cost"] + 0.001,
                f"${row['avg_cost']:.4f}",
                ha='center'
            )

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300)
            print(f"Saved plot to {output_path}")
        else:
            plt.show()

    def generate_report(self, results: List[Dict[str, Any]] = None) -> str:
        """
        Generate text summary report.

        Args:
            results: Optional list of results. If None, loads from directory.

        Returns:
            Formatted report string
        """
        if results is None:
            results = self.load_results()

        if not results:
            return "No results to analyze."

        win_stats = self.calculate_win_rates(results)
        cost_stats = self.calculate_cost_stats(results)

        report = []
        report.append("=" * 60)
        report.append("LLM CATAN ARENA - ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"\nTotal Games: {len(results)}\n")

        report.append("-" * 60)
        report.append("WIN RATES BY MODEL")
        report.append("-" * 60)
        for _, row in win_stats.iterrows():
            report.append(
                f"{row['model']:.<30} {row['win_rate']:>6.1%}  "
                f"({row['wins']}/{row['games']} games)"
            )

        if not cost_stats.empty:
            report.append("\n" + "-" * 60)
            report.append("COST STATISTICS")
            report.append("-" * 60)
            for _, row in cost_stats.iterrows():
                report.append(
                    f"{row['model']:.<30} ${row['avg_cost']:>8.4f} avg  "
                    f"(${row['total_cost']:.2f} total)"
                )

        report.append("\n" + "=" * 60)

        return "\n".join(report)

    def print_report(self, results: List[Dict[str, Any]] = None):
        """
        Print analysis report to console.

        Args:
            results: Optional list of results. If None, loads from directory.
        """
        print(self.generate_report(results))
