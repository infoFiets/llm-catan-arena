#!/usr/bin/env python3
"""
Generate a blog post draft from game analysis.

Automatically creates a markdown blog post with statistics, charts, and highlights.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis import (
    load_all_games,
    calculate_win_rates,
    calculate_costs,
    calculate_game_stats,
)
from src.highlight_finder import (
    find_interesting_moments,
    get_game_details,
)


def generate_blog_draft(games, output_file: str = "output/blog_draft.md"):
    """
    Generate a markdown blog post draft.

    Args:
        games: List of game result dictionaries
        output_file: Path to save the blog draft
    """
    if not games:
        print("No games to analyze")
        return

    # Calculate statistics
    stats = calculate_game_stats(games)
    win_rates = calculate_win_rates(games)
    costs = calculate_costs(games)
    highlights = find_interesting_moments(games)

    # Find most interesting games for storytelling
    close_game = None
    if highlights["close_finishes"]:
        close_game = get_game_details(games, highlights["close_finishes"][0])

    dominant_game = None
    if highlights["dominant_wins"]:
        dominant_game = get_game_details(games, highlights["dominant_wins"][0])

    fast_game = None
    if highlights["fastest_wins"]:
        fast_game = get_game_details(games, highlights["fastest_wins"][0])

    # Build blog post
    lines = []

    # Header
    lines.append("# Which AI is the Best Catan Player? LLMs Battle for Supremacy\n")
    lines.append(f"*Analysis of {stats['total_games']} games • "
                f"Generated {datetime.now().strftime('%B %d, %Y')}*\n")

    # Introduction
    lines.append("## Introduction\n")
    lines.append("Settlers of Catan is a game of strategy, negotiation, and resource management. "
                "But how would advanced AI language models fare when pitted against each other? "
                "We created an automated arena where LLMs play Catan autonomously, making strategic "
                "decisions based on game state and reasoning through each move.\n")

    lines.append(f"After running {stats['total_games']} complete games, the results are in. "
                f"Each game took an average of {stats['avg_turns']:.0f} turns and "
                f"{stats['avg_duration_minutes']:.1f} minutes to complete. "
                "Let's dive into which models dominated, which made costly mistakes, "
                "and what fascinating patterns emerged.\n")

    # The Contenders
    lines.append("## The Contenders\n")
    lines.append("We tested multiple LLM models, each making independent strategic decisions:\n")
    for _, row in win_rates.iterrows():
        lines.append(f"- **{row['model']}**: {row['games']} games played")
    lines.append("")

    # Results Section
    lines.append("## The Results\n")

    # Win Rates
    lines.append("### Overall Win Rates\n")
    lines.append("![Win Rates](charts/win_rates.png)\n")

    winner = win_rates.iloc[0]
    lines.append(f"**{winner['model']}** emerged as the top performer, winning "
                f"{winner['wins']} out of {winner['games']} games ({winner['win_rate']:.1%} win rate). ")

    if len(win_rates) > 1:
        second = win_rates.iloc[1]
        lines.append(f"**{second['model']}** came in second with a {second['win_rate']:.1%} win rate "
                    f"({second['wins']}/{second['games']} games).\n")

    lines.append("\n| Model | Games | Wins | Win Rate |")
    lines.append("|-------|-------|------|----------|")
    for _, row in win_rates.iterrows():
        lines.append(f"| {row['model']} | {row['games']} | {row['wins']} | {row['win_rate']:.1%} |")
    lines.append("")

    # Cost Analysis
    lines.append("### Cost Efficiency\n")
    lines.append("![Cost Efficiency](charts/cost_efficiency.png)\n")
    lines.append("![Cost per Win](charts/cost_per_win.png)\n")

    lines.append("While winning is important, cost efficiency matters too. Here's how the models "
                "compared in terms of API costs:\n")

    most_efficient = costs.iloc[0]
    lines.append(f"**{most_efficient['model']}** was the most cost-efficient, averaging "
                f"${most_efficient['avg_cost_per_game']:.4f} per game. ")

    # Find the model with best cost per win
    valid_costs = costs[costs['cost_per_win'] != float('inf')]
    if not valid_costs.empty:
        best_roi = valid_costs.loc[valid_costs['cost_per_win'].idxmin()]
        lines.append(f"When it comes to cost per win, **{best_roi['model']}** takes the crown at "
                    f"${best_roi['cost_per_win']:.4f} per victory.\n")

    lines.append("\n| Model | Avg Cost/Game | Cost/Win | Total Cost |")
    lines.append("|-------|---------------|----------|------------|")
    for _, row in costs.iterrows():
        cpw = f"${row['cost_per_win']:.4f}" if row['cost_per_win'] != float('inf') else "N/A"
        lines.append(f"| {row['model']} | ${row['avg_cost_per_game']:.4f} | {cpw} | ${row['total_cost']:.4f} |")
    lines.append("")

    # Game Dynamics
    lines.append("### Game Dynamics\n")
    lines.append("![Game Length Distribution](charts/game_length_distribution.png)\n")

    lines.append(f"Games averaged {stats['avg_turns']:.1f} turns, with the shortest game finishing in "
                f"{stats['min_turns']:.0f} turns and the longest stretching to {stats['max_turns']:.0f} turns. "
                f"The average winning score was {stats['avg_winning_score']:.1f} victory points, "
                f"with an average victory margin of {stats['avg_victory_margin']:.1f} points.\n")

    # Head to Head
    lines.append("### Head-to-Head Matchups\n")
    lines.append("![Head-to-Head](charts/head_to_head.png)\n")
    lines.append("Some fascinating patterns emerged in direct matchups between specific models. "
                "The heatmap above shows win rates when one model plays against another.\n")

    # Interesting Moments
    lines.append("## Interesting Moments\n")

    # Close finish
    if close_game:
        lines.append("### The Nail-Biter\n")
        lines.append(f"Game `{close_game['session_id']}` showcased the strategic depth of Catan. "
                    f"**{close_game['winner']}** eked out a victory with {close_game['winner_score']} points, "
                    f"winning by a razor-thin margin of just {close_game['victory_margin']} victory point(s). "
                    f"The game lasted {close_game['total_turns']} intense turns, demonstrating that even "
                    f"advanced AI models can be evenly matched.\n")

    # Dominant win
    if dominant_game:
        lines.append("### The Dominant Performance\n")
        lines.append(f"In contrast, game `{dominant_game['session_id']}` showed what happens when "
                    f"everything goes right. **{dominant_game['winner']}** crushed the competition, "
                    f"winning with {dominant_game['winner_score']} points and a commanding "
                    f"{dominant_game['victory_margin']}-point lead. This game showcased optimal "
                    f"Catan strategy in action.\n")

    # Fast game
    if fast_game:
        lines.append("### The Speed Run\n")
        lines.append(f"The fastest game was `{fast_game['session_id']}`, wrapping up in just "
                    f"{fast_game['total_turns']} turns. **{fast_game['winner']}** demonstrated "
                    f"efficient decision-making and aggressive expansion to secure a quick victory.\n")

    # Performance Analysis
    lines.append("## What We Learned\n")
    lines.append("![Decision Speed](charts/decision_speed.png)\n")
    lines.append("![Token Usage](charts/token_usage.png)\n")

    lines.append("Several interesting patterns emerged from the data:\n")
    lines.append(f"1. **Game length varies significantly**: The spread from {stats['min_turns']:.0f} "
                f"to {stats['max_turns']:.0f} turns shows that games can end quickly with aggressive "
                f"play or drag on when players are evenly matched.\n")
    lines.append(f"2. **Close games are common**: With an average victory margin of "
                f"{stats['avg_victory_margin']:.1f} points, most games were competitive.\n")
    lines.append(f"3. **Cost vs Performance trade-off**: The most expensive models weren't always "
                f"the best performers, suggesting that strategic reasoning matters more than "
                f"raw model size.\n")

    # Conclusion
    lines.append("## Conclusion\n")
    lines.append(f"After {stats['total_games']} games, **{winner['model']}** proved to be the "
                f"strongest Catan player with a {winner['win_rate']:.1%} win rate. However, "
                f"the real insight is how well all models performed, showcasing impressive "
                f"strategic thinking and adaptability.\n")

    lines.append("This experiment demonstrates that modern LLMs can play complex strategy games "
                "at a reasonable level, making strategic decisions, managing resources, and "
                "adapting to changing game states. The future of AI game-playing is bright!\n")

    # Methodology
    lines.append("## Methodology\n")
    lines.append("All games were played using an automated Catan implementation where each LLM "
                "received the game state and list of legal actions, then reasoned through "
                "their decision and selected an action. No human intervention occurred during "
                "gameplay. API costs and response times were tracked for each decision.\n")

    lines.append(f"- **Total Games**: {stats['total_games']}")
    lines.append(f"- **Average Game Length**: {stats['avg_turns']:.1f} turns")
    lines.append(f"- **Average Duration**: {stats['avg_duration_minutes']:.1f} minutes")
    lines.append(f"- **Victory Point Target**: 10 VP\n")

    # Footer
    lines.append("---\n")
    lines.append("*This analysis was generated automatically from game logs. "
                "All charts and statistics are derived from actual gameplay data.*\n")

    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"✅ Blog draft generated: {output_file}")
    print(f"\nNext steps:")
    print(f"  1. Review and edit the draft")
    print(f"  2. Generate visualizations: python scripts/analyze.py --charts")
    print(f"  3. Place chart images in the same directory as the blog post")
    print(f"  4. Add personal insights and commentary")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate blog post draft from game analysis")
    parser.add_argument('--data-dir', type=str, default='data/games',
                       help='Directory containing game JSON files')
    parser.add_argument('--output', type=str, default='output/blog_draft.md',
                       help='Output file for blog draft')

    args = parser.parse_args()

    print(f"📂 Loading games from {args.data_dir}...")
    games = load_all_games(args.data_dir)

    if not games:
        print(f"❌ No games found in {args.data_dir}")
        return 1

    print(f"✅ Loaded {len(games)} games")
    print(f"\n📝 Generating blog draft...")

    generate_blog_draft(games, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
