#!/usr/bin/env python3
"""
Generate Leaderboard for Website.

Creates HTML, JSON, and Markdown leaderboards from Elo ratings.
Can be used to embed on a website or auto-update via CI/CD.

Usage:
    python scripts/generate_leaderboard.py
    python scripts/generate_leaderboard.py --output docs/leaderboard
    python scripts/generate_leaderboard.py --format html --embed
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from src.elo import EloRating

# Model metadata for rich display
MODEL_INFO = {
    # ==========================================================================
    # ANTHROPIC - Claude Family (Evolution: 3.0 → 3.5 → 3.7 → 4.0 → 4.5)
    # ==========================================================================
    # Claude 4.5 (Latest)
    "claude-4.5-opus": {"provider": "Anthropic", "icon": "🟣", "tier": "Flagship", "gen": "4.5"},
    "claude-4.5-sonnet": {"provider": "Anthropic", "icon": "🟣", "tier": "Flagship", "gen": "4.5"},
    "claude-4.5-haiku": {"provider": "Anthropic", "icon": "🟣", "tier": "Fast", "gen": "4.5"},
    # Claude 4.0
    "claude-4-opus": {"provider": "Anthropic", "icon": "🟣", "tier": "Legacy", "gen": "4.0"},
    "claude-4-sonnet": {"provider": "Anthropic", "icon": "🟣", "tier": "Legacy", "gen": "4.0"},
    # Claude 3.7
    "claude-3.7-sonnet": {"provider": "Anthropic", "icon": "🟣", "tier": "Legacy", "gen": "3.7"},
    "claude-3.7-sonnet-thinking": {"provider": "Anthropic", "icon": "🟣", "tier": "Reasoning", "gen": "3.7"},
    # Claude 3.5
    "claude-3.5-sonnet": {"provider": "Anthropic", "icon": "🟣", "tier": "Legacy", "gen": "3.5"},
    "claude-3.5-haiku": {"provider": "Anthropic", "icon": "🟣", "tier": "Legacy", "gen": "3.5"},
    # Claude 3.0
    "claude-3-opus": {"provider": "Anthropic", "icon": "🟣", "tier": "Legacy", "gen": "3.0"},
    "claude-3-haiku": {"provider": "Anthropic", "icon": "🟣", "tier": "Legacy", "gen": "3.0"},

    # ==========================================================================
    # OPENAI - GPT Family (Evolution: 4o → 4.1 → 5.0 → 5.1 → 5.2)
    # ==========================================================================
    # GPT-5.2 (Latest)
    "gpt-5.2": {"provider": "OpenAI", "icon": "🟢", "tier": "Flagship", "gen": "5.2"},
    # GPT-5.1
    "gpt-5.1": {"provider": "OpenAI", "icon": "🟢", "tier": "Flagship", "gen": "5.1"},
    # GPT-5.0
    "gpt-5": {"provider": "OpenAI", "icon": "🟢", "tier": "Flagship", "gen": "5.0"},
    "gpt-5-mini": {"provider": "OpenAI", "icon": "🟢", "tier": "Fast", "gen": "5.0"},
    "gpt-5-nano": {"provider": "OpenAI", "icon": "🟢", "tier": "Fast", "gen": "5.0"},
    # GPT-4.1
    "gpt-4.1": {"provider": "OpenAI", "icon": "🟢", "tier": "Legacy", "gen": "4.1"},
    "gpt-4.1-mini": {"provider": "OpenAI", "icon": "🟢", "tier": "Legacy", "gen": "4.1"},
    # GPT-4o
    "gpt-4o": {"provider": "OpenAI", "icon": "🟢", "tier": "Legacy", "gen": "4.0"},
    "gpt-4o-mini": {"provider": "OpenAI", "icon": "🟢", "tier": "Legacy", "gen": "4.0"},

    # ==========================================================================
    # GOOGLE - Gemini Family (Evolution: 2.0 → 2.5 → 3.0)
    # ==========================================================================
    # Gemini 3.0 (Latest)
    "gemini-3-pro": {"provider": "Google", "icon": "🔵", "tier": "Flagship", "gen": "3.0"},
    "gemini-3-flash": {"provider": "Google", "icon": "🔵", "tier": "Fast", "gen": "3.0"},
    # Gemini 2.5
    "gemini-2.5-pro": {"provider": "Google", "icon": "🔵", "tier": "Flagship", "gen": "2.5"},
    "gemini-2.5-flash": {"provider": "Google", "icon": "🔵", "tier": "Fast", "gen": "2.5"},
    "gemini-2.5-flash-lite": {"provider": "Google", "icon": "🔵", "tier": "Fast", "gen": "2.5"},
    # Gemini 2.0
    "gemini-2.0-flash": {"provider": "Google", "icon": "🔵", "tier": "Legacy", "gen": "2.0"},

    # ==========================================================================
    # META - Llama Family (Evolution: 3.0 → 3.1 → 3.3 → 4.0)
    # ==========================================================================
    # Llama 4.0 (Latest)
    "llama-4-maverick": {"provider": "Meta", "icon": "🦙", "tier": "Flagship", "gen": "4.0"},
    "llama-4-scout": {"provider": "Meta", "icon": "🦙", "tier": "Mid", "gen": "4.0"},
    # Llama 3.3
    "llama-3.3-70b": {"provider": "Meta", "icon": "🦙", "tier": "Legacy", "gen": "3.3"},
    # Llama 3.1
    "llama-3.1-405b": {"provider": "Meta", "icon": "🦙", "tier": "Legacy", "gen": "3.1"},
    "llama-3.1-70b": {"provider": "Meta", "icon": "🦙", "tier": "Legacy", "gen": "3.1"},
    "llama-3.1-8b": {"provider": "Meta", "icon": "🦙", "tier": "Fast", "gen": "3.1"},
    # Llama 3.0
    "llama-3-70b": {"provider": "Meta", "icon": "🦙", "tier": "Legacy", "gen": "3.0"},
    "llama-3-8b": {"provider": "Meta", "icon": "🦙", "tier": "Legacy", "gen": "3.0"},

    # ==========================================================================
    # MISTRAL
    # ==========================================================================
    "mistral-large": {"provider": "Mistral", "icon": "🟠", "tier": "Flagship"},
    "mistral-medium": {"provider": "Mistral", "icon": "🟠", "tier": "Mid"},
    "mistral-small": {"provider": "Mistral", "icon": "🟠", "tier": "Fast"},
    "mixtral-8x7b": {"provider": "Mistral", "icon": "🟠", "tier": "Mid"},

    # ==========================================================================
    # DEEPSEEK (Open Source)
    # ==========================================================================
    "deepseek-v3.2": {"provider": "DeepSeek", "icon": "🔷", "tier": "Flagship"},
    "deepseek-v3.1": {"provider": "DeepSeek", "icon": "🔷", "tier": "Flagship"},
    "deepseek-r1": {"provider": "DeepSeek", "icon": "🔷", "tier": "Reasoning"},

    # ==========================================================================
    # XAI - Grok
    # ==========================================================================
    "grok-4.1": {"provider": "xAI", "icon": "⚡", "tier": "Flagship"},
    "grok-4": {"provider": "xAI", "icon": "⚡", "tier": "Flagship"},
    "grok-3-mini": {"provider": "xAI", "icon": "⚡", "tier": "Fast"},

    # ==========================================================================
    # ALIBABA - Qwen (Open Source)
    # ==========================================================================
    "qwen3-235b": {"provider": "Alibaba", "icon": "🟡", "tier": "Flagship"},
    "qwen3-235b-thinking": {"provider": "Alibaba", "icon": "🟡", "tier": "Reasoning"},
    "qwen3-max": {"provider": "Alibaba", "icon": "🟡", "tier": "Flagship"},
    "qwen-2.5-72b": {"provider": "Alibaba", "icon": "🟡", "tier": "Mid"},
}


def get_model_info(player_id: str) -> Dict:
    """Get model metadata, handling mode suffixes."""
    base_model = player_id.replace("-mcp", "").replace("-text", "")
    mode = "tool" if "-mcp" in player_id else "text" if "-text" in player_id else "text"

    info = MODEL_INFO.get(base_model, {
        "provider": "Unknown",
        "icon": "⚪",
        "tier": "Unknown"
    })

    return {
        **info,
        "mode": mode,
        "base_model": base_model
    }


def generate_json_leaderboard(elo: EloRating, min_games: int = 3) -> Dict:
    """Generate JSON leaderboard data."""
    leaderboard = elo.get_leaderboard(min_games=min_games)

    data = {
        "generated_at": datetime.now().isoformat(),
        "total_players": len(leaderboard),
        "min_games_required": min_games,
        "starting_elo": 1500,
        "rankings": []
    }

    for i, entry in enumerate(leaderboard, 1):
        player_id = entry["player"]
        info = get_model_info(player_id)

        data["rankings"].append({
            "rank": i,
            "player_id": player_id,
            "display_name": player_id.replace("-", " ").title(),
            "provider": info["provider"],
            "tier": info["tier"],
            "mode": info["mode"],
            "elo": round(entry["rating"]),
            "games": entry["games"],
            "elo_vs_start": round(entry["rating"] - 1500),
            "icon": info["icon"]
        })

    return data


def generate_markdown_leaderboard(data: Dict) -> str:
    """Generate Markdown leaderboard."""
    md = f"""# LLM Catan Arena Leaderboard

