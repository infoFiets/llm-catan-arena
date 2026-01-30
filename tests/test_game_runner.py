"""
Tests for game_runner module, particularly mixed-mode support.
"""

import pytest

from src.game_runner import parse_player_spec


class TestParsePlayerSpec:
    """Test cases for parse_player_spec function."""

    def test_plain_model_key(self):
        """Test parsing plain model key without mode suffix."""
        model_key, mode = parse_player_spec("claude")
        assert model_key == "claude"
        assert mode is None

    def test_mcp_suffix(self):
        """Test parsing model key with -mcp suffix."""
        model_key, mode = parse_player_spec("claude-mcp")
        assert model_key == "claude"
        assert mode == "mcp"

    def test_text_suffix(self):
        """Test parsing model key with -text suffix."""
        model_key, mode = parse_player_spec("claude-text")
        assert model_key == "claude"
        assert mode == "text"

    def test_gpt4_text(self):
        """Test parsing gpt4-text."""
        model_key, mode = parse_player_spec("gpt4-text")
        assert model_key == "gpt4"
        assert mode == "text"

    def test_gemini_text(self):
        """Test parsing gemini-text."""
        model_key, mode = parse_player_spec("gemini-text")
        assert model_key == "gemini"
        assert mode == "text"

    def test_haiku_mcp(self):
        """Test parsing haiku-mcp."""
        model_key, mode = parse_player_spec("haiku-mcp")
        assert model_key == "haiku"
        assert mode == "mcp"

    def test_model_with_hyphen_in_name(self):
        """Test that hyphens in model name don't break parsing."""
        # Only -mcp and -text are recognized as mode suffixes
        model_key, mode = parse_player_spec("gpt-4-turbo")
        assert model_key == "gpt-4-turbo"
        assert mode is None

    def test_model_key_preserved_case(self):
        """Test that model key case is preserved."""
        model_key, mode = parse_player_spec("Claude-mcp")
        assert model_key == "Claude"
        assert mode == "mcp"
