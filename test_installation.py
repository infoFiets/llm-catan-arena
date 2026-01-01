#!/usr/bin/env python3
"""
Test script to verify llm-game-utils package installation and functionality.
Tests all main components: OpenRouterClient, GameResultLogger, and PromptFormatter.
"""

import os
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_imports():
    """Test that all main components can be imported."""
    print("=" * 60)
    print("TEST 1: Importing Components")
    print("=" * 60)

    try:
        from llm_game_utils import (
            OpenRouterClient,
            GameResultLogger,
            PromptFormatter,
            LLMResponse,
            BaseLLMClient
        )
        print("✓ All components imported successfully!")
        print(f"  - OpenRouterClient: {OpenRouterClient}")
        print(f"  - GameResultLogger: {GameResultLogger}")
        print(f"  - PromptFormatter: {PromptFormatter}")
        print(f"  - LLMResponse: {LLMResponse}")
        print(f"  - BaseLLMClient: {BaseLLMClient}")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_openrouter_client():
    """Test OpenRouterClient initialization and a simple API call."""
    print("\n" + "=" * 60)
    print("TEST 2: OpenRouterClient")
    print("=" * 60)

    try:
        from llm_game_utils import OpenRouterClient

        # Check if API key is available
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("⚠ OPENROUTER_API_KEY not found in environment")
            print("  Skipping live API test")
            return True

        # Initialize client
        client = OpenRouterClient(
            app_name="LLM Catan Arena Test",
            site_url="https://github.com/infoFiets/llm-catan-arena"
        )
        print(f"✓ OpenRouterClient initialized successfully")

        # Add model configuration (using a valid OpenRouter model ID)
        client.add_model_config(
            model_id="anthropic/claude-3-haiku",
            name="Claude 3 Haiku",
            input_cost=0.00025,
            output_cost=0.00125
        )
        print(f"✓ Model configuration added")

        # Test a simple prompt
        print("\nTesting simple API call...")
        prompt = "Say 'Hello from llm-game-utils test!' and nothing else."

        response = client.query(
            model_id="anthropic/claude-3-haiku",
            prompt=prompt,
            system_prompt="You are a test assistant. Be concise.",
            max_tokens=50
        )

        print(f"✓ API call successful!")
        print(f"  Response: {response.response[:100]}...")
        print(f"  Tokens used: {response.total_tokens}")
        print(f"  Cost: ${response.cost:.6f}")
        print(f"  Time: {response.response_time:.2f}s")

        return True

    except Exception as e:
        print(f"✗ OpenRouterClient test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_game_result_logger():
    """Test GameResultLogger functionality."""
    print("\n" + "=" * 60)
    print("TEST 3: GameResultLogger")
    print("=" * 60)

    try:
        from llm_game_utils import GameResultLogger

        # Create temporary directory for test logs
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            # Initialize logger
            logger = GameResultLogger(output_dir=log_dir)
            print(f"✓ GameResultLogger initialized")
            print(f"  Log directory: {log_dir}")

            # Start a game session
            session_id = logger.start_session(
                game_name="Settlers of Catan",
                players=["TestPlayer", "Opponent"],
                game_config={"max_turns": 100}
            )
            print(f"✓ Session started: {session_id}")

            # Log a game move
            logger.log_move(
                session_id=session_id,
                player="TestPlayer",
                move_data={"action": "build_settlement", "location": "A1"},
                turn_number=1
            )
            print(f"✓ Move logged successfully")

            # End session with results
            logger.end_session(
                session_id=session_id,
                winner="TestPlayer",
                final_scores={"TestPlayer": 10, "Opponent": 7}
            )
            print(f"✓ Session ended successfully")

            # Get session summary
            summary = logger.get_session_summary(session_id)
            print(f"✓ Session summary retrieved:")
            print(f"  - Game: {summary['game_name']}")
            print(f"  - Players: {summary['players']}")
            print(f"  - Winner: {summary['winner']}")
            print(f"  - Total Moves: {summary['total_moves']}")

        return True

    except Exception as e:
        print(f"✗ GameResultLogger test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_formatter():
    """Test PromptFormatter utilities."""
    print("\n" + "=" * 60)
    print("TEST 4: PromptFormatter")
    print("=" * 60)

    try:
        from llm_game_utils import PromptFormatter

        formatter = PromptFormatter()

        # Test game state formatting
        state = {
            "resources": {"wood": 2, "brick": 1, "wheat": 3},
            "settlements": 2,
            "cities": 1,
            "victory_points": 5
        }

        actions = [
            "Build a settlement",
            "Build a road",
            "Trade resources",
            "End turn"
        ]

        formatted = formatter.format_game_state(
            game_name="Settlers of Catan",
            current_state=state,
            available_actions=actions,
            additional_context="It's your turn. Choose wisely!"
        )

        print("✓ Game state formatted successfully:")
        print("\n" + "-" * 60)
        print(formatted)
        print("-" * 60)

        # Verify it contains key information
        assert "Settlers of Catan" in formatted
        assert "wood" in formatted.lower() or "resources" in formatted.lower()
        print("\n✓ Formatted prompt contains expected information")

        return True

    except Exception as e:
        print(f"✗ PromptFormatter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests and report results."""
    print("\n" + "=" * 60)
    print("LLM-GAME-UTILS INSTALLATION TEST")
    print("=" * 60)

    results = {
        "Imports": test_imports(),
        "OpenRouterClient": test_openrouter_client(),
        "GameResultLogger": test_game_result_logger(),
        "PromptFormatter": test_prompt_formatter()
    }

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:.<40} {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: All tests passed! ✓")
        print("llm-game-utils is ready to use.")
    else:
        print("FAILURE: Some tests failed. ✗")
        print("Please check the errors above.")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
