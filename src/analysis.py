"""
Analysis Module for LLM Catan Arena.

Load game results, calculate statistics, and generate comparison charts.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


# ============================================================================
# Standalone Analysis Functions
# ============================================================================

def load_all_games(data_dir: str = "data/games") -> List[Dict[str, Any]]:
    """
    Load all game JSON files from the data directory.

    Args:
        data_dir: Directory containing game result JSON files

    Returns:
        List of game result dictionaries
    """
    results = []
    data_path = Path(data_dir)

    if not data_path.exists():
        logging.warning(f"Results directory not found: {data_dir}")
        return results

    for json_file in sorted(data_path.glob("*.json")):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                # Add filename for reference
                data['_filename'] = json_file.name
                results.append(data)
        except Exception as e:
            logging.error(f"Error loading {json_file}: {e}")

    logging.info(f"Loaded {len(results)} game results from {data_dir}")
    return results


def extract_model_name(player_str: str) -> str:
    """
    Extract model name from player string (e.g., 'claude:RED' -> 'claude').

    Args:
        player_str: Player string in format 'model:COLOR'

    Returns:
        Model name
    """
    return player_str.split(':')[0] if ':' in player_str else player_str


def extract_full_model_name(final_scores: Dict[str, int], player_str: str) -> str:
    """
    Extract full model name from final_scores dictionary.

    Args:
        final_scores: Dictionary mapping full model names to scores
        player_str: Player string in format 'model:COLOR'

    Returns:
        Full model name (e.g., 'Claude 3.5 Sonnet')
    """
    color = player_str.split(':')[1] if ':' in player_str else None
    if not color:
        return player_str

    for full_name in final_scores.keys():
        if full_name.endswith(f':{color}'):
            # Extract just the model part without the color
            return full_name.rsplit(':', 1)[0]

    return extract_model_name(player_str)


def calculate_win_rates(games: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Calculate win rates for each model.

    Args:
        games: List of game result dictionaries

    Returns:
        DataFrame with columns: model, games, wins, losses, win_rate
    """
    stats = defaultdict(lambda: {"games": 0, "wins": 0, "losses": 0})

    for game in games:
        winner = game.get("winner", "")
        players = game.get("players", [])
        final_scores = game.get("final_scores", {})

        for player in players:
            model = extract_model_name(player)
            full_model = extract_full_model_name(final_scores, player)

            # Use full model name for better reporting
            stats[full_model]["games"] += 1

            if winner and extract_model_name(winner) == model:
                stats[full_model]["wins"] += 1
            else:
                stats[full_model]["losses"] += 1

    # Convert to DataFrame
    df_data = []
    for model, model_stats in stats.items():
        win_rate = model_stats["wins"] / model_stats["games"] if model_stats["games"] > 0 else 0
        df_data.append({
            "model": model,
            "games": model_stats["games"],
            "wins": model_stats["wins"],
            "losses": model_stats["losses"],
            "win_rate": win_rate
        })

    df = pd.DataFrame(df_data)
    df = df.sort_values("win_rate", ascending=False)

    return df


