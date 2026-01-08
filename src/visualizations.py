"""
Visualization Module for LLM Catan Arena.

Generate professional, blog-ready charts and visualizations.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from .analysis import (
    calculate_win_rates,
    calculate_costs,
    calculate_game_stats,
    head_to_head_matrix,
    extract_model_name,
    extract_full_model_name,
)


# Set professional styling
sns.set_style("whitegrid")
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9


def plot_win_rates(games: List[Dict[str, Any]],
                   output_path: str = "output/charts/win_rates.png") -> None:
    """
    Create and save win rate bar chart.

    Args:
        games: List of game result dictionaries
        output_path: Path to save the chart
    """
    win_rates = calculate_win_rates(games)

    if win_rates.empty:
        logging.warning("No win rate data to plot")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bar plot
    bars = ax.bar(range(len(win_rates)), win_rates['win_rate'],
                  color=sns.color_palette("husl", len(win_rates)),
                  edgecolor='black', linewidth=0.5)

    # Customize
    ax.set_xlabel('Model', fontweight='bold')
    ax.set_ylabel('Win Rate', fontweight='bold')
    ax.set_title(f'Win Rates by Model (N={len(games)} games)',
                 fontweight='bold', pad=20)
    ax.set_xticks(range(len(win_rates)))
    ax.set_xticklabels(win_rates['model'], rotation=45, ha='right')
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))

    # Add value labels on bars
    for i, (idx, row) in enumerate(win_rates.iterrows()):
        height = row['win_rate']
        ax.text(i, height + 0.02,
               f"{row['win_rate']:.1%}\n({row['wins']}/{row['games']})",
               ha='center', va='bottom', fontsize=8, fontweight='bold')

    # Add grid
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    plt.tight_layout()

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logging.info(f"Win rates chart saved to {output_path}")
    print(f"✓ Win rates chart saved to {output_path}")


def plot_cost_efficiency(games: List[Dict[str, Any]],
                        output_path: str = "output/charts/cost_efficiency.png") -> None:
    """
    Create and save cost efficiency scatter plot (cost vs wins).

    Args:
        games: List of game result dictionaries
        output_path: Path to save the chart
    """
    costs = calculate_costs(games)

    if costs.empty:
        logging.warning("No cost data to plot")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create scatter plot with size based on games played
    scatter = ax.scatter(costs['total_cost'], costs['wins'],
                        s=costs['games'] * 50,  # Size proportional to games
                        alpha=0.6,
                        c=range(len(costs)),
                        cmap='viridis',
                        edgecolors='black',
                        linewidth=1)

    # Add model labels
    for _, row in costs.iterrows():
        ax.annotate(row['model'],
                   (row['total_cost'], row['wins']),
                   xytext=(5, 5), textcoords='offset points',
                   fontsize=8, fontweight='bold')

    # Customize
    ax.set_xlabel('Total Cost ($)', fontweight='bold')
    ax.set_ylabel('Total Wins', fontweight='bold')
    ax.set_title(f'Cost Efficiency: Cost vs Wins (N={len(games)} games)\nBubble size = games played',
                 fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle='--')

    plt.tight_layout()

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logging.info(f"Cost efficiency chart saved to {output_path}")
    print(f"✓ Cost efficiency chart saved to {output_path}")


def plot_cost_per_win(games: List[Dict[str, Any]],
                     output_path: str = "output/charts/cost_per_win.png") -> None:
    """
    Create and save cost per win bar chart.

    Args:
        games: List of game result dictionaries
        output_path: Path to save the chart
    """
    costs = calculate_costs(games)

    if costs.empty:
        logging.warning("No cost data to plot")
        return

    # Filter out infinite values (models with no wins)
    costs_filtered = costs[costs['cost_per_win'] != float('inf')].copy()

    if costs_filtered.empty:
        logging.warning("No models with wins to plot cost per win")
        return

    costs_filtered = costs_filtered.sort_values('cost_per_win')

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bar plot
    bars = ax.bar(range(len(costs_filtered)), costs_filtered['cost_per_win'],
                  color=sns.color_palette("rocket", len(costs_filtered)),
                  edgecolor='black', linewidth=0.5)

    # Customize
    ax.set_xlabel('Model', fontweight='bold')
    ax.set_ylabel('Cost per Win ($)', fontweight='bold')
    ax.set_title(f'Average Cost per Win (N={len(games)} games)',
                 fontweight='bold', pad=20)
    ax.set_xticks(range(len(costs_filtered)))
    ax.set_xticklabels(costs_filtered['model'], rotation=45, ha='right')

    # Add value labels
    for i, (idx, row) in enumerate(costs_filtered.iterrows()):
        height = row['cost_per_win']
        ax.text(i, height + (ax.get_ylim()[1] * 0.01),
               f"${height:.4f}",
               ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    plt.tight_layout()

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logging.info(f"Cost per win chart saved to {output_path}")
    print(f"✓ Cost per win chart saved to {output_path}")


def plot_game_length_distribution(games: List[Dict[str, Any]],
                                  output_path: str = "output/charts/game_length_distribution.png") -> None:
    """
    Create and save game length distribution histogram.

    Args:
        games: List of game result dictionaries
        output_path: Path to save the chart
    """
    game_lengths = []

    for game in games:
        moves = game.get("moves", [])
        if moves:
            max_turn = max(m.get("turn_number", 0) for m in moves)
            game_lengths.append(max_turn)

    if not game_lengths:
        logging.warning("No game length data to plot")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create histogram
    n, bins, patches = ax.hist(game_lengths, bins=15,
                               edgecolor='black', linewidth=0.5,
                               color=sns.color_palette("mako")[3])

    # Add mean and median lines
    mean_length = np.mean(game_lengths)
    median_length = np.median(game_lengths)

    ax.axvline(mean_length, color='red', linestyle='--', linewidth=2,
              label=f'Mean: {mean_length:.1f}')
    ax.axvline(median_length, color='orange', linestyle='--', linewidth=2,
              label=f'Median: {median_length:.1f}')

    # Customize
    ax.set_xlabel('Game Length (turns)', fontweight='bold')
    ax.set_ylabel('Frequency', fontweight='bold')
    ax.set_title(f'Distribution of Game Lengths (N={len(games)} games)',
                 fontweight='bold', pad=20)
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    plt.tight_layout()

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logging.info(f"Game length distribution chart saved to {output_path}")
    print(f"✓ Game length distribution chart saved to {output_path}")


def plot_head_to_head(games: List[Dict[str, Any]],
                     output_path: str = "output/charts/head_to_head.png") -> None:
    """
    Create and save head-to-head win rate heatmap.

    Args:
        games: List of game result dictionaries
        output_path: Path to save the chart
    """
    h2h_matrix = head_to_head_matrix(games)

    if h2h_matrix.empty:
        logging.warning("No head-to-head data to plot")
        return

    fig, ax = plt.subplots(figsize=(10, 8))

    # Create heatmap
    sns.heatmap(h2h_matrix, annot=True, fmt='.2%', cmap='RdYlGn',
               center=0.5, vmin=0, vmax=1,
               cbar_kws={'label': 'Win Rate'},
               linewidths=0.5, linecolor='gray',
               ax=ax)

    # Customize
    ax.set_title(f'Head-to-Head Win Rates (N={len(games)} games)\n' +
                'Row model vs Column model',
                fontweight='bold', pad=20)
    ax.set_xlabel('Opponent', fontweight='bold')
    ax.set_ylabel('Player', fontweight='bold')

    # Rotate labels for better readability
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    plt.setp(ax.get_yticklabels(), rotation=0)

    plt.tight_layout()

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logging.info(f"Head-to-head heatmap saved to {output_path}")
    print(f"✓ Head-to-head heatmap saved to {output_path}")


def plot_decision_speed(games: List[Dict[str, Any]],
                       output_path: str = "output/charts/decision_speed.png") -> None:
    """
    Create and save decision speed box plot (API response times).

    Args:
        games: List of game result dictionaries
        output_path: Path to save the chart
    """
    from datetime import datetime
    from collections import defaultdict

    # Collect decision times per model
    decision_times = defaultdict(list)

    for game in games:
        moves = game.get("moves", [])
        final_scores = game.get("final_scores", {})

        for i, move in enumerate(moves):
            if i == 0:
                continue  # Skip first move (no previous timestamp)

            try:
                current_time = datetime.fromisoformat(move['timestamp'])
                prev_time = datetime.fromisoformat(moves[i-1]['timestamp'])
                duration = (current_time - prev_time).total_seconds()

                # Only count reasonable durations (< 60 seconds)
                if 0 < duration < 60:
                    player = move['player']
                    # Find model for this player color
                    for player_str in game.get('players', []):
                        if player_str.endswith(f':{player}'):
                            full_model = extract_full_model_name(final_scores, player_str)
                            decision_times[full_model].append(duration)
                            break
            except:
                continue

    if not decision_times:
        logging.warning("No decision time data to plot")
        return

    # Prepare data for box plot
    models = sorted(decision_times.keys())
    data = [decision_times[model] for model in models]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create box plot
    bp = ax.boxplot(data, labels=models, patch_artist=True,
                    notch=True, showfliers=False)

    # Color the boxes
    colors = sns.color_palette("Set2", len(models))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Customize
    ax.set_xlabel('Model', fontweight='bold')
    ax.set_ylabel('Decision Time (seconds)', fontweight='bold')
    ax.set_title(f'API Response Time Distribution (N={len(games)} games)',
                 fontweight='bold', pad=20)
    plt.xticks(rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    plt.tight_layout()

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logging.info(f"Decision speed chart saved to {output_path}")
    print(f"✓ Decision speed chart saved to {output_path}")


def plot_token_usage(games: List[Dict[str, Any]],
                    output_path: str = "output/charts/token_usage.png") -> None:
    """
    Create and save token usage stacked bar chart.

    Args:
        games: List of game result dictionaries
        output_path: Path to save the chart
    """
    from collections import defaultdict

    # Collect token usage per model
    token_stats = defaultdict(lambda: {"input": [], "output": []})

    for game in games:
        moves = game.get("moves", [])
        final_scores = game.get("final_scores", {})

        for move in moves:
            player = move['player']
            move_data = move.get('move_data', {})

            # Find model for this player
            for player_str in game.get('players', []):
                if player_str.endswith(f':{player}'):
                    full_model = extract_full_model_name(final_scores, player_str)

                    # Estimate input/output tokens (rough approximation)
                    total_tokens = move_data.get('tokens', 0)
                    prompt_length = move_data.get('prompt_length', 0)

                    # Rough estimate: input ~= prompt_length/4, output = rest
                    input_tokens = prompt_length // 4
                    output_tokens = max(0, total_tokens - input_tokens)

                    token_stats[full_model]["input"].append(input_tokens)
                    token_stats[full_model]["output"].append(output_tokens)
                    break

    if not token_stats:
        logging.warning("No token usage data to plot")
        return

    # Calculate averages
    models = sorted(token_stats.keys())
    avg_input = [np.mean(token_stats[m]["input"]) for m in models]
    avg_output = [np.mean(token_stats[m]["output"]) for m in models]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create stacked bar chart
    x = np.arange(len(models))
    width = 0.6

    p1 = ax.bar(x, avg_input, width, label='Input Tokens',
               color=sns.color_palette("muted")[0], edgecolor='black', linewidth=0.5)
    p2 = ax.bar(x, avg_output, width, bottom=avg_input, label='Output Tokens',
               color=sns.color_palette("muted")[1], edgecolor='black', linewidth=0.5)

    # Customize
    ax.set_xlabel('Model', fontweight='bold')
    ax.set_ylabel('Average Tokens per Move', fontweight='bold')
    ax.set_title(f'Token Usage Patterns (N={len(games)} games)',
                 fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Add total labels
    for i, model in enumerate(models):
        total = avg_input[i] + avg_output[i]
        ax.text(i, total + (ax.get_ylim()[1] * 0.02),
               f'{int(total)}',
               ha='center', va='bottom', fontsize=8, fontweight='bold')

    plt.tight_layout()

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logging.info(f"Token usage chart saved to {output_path}")
    print(f"✓ Token usage chart saved to {output_path}")


def plot_example_game_timeline(games: List[Dict[str, Any]],
                               game_index: int = 0,
                               output_path: str = "output/charts/example_game_timeline.png") -> None:
    """
    Create and save victory point timeline for an example game.

    Args:
        games: List of game result dictionaries
        game_index: Index of game to visualize
        output_path: Path to save the chart
    """
    if game_index >= len(games):
        logging.warning(f"Game index {game_index} out of range")
        return

    game = games[game_index]

    # This is a simplified version - full VP tracking would require
    # parsing the game state from moves
    final_scores = game.get("final_scores", {})

    if not final_scores:
        logging.warning("No final scores available for timeline")
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    # For now, just show final scores as a bar chart
    # (Full timeline would require state reconstruction)
    players = list(final_scores.keys())
    scores = list(final_scores.values())

    bars = ax.barh(players, scores,
                   color=sns.color_palette("viridis", len(players)),
                   edgecolor='black', linewidth=0.5)

    # Highlight winner
    winner = game.get("winner", "")
    for i, player in enumerate(players):
        if player.endswith(winner.split(':')[-1]):
            bars[i].set_color('gold')
            bars[i].set_edgecolor('darkgoldenrod')
            bars[i].set_linewidth(2)

    # Add value labels
    for i, score in enumerate(scores):
        ax.text(score + 0.2, i, str(score),
               va='center', fontweight='bold')

    # Customize
    ax.set_xlabel('Victory Points', fontweight='bold')
    ax.set_ylabel('Player', fontweight='bold')
    ax.set_title(f'Final Scores - Game {game_index + 1}\n{game.get("session_id", "")}',
                 fontweight='bold', pad=20)
    ax.axvline(10, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Victory threshold')
    ax.legend()
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    plt.tight_layout()

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logging.info(f"Example game timeline saved to {output_path}")
    print(f"✓ Example game timeline saved to {output_path}")


def generate_all_visualizations(games: List[Dict[str, Any]],
                               output_dir: str = "output/charts") -> None:
    """
    Generate all visualization charts at once.

    Args:
        games: List of game result dictionaries
        output_dir: Directory to save all charts
    """
    print(f"\nGenerating all visualizations...")
    print(f"Output directory: {output_dir}\n")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate all charts
    plot_win_rates(games, str(output_dir / "win_rates.png"))
    plot_cost_efficiency(games, str(output_dir / "cost_efficiency.png"))
    plot_cost_per_win(games, str(output_dir / "cost_per_win.png"))
    plot_game_length_distribution(games, str(output_dir / "game_length_distribution.png"))
    plot_head_to_head(games, str(output_dir / "head_to_head.png"))
    plot_decision_speed(games, str(output_dir / "decision_speed.png"))
    plot_token_usage(games, str(output_dir / "token_usage.png"))
    plot_example_game_timeline(games, 0, str(output_dir / "example_game_timeline.png"))

    print(f"\n✅ All visualizations generated successfully!")
    print(f"   Saved to: {output_dir}")
