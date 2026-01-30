# CLAUDE.md - Project Context for Claude Code

## Project Overview

LLM Catan Arena is a benchmarking platform that pits different LLM models against each other in Settlers of Catan. The goal is to evaluate strategic reasoning capabilities of various AI models through competitive gameplay.

## Architecture

### Player Modes

The arena supports two distinct player modes:

1. **Text Mode** - `src/players/text_based/`
   - LLM receives full game state as JSON in a prompt
   - LLM responds with natural language action selection
   - Response is parsed to extract chosen action
   - Uses **OpenRouter API** for all models

2. **Tool-Calling Mode** (called "MCP" in code) - `src/players/mcp_based/`
   - LLM uses native tool/function calling to query game state
   - Three tools: `get_game_state`, `get_valid_actions`, `select_action`
   - More structured interaction, better parsing reliability
   - Uses **OpenRouter API** tool calling for all models
   - Works with Claude, GPT-4, Gemini, and other tool-capable models

**Both modes use OpenRouter** - you only need `OPENROUTER_API_KEY`.

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
- **Mixed-mode games** - Pit MCP Claude vs Text Claude in same game for direct comparison
- Tournament system with configurable matchups
- Game logging to JSON files in `data/games/`
- **Elo rating system** - Multiplayer Elo with persistence (`data/elo_ratings.json`)
- Basic analysis and visualization
- **TOON-style prompt formatting** - Reduces tokens by ~40-53% (see Token Optimization section)
- Mode and format comparison tools (`compare_modes.py`)

### What's NOT Implemented Yet
- **TOON format validation** - Need to verify TOON parsing works for all models
- **Parallel game execution** - Currently runs games sequentially

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

TOON (Token-Oriented Object Notation) is a compact prompt format that reduces tokens by ~40-53%.

**Supported formats via `--format` flag:**
| Format | Flag | Token Reduction |
|--------|------|----------------|
| JSON Standard | `--format json` | baseline (default) |
| JSON Minified | `--format json-minified` | ~25-33% |
| TOON-Style | `--format toon` | ~40-53% |

**Commands:**
```bash
# Run with TOON format for maximum efficiency
python scripts/run_tournament.py --mode text --format toon --games 5

# Compare formats (TOON vs JSON)
python scripts/compare_modes.py --compare-formats json toon --games 5 --matchup claude claude claude claude
```

**Implementation:** `src/prompt_builder.py` supports all three formats via the `CatanPromptBuilder(format="toon")` constructor or `--format` CLI flag.

## Running the Project

```bash
# Activate venv
source venv/bin/activate

# Text mode tournament (default JSON format)
python scripts/run_tournament.py --mode text --games 5

# Text mode with TOON format (token efficient)
python scripts/run_tournament.py --mode text --format toon --games 5

# MCP/Tool-calling mode tournament
python scripts/run_tournament.py --mode mcp --games 5

# Single game with format option
python scripts/run_tournament.py --single-game claude gpt5 gemini haiku --mode text --format toon

# Mixed-mode: MCP vs Text direct comparison
python scripts/run_tournament.py --single-game claude-mcp claude-text gpt5-mcp gpt5-text

# Compare text vs MCP modes
python scripts/compare_modes.py --games 5 --matchup claude claude claude claude

# Compare prompt formats (JSON vs TOON)
python scripts/compare_modes.py --compare-formats json toon --games 5 --matchup claude claude claude claude

# Run full tournament with all models
python scripts/run_full_tournament.py --estimate-only  # Check costs first
python scripts/run_full_tournament.py --all --quick    # Quick test run

# Generate leaderboard for website
python scripts/generate_leaderboard.py --output docs/leaderboard

# Run tests
./venv/bin/python -m pytest tests/ -v

# Analyze token efficiency
python scripts/analyze_token_efficiency.py --show-examples
```

## Dependencies

- `catanatron` - Catan game engine
- `llm-game-utils` - Shared utilities (installed from `../llm-game-utils`)
- `anthropic` - For tool-calling mode with Claude
- OpenRouter handles text mode API calls for all models

## API Keys & Providers

| Mode | Provider | API Key | Models Supported |
|------|----------|---------|------------------|
| Text | OpenRouter | `OPENROUTER_API_KEY` | All models |
| Tool-calling | OpenRouter | `OPENROUTER_API_KEY` | All models with tool support |

**OpenRouter** is an API aggregator that provides access to many models through a single API.
Both text mode and tool-calling mode use OpenRouter, so you only need one API key.

**Setup:**
```bash
# .env file
OPENROUTER_API_KEY=sk-or-...  # Required - used for both modes
```

**Current models (Jan 2026):**
- Claude 4.5 (Opus, Sonnet, Haiku)
- GPT-5 series (5.2, 5.1, 5-mini, 5-nano)
- Gemini 3 Pro, 2.5 Pro/Flash
- Llama 4 (Maverick, Scout)
- DeepSeek V3.2, R1
- Mistral Large, Medium, Small
- Grok 4.1
- Qwen 3 (235B, Max)

**Full model list:** See `config_full_tournament.yaml` for 30+ models with pricing.

**Alternative providers** (not currently implemented):
- **Groq** - Fast inference for Llama, Mixtral
- **TogetherAI** - Open-source models
- **Direct APIs** - Anthropic, OpenAI, Google directly

## Common Tasks

### Adding a new model
1. Add config to `config.yaml` under `models:`
2. If new provider, may need new player class in `src/players/text_based/`

### Adding MCP support for GPT
1. Create `src/players/mcp_based/mcp_gpt_player.py`
2. Use OpenAI function calling format
3. Map MCP tools to OpenAI function schemas
4. Update `game_runner.py` to route GPT to MCP player

## Test Coverage

62 tests covering:
- `test_game_wrapper.py` - Game state serialization
- `test_action_mapper.py` - Action ID generation
- `test_mcp_server.py` - MCP server functionality
- `test_mcp_players.py` - MCP player integration
- `test_elo.py` - Elo rating system

## Mixed-Mode Games

Compare MCP vs Text players directly in the same game using mode suffixes:

```bash
# Direct head-to-head: MCP Claude vs Text Claude
python scripts/run_tournament.py --single-game claude-mcp claude-text claude-mcp claude-text

# Mix of modes and models
python scripts/run_tournament.py --single-game claude-mcp claude-text gpt5-mcp gpt5-text

# Cross-provider comparison
python scripts/run_tournament.py --single-game claude-mcp gpt5-mcp gemini-mcp deepseek-mcp
```

**Player spec format:** `{model_key}-{mode}` where mode is `mcp` or `text`
- `claude-mcp` - Claude using MCP mode (tool calling)
- `claude-text` - Claude using text mode (prompt/response)
- `gpt5-mcp` - GPT-5 using tool calling
- `claude` - Uses default mode from `--mode` flag (defaults to text)

**Elo tracking:** Each model+mode combination is tracked separately (e.g., `claude-mcp` vs `claude-text`).

## Known Limitations

1. Reasoning models (o1, DeepSeek R1) may have different behavior due to extended thinking
2. Some smaller models may struggle with complex game state parsing
