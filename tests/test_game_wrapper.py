"""
Unit tests for CatanatronGameWrapper.

Tests game state serialization and JSON compatibility.
"""

import pytest
from unittest.mock import Mock, MagicMock
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.game_wrapper import CatanatronGameWrapper


class TestCatanatronGameWrapper:
    """Test suite for game state wrapper."""

    @pytest.fixture
    def mock_game(self):
        """Create a mock Catanatron game."""
        game = Mock()
        game.id = "test_game_123"

        # Mock game state
        game.state = Mock()
        game.state.color_to_index = {
            "RED": 0,
            "BLUE": 1,
            "WHITE": 2,
            "ORANGE": 3
        }

        # Mock player state (flat dict)
        game.state.player_state = {
            # RED player (index 0)
            "P0_WOOD_IN_HAND": 2,
            "P0_BRICK_IN_HAND": 1,
            "P0_SHEEP_IN_HAND": 3,
            "P0_WHEAT_IN_HAND": 1,
            "P0_ORE_IN_HAND": 0,
            "P0_ACTUAL_VICTORY_POINTS": 4,
            "P0_VICTORY_POINTS": 3,
            "P0_SETTLEMENTS_AVAILABLE": 2,  # Built 3
            "P0_CITIES_AVAILABLE": 3,  # Built 1
            "P0_ROADS_AVAILABLE": 10,  # Built 5
            "P0_KNIGHT_IN_HAND": 1,
            "P0_YEAR_OF_PLENTY_IN_HAND": 0,
            "P0_MONOPOLY_IN_HAND": 0,
            "P0_ROAD_BUILDING_IN_HAND": 0,
            "P0_VICTORY_POINT_IN_HAND": 1,
            "P0_HAS_ROAD": False,
            "P0_HAS_ARMY": False,
            "P0_PLAYED_KNIGHT": 2,
            "P0_LONGEST_ROAD_LENGTH": 4,

            # BLUE player (index 1)
            "P1_WOOD_IN_HAND": 1,
            "P1_BRICK_IN_HAND": 2,
            "P1_SHEEP_IN_HAND": 0,
            "P1_WHEAT_IN_HAND": 1,
            "P1_ORE_IN_HAND": 1,
            "P1_ACTUAL_VICTORY_POINTS": 5,
            "P1_VICTORY_POINTS": 5,
            "P1_SETTLEMENTS_AVAILABLE": 3,
            "P1_CITIES_AVAILABLE": 4,
            "P1_ROADS_AVAILABLE": 12,
            "P1_KNIGHT_IN_HAND": 0,
            "P1_YEAR_OF_PLENTY_IN_HAND": 1,
            "P1_MONOPOLY_IN_HAND": 0,
            "P1_ROAD_BUILDING_IN_HAND": 0,
            "P1_VICTORY_POINT_IN_HAND": 0,
            "P1_HAS_ROAD": True,
            "P1_HAS_ARMY": False,
            "P1_PLAYED_KNIGHT": 0,

            # WHITE player (index 2)
            "P2_WOOD_IN_HAND": 0,
            "P2_BRICK_IN_HAND": 0,
            "P2_SHEEP_IN_HAND": 2,
            "P2_WHEAT_IN_HAND": 3,
            "P2_ORE_IN_HAND": 2,
            "P2_ACTUAL_VICTORY_POINTS": 3,
            "P2_VICTORY_POINTS": 2,
            "P2_SETTLEMENTS_AVAILABLE": 3,
            "P2_CITIES_AVAILABLE": 4,
            "P2_ROADS_AVAILABLE": 13,
            "P2_HAS_ROAD": False,
            "P2_HAS_ARMY": False,
            "P2_PLAYED_KNIGHT": 1,

            # ORANGE player (index 3)
            "P3_WOOD_IN_HAND": 3,
            "P3_BRICK_IN_HAND": 3,
            "P3_SHEEP_IN_HAND": 1,
            "P3_WHEAT_IN_HAND": 0,
            "P3_ORE_IN_HAND": 0,
            "P3_ACTUAL_VICTORY_POINTS": 2,
            "P3_VICTORY_POINTS": 2,
            "P3_SETTLEMENTS_AVAILABLE": 3,
            "P3_CITIES_AVAILABLE": 4,
            "P3_ROADS_AVAILABLE": 11,
            "P3_HAS_ROAD": False,
            "P3_HAS_ARMY": False,
            "P3_PLAYED_KNIGHT": 0,
        }

        # Mock actions list
        game.state.actions = [Mock() for _ in range(15)]

        # Mock development deck
        game.state.development_deck = [Mock() for _ in range(20)]

        # Mock board
        game.state.board = Mock()
        game.state.board.settlements = {}
        game.state.board.cities = {}
        game.state.board.roads = {}
        game.state.board.robber_tile = "hex_5"

        return game

    def test_initialization(self, mock_game):
        """Test wrapper initialization."""
        wrapper = CatanatronGameWrapper(mock_game, "RED")

        assert wrapper.game == mock_game
        assert wrapper.player_color == "RED"
        assert wrapper.player_index == 0

    def test_get_state_basic(self, mock_game):
        """Test basic state extraction."""
        wrapper = CatanatronGameWrapper(mock_game, "RED")
        state = wrapper.get_state()

        # Verify JSON serializable
        json_str = json.dumps(state)
        assert json_str is not None

        # Check structure
        assert "game_id" in state
        assert "turn_number" in state
        assert "your_color" in state
        assert "your_state" in state
        assert "opponents" in state
        assert "development_cards_remaining" in state

        # Verify values
        assert state["game_id"] == "test_game_123"
        assert state["turn_number"] == 15
        assert state["your_color"] == "RED"
        assert state["development_cards_remaining"] == 20

    def test_your_state_extraction(self, mock_game):
        """Test player state extraction for current player."""
        wrapper = CatanatronGameWrapper(mock_game, "RED")
        state = wrapper.get_state()

        your_state = state["your_state"]

        # Check resources
        assert your_state["resources"]["wood"] == 2
        assert your_state["resources"]["brick"] == 1
        assert your_state["resources"]["sheep"] == 3
        assert your_state["resources"]["wheat"] == 1
        assert your_state["resources"]["ore"] == 0
        assert your_state["total_resources"] == 7

        # Check victory points
        assert your_state["victory_points"] == 4
        assert your_state["public_victory_points"] == 3

        # Check buildings
        assert your_state["buildings"]["settlements_built"] == 3
        assert your_state["buildings"]["cities_built"] == 1
        assert your_state["buildings"]["roads_built"] == 5
        assert your_state["buildings"]["settlements_available"] == 2
        assert your_state["buildings"]["cities_available"] == 3
        assert your_state["buildings"]["roads_available"] == 10

        # Check dev cards
        assert your_state["development_cards"]["knight"] == 1
        assert your_state["development_cards"]["victory_point"] == 1
        assert your_state["development_cards"]["total"] == 2

        # Check special achievements
        assert your_state["has_longest_road"] is False
        assert your_state["has_largest_army"] is False
        assert your_state["knights_played"] == 2
        assert your_state["longest_road_length"] == 4

    def test_opponents_state_extraction(self, mock_game):
        """Test opponent state extraction."""
        wrapper = CatanatronGameWrapper(mock_game, "RED")
        state = wrapper.get_state()

        opponents = state["opponents"]

        # Should have 3 opponents (not including RED)
        assert len(opponents) == 3

        # Check BLUE opponent
        blue = next((opp for opp in opponents if opp["color"] == "BLUE"), None)
        assert blue is not None
        assert blue["victory_points"] == 5
        assert blue["resource_count"] == 5  # 1+2+0+1+1
        assert blue["development_card_count"] == 1
        assert blue["buildings"]["settlements"] == 2
        assert blue["buildings"]["cities"] == 0
        assert blue["buildings"]["roads"] == 3
        assert blue["has_longest_road"] is True

    def test_include_board_state(self, mock_game):
        """Test board state inclusion."""
        wrapper = CatanatronGameWrapper(mock_game, "RED")

        # Without board
        state_no_board = wrapper.get_state(include_board=False)
        assert "board" not in state_no_board

        # With board
        state_with_board = wrapper.get_state(include_board=True)
        assert "board" in state_with_board
        assert "settlements" in state_with_board["board"]
        assert "cities" in state_with_board["board"]
        assert "roads" in state_with_board["board"]
        assert "robber_tile" in state_with_board["board"]
        assert state_with_board["board"]["robber_tile"] == "hex_5"

    def test_include_history(self, mock_game):
        """Test action history inclusion."""
        wrapper = CatanatronGameWrapper(mock_game, "RED")

        # Without history
        state_no_history = wrapper.get_state(include_history=False)
        assert "recent_actions" not in state_no_history

        # With history
        state_with_history = wrapper.get_state(include_history=True)
        assert "recent_actions" in state_with_history
        assert len(state_with_history["recent_actions"]) == 10

    def test_different_player_perspectives(self, mock_game):
        """Test that different players get different perspectives."""
        wrapper_red = CatanatronGameWrapper(mock_game, "RED")
        wrapper_blue = CatanatronGameWrapper(mock_game, "BLUE")

        state_red = wrapper_red.get_state()
        state_blue = wrapper_blue.get_state()

        # Different colors
        assert state_red["your_color"] == "RED"
        assert state_blue["your_color"] == "BLUE"

        # Different states
        assert state_red["your_state"]["victory_points"] == 4
        assert state_blue["your_state"]["victory_points"] == 5

        # Different opponents
        assert len(state_red["opponents"]) == 3
        assert len(state_blue["opponents"]) == 3
        assert "RED" not in [opp["color"] for opp in state_red["opponents"]]
        assert "BLUE" not in [opp["color"] for opp in state_blue["opponents"]]

    def test_json_serialization(self, mock_game):
        """Test that entire state is JSON serializable."""
        wrapper = CatanatronGameWrapper(mock_game, "RED")
        state = wrapper.get_state(include_board=True, include_history=True)

        # Should not raise exception
        json_str = json.dumps(state)
        assert len(json_str) > 0

        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed["your_color"] == "RED"
        assert parsed["turn_number"] == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