def calculate_costs(games: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Calculate cost statistics by model.

    Args:
        games: List of game result dictionaries

    Returns:
        DataFrame with columns: model, total_cost, avg_cost_per_game,
                                cost_per_win, games, wins
    """
    costs = defaultdict(lambda: {"costs": [], "wins": 0})

    for game in games:
        players = game.get("players", [])
        final_scores = game.get("final_scores", {})
        moves = game.get("moves", [])
        winner = game.get("winner", "")

        # Calculate cost per player from moves
        player_costs = defaultdict(float)
        for move in moves:
            player_color = move.get("player", "")
            cost = move.get("move_data", {}).get("cost", 0)
            player_costs[player_color] += cost

        # Aggregate by model
        for player in players:
            model = extract_model_name(player)
            full_model = extract_full_model_name(final_scores, player)
            color = player.split(':')[1] if ':' in player else player

            game_cost = player_costs.get(color, 0)
            costs[full_model]["costs"].append(game_cost)

            if winner and extract_model_name(winner) == model:
                costs[full_model]["wins"] += 1

    # Convert to DataFrame
    df_data = []
    for model, model_data in costs.items():
        model_costs = model_data["costs"]
        wins = model_data["wins"]

        if model_costs:
            total_cost = sum(model_costs)
            avg_cost = total_cost / len(model_costs)
            cost_per_win = total_cost / wins if wins > 0 else float('inf')

            df_data.append({
                "model": model,
                "total_cost": total_cost,
                "avg_cost_per_game": avg_cost,
                "cost_per_win": cost_per_win,
                "games": len(model_costs),
                "wins": wins
            })

    df = pd.DataFrame(df_data)
    df = df.sort_values("avg_cost_per_game")

    return df


def calculate_game_stats(games: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate overall game statistics.

    Args:
        games: List of game result dictionaries

    Returns:
        Dictionary with statistics: avg_turns, avg_duration_seconds,
        avg_scores, total_games, etc.
    """
    if not games:
        return {}

    total_turns = []
    durations = []
    all_scores = []
    victory_margins = []

    for game in games:
        # Count moves (turns)
        moves = game.get("moves", [])
        if moves:
            max_turn = max(m.get("turn_number", 0) for m in moves)
            total_turns.append(max_turn)

        # Calculate duration
        start_time = game.get("start_time")
        end_time = game.get("end_time")
        if start_time and end_time:
            try:
                start = datetime.fromisoformat(start_time)
                end = datetime.fromisoformat(end_time)
                duration = (end - start).total_seconds()
                durations.append(duration)
            except:
                pass

        # Scores
        final_scores = game.get("final_scores", {})
        if final_scores:
            scores = list(final_scores.values())
            all_scores.extend(scores)

            # Victory margin (winner score - second place score)
            sorted_scores = sorted(scores, reverse=True)
            if len(sorted_scores) >= 2:
                victory_margins.append(sorted_scores[0] - sorted_scores[1])

    stats = {
        "total_games": len(games),
        "avg_turns": np.mean(total_turns) if total_turns else 0,
        "median_turns": np.median(total_turns) if total_turns else 0,
        "min_turns": min(total_turns) if total_turns else 0,
        "max_turns": max(total_turns) if total_turns else 0,
        "avg_duration_seconds": np.mean(durations) if durations else 0,
        "avg_duration_minutes": np.mean(durations) / 60 if durations else 0,
        "median_duration_minutes": np.median(durations) / 60 if durations else 0,
        "avg_final_score": np.mean(all_scores) if all_scores else 0,
        "avg_winning_score": np.mean([max(game.get("final_scores", {}).values()) for game in games if game.get("final_scores")]),
        "avg_victory_margin": np.mean(victory_margins) if victory_margins else 0,
        "median_victory_margin": np.median(victory_margins) if victory_margins else 0,
    }

    return stats


def head_to_head_matrix(games: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Create a head-to-head win rate matrix between models.

    Args:
        games: List of game result dictionaries

    Returns:
        DataFrame with models as both rows and columns, values are win rates
    """
    # Track matchups: (model_a, model_b) -> {wins: X, losses: Y}
    matchups = defaultdict(lambda: {"wins": 0, "losses": 0})

    for game in games:
        winner = game.get("winner", "")
        if not winner:
            continue

        winner_model = extract_model_name(winner)
        players = game.get("players", [])
        final_scores = game.get("final_scores", {})

        # Get full model names
        winner_full = extract_full_model_name(final_scores, winner)

        for player in players:
            player_model = extract_model_name(player)
            player_full = extract_full_model_name(final_scores, player)

            if player_model != winner_model:
                # Winner beat this player
                matchups[(winner_full, player_full)]["wins"] += 1
                matchups[(player_full, winner_full)]["losses"] += 1

    # Get all unique models
    all_models = set()
    for (model_a, model_b) in matchups.keys():
        all_models.add(model_a)
        all_models.add(model_b)
    all_models = sorted(all_models)

    # Create matrix
    matrix = []
    for model_a in all_models:
        row = []
        for model_b in all_models:
            if model_a == model_b:
                row.append(np.nan)  # Can't play against self
            else:
                stats = matchups[(model_a, model_b)]
                total = stats["wins"] + stats["losses"]
                win_rate = stats["wins"] / total if total > 0 else 0
                row.append(win_rate)
        matrix.append(row)

    df = pd.DataFrame(matrix, index=all_models, columns=all_models)
    return df


def export_summary_report(games: List[Dict[str, Any]],
                         output_file: str = "output/summary_report.md") -> None:
    """
    Generate a comprehensive markdown summary report.

    Args:
        games: List of game result dictionaries
        output_file: Path to save the markdown report
    """
    if not games:
        logging.warning("No games to analyze")
        return

    # Calculate all statistics
    win_rates = calculate_win_rates(games)
    costs = calculate_costs(games)
    game_stats = calculate_game_stats(games)
    h2h_matrix = head_to_head_matrix(games)

    # Build markdown report
    lines = []
    lines.append("# LLM Catan Arena - Analysis Report")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"\n## Overview\n")
    lines.append(f"- **Total Games Analyzed**: {game_stats['total_games']}")
    lines.append(f"- **Average Game Length**: {game_stats['avg_turns']:.1f} turns")
    lines.append(f"- **Average Game Duration**: {game_stats['avg_duration_minutes']:.1f} minutes")
    lines.append(f"- **Average Winning Score**: {game_stats['avg_winning_score']:.1f} VP")
    lines.append(f"- **Average Victory Margin**: {game_stats['avg_victory_margin']:.1f} VP")

    lines.append("\n## Win Rates by Model\n")
    lines.append("| Model | Games | Wins | Losses | Win Rate |")
    lines.append("|-------|-------|------|--------|----------|")
    for _, row in win_rates.iterrows():
        lines.append(f"| {row['model']} | {row['games']} | {row['wins']} | "
                    f"{row['losses']} | {row['win_rate']:.1%} |")

    lines.append("\n## Cost Analysis\n")
    lines.append("| Model | Games | Total Cost | Avg Cost/Game | Cost/Win | Wins |")
    lines.append("|-------|-------|------------|---------------|----------|------|")
    for _, row in costs.iterrows():
        cost_per_win_str = f"${row['cost_per_win']:.4f}" if row['cost_per_win'] != float('inf') else "N/A"
        lines.append(f"| {row['model']} | {row['games']} | ${row['total_cost']:.4f} | "
                    f"${row['avg_cost_per_game']:.4f} | {cost_per_win_str} | {row['wins']} |")

    lines.append("\n## Head-to-Head Win Rates\n")
    lines.append("Win rate when ROW model plays against COLUMN model:\n")
    lines.append(h2h_matrix.to_markdown())

    lines.append("\n## Game Statistics Details\n")
    lines.append(f"- **Median Game Length**: {game_stats['median_turns']:.0f} turns")
    lines.append(f"- **Shortest Game**: {game_stats['min_turns']:.0f} turns")
    lines.append(f"- **Longest Game**: {game_stats['max_turns']:.0f} turns")
    lines.append(f"- **Median Game Duration**: {game_stats['median_duration_minutes']:.1f} minutes")
    lines.append(f"- **Average Final Score**: {game_stats['avg_final_score']:.1f} VP")
    lines.append(f"- **Median Victory Margin**: {game_stats['median_victory_margin']:.1f} VP")

    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    logging.info(f"Summary report saved to {output_file}")
    print(f"Summary report saved to {output_file}")


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
