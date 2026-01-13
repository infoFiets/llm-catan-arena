"""
Unit tests for CatanatronMCPServer.

Tests tool handlers, context management, and action selection.
"""

import pytest
from unittest.mock import Mock, MagicMock
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.server import CatanatronMCPServer


class TestCatanatronMCPServer:
    """Test suite for MCP server."""

    @pytest.fixture
    def mock_game(self):
        """Create a mock Catanatron game."""
        game = Mock()
        game.id = "test_game"
        game.state = Mock()
        game.state.color_to_index = {"RED": 0, "BLUE": 1, "WHITE": 2, "ORANGE": 3}
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
            "P0_PLAYED_KNIGHT": 2,
            "P0_LONGEST_ROAD_LENGTH": 4,
            "P1_VICTORY_POINTS": 5,
            "P1_WOOD_IN_HAND": 1,
            "P1_BRICK_IN_HAND": 2,
            "P1_SHEEP_IN_HAND": 0,
            "P1_WHEAT_IN_HAND": 1,
            "P1_ORE_IN_HAND": 1,
        }
        game.state.actions = [Mock() for _ in range(10)]
        game.state.development_deck = [Mock() for _ in range(15)]
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

    def test_initialization(self):
        """Test server initialization."""
        server = CatanatronMCPServer("test_game")

        assert server.game_id == "test_game"
        assert server.game_wrapper is None
        assert server.selected_action_id is None

    def test_set_game_context(self, mock_game, mock_actions):
        """Test setting game context."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        assert server.game_wrapper is not None
        assert server.game_wrapper.player_color == "RED"
        assert server.selected_action_id is None
        assert len(server.action_mapper.get_all_action_ids()) == 3

    def test_get_tools(self):
        """Test getting tool definitions."""
        server = CatanatronMCPServer()
        tools = server.get_tools()

        assert len(tools) == 3
        tool_names = [tool["name"] for tool in tools]
        assert "get_game_state" in tool_names
        assert "get_valid_actions" in tool_names
        assert "select_action" in tool_names

        # Check tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool

    def test_handle_tool_call_without_context(self):
        """Test tool call without game context."""
        server = CatanatronMCPServer()

        result = server.handle_tool_call("get_game_state", {})
        result_dict = json.loads(result)

        assert "error" in result_dict
        assert "context" in result_dict["error"].lower()

    def test_get_game_state_tool(self, mock_game, mock_actions):
        """Test get_game_state tool handler."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        result = server.handle_tool_call("get_game_state", {})
        state = json.loads(result)

        # Verify structure
        assert "your_color" in state
        assert "your_state" in state
        assert "opponents" in state
        assert state["your_color"] == "RED"

        # Verify player state
        assert state["your_state"]["resources"]["wood"] == 2
        assert state["your_state"]["victory_points"] == 4

    def test_get_game_state_with_board(self, mock_game, mock_actions):
        """Test get_game_state with board inclusion."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        # Without board
        result_no_board = server.handle_tool_call("get_game_state", {"include_board": False})
        state_no_board = json.loads(result_no_board)
        assert "board" not in state_no_board

        # With board
        result_with_board = server.handle_tool_call("get_game_state", {"include_board": True})
        state_with_board = json.loads(result_with_board)
        assert "board" in state_with_board

    def test_get_valid_actions_tool(self, mock_game, mock_actions):
        """Test get_valid_actions tool handler."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        result = server.handle_tool_call("get_valid_actions", {})
        actions_data = json.loads(result)

        assert "num_actions" in actions_data
        assert "actions" in actions_data
        assert actions_data["num_actions"] == 3

        # Verify action structure
        first_action = actions_data["actions"][0]
        assert "action_id" in first_action
        assert "description" in first_action
        assert "action_type" in first_action

    def test_select_action_tool_success(self, mock_game, mock_actions):
        """Test successful action selection."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        # Get valid action IDs first
        actions_result = server.handle_tool_call("get_valid_actions", {})
        actions_data = json.loads(actions_result)
        first_action_id = actions_data["actions"][0]["action_id"]

        # Select the action
        result = server.handle_tool_call("select_action", {"action_id": first_action_id})
        selection = json.loads(result)

        assert selection["success"] is True
        assert selection["action_id"] == first_action_id
        assert "message" in selection

        # Verify server state
        assert server.selected_action_id == first_action_id

    def test_select_action_missing_id(self, mock_game, mock_actions):
        """Test select_action without action_id."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        result = server.handle_tool_call("select_action", {})
        error = json.loads(result)

        assert "error" in error
        assert "action_id" in error["error"]

    def test_select_action_invalid_id(self, mock_game, mock_actions):
        """Test select_action with invalid action_id."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        result = server.handle_tool_call("select_action", {"action_id": "invalid_action"})
        error = json.loads(result)

        assert "error" in error
        assert "valid_action_ids" in error

    def test_get_selected_action(self, mock_game, mock_actions):
        """Test retrieving selected action."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        # Initially no selection
        assert server.get_selected_action() is None

        # Select an action
        actions_result = server.handle_tool_call("get_valid_actions", {})
        actions_data = json.loads(actions_result)
        first_action_id = actions_data["actions"][0]["action_id"]

        server.handle_tool_call("select_action", {"action_id": first_action_id})

        # Now should return the action
        selected_action = server.get_selected_action()
        assert selected_action is not None
        assert selected_action == mock_actions[0]

    def test_unknown_tool(self, mock_game, mock_actions):
        """Test calling unknown tool."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        result = server.handle_tool_call("unknown_tool", {})
        error = json.loads(result)

        assert "error" in error
        assert "available_tools" in error

    def test_clear_context(self, mock_game, mock_actions):
        """Test clearing game context."""
        server = CatanatronMCPServer()
        server.set_game_context(mock_game, "RED", mock_actions)

        # Select an action
        actions_result = server.handle_tool_call("get_valid_actions", {})
        actions_data = json.loads(actions_result)
        first_action_id = actions_data["actions"][0]["action_id"]
        server.handle_tool_call("select_action", {"action_id": first_action_id})

        # Verify context is set
        assert server.game_wrapper is not None
        assert server.selected_action_id is not None

        # Clear context
        server.clear_context()

        # Verify context is cleared
        assert server.game_wrapper is None
        assert server.selected_action_id is None

    def test_multiple_decisions(self, mock_game, mock_actions):
        """Test server handling multiple decisions."""
        server = CatanatronMCPServer()

        # First decision
        server.set_game_context(mock_game, "RED", mock_actions)
        result1 = server.handle_tool_call("get_valid_actions", {})
        actions1 = json.loads(result1)
        server.handle_tool_call("select_action", {"action_id": actions1["actions"][0]["action_id"]})
        selected1 = server.get_selected_action()

        # Second decision (context reset)
        server.set_game_context(mock_game, "BLUE", mock_actions)
        result2 = server.handle_tool_call("get_valid_actions", {})
        actions2 = json.loads(result2)

        # Previous selection should be cleared
        assert server.selected_action_id is None

        # New selection
        server.handle_tool_call("select_action", {"action_id": actions2["actions"][1]["action_id"]})
        selected2 = server.get_selected_action()

        assert selected1 != selected2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