*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*

| Rank | Model | Provider | Elo | +/- | Games | Mode |
|------|-------|----------|-----|-----|-------|------|
"""

    for entry in data["rankings"]:
        elo_change = entry["elo_vs_start"]
        change_str = f"+{elo_change}" if elo_change >= 0 else str(elo_change)

        md += f"| {entry['rank']} | {entry['icon']} {entry['display_name']} | {entry['provider']} | "
        md += f"**{entry['elo']}** | {change_str} | {entry['games']} | {entry['mode']} |\n"

    md += f"""
---

**Total models tested:** {data['total_players']}
**Minimum games required:** {data['min_games_required']}
**Starting Elo:** {data['starting_elo']}

## How It Works

Models play Settlers of Catan against each other. Elo ratings are calculated using a multiplayer Elo system with K-factor of 32.

- **Text mode**: LLM receives game state as JSON, responds with action choice
- **Tool mode**: LLM uses function calling to query game state and select actions

[View full methodology →](#methodology)
"""

    return md


def generate_html_leaderboard(data: Dict, embed: bool = False) -> str:
    """Generate HTML leaderboard (full page or embeddable)."""

    # Generate table rows
    rows = ""
    for entry in data["rankings"]:
        elo_change = entry["elo_vs_start"]
        change_class = "positive" if elo_change >= 0 else "negative"
        change_str = f"+{elo_change}" if elo_change >= 0 else str(elo_change)

        rows += f"""
        <tr>
            <td class="rank">{entry['rank']}</td>
            <td class="model">
                <span class="icon">{entry['icon']}</span>
                <span class="name">{entry['display_name']}</span>
                <span class="provider">{entry['provider']}</span>
            </td>
            <td class="elo"><strong>{entry['elo']}</strong></td>
            <td class="change {change_class}">{change_str}</td>
            <td class="games">{entry['games']}</td>
            <td class="mode"><span class="badge {entry['mode']}">{entry['mode']}</span></td>
        </tr>"""

    table = f"""
    <div class="leaderboard-container">
        <table class="leaderboard">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Model</th>
                    <th>Elo</th>
                    <th>+/-</th>
                    <th>Games</th>
                    <th>Mode</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <p class="updated">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
    """

    if embed:
        return table

    # Full HTML page
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Catan Arena Leaderboard</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --text-color: #c9d1d9;
            --text-muted: #8b949e;
            --border-color: #30363d;
            --positive: #3fb950;
            --negative: #f85149;
            --accent: #58a6ff;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        h1 {{
            text-align: center;
            margin-bottom: 10px;
        }}

        .subtitle {{
            text-align: center;
            color: var(--text-muted);
            margin-bottom: 30px;
        }}

        .leaderboard-container {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border-color);
        }}

        .leaderboard {{
            width: 100%;
            border-collapse: collapse;
        }}

        .leaderboard th {{
            text-align: left;
            padding: 12px 8px;
            border-bottom: 2px solid var(--border-color);
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
        }}

        .leaderboard td {{
            padding: 12px 8px;
            border-bottom: 1px solid var(--border-color);
        }}

        .leaderboard tr:hover {{
            background: rgba(88, 166, 255, 0.1);
        }}

        .rank {{
            font-weight: bold;
            color: var(--accent);
            width: 50px;
        }}

        .model {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .model .icon {{
            font-size: 1.2em;
        }}

        .model .name {{
            font-weight: 500;
        }}

        .model .provider {{
            color: var(--text-muted);
            font-size: 0.85em;
        }}

        .elo {{
            font-size: 1.1em;
        }}

        .change.positive {{
            color: var(--positive);
        }}

        .change.negative {{
            color: var(--negative);
        }}

        .badge {{
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            text-transform: uppercase;
        }}

        .badge.text {{
            background: #238636;
            color: white;
        }}

        .badge.tool {{
            background: #8957e5;
            color: white;
        }}

        .updated {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85em;
            margin-top: 15px;
        }}

        .stats {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
        }}

        .stat {{
            text-align: center;
        }}

        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: var(--accent);
        }}

        .stat-label {{
            color: var(--text-muted);
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎲 LLM Catan Arena</h1>
        <p class="subtitle">Which AI is the best Settlers of Catan player?</p>

        {table}

        <div class="stats">
            <div class="stat">
                <div class="stat-value">{data['total_players']}</div>
                <div class="stat-label">Models Tested</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sum(e['games'] for e in data['rankings'])}</div>
                <div class="stat-label">Games Played</div>
            </div>
            <div class="stat">
                <div class="stat-value">{data['min_games_required']}+</div>
                <div class="stat-label">Min Games</div>
            </div>
        </div>
    </div>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate leaderboard for website")
    parser.add_argument("--output", "-o", default="output/leaderboard",
                       help="Output directory")
    parser.add_argument("--format", choices=["all", "json", "md", "html"],
                       default="all", help="Output format")
    parser.add_argument("--min-games", type=int, default=3,
                       help="Minimum games to appear on leaderboard")
    parser.add_argument("--embed", action="store_true",
                       help="Generate embeddable HTML (no full page)")

    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load Elo ratings
    elo = EloRating()

    if not elo.ratings:
        print("No Elo ratings found. Run some games first!")
        print("  python scripts/run_tournament.py --single-game claude gpt4 gemini haiku")
        return

    # Generate JSON data
    data = generate_json_leaderboard(elo, min_games=args.min_games)

    if args.format in ["all", "json"]:
        json_file = output_dir / "leaderboard.json"
        with open(json_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"JSON leaderboard: {json_file}")

    if args.format in ["all", "md"]:
        md_file = output_dir / "leaderboard.md"
        with open(md_file, "w") as f:
            f.write(generate_markdown_leaderboard(data))
        print(f"Markdown leaderboard: {md_file}")

    if args.format in ["all", "html"]:
        html_file = output_dir / ("leaderboard_embed.html" if args.embed else "leaderboard.html")
        with open(html_file, "w") as f:
            f.write(generate_html_leaderboard(data, embed=args.embed))
        print(f"HTML leaderboard: {html_file}")

    # Print summary
    print(f"\n{'='*50}")
    print("LEADERBOARD SUMMARY")
    print(f"{'='*50}")
    print(f"Total models: {data['total_players']}")
    if data['rankings']:
        top = data['rankings'][0]
        print(f"#1: {top['icon']} {top['display_name']} (Elo: {top['elo']})")


if __name__ == "__main__":
    main()
