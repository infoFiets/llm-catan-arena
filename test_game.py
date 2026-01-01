#!/usr/bin/env python3
"""Quick test to verify game runs with random players."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.players import RandomPlayer
from catanatron.game import Game

print("Testing Catan game with random players...")

# Create 4 random players
players = [
    RandomPlayer("RED"),
    RandomPlayer("BLUE"),
    RandomPlayer("WHITE"),
    RandomPlayer("ORANGE")
]

print(f"Players: {players}")

# Run a game
print("Starting game...")
game = Game(players)
game.play()

print("Game completed!")

# Get winner
winner_color = game.winning_color()
print(f"Winner color: {winner_color}")

# Get scores
for player in players:
    player_index = game.state.color_to_index[player.color]
    vp = game.state.player_state.get(f"P{player_index}_ACTUAL_VICTORY_POINTS", 0)
    print(f"  {player.color}: {vp} VP")

print("\nTest successful!")
