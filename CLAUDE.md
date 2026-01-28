# CLAUDE.md - Project Context for Claude Code

## Project Overview

LLM Catan Arena is a benchmarking platform that pits different LLM models against each other in Settlers of Catan. The goal is to evaluate strategic reasoning capabilities of various AI models through competitive gameplay.

## Architecture

### Player Modes

The arena supports two distinct player modes:

1. **Text Mode** (original) - `src/players/text_based/`
   - LLM receives full game state as JSON in a prompt
   - LLM responds with natural language action selection
   - Response is parsed to extract chosen action
   - Uses OpenRouter API for all models

2. **MCP Mode** (Model Context Protocol) - `src/players/mcp_based/`
   - LLM uses native tool calling to query game state
   - Three tools: `get_game_state`, `get_valid_actions`, `select_action`
   - More structured interaction, potentially better parsing reliability
   - Currently only implemented for Claude (uses Anthropic API directly)
   - GPT and Gemini fall back to text mode

### Key Directories

```
src/
├── players/
│   ├── text_based/          # Text mode players (Claude, GPT, Gemini)
│   ├── mcp_based/           # MCP mode players (Claude only for now)
│   └── random_player.py     # Baseline random player
├── mcp/                     # MCP server implementation
│   ├── server.py            # Core server with tool handling
│   ├── tools.py             # Tool definitions (JSON schema)
│   ├── game_wrapper.py      # Serializes Catanatron state to JSON
│   └── action_mapper.py     # Generates human-readable action IDs
├── prompt_builder.py        # Converts game state to prompts (text mode)
├── game_runner.py           # Orchestrates games, supports --mode flag
└── analysis.py              # Statistics and visualization

scripts/
├── run_tournament.py        # Main entry point (--mode text|mcp)
├── compare_modes.py         # Text vs MCP comparison tool
├── analyze_token_efficiency.py  # Token format analysis
└── analyze.py               # Game analysis scripts
```

### Configuration

- `config.yaml` - Model configs, tournament matchups, game settings
- `.env` - API keys (OPENROUTER_API_KEY, ANTHROPIC_API_KEY)

## Current State

### What's Implemented
- Full text mode for Claude, GPT-4, Gemini
- Full MCP mode for Claude only
- Tournament system with configurable matchups
- Game logging to JSON files in `data/games/`
- **Elo rating system** - Multiplayer Elo with persistence (`data/elo_ratings.json`)
- Basic analysis and visualization
- Token efficiency analysis (TOON format documented but not implemented)
- Mode comparison tool (`compare_modes.py`)

### What's NOT Implemented Yet
- **TOON-style prompt formatting** - Documented in `docs/TOKEN_OPTIMIZATION_GUIDE.md` but `prompt_builder.py` still uses standard JSON
- **MCP mode for GPT/Gemini** - Would need function calling implementations
- **Mixed-mode games** - Can't pit MCP Claude vs Text Claude in same game (yet)

## Elo Rating System

Multiplayer Elo rating system that tracks player performance across games.

**Key files:**
- `src/elo.py` - Core Elo implementation
- `scripts/elo_ratings.py` - CLI for viewing/managing ratings
- `data/elo_ratings.json` - Persistent ratings storage

**How it works:**
- Each player variant is tracked separately (e.g., `claude-text`, `claude-mcp`, `gpt4-text`)
- Uses "average opponent" method for 4-player games
- Placement scoring: 1st=1.0, 2nd=0.67, 3rd=0.33, 4th=0.0
- K-factor: 32 (configurable in config.yaml)
- Starting Elo: 1500

**Commands:**
```bash
# View leaderboard
python scripts/elo_ratings.py

# View leaderboard with minimum games filter
python scripts/elo_ratings.py --min-games 5

# Compare two players
python scripts/elo_ratings.py --compare claude-mcp claude-text

# Show recent game history
python scripts/elo_ratings.py --history 10

# Reset all ratings
python scripts/elo_ratings.py --reset
```

**Config options (config.yaml):**
```yaml
elo:
  enabled: true
  ratings_file: "data/elo_ratings.json"
  k_factor: 32
```

## Token Optimization / TOON Format

TOON (Token-Oriented Object Notation) is a compact prompt format that reduces tokens by ~53%.

**Current implementation:** Standard JSON with indentation in `prompt_builder.py`

**Analyzed formats (see `scripts/analyze_token_efficiency.py`):**
| Format | Token Reduction |
|--------|----------------|
| Ultra-Compact | 75% |
| TOON-Style | 53% |
| JSON Minified | 33% |
| JSON Standard | baseline |

To implement TOON, modify `src/prompt_builder.py` to use the `format_toon_style()` function pattern.

## Running the Project

```bash
# Activate venv
source venv/bin/activate

# Text mode tournament
python scripts/run_tournament.py --mode text --games 5

# MCP mode tournament (Claude only)
python scripts/run_tournament.py --mode mcp --games 5

# Single game
python scripts/run_tournament.py --single-game claude gpt4 gemini haiku --mode text

# Compare text vs MCP
python scripts/compare_modes.py --games 5 --matchup claude claude claude claude

# Run tests
./venv/bin/python -m pytest tests/ -v

# Analyze token efficiency
python scripts/analyze_token_efficiency.py --show-examples
```

## Dependencies

- `catanatron` - Catan game engine
- `llm-game-utils` - Shared utilities (installed from `../llm-game-utils`)
- `anthropic` - For MCP mode with Claude
- OpenRouter handles text mode API calls for all models

## Common Tasks

### Adding a new model
1. Add config to `config.yaml` under `models:`
2. If new provider, may need new player class in `src/players/text_based/`

### Implementing TOON format
1. Add TOON formatter to `src/prompt_builder.py`
2. Add `--format` flag to `run_tournament.py`
3. Run comparison tests to validate performance

### Adding MCP support for GPT
1. Create `src/players/mcp_based/mcp_gpt_player.py`
2. Use OpenAI function calling format
3. Map MCP tools to OpenAI function schemas
4. Update `game_runner.py` to route GPT to MCP player

## Test Coverage

45 tests covering:
- `test_game_wrapper.py` - Game state serialization
- `test_action_mapper.py` - Action ID generation
- `test_mcp_server.py` - MCP server functionality
- `test_mcp_players.py` - MCP player integration

## Known Limitations

1. Can't directly compare MCP vs Text Claude in the same game (different player instances) - needs mixed-mode support
2. MCP mode only works with Claude models
3. TOON format is documented but not implemented in production prompts
