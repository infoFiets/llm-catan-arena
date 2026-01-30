"""
Gemini Player for Settlers of Catan.

LLM player implementation using Gemini models via OpenRouter.
"""

from llm_game_utils import OpenRouterClient, GameResultLogger
from .base_player import BaseLLMPlayer


class GeminiPlayer(BaseLLMPlayer):
    """
    Catan player powered by Gemini (Google).

    Uses OpenRouter API to query Gemini models.
    """

    def __init__(
        self,
        color,
        client: OpenRouterClient,
        model_config: dict,
        session_id: str = None,
        logger: GameResultLogger = None,
        prompt_format: str = "json"
    ):
        """
        Initialize Gemini player.

        Args:
            color: Catanatron color enum
            client: OpenRouterClient instance
            model_config: Dictionary with model configuration
                         (model_id, name, temperature, max_tokens)
            session_id: Optional session ID for logging
            logger: Optional GameResultLogger instance
            prompt_format: Prompt format - "json", "json-minified", or "toon"
        """
        model_name = model_config.get("name", "Gemini")
        super().__init__(color, model_name, session_id, logger, prompt_format=prompt_format)

        self.client = client
        self.model_id = model_config["model_id"]
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 1000)

    def query_llm(self, prompt: str) -> tuple[str, float, int]:
        """
        Query Gemini via OpenRouter.

        Args:
            prompt: The prompt to send to Gemini

        Returns:
            Tuple of (response_text, cost, tokens_used)

        Raises:
            Exception: If the API call fails (will be retried by base class)
        """
        response = self.client.query(
            model_id=self.model_id,
            prompt=prompt,
            system_prompt=(
                "You are a skilled Settlers of Catan player. "
                "Analyze the current game state and available actions carefully. "
                "Select the action that best advances your position towards victory. "
                "Respond with the action number and explain your strategic thinking."
            ),
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        return (
            response.response,
            response.cost,
            response.total_tokens
        )
