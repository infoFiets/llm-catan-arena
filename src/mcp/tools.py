"""
MCP Tool Definitions

Defines the three core tools for Catan game interaction.
These definitions are compatible with Anthropic's tool calling format.
"""

def get_game_state_tool() -> dict:
    """
    Define get_game_state tool.

    Returns current game state from player's perspective.
    """
    return {
        "name": "get_game_state",
        "description": (
            "Get the current game state in Settlers of Catan. "
            "Returns your resources, buildings, victory points, and opponent information. "
            "Use this to understand the current situation before making decisions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "include_board": {
                    "type": "boolean",
                    "description": "Include detailed board state (settlements, cities, roads). This is expensive, only request if needed for spatial decisions.",
                    "default": False
                },
                "include_history": {
                    "type": "boolean",
                    "description": "Include recent game actions for context.",
                    "default": False
                }
            }
        }
    }


def get_valid_actions_tool() -> dict:
    """
    Define get_valid_actions tool.

    Returns list of valid actions with IDs.
    """
    return {
        "name": "get_valid_actions",
        "description": (
            "Get all valid actions you can take right now. "
            "Returns a list of action objects with unique action_ids and descriptions. "
            "Use this to see what moves are available before selecting one. "
            "Each action includes its type, description, and any relevant details."
        ),
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }


def select_action_tool() -> dict:
    """
    Define select_action tool.

    Marks an action as selected (doesn't execute it).
    """
    return {
        "name": "select_action",
        "description": (
            "Select an action to take by providing its action_id. "
            "This marks your choice but does NOT execute it - the game engine will execute it after you make your selection. "
            "You must call this with a valid action_id from get_valid_actions. "
            "This is the final step in your turn - after calling this, your turn will proceed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action_id": {
                    "type": "string",
                    "description": "The action_id of the action you want to take. Get valid IDs from get_valid_actions."
                }
            },
            "required": ["action_id"]
        }
    }


def get_all_tools() -> list:
    """Get all tool definitions as a list."""
    return [
        get_game_state_tool(),
        get_valid_actions_tool(),
        select_action_tool()
    ]
