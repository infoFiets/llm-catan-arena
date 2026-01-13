"""
Unit tests for ActionMapper.

Tests action ID generation and bidirectional mapping.
"""

import pytest
from unittest.mock import Mock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.action_mapper import ActionMapper


class TestActionMapper:
    """Test suite for action ID mapping."""

    @pytest.fixture
    def mock_actions(self):
        """Create mock Catanatron actions."""
        actions = []

        # BUILD_SETTLEMENT action
        action1 = Mock()
        action1.action_type = Mock()
        action1.action_type.__str__ = lambda self: "ActionType.BUILD_SETTLEMENT"
        action1.color = "RED"
        action1.value = 42
        actions.append(action1)

        # BUILD_ROAD action
        action2 = Mock()
        action2.action_type = Mock()
        action2.action_type.__str__ = lambda self: "ActionType.BUILD_ROAD"
        action2.color = "RED"
        action2.value = 15
        actions.append(action2)

        # PLAY_KNIGHT_CARD action
        action3 = Mock()
        action3.action_type = Mock()
        action3.action_type.__str__ = lambda self: "ActionType.PLAY_KNIGHT_CARD"
        action3.color = "RED"
        action3.value = None
        actions.append(action3)

        # END_TURN action
        action4 = Mock()
        action4.action_type = Mock()
        action4.action_type.__str__ = lambda self: "ActionType.END_TURN"
        action4.color = "RED"
        action4.value = None
        actions.append(action4)

        # BUY_DEVELOPMENT_CARD action
        action5 = Mock()
        action5.action_type = Mock()
        action5.action_type.__str__ = lambda self: "ActionType.BUY_DEVELOPMENT_CARD"
        action5.color = "RED"
        action5.value = None
        actions.append(action5)

        return actions

    def test_initialization_descriptive(self):
        """Test mapper initialization with descriptive IDs."""
        mapper = ActionMapper(use_descriptive_ids=True)
        assert mapper.use_descriptive_ids is True
        assert len(mapper.actions) == 0

    def test_initialization_simple(self):
        """Test mapper initialization with simple IDs."""
        mapper = ActionMapper(use_descriptive_ids=False)
        assert mapper.use_descriptive_ids is False

    def test_set_actions(self, mock_actions):
        """Test setting actions and generating IDs."""
        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions(mock_actions)

        assert len(mapper.actions) == 5
        assert len(mapper.id_to_action) == 5
        assert len(mapper.action_to_id) == 5

    def test_descriptive_action_ids(self, mock_actions):
        """Test descriptive action ID generation."""
        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions(mock_actions)

        action_ids = mapper.get_all_action_ids()

        # Check expected IDs
        assert "build_settlement_42" in action_ids
        assert "build_road_15" in action_ids
        assert "play_knight_card" in action_ids
        assert "end_turn" in action_ids
        assert "buy_development_card" in action_ids

    def test_simple_action_ids(self, mock_actions):
        """Test simple numeric action IDs."""
        mapper = ActionMapper(use_descriptive_ids=False)
        mapper.set_actions(mock_actions)

        action_ids = mapper.get_all_action_ids()

        # Should be simple numeric IDs
        assert "action_0" in action_ids
        assert "action_1" in action_ids
        assert "action_2" in action_ids
        assert "action_3" in action_ids
        assert "action_4" in action_ids

    def test_get_action_by_id(self, mock_actions):
        """Test retrieving action by ID."""
        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions(mock_actions)

        action = mapper.get_action("build_settlement_42")
        assert action is not None
        assert action == mock_actions[0]

    def test_get_action_id_by_object(self, mock_actions):
        """Test retrieving ID by action object."""
        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions(mock_actions)

        action_id = mapper.get_action_id(mock_actions[0])
        assert action_id == "build_settlement_42"

    def test_is_valid_action_id(self, mock_actions):
        """Test action ID validation."""
        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions(mock_actions)

        assert mapper.is_valid_action_id("build_settlement_42") is True
        assert mapper.is_valid_action_id("build_road_15") is True
        assert mapper.is_valid_action_id("invalid_action") is False
        assert mapper.is_valid_action_id("") is False

    def test_get_all_actions_with_ids(self, mock_actions):
        """Test getting all actions with metadata."""
        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions(mock_actions)

        actions_with_ids = mapper.get_all_actions_with_ids()

        assert len(actions_with_ids) == 5

        # Check structure of first action
        first = actions_with_ids[0]
        assert "action_id" in first
        assert "description" in first
        assert "action_type" in first
        assert "details" in first

        # Find BUILD_SETTLEMENT action
        settlement_action = next(
            (a for a in actions_with_ids if "settlement" in a["action_id"]),
            None
        )
        assert settlement_action is not None
        assert settlement_action["action_id"] == "build_settlement_42"
        assert settlement_action["action_type"] == "BUILD_SETTLEMENT"
        assert settlement_action["details"]["color"] == "RED"
        assert settlement_action["details"]["value"] == "42"

    def test_duplicate_action_ids(self):
        """Test handling of duplicate action IDs."""
        actions = []

        # Create two identical actions (same type and value)
        for i in range(2):
            action = Mock()
            action.action_type = Mock()
            action.action_type.__str__ = lambda self: "ActionType.BUILD_SETTLEMENT"
            action.color = "RED"
            action.value = 42
            actions.append(action)

        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions(actions)

        action_ids = mapper.get_all_action_ids()

        # Should have 2 unique IDs (second one gets index suffix)
        assert len(action_ids) == 2
        assert "build_settlement_42" in action_ids
        assert "build_settlement_42_1" in action_ids

    def test_empty_actions_list(self):
        """Test with empty actions list."""
        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions([])

        assert len(mapper.get_all_action_ids()) == 0
        assert mapper.get_action("any_id") is None
        assert mapper.is_valid_action_id("any_id") is False

    def test_bidirectional_mapping(self, mock_actions):
        """Test that mapping works in both directions."""
        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions(mock_actions)

        for action in mock_actions:
            # Get ID from action
            action_id = mapper.get_action_id(action)
            assert action_id is not None

            # Get action back from ID
            retrieved_action = mapper.get_action(action_id)
            assert retrieved_action == action

    def test_context_reset(self, mock_actions):
        """Test that setting new actions clears old mappings."""
        mapper = ActionMapper(use_descriptive_ids=True)

        # Set first batch of actions
        mapper.set_actions(mock_actions)
        first_ids = set(mapper.get_all_action_ids())

        # Create new actions
        new_actions = []
        action = Mock()
        action.action_type = Mock()
        action.action_type.__str__ = lambda self: "ActionType.ROLL"
        action.color = "BLUE"
        action.value = None
        new_actions.append(action)

        # Set new actions
        mapper.set_actions(new_actions)
        new_ids = set(mapper.get_all_action_ids())

        # Should be completely different
        assert len(new_ids) == 1
        assert "roll" in new_ids
        assert new_ids != first_ids

        # Old IDs should no longer be valid
        assert mapper.is_valid_action_id("build_settlement_42") is False

    def test_safe_action_str(self, mock_actions):
        """Test safe string conversion of actions."""
        mapper = ActionMapper(use_descriptive_ids=True)

        # Normal case - Mock's default str() just returns its class name
        result = mapper._safe_action_str(mock_actions[0])
        assert "Mock" in result or "action" in result.lower()

        # Test with object that has proper string representation
        class FakeAction:
            def __str__(self):
                return "BUILD_SETTLEMENT at node 42"

        fake_action = FakeAction()
        result = mapper._safe_action_str(fake_action)
        assert result == "BUILD_SETTLEMENT at node 42"

    def test_action_type_extraction(self, mock_actions):
        """Test action type extraction."""
        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions(mock_actions)

        # Check that action types are properly extracted
        action_type = mapper._get_action_type(mock_actions[0])
        assert action_type == "BUILD_SETTLEMENT"

        action_type = mapper._get_action_type(mock_actions[3])
        assert action_type == "END_TURN"

    def test_action_without_action_type_attribute(self):
        """Test handling actions without action_type attribute."""
        action = Mock(spec=[])  # No attributes
        action.color = "RED"
        action.value = 10

        mapper = ActionMapper(use_descriptive_ids=True)
        mapper.set_actions([action])

        # Should fall back to class name
        action_ids = mapper.get_all_action_ids()
        assert len(action_ids) == 1
        # ID should contain "mock" (from Mock class name)
        assert "mock" in action_ids[0].lower() or "action_0" in action_ids[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
