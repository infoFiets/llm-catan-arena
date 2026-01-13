"""
Integration tests for MCP-based players.

Tests the full decide() flow with mock LLM responses.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp.server import CatanatronMCPServer
from src.players.mcp_based.base_mcp_player import BaseMCPPlayer


class MockMCPPlayer(BaseMCPPlayer):
    """Mock MCP player for testing."""

    def __init__(self, color, mcp_server=None):
        super().__init__(
            color=color,
            model_name="MockModel",
            session_id=None,
            logger=None,
            mcp_server=mcp_server
        )
        self.query_count = 0

    def query_llm_with_mcp(self, system_prompt, mcp_server):
        """Mock LLM query that selects first action."""
        self.query_count += 1

        # Simulate LLM querying game state
        mcp_server.handle_tool_call("get_game_state", {})

        # Simulate LLM getting valid actions
        actions_result = mcp_server.handle_tool_call("get_valid_actions", {})
        import json
        actions = json.loads(actions_result)

        # Select first action
        if actions["num_actions"] > 0:
            first_action_id = actions["actions"][0]["action_id"]
            mcp_server.handle_tool_call("select_action", {"action_id": first_action_id})

        return ("Selected action via MCP tools", 0.001, 100)


class TestMCPPlayers:
    """Test suite for MCP player integration."""

    @pytest.fixture
    def mock_game(self):
        """Create a mock Catanatron game."""
        game = Mock()
        game.id = "test_game"
        game.state = Mock()
        game.state.color_to_index = {"RED": 0, "BLUE": 1}
        game.state.player_state = {
            "P0_WOOD_IN_HAND": 2,
            "P0_BRICK_IN_HAND": 1,
            "P0_SHEEP_IN_HAND": 3,
            "P0_WHEAT_IN_HAND": 1,
            "P0_ORE_IN_HAND": 0,
            "P0_ACTUAL_VICTORY_POINTS": 4,
            "P0_VICTORY_POINTS": 3,
            "P0_SETTLEMENTS_AVAILABLE": 2,
            "P0_CITIES_AVAILABLE": 3,
            "P0_ROADS_AVAILABLE": 10,
            "P0_KNIGHT_IN_HAND": 1,
            "P0_YEAR_OF_PLENTY_IN_HAND": 0,
            "P0_MONOPOLY_IN_HAND": 0,
            "P0_ROAD_BUILDING_IN_HAND": 0,
            "P0_VICTORY_POINT_IN_HAND": 1,
            "P0_HAS_ROAD": False,
            "P0_HAS_ARMY": False,
            "P0_PLAYED_KNIGHT": 0,
        }
        game.state.actions = []
        game.state.development_deck = []
        game.state.board = Mock()
        game.state.board.settlements = {}
        game.state.board.cities = {}
        game.state.board.roads = {}
        return game

    @pytest.fixture
    def mock_actions(self):
        """Create mock actions."""
        actions = []
        for i, action_type in enumerate(["BUILD_SETTLEMENT", "BUILD_ROAD", "END_TURN"]):
            action = Mock()
            action.action_type = Mock()
            action.action_type.__str__ = lambda self, at=action_type: f"ActionType.{at}"
            action.color = "RED"
            action.value = i * 10 if i < 2 else None
            action.__str__ = Mock(return_value=f"{action_type} action")
            actions.append(action)
        return actions

    def test_base_mcp_player_decide_flow(self, mock_game, mock_actions):
        """Test full decide() flow with MCP player."""
        mcp_server = CatanatronMCPServer("test_game")
        player = MockMCPPlayer("RED", mcp_server=mcp_server)

        # Call decide
        selected_action = player.decide(mock_game, mock_actions)

        # Verify action was selected
        assert selected_action is not None
        assert selected_action in mock_actions

        # Verify LLM was queried
        assert player.query_count == 1

        # Verify stats updated
        assert player.move_count == 1
        assert player.total_tokens == 100
        assert player.total_cost > 0

    def test_mcp_player_fallback(self, mock_game, mock_actions):
        """Test fallback when LLM doesn't select action."""
        class NoSelectPlayer(BaseMCPPlayer):
            def query_llm_with_mcp(self, system_prompt, mcp_server):
                # Don't call select_action
                return ("No action selected", 0.0, 0)

        mcp_server = CatanatronMCPServer("test_game")
        player = NoSelectPlayer(
            color="RED",
            model_name="NoSelect",
            mcp_server=mcp_server
        )

        # Should fall back to random action
        selected_action = player.decide(mock_game, mock_actions)

        assert selected_action is not None
        assert selected_action in mock_actions

    def test_mcp_player_multiple_decisions(self, mock_game, mock_actions):
        """Test player handling multiple decisions."""
        mcp_server = CatanatronMCPServer("test_game")
        player = MockMCPPlayer("RED", mcp_server=mcp_server)

        # First decision
        action1 = player.decide(mock_game, mock_actions)

        # Second decision
        action2 = player.decide(mock_game, mock_actions)

        assert action1 in mock_actions
        assert action2 in mock_actions
        assert player.move_count == 2

    def test_mcp_player_stats(self, mock_game, mock_actions):
        """Test player statistics tracking."""
        mcp_server = CatanatronMCPServer("test_game")
        player = MockMCPPlayer("RED", mcp_server=mcp_server)

        # Make a few decisions
        for _ in range(3):
            player.decide(mock_game, mock_actions)

        stats = player.get_stats()

        assert stats["model"] == "MockModel"
        assert stats["color"] == "RED"
        assert stats["move_count"] == 3
        assert stats["total_tokens"] == 300
        assert stats["mode"] == "mcp"

    def test_mcp_player_reset(self, mock_game, mock_actions):
        """Test player state reset."""
        mcp_server = CatanatronMCPServer("test_game")
        player = MockMCPPlayer("RED", mcp_server=mcp_server)

        # Make some decisions
        player.decide(mock_game, mock_actions)
        player.decide(mock_game, mock_actions)

        assert player.move_count == 2

        # Reset
        player.reset_state()

        assert player.move_count == 0
        assert player.total_tokens == 0
        assert player.total_cost == 0.0
        assert len(player.recent_moves) == 0

    def test_system_prompt_generation(self, mock_game):
        """Test system prompt includes necessary information."""
        mcp_server = CatanatronMCPServer("test_game")
        player = MockMCPPlayer("RED", mcp_server=mcp_server)

        prompt = player._build_system_prompt(mock_game)

        # Check key elements
        assert "RED" in prompt
        assert "10 victory points" in prompt
        assert "get_game_state" in prompt
        assert "get_valid_actions" in prompt
        assert "select_action" in prompt
        assert "Strategy" in prompt or "strategy" in prompt

    def test_mcp_player_error_handling(self, mock_game, mock_actions):
        """Test error handling in decide()."""
        class ErrorPlayer(BaseMCPPlayer):
            def query_llm_with_mcp(self, system_prompt, mcp_server):
                raise ValueError("Test error")

        mcp_server = CatanatronMCPServer("test_game")
        player = ErrorPlayer(
            color="RED",
            model_name="Error",
            mcp_server=mcp_server
        )

        # Should handle error and fall back
        selected_action = player.decide(mock_game, mock_actions)

        assert selected_action is not None
        assert selected_action in mock_actions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
