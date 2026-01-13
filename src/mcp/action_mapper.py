"""
Action ID Mapper

Generates stable, human-readable action IDs for MCP tools
and maintains bidirectional mapping to Catanatron Action objects.
"""

from typing import Dict, List, Any, Optional
import logging


class ActionMapper:
    """
    Maps between action IDs (strings) and Catanatron Action objects.

    Action IDs are generated as descriptive strings:
    - "build_settlement_node_42"
    - "build_road_edge_12"
    - "play_knight"
    - "end_turn"

    Maintains bidirectional mapping for current decision context.
    """

    def __init__(self, use_descriptive_ids: bool = True):
        """
        Initialize action mapper.

        Args:
            use_descriptive_ids: If True, generate descriptive IDs
        """
        self.use_descriptive_ids = use_descriptive_ids
        self.actions: List[Any] = []
        self.id_to_action: Dict[str, Any] = {}
        self.action_to_id: Dict[int, str] = {}  # Using id() for hash
        self.log = logging.getLogger("ActionMapper")

    def set_actions(self, actions: List[Any]):
        """
        Set current action list and generate IDs.

        Args:
            actions: List of Catanatron Action objects
        """
        self.actions = actions
        self.id_to_action = {}
        self.action_to_id = {}

        for i, action in enumerate(actions):
            action_id = self._generate_action_id(action, i)
            self.id_to_action[action_id] = action
            self.action_to_id[id(action)] = action_id

        self.log.debug(f"Mapped {len(actions)} actions")

    def _generate_action_id(self, action: Any, index: int) -> str:
        """
        Generate action ID.

        Args:
            action: Catanatron Action object
            index: Position in action list

        Returns:
            Action ID string
        """
        if self.use_descriptive_ids:
            return self._descriptive_action_id(action, index)
        else:
            return f"action_{index}"

    def _descriptive_action_id(self, action: Any, index: int) -> str:
        """
        Generate descriptive action ID from action properties.

        Examples:
        - "build_settlement_42"
        - "build_road_edge_12"
        - "play_knight"
        - "end_turn"
        """
        try:
            # Get action type
            if hasattr(action, 'action_type'):
                action_type = str(action.action_type)
                # Remove "ActionType." prefix if present
                if "." in action_type:
                    action_type = action_type.split(".")[-1]
            else:
                action_type = type(action).__name__

            action_type_clean = action_type.lower()

            # Build ID parts
            parts = [action_type_clean]

            # Add value if present
            if hasattr(action, 'value'):
                value = action.value
                if value is not None:
                    if isinstance(value, (int, float)):
                        parts.append(str(int(value)))
                    elif isinstance(value, str):
                        parts.append(value.lower())
                    elif isinstance(value, tuple):
                        parts.extend([str(v) for v in value])

            # Create ID
            action_id = "_".join(parts)

            # Add index suffix if ID already exists (for uniqueness)
            if action_id in self.id_to_action:
                action_id = f"{action_id}_{index}"

            return action_id

        except Exception as e:
            self.log.warning(f"Error generating descriptive ID: {e}")
            return f"action_{index}"

    def get_action(self, action_id: str) -> Optional[Any]:
        """
        Get Action object from action ID.

        Args:
            action_id: Action ID string

        Returns:
            Action object or None
        """
        return self.id_to_action.get(action_id)

    def get_action_id(self, action: Any) -> Optional[str]:
        """
        Get action ID from Action object.

        Args:
            action: Action object

        Returns:
            Action ID string or None
        """
        return self.action_to_id.get(id(action))

    def is_valid_action_id(self, action_id: str) -> bool:
        """Check if action ID is valid."""
        return action_id in self.id_to_action

    def get_all_action_ids(self) -> List[str]:
        """Get list of all valid action IDs."""
        return list(self.id_to_action.keys())

    def get_all_actions_with_ids(self) -> List[Dict[str, Any]]:
        """
        Get all actions with IDs and descriptions.

        Returns:
            List of dicts with action_id, description, and details
        """
        result = []
        for action_id, action in self.id_to_action.items():
            result.append({
                "action_id": action_id,
                "description": self._safe_action_str(action),
                "action_type": self._get_action_type(action),
                "details": self._get_action_details(action)
            })
        return result

    def _safe_action_str(self, action: Any) -> str:
        """Safely convert action to string."""
        try:
            # Try standard string conversion
            return str(action)
        except (AttributeError, TypeError):
            try:
                # Fallback to class name
                return type(action).__name__
            except:
                return "Action"

    def _get_action_type(self, action: Any) -> str:
        """Get action type as string."""
        if hasattr(action, 'action_type'):
            action_type = str(action.action_type)
            # Remove enum prefix
            if "." in action_type:
                return action_type.split(".")[-1]
            return action_type
        return type(action).__name__

    def _get_action_details(self, action: Any) -> Dict[str, Any]:
        """Extract action details as dict."""
        details = {}

        if hasattr(action, 'color'):
            details['color'] = str(action.color)

        if hasattr(action, 'value'):
            value = action.value
            if value is not None:
                details['value'] = str(value)

        return details
