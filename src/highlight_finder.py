"""
Highlight Finder Module for LLM Catan Arena.

Automatically identify interesting game moments and patterns for blog content.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

import numpy as np

from .analysis import (
    extract_model_name,
    extract_full_model_name,
)


def find_interesting_moments(games: List[Dict[str, Any]],
                            comeback_threshold: float = 0.3,
                            dominant_margin: int = 5,
                            close_margin: int = 2) -> Dict[str, List[str]]:
    """
    Find interesting moments and patterns in games.

    Args:
        games: List of game result dictionaries
        comeback_threshold: Threshold for comeback victories (default: winner had <30% of leader's VPs)
        dominant_margin: Minimum VP margin for dominant wins (default: 5)
        close_margin: Maximum VP margin for close finishes (default: 2)

    Returns:
        Dictionary with categories of interesting game IDs
    """
    highlights = {
        "comeback_victories": [],
        "dominant_wins": [],
        "close_finishes": [],
        "fastest_wins": [],
        "longest_games": [],
        "costly_mistakes": [],
        "high_scoring": [],
        "low_scoring": [],
    }

    game_lengths = []
    game_costs = []

    # First pass: collect statistics
    for game in games:
        moves = game.get("moves", [])
        if moves:
            max_turn = max(m.get("turn_number", 0) for m in moves)
            game_lengths.append((game.get("session_id"), max_turn))

        # Calculate total cost
        total_cost = sum(m.get("move_data", {}).get("cost", 0) for m in moves)
        game_costs.append((game.get("session_id"), total_cost))

    # Calculate percentiles for fast/slow games
    if game_lengths:
        lengths_only = [length for _, length in game_lengths]
        fast_threshold = np.percentile(lengths_only, 25)  # Bottom 25%
        slow_threshold = np.percentile(lengths_only, 75)  # Top 25%
    else:
        fast_threshold = float('inf')
        slow_threshold = 0

    # Second pass: categorize games
    for game in games:
        session_id = game.get("session_id", "Unknown")
        final_scores = game.get("final_scores", {})
        winner = game.get("winner", "")
        moves = game.get("moves", [])

        if not final_scores or not winner:
            continue

        scores = list(final_scores.values())
        sorted_scores = sorted(scores, reverse=True)

        if len(sorted_scores) < 2:
            continue

        winner_score = sorted_scores[0]
        second_score = sorted_scores[1]
        margin = winner_score - second_score

        # Close finishes
        if margin <= close_margin:
            highlights["close_finishes"].append(session_id)

        # Dominant wins
        if margin >= dominant_margin:
            highlights["dominant_wins"].append(session_id)

        # High/low scoring games
        avg_score = np.mean(scores)
        if winner_score >= 12:  # High scoring
            highlights["high_scoring"].append(session_id)
        if winner_score <= 10 and margin <= 1:  # Barely won
            highlights["low_scoring"].append(session_id)

        # Fastest/longest games
        if moves:
            max_turn = max(m.get("turn_number", 0) for m in moves)
            if max_turn <= fast_threshold:
                highlights["fastest_wins"].append(session_id)
            if max_turn >= slow_threshold:
                highlights["longest_games"].append(session_id)

        # Costly mistakes (high cost but lost)
        # Calculate cost per player
        player_costs = defaultdict(float)
        for move in moves:
            player_color = move.get("player", "")
            cost = move.get("move_data", {}).get("cost", 0)
            player_costs[player_color] += cost

        # Find non-winners with high costs
        winner_color = winner.split(":")[-1] if ":" in winner else ""
        for player_str in game.get("players", []):
            color = player_str.split(":")[-1] if ":" in player_str else ""
            if color != winner_color:
                player_cost = player_costs.get(color, 0)
                # If a loser spent more than $0.10, it's costly
                if player_cost > 0.10:
                    highlights["costly_mistakes"].append(session_id)
                    break

    # Remove duplicates and sort
    for category in highlights:
        highlights[category] = sorted(list(set(highlights[category])))

    return highlights


def analyze_model_patterns(games: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Analyze model-specific patterns and strategies.

    Args:
        games: List of game result dictionaries

    Returns:
        Dictionary with model-specific patterns
    """
    model_patterns = defaultdict(lambda: {
        "total_moves": 0,
        "avg_cost_per_move": [],
        "avg_response_time": [],
        "action_types": defaultdict(int),
    })

    for game in games:
        moves = game.get("moves", [])
        final_scores = game.get("final_scores", {})

        prev_timestamp = None

        for move in moves:
            player_color = move.get("player", "")
            move_data = move.get("move_data", {})

            # Find model for this player
            for player_str in game.get("players", []):
                if player_str.endswith(f":{player_color}"):
                    full_model = extract_full_model_name(final_scores, player_str)

                    model_patterns[full_model]["total_moves"] += 1

                    # Cost per move
                    cost = move_data.get("cost", 0)
                    model_patterns[full_model]["avg_cost_per_move"].append(cost)

                    # Action type
                    action = move_data.get("action", "Unknown")
                    model_patterns[full_model]["action_types"][action] += 1

                    # Response time
                    if prev_timestamp:
                        try:
                            current = datetime.fromisoformat(move["timestamp"])
                            prev = datetime.fromisoformat(prev_timestamp)
                            duration = (current - prev).total_seconds()
                            if 0 < duration < 60:
                                model_patterns[full_model]["avg_response_time"].append(duration)
                        except:
                            pass

                    prev_timestamp = move["timestamp"]
                    break

    # Calculate averages
    result = {}
    for model, patterns in model_patterns.items():
        avg_cost = np.mean(patterns["avg_cost_per_move"]) if patterns["avg_cost_per_move"] else 0
        avg_time = np.mean(patterns["avg_response_time"]) if patterns["avg_response_time"] else 0

        # Find most common action
        if patterns["action_types"]:
            most_common_action = max(patterns["action_types"].items(), key=lambda x: x[1])
        else:
            most_common_action = ("Unknown", 0)

        result[model] = {
            "total_moves": patterns["total_moves"],
            "avg_cost_per_move": avg_cost,
            "avg_response_time": avg_time,
            "most_common_action": most_common_action[0],
            "action_distribution": dict(patterns["action_types"]),
        }

    return result


def get_game_details(games: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific game.

    Args:
        games: List of game result dictionaries
        session_id: Session ID of the game to analyze

    Returns:
        Dictionary with detailed game information
    """
    for game in games:
        if game.get("session_id") == session_id:
            moves = game.get("moves", [])
            final_scores = game.get("final_scores", {})

            # Calculate statistics
            total_turns = max(m.get("turn_number", 0) for m in moves) if moves else 0
            total_cost = sum(m.get("move_data", {}).get("cost", 0) for m in moves)

            # Duration
            start = game.get("start_time")
            end = game.get("end_time")
            duration_minutes = 0
            if start and end:
                try:
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
                    duration_minutes = (end_dt - start_dt).total_seconds() / 60
                except:
                    pass

            # Winner details
            winner = game.get("winner", "")
            winner_score = 0
            if winner and final_scores:
                for player, score in final_scores.items():
                    if player.endswith(winner.split(":")[-1]):
                        winner_score = score
                        break

            # Victory margin
            scores = list(final_scores.values())
            sorted_scores = sorted(scores, reverse=True)
            margin = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) >= 2 else 0

            return {
                "session_id": session_id,
                "winner": winner,
                "winner_score": winner_score,
                "final_scores": final_scores,
                "total_turns": total_turns,
                "duration_minutes": duration_minutes,
                "total_cost": total_cost,
                "victory_margin": margin,
                "players": game.get("players", []),
            }

    return {}


def generate_highlights_report(games: List[Dict[str, Any]],
                              output_file: str = "output/highlights_report.md") -> None:
    """
    Generate markdown file with interesting game highlights.

    Args:
        games: List of game result dictionaries
        output_file: Path to save the markdown report
    """
    highlights = find_interesting_moments(games)
    model_patterns = analyze_model_patterns(games)

    lines = []
    lines.append("# LLM Catan Arena - Interesting Moments Report")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"\nTotal Games Analyzed: {len(games)}\n")

    # Interesting moments
    lines.append("## Interesting Games by Category\n")

    for category, game_ids in highlights.items():
        if game_ids:
            category_name = category.replace("_", " ").title()
            lines.append(f"### {category_name} ({len(game_ids)} games)\n")

            for game_id in game_ids[:5]:  # Show top 5
                details = get_game_details(games, game_id)
                if details:
                    lines.append(f"**{game_id}**")
                    lines.append(f"- Winner: {details['winner']} ({details['winner_score']} VP)")
                    lines.append(f"- Victory Margin: {details['victory_margin']} VP")
                    lines.append(f"- Game Length: {details['total_turns']} turns")
                    lines.append(f"- Duration: {details['duration_minutes']:.1f} minutes")
                    lines.append(f"- Total Cost: ${details['total_cost']:.4f}\n")

    # Model patterns
    lines.append("\n## Model-Specific Patterns\n")

    for model, patterns in sorted(model_patterns.items()):
        lines.append(f"### {model}\n")
        lines.append(f"- Total Moves: {patterns['total_moves']}")
        lines.append(f"- Avg Cost per Move: ${patterns['avg_cost_per_move']:.5f}")
        lines.append(f"- Avg Response Time: {patterns['avg_response_time']:.2f}s")
        lines.append(f"- Most Common Action: {patterns['most_common_action']}\n")

    # Suggested blog moments
    lines.append("\n## Suggested Blog Highlights\n")

    if highlights["close_finishes"]:
        game_id = highlights["close_finishes"][0]
        details = get_game_details(games, game_id)
        lines.append("### Nail-Biting Finish\n")
        lines.append(f"In game `{game_id}`, {details.get('winner', 'Unknown')} won by just "
                    f"{details.get('victory_margin', 0)} victory points! This game showcased "
                    f"the strategic depth of Catan, with the lead changing hands multiple times.\n")

    if highlights["dominant_wins"]:
        game_id = highlights["dominant_wins"][0]
        details = get_game_details(games, game_id)
        lines.append("### Dominant Performance\n")
        lines.append(f"Game `{game_id}` saw an impressive victory by {details.get('winner', 'Unknown')}, "
                    f"winning by a margin of {details.get('victory_margin', 0)} points. "
                    f"This demonstrates mastery of Catan strategy.\n")

    if highlights["fastest_wins"]:
        game_id = highlights["fastest_wins"][0]
        details = get_game_details(games, game_id)
        lines.append("### Speed Run\n")
        lines.append(f"The fastest game was `{game_id}`, completed in just {details.get('total_turns', 0)} turns. "
                    f"{details.get('winner', 'Unknown')} demonstrated efficient decision-making and optimal play.\n")

    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    logging.info(f"Highlights report saved to {output_file}")
    print(f"Highlights report saved to {output_file}")


def export_interesting_game_details(games: List[Dict[str, Any]],
                                   game_id: str,
                                   output_file: str = None) -> None:
    """
    Export detailed view of a specific interesting game for blog.

    Args:
        games: List of game result dictionaries
        game_id: Session ID of the game to export
        output_file: Optional path to save the details (defaults to output/game_{id}_details.md)
    """
    if output_file is None:
        safe_id = game_id.replace(" ", "_").replace(":", "_")
        output_file = f"output/game_{safe_id}_details.md"

    details = get_game_details(games, game_id)

    if not details:
        logging.warning(f"Game {game_id} not found")
        return

    # Find the full game object
    game = None
    for g in games:
        if g.get("session_id") == game_id:
            game = g
            break

    if not game:
        return

    lines = []
    lines.append(f"# Game Details: {game_id}\n")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    lines.append("## Overview\n")
    lines.append(f"- **Winner**: {details['winner']} ({details['winner_score']} VP)")
    lines.append(f"- **Victory Margin**: {details['victory_margin']} VP")
    lines.append(f"- **Game Length**: {details['total_turns']} turns")
    lines.append(f"- **Duration**: {details['duration_minutes']:.1f} minutes")
    lines.append(f"- **Total Cost**: ${details['total_cost']:.4f}\n")

    lines.append("## Final Scores\n")
    for player, score in sorted(details['final_scores'].items(), key=lambda x: x[1], reverse=True):
        winner_mark = "👑 " if player.endswith(details['winner'].split(":")[-1]) else "   "
        lines.append(f"{winner_mark}**{player}**: {score} VP")

    lines.append("\n## Move Summary\n")
    moves = game.get("moves", [])
    lines.append(f"Total moves: {len(moves)}\n")

    # Sample some key moves
    lines.append("### Sample Moves\n")
    sample_indices = [0, len(moves)//4, len(moves)//2, 3*len(moves)//4, -1]

    for idx in sample_indices:
        if 0 <= idx < len(moves) or idx == -1:
            move = moves[idx]
            turn = move.get("turn_number", 0)
            player = move.get("player", "")
            action = move.get("move_data", {}).get("action", "Unknown")
            cost = move.get("move_data", {}).get("cost", 0)

            lines.append(f"**Turn {turn}** - {player}: {action} (Cost: ${cost:.5f})")

    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    logging.info(f"Game details exported to {output_file}")
    print(f"Game details exported to {output_file}")
