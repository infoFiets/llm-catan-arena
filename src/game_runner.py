"""
Game Runner for LLM Catan Arena.

Orchestrates Catan games with LLM players, handles logging, and tracks results.
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

import yaml
from catanatron.game import Game
from llm_game_utils import OpenRouterClient, GameResultLogger

from .players.text_based import ClaudePlayer, GPTPlayer, GeminiPlayer
from .players import RandomPlayer

# Define available colors (strings in Catanatron 3.x)
COLORS = ["RED", "BLUE", "WHITE", "ORANGE"]


class CatanGameRunner:
    """
    Runs Settlers of Catan games with LLM players.

    Handles:
    - Player initialization
    - Game execution
    - Result logging
    - Statistics tracking
    """

    def __init__(self, config_path: str = "config.yaml", mode: str = "text"):
        """
        Initialize game runner.

        Args:
            config_path: Path to configuration YAML file
            mode: "text" for text-based players, "mcp" for MCP-based players
        """
        self.mode = mode
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
        self.log.info(f"Initializing game runner in {mode} mode")

        # Initialize OpenRouter client (for text mode)
        self.client = OpenRouterClient(
            app_name=self.config["openrouter"]["app_name"],
            site_url=self.config["openrouter"]["site_url"]
        )

        # Register model configurations
        self._register_models()

        # Initialize MCP server if in MCP mode
        if self.mode == "mcp":
            from .mcp.server import CatanatronMCPServer
            self.mcp_server = CatanatronMCPServer("catan_arena")
            self.log.info("MCP server initialized")
        else:
            self.mcp_server = None

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
        model_key: str,
        color: str,
        session_id: str
    ):
        """
        Create a player instance based on model key.

        Args:
            model_key: Key from config (e.g., 'claude', 'gpt4')
            color: Catanatron color enum
            session_id: Session ID for logging

        Returns:
            Player instance
        """
        model_config = self.config["models"].get(model_key)

        if not model_config:
            raise ValueError(f"Unknown model key: {model_key}")

        # Route based on mode
        if self.mode == "text":
            return self._create_text_player(model_key, model_config, color, session_id)
        elif self.mode == "mcp":
            return self._create_mcp_player(model_key, model_config, color, session_id)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

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
                logger=self.logger
            )
        elif "gpt" in model_key.lower():
            return GPTPlayer(
                color=color,
                client=self.client,
                model_config=model_config,
                session_id=session_id,
                logger=self.logger
            )
        elif "gemini" in model_key.lower():
            return GeminiPlayer(
                color=color,
                client=self.client,
                model_config=model_config,
                session_id=session_id,
                logger=self.logger
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
        """Create MCP-based player."""
        import os

        if "claude" in model_key.lower() or "haiku" in model_key.lower() or "sonnet" in model_key.lower():
            from .players.mcp_based import MCPClaudePlayer
            return MCPClaudePlayer(
                color=color,
                model_config=model_config,
                session_id=session_id,
                logger=self.logger,
                mcp_server=self.mcp_server,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        elif "gpt" in model_key.lower():
            # TODO: Implement MCPGPTPlayer
            self.log.warning("GPT MCP player not yet implemented, using text-based")
            return self._create_text_player(model_key, model_config, color, session_id)
        elif "gemini" in model_key.lower():
            # TODO: Implement MCPGeminiPlayer
            self.log.warning("Gemini MCP player not yet implemented, using text-based")
            return self._create_text_player(model_key, model_config, color, session_id)
        else:
            self.log.warning(f"Unknown model key '{model_key}', using RandomPlayer")
            return RandomPlayer(color=color)

    def run_game(self, player_models: List[str], game_id: str = None) -> Dict[str, Any]:
        """
        Run a single Catan game.

        Args:
            player_models: List of 4 model keys for the players
            game_id: Optional game identifier

        Returns:
            Dictionary with game results
        """
        if len(player_models) != 4:
            raise ValueError("Exactly 4 players required for Catan")

        # Create session
        session_id = self.logger.start_session(
            game_name="Settlers of Catan",
            players=[f"{model}:{color}" for model, color in zip(player_models, COLORS)],
            game_config={
                "player_models": player_models,
                "max_turns": self.config["game"]["max_turns"],
                "victory_points": self.config["game"]["victory_points"]
            }
        )

        self.log.info(f"Starting game {session_id}")
        self.log.info(f"Players: {player_models}")

        # Create players
        colors = COLORS  # RED, BLUE, WHITE, ORANGE
        players = [
            self.create_player(model, color, session_id)
            for model, color in zip(player_models, colors)
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
            winner_model = player_models[colors.index(winner_color)] if winner_color else None

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
                winner=f"{winner_model}:{winner_color}" if winner_model else "Draw",
                final_scores=scores
            )

            # Get summary
            summary = self.logger.get_session_summary(session_id)

            results = {
                "session_id": session_id,
                "winner": winner_model,
                "winner_color": winner_color if winner_color else None,
                "scores": scores,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "player_models": player_models,
                "full_summary": summary
            }

            self.log.info(f"Game {session_id} completed. Winner: {winner_model}")
            self.log.info(f"Scores: {scores}")
            self.log.info(f"Total cost: ${total_cost:.4f}, Total tokens: {total_tokens}")

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
        num_games: int = None
    ) -> List[Dict[str, Any]]:
        """
        Run multiple games (tournament).

        Args:
            matchups: List of player model combinations to test
                     If None, uses matchups from config
            num_games: Number of times to run each matchup
                      If None, uses default from config

        Returns:
            List of game results
        """
        if matchups is None:
            matchups = self.config["tournament"]["matchups"]

        if num_games is None:
            num_games = self.config["tournament"]["default_games"]

        self.log.info(f"Starting tournament: {len(matchups)} matchups, {num_games} games each")

        all_results = []

        for i, matchup in enumerate(matchups, 1):
            self.log.info(f"\nMatchup {i}/{len(matchups)}: {matchup}")

            for game_num in range(num_games):
                self.log.info(f"  Game {game_num + 1}/{num_games}")

                try:
                    result = self.run_game(matchup, game_id=f"m{i}_g{game_num + 1}")
                    all_results.append(result)
                except Exception as e:
                    self.log.error(f"  Game failed: {e}")
                    continue

        self.log.info(f"\nTournament complete: {len(all_results)} games played")

        return all_results
