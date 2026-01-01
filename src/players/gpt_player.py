"""
GPT Player for Settlers of Catan.

LLM player implementation using GPT models via OpenRouter.
"""

from llm_game_utils import OpenRouterClient, GameResultLogger
from .base_player import BaseLLMPlayer


class GPTPlayer(BaseLLMPlayer):
    """
    Catan player powered by GPT (OpenAI).

    Uses OpenRouter API to query GPT models.
    """

    def __init__(
        self,
        color,
        client: OpenRouterClient,
        model_config: dict,
        session_id: str = None,
        logger: GameResultLogger = None
    ):
        """
        Initialize GPT player.

        Args:
            color: Catanatron color enum
            client: OpenRouterClient instance
            model_config: Dictionary with model configuration
                         (model_id, name, temperature, max_tokens)
            session_id: Optional session ID for logging
            logger: Optional GameResultLogger instance
        """
        model_name = model_config.get("name", "GPT-4")
        super().__init__(color, model_name, session_id, logger)

        self.client = client
        self.model_id = model_config["model_id"]
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 1000)

    def query_llm(self, prompt: str) -> tuple[str, float, int]:
        """
        Query GPT via OpenRouter.

        Args:
            prompt: The prompt to send to GPT

        Returns:
            Tuple of (response_text, cost, tokens_used)
        """
        try:
            response = self.client.query(
                model_id=self.model_id,
                prompt=prompt,
                system_prompt=(
                    "You are an expert Settlers of Catan player with strong strategic thinking. "
                    "Carefully evaluate each available action and choose the one that maximizes "
                    "your chances of winning. Respond with the number of your chosen action "
                    "followed by your reasoning."
                ),
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            return (
                response.response,
                response.cost,
                response.total_tokens
            )

        except Exception as e:
            self.log.error(f"Error querying GPT: {e}")
            # Return fallback response
            return ("1", 0.0, 0)
