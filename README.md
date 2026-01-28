# LLM Catan Arena

AI strategy benchmarking through competitive Settlers of Catan gameplay. Watch different LLM models (Claude, GPT-4, Gemini) compete head-to-head in one of the world's most popular strategy board games.

## Overview

This project uses [Catanatron](https://github.com/bcollazo/catanatron), a fast Settlers of Catan engine, combined with [llm-game-utils](https://github.com/infoFiets/llm-game-utils) to run automated tournaments where LLM agents play against each other. Each agent makes strategic decisions by analyzing the game state and selecting optimal actions through natural language reasoning.

### Why Catan?

Settlers of Catan is an excellent benchmark for LLM strategic reasoning because it requires:
- Resource management and planning
- Negotiation and trade decisions
- Probabilistic thinking (dice rolls)
- Spatial reasoning (board placement)
- Long-term strategy vs. short-term tactics

## Features

- Multiple LLM players (Claude Sonnet 4, GPT-4, Gemini Pro, Claude Haiku)
- **Two player modes:**
  - **Text mode**: Traditional prompt/response with action parsing
  - **MCP mode**: Model Context Protocol with native tool calling
- Automated tournament system with configurable matchups
- **Elo rating system** for persistent player rankings
- Comprehensive game logging and analysis
- Cost tracking per model and per game
- Win rate and performance statistics
- Mode comparison tools for benchmarking
- Visualization of results

## Installation

### Prerequisites

- Python 3.13+ (or 3.9+)
- OpenRouter API key ([get one here](https://openrouter.ai/keys))

### Setup

1. Clone the repository:
```bash
git clone https://github.com/infoFiets/llm-catan-arena.git
cd llm-catan-arena
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

## Quick Start

### Run a Single Test Game

```bash
python scripts/run_tournament.py --single-game claude gpt4 gemini haiku
```

This runs one game with all four LLM models competing.

### Run a Tournament

```bash
python scripts/run_tournament.py --games 5
```

This runs the tournament defined in `config.yaml`, playing each matchup 5 times.

### Analyze Results

```bash
python scripts/run_tournament.py --analyze
```

View statistics from all previously played games.

## Player Modes

The arena supports two different modes for LLM players:

### Text Mode (Default)

Traditional prompt/response approach where:
- Game state is serialized into a text prompt
- LLM responds with action selection in natural language
- Response is parsed to extract the selected action

```bash
python scripts/run_tournament.py --mode text --games 5
```

### MCP Mode (Model Context Protocol)

Uses native tool calling for more structured interaction:
- LLM queries game state through `get_game_state` tool
- Available actions retrieved via `get_valid_actions` tool
- Action selected using `select_action` tool
- More reliable action parsing, potentially better token efficiency

```bash
python scripts/run_tournament.py --mode mcp --games 5
```

**Note:** MCP mode currently supports Claude models only. GPT and Gemini fall back to text mode.

### Comparing Modes

Use the comparison tool to benchmark text vs MCP performance:

```bash
python scripts/compare_modes.py --games 5 --matchup claude claude claude claude
```

This runs identical matchups in both modes and generates:
- Cost comparison between modes
- Token usage analysis
- Performance metrics
- Comparison plots

## Elo Rating System

The arena includes a multiplayer Elo rating system that tracks player performance across games.

Each player variant is tracked separately (e.g., `claude-mcp` vs `claude-text`), allowing direct comparison between modes.

### View Leaderboard

```bash
python scripts/elo_ratings.py
```

### Compare Players Head-to-Head

```bash
python scripts/elo_ratings.py --compare claude-mcp claude-text
```

### Show Recent Games

```bash
python scripts/elo_ratings.py --history 10
```

Ratings are automatically updated after each game and persisted to `data/elo_ratings.json`.

## Configuration

Edit `config.yaml` to customize:

- **Models**: Add/remove LLM models, adjust temperature and costs
- **Game settings**: Victory points, max turns, trading rules
- **Tournament matchups**: Define which combinations of models to test
- **Logging**: Output directory and verbosity

Example model configuration:
```yaml
models:
  claude:
    model_id: "anthropic/claude-sonnet-4-20250514"
    name: "Claude Sonnet 4"
    temperature: 0.7
    max_tokens: 1000
    input_cost: 0.003
    output_cost: 0.015
```

## How It Works

### Architecture

1. **Catanatron Engine**: Handles game rules, board state, and action validation
2. **Player Classes**: LLM-powered players that extend Catanatron's base Player class
3. **Prompt Builder**: Converts game state into structured prompts for LLMs
4. **Game Runner**: Orchestrates games, manages logging, tracks costs
5. **Analyzer**: Processes results and generates statistics

### Game Flow

1. Game starts with 4 players (different LLM models or same model)
2. On each turn:
   - Current player's state is extracted from game
   - Prompt is built showing resources, board state, available actions
   - LLM is queried to select an action
   - Response is parsed and validated
   - Action is executed in Catanatron
   - Move is logged with cost and token usage
3. Game continues until a player reaches 10 victory points
4. Results are saved as JSON with full statistics

### Prompt Example

The system generates prompts like:

```
Game: Settlers of Catan

Recent moves: Built road, Traded 2 wheat for 1 ore

Current Game State:
{
  "your_resources": {"wood": 2, "brick": 1, "wheat": 3},
  "your_victory_points": 5,
  "your_buildings": {"settlements": 2, "cities": 1, "roads": 3},
  "opponents": [...]
}

Available Actions:
  1. Build a settlement at location A
  2. Build a road from X to Y
  3. Trade 4 wheat for 1 ore with bank
  4. End turn

What action do you choose? Please respond with your choice and reasoning.
```

## Project Structure

```
llm-catan-arena/
├── src/
│   ├── players/
│   │   ├── text_based/             # Text mode players
│   │   │   ├── base_player.py      # Abstract LLM player base
│   │   │   ├── claude_player.py    # Claude implementation
│   │   │   ├── gpt_player.py       # GPT-4 implementation
│   │   │   └── gemini_player.py    # Gemini implementation
│   │   ├── mcp_based/              # MCP mode players
│   │   │   ├── base_mcp_player.py  # Abstract MCP player base
│   │   │   └── mcp_claude_player.py # Claude with tool calling
│   │   └── random_player.py        # Random baseline
│   ├── mcp/                        # MCP server implementation
│   │   ├── server.py               # MCP server core
│   │   ├── tools.py                # Tool definitions
│   │   ├── game_wrapper.py         # Game state serialization
│   │   └── action_mapper.py        # Action ID generation
│   ├── prompt_builder.py           # Game state → LLM prompts
│   ├── game_runner.py              # Game orchestration
│   └── analysis.py                 # Statistics and visualization
├── scripts/
│   ├── run_tournament.py           # Main entry point
│   ├── compare_modes.py            # Text vs MCP comparison
│   └── analyze_token_efficiency.py # Token optimization analysis
├── tests/
│   ├── test_game_wrapper.py        # MCP game wrapper tests
│   ├── test_action_mapper.py       # Action mapper tests
│   ├── test_mcp_server.py          # MCP server tests
│   └── test_mcp_players.py         # MCP player integration tests
├── data/
│   └── games/                      # Game logs (JSON)
├── config.yaml                     # Configuration
├── requirements.txt                # Python dependencies
└── README.md
```

## Results & Analysis

After running games, analyze results with:

```python
from src.analysis import CatanAnalyzer

analyzer = CatanAnalyzer()
analyzer.print_report()

# Generate visualizations
results = analyzer.load_results()
win_stats = analyzer.calculate_win_rates(results)
cost_stats = analyzer.calculate_cost_stats(results)

analyzer.plot_win_rates(win_stats, "win_rates.png")
analyzer.plot_cost_comparison(cost_stats, "costs.png")
```

Game results include:
- Winner and final scores
- Total cost and token usage per model
- All moves and decisions made
- Timestamps and session IDs for tracking

## Dependencies

Key libraries used:
- **catanatron**: Fast Settlers of Catan game engine
- **llm-game-utils**: Shared utilities for LLM game projects (OpenRouter client, logging, prompt formatting)
- **anthropic**: Anthropic API client for MCP mode with Claude
- **pandas, matplotlib, seaborn**: Data analysis and visualization
- **pyyaml**: Configuration management

## Cost Estimates

Approximate costs per game (4 players, ~100-200 turns):
- Claude Sonnet 4: $0.30 - $0.60
- GPT-4 Turbo: $0.50 - $1.00
- Gemini Pro 1.5: $0.15 - $0.30
- Claude Haiku: $0.03 - $0.06

### Token Optimization 💰

**Save 50-75% on API costs** with optimized prompt formats!

We've analyzed different data serialization formats and found you can reduce tokens dramatically:

| Format | Token Reduction | Savings/Game (Haiku) | Savings/Game (GPT-4) |
|--------|----------------|---------------------|---------------------|
| **TOON-Style** | **53%** ⭐ | **$0.06** | **$0.20** |
| Ultra-Compact | 75% | $0.08 | $0.25 |
| JSON (Minified) | 33% | $0.03 | $0.10 |

**Quick Win:** Minify your JSON prompts (1-line code change, 33% savings!)

```python
# Change from:
json.dumps(state, indent=2)
# To:
json.dumps(state, separators=(',', ':'))
```

**Full Analysis:** See `docs/TOKEN_OPTIMIZATION_GUIDE.md` for complete details and implementation guide.

**Run the analysis yourself:**
```bash
python scripts/analyze_token_efficiency.py --show-examples
```

Costs vary based on game length and decision complexity.

## Future Improvements

- [ ] Add more sophisticated prompt engineering
- [ ] Implement multi-turn strategy memory
- [ ] Add support for player-to-player trading negotiations
- [ ] Create web UI for watching games in real-time
- [ ] Support for custom game variants
- [ ] MCP mode for GPT models (function calling)
- [ ] MCP mode for Gemini models (tool use)
- [ ] TOON-style prompt formatting for token efficiency
- [ ] Mixed-mode games (MCP vs Text players in same game)

## Contributing

Contributions welcome! Areas of interest:
- Better prompt templates for strategic reasoning
- Additional LLM model integrations
- Performance optimizations
- Analysis visualizations

## License

MIT License - see LICENSE file

## Acknowledgments

- [Catanatron](https://github.com/bcollazo/catanatron) for the excellent Catan engine
- OpenRouter for unified LLM API access
- The board game Settlers of Catan by Klaus Teuber

## Related Projects

- [llm-game-utils](https://github.com/infoFiets/llm-game-utils) - Shared utilities for LLM game projects
- [Catanatron](https://github.com/bcollazo/catanatron) - Fast Settlers of Catan simulator

---

Built with curiosity about AI strategic reasoning 🎲🤖
