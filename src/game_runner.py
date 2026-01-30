"""
Game Runner for LLM Catan Arena.

Orchestrates Catan games with LLM players, handles logging, and tracks results.
Supports mixed-mode games where MCP and Text players compete together.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

import yaml
from catanatron.game import Game
from llm_game_utils import OpenRouterClient, GameResultLogger

from .players.text_based import ClaudePlayer, GPTPlayer, GeminiPlayer
from .players import RandomPlayer
from .elo import EloRating

# Define available colors (strings in Catanatron 3.x)
COLORS = ["RED", "BLUE", "WHITE", "ORANGE"]


def parse_player_spec(player_spec: str) -> Tuple[str, Optional[str]]:
    """
    Parse a player specification to extract model key and optional mode.

    Supports formats:
    - "claude" -> ("claude", None) - uses default mode
    - "claude-mcp" -> ("claude", "mcp")
    - "claude-text" -> ("claude", "text")
    - "gpt4-text" -> ("gpt4", "text")

    Args:
        player_spec: Player specification string

    Returns:
        Tuple of (model_key, mode) where mode is None if not specified
    """
    # Check for mode suffix
    if player_spec.endswith("-mcp"):
        return player_spec[:-4], "mcp"
    elif player_spec.endswith("-text"):
        return player_spec[:-5], "text"
    else:
        return player_spec, None


class CatanGameRunner:
    """
    Runs Settlers of Catan games with LLM players.

    Handles:
    - Player initialization
    - Game execution
    - Result logging
    - Statistics tracking
    """

    def __init__(self, config_path: str = "config.yaml", mode: str = "text", prompt_format: str = "json"):
        """
        Initialize game runner.

        Args:
            config_path: Path to configuration YAML file
            mode: Default mode - "text" for text-based players, "mcp" for MCP-based players.
                  Can be overridden per-player using mode suffixes (e.g., "claude-mcp")
            prompt_format: Prompt format - "json", "json-minified", or "toon"
        """
        self.default_mode = mode
        self.prompt_format = prompt_format
        self.config = self._load_config(config_path)
        self.logger = GameResultLogger(
            output_dir=self.config["logging"]["output_dir"]
        )

        # Set up logging first
        logging.basicConfig(
            level=getattr(logging, self.config["game"]["log_level"]),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.log = logging.getLogger(__name__)
        self.log.info(f"Initializing game runner with default mode={mode}, format={prompt_format}")

        # Initialize OpenRouter client (for text mode)
        self.client = OpenRouterClient(
            app_name=self.config["openrouter"]["app_name"],
            site_url=self.config["openrouter"]["site_url"]
        )

        # Validate OpenRouter API key
        import os
        if not os.getenv("OPENROUTER_API_KEY"):
            self.log.warning(
                "OPENROUTER_API_KEY not set. Text mode API calls will fail. "
                "Set it in .env or environment."
            )

        # Register model configurations
        self._register_models()

        # MCP server initialized lazily when needed
        self._mcp_server = None

        # Initialize Elo rating system
        self.elo = EloRating(
            ratings_file=self.config.get("elo", {}).get("ratings_file", "data/elo_ratings.json"),
            k_factor=self.config.get("elo", {}).get("k_factor", 32)
        )
        self.track_elo = self.config.get("elo", {}).get("enabled", True)

    @property
    def mcp_server(self):
        """Lazily initialize MCP server on first access."""
        if self._mcp_server is None:
            from .mcp.server import CatanatronMCPServer
            self._mcp_server = CatanatronMCPServer("catan_arena")
            self.log.info("MCP server initialized (lazy)")
        return self._mcp_server

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _register_models(self):
        """Register all model configurations with OpenRouter client."""
        for model_key, model_config in self.config["models"].items():
            self.client.add_model_config(
                model_id=model_config["model_id"],
                name=model_config["name"],
                input_cost=model_config.get("input_cost", 0),
                output_cost=model_config.get("output_cost", 0)
            )
            self.log.info(f"Registered model: {model_config['name']}")

    def create_player(
        self,
        player_spec: str,
        color: str,
        session_id: str
    ):
        """
        Create a player instance based on player specification.

        Args:
            player_spec: Player specification with optional mode suffix
                        (e.g., 'claude', 'claude-mcp', 'gpt4-text')
            color: Catanatron color enum
            session_id: Session ID for logging

        Returns:
            Tuple of (player instance, effective mode used)
        """
        # Parse player spec to get model key and mode
        model_key, mode_override = parse_player_spec(player_spec)

        # Use override mode or fall back to default
        effective_mode = mode_override if mode_override else self.default_mode

        model_config = self.config["models"].get(model_key)

        if not model_config:
            raise ValueError(f"Unknown model key: {model_key}")

        self.log.debug(f"Creating player: {player_spec} -> model={model_key}, mode={effective_mode}")

        # Route based on effective mode
        if effective_mode == "text":
            player = self._create_text_player(model_key, model_config, color, session_id)
        elif effective_mode == "mcp":
            player = self._create_mcp_player(model_key, model_config, color, session_id)
        else:
            raise ValueError(f"Unknown mode: {effective_mode}")

        # Store the effective mode on the player for Elo tracking
        player._effective_mode = effective_mode
        return player

    def _create_text_player(
        self,
        model_key: str,
        model_config: dict,
        color: str,
        session_id: str
    ):
        """Create text-based player."""
        # Determine player class based on model
        if "claude" in model_key.lower() or "haiku" in model_key.lower() or "sonnet" in model_key.lower():
            return ClaudePlayer(
                color=color,
                client=self.client,
                model_config=model_config,
                session_id=session_id,
                logger=self.logger,
                prompt_format=self.prompt_format
            )
        elif "gpt" in model_key.lower():
            return GPTPlayer(
                color=color,
                client=self.client,
                model_config=model_config,
                session_id=session_id,
                logger=self.logger,
                prompt_format=self.prompt_format
            )
        elif "gemini" in model_key.lower():
            return GeminiPlayer(
                color=color,
                client=self.client,
                model_config=model_config,
                session_id=session_id,
                logger=self.logger,
                prompt_format=self.prompt_format
            )
        else:
            # Default to random player for unknown models
            self.log.warning(f"Unknown model type for {model_key}, using RandomPlayer")
            return RandomPlayer(color=color)

    def _create_mcp_player(
        self,
        model_key: str,
        model_config: dict,
        color: str,
        session_id: str
    ):
        """
        Create tool-calling player using OpenRouter.

        All models use OpenRouter's tool calling API, so only OPENROUTER_API_KEY is needed.
        """
        from .players.mcp_based import OpenRouterToolsPlayer

        # Check for known non-tool-calling models
        model_id = model_config.get("model_id", "")
        known_no_tools = ["random"]

        if any(x in model_key.lower() for x in known_no_tools):
            self.log.warning(f"Unknown model key '{model_key}', using RandomPlayer")
            return RandomPlayer(color=color)

        # Use OpenRouterToolsPlayer for all models with tool calling
        self.log.info(f"Creating tool-calling player for {model_key} ({model_id})")

        return OpenRouterToolsPlayer(
            color=color,
            model_config=model_config,
            session_id=session_id,
            logger=self.logger,
            mcp_server=self.mcp_server
        )

    def run_game(self, player_specs: List[str], game_id: str = None) -> Dict[str, Any]:
        """
        Run a single Catan game.

        Args:
            player_specs: List of 4 player specifications (e.g., ['claude-mcp', 'claude-text', 'gpt4', 'gemini'])
                         Each spec can have a mode suffix (-mcp, -text) or use the default mode
            game_id: Optional game identifier

        Returns:
            Dictionary with game results
        """
        if len(player_specs) != 4:
            raise ValueError("Exactly 4 players required for Catan")

        # Create session
        session_id = self.logger.start_session(
            game_name="Settlers of Catan",
            players=[f"{spec}:{color}" for spec, color in zip(player_specs, COLORS)],
            game_config={
                "player_specs": player_specs,
                "max_turns": self.config["game"]["max_turns"],
                "victory_points": self.config["game"]["victory_points"]
            }
        )

        self.log.info(f"Starting game {session_id}")
        self.log.info(f"Players: {player_specs}")

        # Create players
        colors = COLORS  # RED, BLUE, WHITE, ORANGE
        players = [
            self.create_player(spec, color, session_id)
            for spec, color in zip(player_specs, colors)
        ]

        try:
            # Run the game
            self.log.info(f"Creating game with {len(players)} players...")
            game = Game(players)
            self.log.info("Game created, starting play()...")
            game.play()
            self.log.info("Game.play() completed!")

            # Determine winner
            winner_color = game.winning_color()
            winner_spec = player_specs[colors.index(winner_color)] if winner_color else None

            # Collect scores
            scores = {}
            total_cost = 0.0
            total_tokens = 0

            for player in players:
                player_key = f"{player.model_name}:{player.color}"

                # Get victory points using indexed player_state
                player_index = game.state.color_to_index[player.color]
                vp = game.state.player_state.get(f"P{player_index}_ACTUAL_VICTORY_POINTS", 0)

                scores[player_key] = vp

                # Collect stats from LLM players
                if hasattr(player, 'get_stats'):
                    stats = player.get_stats()
                    total_cost += stats.get("total_cost", 0)
                    total_tokens += stats.get("total_tokens", 0)

            # Log results
            self.logger.end_session(
                session_id=session_id,
                winner=f"{winner_spec}:{winner_color}" if winner_spec else "Draw",
                final_scores=scores
            )

            # Get summary
            summary = self.logger.get_session_summary(session_id)

            results = {
                "session_id": session_id,
                "winner": winner_spec,
                "winner_color": winner_color if winner_color else None,
                "scores": scores,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "player_specs": player_specs,
                "full_summary": summary
            }

            # Update Elo ratings
            elo_changes = {}
            if self.track_elo:
                # Create scores dict with mode-aware player IDs
                elo_scores = {}
                for player_key, vp in scores.items():
                    # player_key is like "Claude 3.5 Sonnet:RED"
                    # We want to track by model_key-mode, e.g., "claude-text" or "claude-mcp"
                    color = player_key.split(":")[-1]
                    color_idx = colors.index(color)
                    player = players[color_idx]
                    # Get base model key from player_spec
                    model_key, _ = parse_player_spec(player_specs[color_idx])
                    # Use the effective mode stored on the player
                    effective_mode = getattr(player, '_effective_mode', self.default_mode)
                    player_id = f"{model_key}-{effective_mode}"
                    elo_scores[player_id] = vp

                elo_changes = self.elo.update_ratings(
                    {"scores": elo_scores},
                    session_id=session_id
                )
                results["elo_changes"] = elo_changes

            self.log.info(f"Game {session_id} completed. Winner: {winner_spec}")
            self.log.info(f"Scores: {scores}")
            self.log.info(f"Total cost: ${total_cost:.4f}, Total tokens: {total_tokens}")

            if elo_changes:
                for player_id, change in elo_changes.items():
                    change_str = f"+{change['change']:.1f}" if change['change'] >= 0 else f"{change['change']:.1f}"
                    self.log.info(f"Elo: {player_id} {change['old']:.0f} -> {change['new']:.0f} ({change_str})")

            return results

        except Exception as e:
            self.log.error(f"Error running game: {e}", exc_info=True)
            # Try to end session gracefully
            try:
                self.logger.end_session(
                    session_id=session_id,
                    winner="ERROR",
                    final_scores={}
                )
            except:
                pass
            raise

    def run_tournament(
        self,
        matchups: List[List[str]] = None,
        num_games: int = None,
        parallel: int = None
    ) -> List[Dict[str, Any]]:
        """
        Run multiple games (tournament).

        Args:
            matchups: List of player model combinations to test
                     If None, uses matchups from config
            num_games: Number of times to run each matchup
                      If None, uses default from config
            parallel: Number of parallel games to run
                     If None, uses parallel_games from config (default 1)

        Returns:
            List of game results
        """
        if matchups is None:
            matchups = self.config["tournament"]["matchups"]

        if num_games is None:
            num_games = self.config["tournament"]["default_games"]

        if parallel is None:
            parallel = self.config["tournament"].get("parallel_games", 1)

        total_games = len(matchups) * num_games
        self.log.info(f"Starting tournament: {len(matchups)} matchups, {num_games} games each = {total_games} total games")

        if parallel > 1:
            self.log.info(f"Running with {parallel} parallel games")
            return self._run_tournament_parallel(matchups, num_games, parallel)
        else:
            return self._run_tournament_sequential(matchups, num_games)

    def _run_tournament_sequential(
        self,
        matchups: List[List[str]],
        num_games: int
    ) -> List[Dict[str, Any]]:
        """Run tournament games sequentially."""
        all_results = []
        total_cost = 0.0
        total_tokens = 0
        games_completed = 0
        total_games = len(matchups) * num_games

        for i, matchup in enumerate(matchups, 1):
            self.log.info(f"\nMatchup {i}/{len(matchups)}: {matchup}")

            for game_num in range(num_games):
                games_completed += 1
                self.log.info(f"  Game {game_num + 1}/{num_games} (#{games_completed}/{total_games})")

                try:
                    result = self.run_game(matchup, game_id=f"m{i}_g{game_num + 1}")
                    all_results.append(result)

                    # Track and display running totals
                    game_cost = result.get("total_cost", 0)
                    game_tokens = result.get("total_tokens", 0)
                    total_cost += game_cost
                    total_tokens += game_tokens

                    winner = result.get("winner", "N/A")
                    self.log.info(f"    -> Winner: {winner} | Cost: ${game_cost:.4f} | Tokens: {game_tokens}")
                    self.log.info(f"    -> Running total: ${total_cost:.4f} ({games_completed}/{total_games} games)")

                except Exception as e:
                    self.log.error(f"  Game failed: {e}")
                    continue

        self.log.info(f"\nTournament complete: {len(all_results)} games played")
        self.log.info(f"Total cost: ${total_cost:.4f} | Total tokens: {total_tokens}")

        return all_results

    def _run_tournament_parallel(
        self,
        matchups: List[List[str]],
        num_games: int,
        max_workers: int
    ) -> List[Dict[str, Any]]:
        """Run tournament games in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        # Build list of all games to run
        games_to_run = []
        for i, matchup in enumerate(matchups, 1):
            for game_num in range(num_games):
                games_to_run.append({
                    "matchup": matchup,
                    "game_id": f"m{i}_g{game_num + 1}",
                    "matchup_idx": i,
                    "game_num": game_num + 1
                })

        total_games = len(games_to_run)
        all_results = []
        total_cost = 0.0
        total_tokens = 0
        games_completed = 0
        lock = threading.Lock()

        def run_single_game(game_info):
            """Run a single game and return result."""
            nonlocal games_completed, total_cost, total_tokens

            try:
                result = self.run_game(
                    game_info["matchup"],
                    game_id=game_info["game_id"]
                )
                result["matchup_idx"] = game_info["matchup_idx"]
                result["game_num"] = game_info["game_num"]

                # Thread-safe update of totals
                with lock:
                    games_completed += 1
                    game_cost = result.get("total_cost", 0)
                    game_tokens = result.get("total_tokens", 0)
                    total_cost += game_cost
                    total_tokens += game_tokens

                    winner = result.get("winner", "N/A")
                    self.log.info(
                        f"[{games_completed}/{total_games}] {game_info['matchup']} -> "
                        f"Winner: {winner} | Cost: ${game_cost:.4f} | "
                        f"Running total: ${total_cost:.4f}"
                    )

                return result

            except Exception as e:
                with lock:
                    games_completed += 1
                self.log.error(f"Game {game_info['game_id']} failed: {e}")
                return None

        # Run games in parallel
        self.log.info(f"Starting {total_games} games with {max_workers} workers...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_single_game, game): game for game in games_to_run}

            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    all_results.append(result)

        self.log.info(f"\nTournament complete: {len(all_results)} games played")
        self.log.info(f"Total cost: ${total_cost:.4f} | Total tokens: {total_tokens}")

        return all_results
