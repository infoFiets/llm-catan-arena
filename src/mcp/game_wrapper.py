"""
Catanatron Game State Wrapper

Serializes Catanatron game state to JSON-compatible dictionaries
for MCP tool responses.
"""

from typing import Dict, Any, List
import logging


class CatanatronGameWrapper:
    """
    Wraps Catanatron game state for JSON serialization.

    Extracts and formats:
    - Player resources, buildings, dev cards
    - Victory points
    - Opponent information
    - Board state (optional, expensive)
    - Game history (optional)
    """

    def __init__(self, game, player_color: str):
        """
        Initialize wrapper.

        Args:
            game: Catanatron game instance
            player_color: Color of player viewing state
        """
        self.game = game
        self.player_color = player_color
        self.player_index = game.state.color_to_index[player_color]
        self.log = logging.getLogger(f"GameWrapper:{player_color}")

    def get_state(
        self,
        include_board: bool = False,
        include_history: bool = False
    ) -> Dict[str, Any]:
        """
        Get complete game state as JSON-serializable dict.

        Args:
            include_board: Include detailed board state (expensive)
            include_history: Include game history

        Returns:
            Dictionary with game state
        """
        state = {
            "game_id": getattr(self.game, 'id', 'unknown'),
            "turn_number": len(self.game.state.actions),
            "your_color": self.player_color,
            "your_state": self._get_player_state(self.player_index),
            "opponents": self._get_opponents_state(),
            "development_cards_remaining": self._get_dev_cards_remaining(),
        }

        if include_board:
            state["board"] = self._get_board_state()

        if include_history:
            state["recent_actions"] = self._get_recent_actions(limit=10)

        return state

    def _get_player_state(self, player_index: int) -> Dict[str, Any]:
        """Extract state for a single player."""
        prefix = f"P{player_index}_"
        ps = self.game.state.player_state

        return {
            "resources": {
                "wood": ps.get(f"{prefix}WOOD_IN_HAND", 0),
                "brick": ps.get(f"{prefix}BRICK_IN_HAND", 0),
                "sheep": ps.get(f"{prefix}SHEEP_IN_HAND", 0),
                "wheat": ps.get(f"{prefix}WHEAT_IN_HAND", 0),
                "ore": ps.get(f"{prefix}ORE_IN_HAND", 0)
            },
            "total_resources": sum([
                ps.get(f"{prefix}WOOD_IN_HAND", 0),
                ps.get(f"{prefix}BRICK_IN_HAND", 0),
                ps.get(f"{prefix}SHEEP_IN_HAND", 0),
                ps.get(f"{prefix}WHEAT_IN_HAND", 0),
                ps.get(f"{prefix}ORE_IN_HAND", 0)
            ]),
            "victory_points": ps.get(f"{prefix}ACTUAL_VICTORY_POINTS", 0),
            "public_victory_points": ps.get(f"{prefix}VICTORY_POINTS", 0),
            "buildings": {
                "settlements_built": 5 - ps.get(f"{prefix}SETTLEMENTS_AVAILABLE", 5),
                "cities_built": 4 - ps.get(f"{prefix}CITIES_AVAILABLE", 4),
                "roads_built": 15 - ps.get(f"{prefix}ROADS_AVAILABLE", 15),
                "settlements_available": ps.get(f"{prefix}SETTLEMENTS_AVAILABLE", 5),
                "cities_available": ps.get(f"{prefix}CITIES_AVAILABLE", 4),
                "roads_available": ps.get(f"{prefix}ROADS_AVAILABLE", 15)
            },
            "development_cards": self._get_dev_cards(prefix, ps),
            "has_longest_road": ps.get(f"{prefix}HAS_ROAD", False),
            "has_largest_army": ps.get(f"{prefix}HAS_ARMY", False),
            "knights_played": ps.get(f"{prefix}PLAYED_KNIGHT", 0),
            "longest_road_length": ps.get(f"{prefix}LONGEST_ROAD_LENGTH", 0)
        }

    def _get_dev_cards(self, prefix: str, ps: dict) -> Dict[str, int]:
        """Get development cards for player."""
        return {
            "knight": ps.get(f"{prefix}KNIGHT_IN_HAND", 0),
            "year_of_plenty": ps.get(f"{prefix}YEAR_OF_PLENTY_IN_HAND", 0),
            "monopoly": ps.get(f"{prefix}MONOPOLY_IN_HAND", 0),
            "road_building": ps.get(f"{prefix}ROAD_BUILDING_IN_HAND", 0),
            "victory_point": ps.get(f"{prefix}VICTORY_POINT_IN_HAND", 0),
            "total": sum([
                ps.get(f"{prefix}KNIGHT_IN_HAND", 0),
                ps.get(f"{prefix}YEAR_OF_PLENTY_IN_HAND", 0),
                ps.get(f"{prefix}MONOPOLY_IN_HAND", 0),
                ps.get(f"{prefix}ROAD_BUILDING_IN_HAND", 0),
                ps.get(f"{prefix}VICTORY_POINT_IN_HAND", 0)
            ])
        }

    def _get_opponents_state(self) -> List[Dict[str, Any]]:
        """Get simplified state for all opponents."""
        opponents = []
        for color, index in self.game.state.color_to_index.items():
            if color != self.player_color:
                prefix = f"P{index}_"
                ps = self.game.state.player_state

                opponents.append({
                    "color": color,
                    "victory_points": ps.get(f"{prefix}VICTORY_POINTS", 0),
                    "resource_count": sum([
                        ps.get(f"{prefix}WOOD_IN_HAND", 0),
                        ps.get(f"{prefix}BRICK_IN_HAND", 0),
                        ps.get(f"{prefix}SHEEP_IN_HAND", 0),
                        ps.get(f"{prefix}WHEAT_IN_HAND", 0),
                        ps.get(f"{prefix}ORE_IN_HAND", 0)
                    ]),
                    "development_card_count": sum([
                        ps.get(f"{prefix}KNIGHT_IN_HAND", 0),
                        ps.get(f"{prefix}YEAR_OF_PLENTY_IN_HAND", 0),
                        ps.get(f"{prefix}MONOPOLY_IN_HAND", 0),
                        ps.get(f"{prefix}ROAD_BUILDING_IN_HAND", 0),
                        ps.get(f"{prefix}VICTORY_POINT_IN_HAND", 0)
                    ]),
                    "buildings": {
                        "settlements": 5 - ps.get(f"{prefix}SETTLEMENTS_AVAILABLE", 5),
                        "cities": 4 - ps.get(f"{prefix}CITIES_AVAILABLE", 4),
                        "roads": 15 - ps.get(f"{prefix}ROADS_AVAILABLE", 15)
                    },
                    "has_longest_road": ps.get(f"{prefix}HAS_ROAD", False),
                    "has_largest_army": ps.get(f"{prefix}HAS_ARMY", False),
                    "knights_played": ps.get(f"{prefix}PLAYED_KNIGHT", 0)
                })

        return opponents

    def _get_dev_cards_remaining(self) -> int:
        """Get development cards remaining in deck."""
        if hasattr(self.game.state, 'development_deck'):
            return len(self.game.state.development_deck)
        return 0

    def _get_board_state(self) -> Dict[str, Any]:
        """
        Get detailed board state (expensive operation).

        Returns board graph, settlements, cities, roads.
        """
        board = self.game.state.board

        return {
            "settlements": self._serialize_buildings(board, "settlements"),
            "cities": self._serialize_buildings(board, "cities"),
            "roads": self._serialize_roads(board),
            "robber_tile": self._get_robber_position()
        }

    def _serialize_buildings(self, board, building_type: str) -> List[Dict[str, Any]]:
        """Serialize settlement or city placements."""
        buildings = []
        building_dict = getattr(board, building_type, {})

        for node_id, color in building_dict.items():
            buildings.append({
                "node_id": str(node_id),
                "color": color
            })
        return buildings

    def _serialize_roads(self, board) -> List[Dict[str, Any]]:
        """Serialize road placements."""
        roads = []
        road_dict = getattr(board, "roads", {})

        for edge_id, color in road_dict.items():
            roads.append({
                "edge_id": str(edge_id),
                "color": color
            })
        return roads

    def _get_robber_position(self):
        """Get robber tile position."""
        if hasattr(self.game.state.board, 'robber_tile'):
            return str(self.game.state.board.robber_tile)
        return None

    def _get_recent_actions(self, limit: int = 10) -> List[str]:
        """Get recent game actions."""
        actions = self.game.state.actions[-limit:] if hasattr(self.game.state, 'actions') else []
        return [self._safe_action_str(action) for action in actions]

    def _safe_action_str(self, action) -> str:
        """Safely convert action to string."""
        try:
            return str(action)
        except Exception:
            return "Action"
