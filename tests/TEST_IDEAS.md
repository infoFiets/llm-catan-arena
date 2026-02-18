# Test Ideas for Parallel Tournament Execution

## Critical Issues Found

1. **Elo race condition** - Multiple games writing to same `elo_ratings.json` overwrite each other
2. **Session ID collision** - Games starting in same second get same ID, overwrite files

---

## Tests to Write

### 1. Elo System Concurrency Tests (`tests/test_elo_concurrency.py`)

```python
# Test: Parallel Elo updates don't lose data
def test_parallel_elo_updates():
    """Simulate 50 games updating Elo simultaneously."""
    # - Create 50 threads, each updating Elo with a fake game result
    # - Verify all 50 games appear in history
    # - Verify no data is lost/overwritten

# Test: File locking works
def test_elo_file_locking():
    """Verify file locking prevents race conditions."""
    # - Start multiple processes writing to same Elo file
    # - Verify final file has all entries merged

# Test: Elo merge logic
def test_elo_merge_on_save():
    """Verify save merges with current file state."""
    # - Load Elo, add game A
    # - Separately load Elo, add game B
    # - Save both
    # - Verify both games A and B are in final file
```

### 2. Session ID Uniqueness Tests (`tests/test_session_id.py`)

```python
# Test: Session IDs are unique even at millisecond scale
def test_session_id_uniqueness():
    """Multiple sessions started simultaneously have unique IDs."""
    # - Start 100 sessions in a loop (no sleep)
    # - Verify all session_ids are unique

# Test: Session files don't overwrite
def test_parallel_session_files():
    """Parallel games create separate files."""
    # - Start 10 game sessions simultaneously (threads)
    # - Verify 10 separate files are created
```

### 3. Tournament Batch Tests (`tests/test_batch_execution.py`)

```python
# Test: Batch completion tracking
def test_batch_tracks_all_games():
    """Batch correctly reports completed vs failed games."""
    # - Run batch with mock games (some succeed, some fail)
    # - Verify completion counts are accurate

# Test: Batch parallel execution
def test_batch_parallel_isolation():
    """Parallel games don't interfere with each other."""
    # - Run 5 games in parallel with mocked game runner
    # - Verify each game has independent state
    # - Verify all 5 results are saved

# Test: Matchup generation considers history
def test_matchup_considers_history():
    """Matchup generator prioritizes underplayed models."""
    # - Create fake history with some models having more games
    # - Generate matchups
    # - Verify underplayed models appear more frequently
```

### 4. Game File Integrity Tests (`tests/test_game_file_integrity.py`)

```python
# Test: Game files are complete
def test_game_file_has_required_fields():
    """Game files have all required fields."""
    # - Run a mock game
    # - Verify file has: players, final_scores, winner, moves, etc.

# Test: Game files survive interruption
def test_game_file_on_sigint():
    """Game file is saved correctly when game is interrupted."""
    # - Start game, send SIGINT mid-game
    # - Verify file exists and has partial results
```

### 5. End-to-End Integration Tests (`tests/test_integration.py`)

```python
# Test: Full tournament flow
def test_mini_tournament():
    """Run small tournament with 4 mock models, verify results."""
    # - Create 4 mock/stub players that return deterministic results
    # - Run 5 games
    # - Verify all games saved to files
    # - Verify Elo ratings updated for all 4 models
    # - Verify statistics are accurate

# Test: Recovery from partial failure
def test_tournament_recovery():
    """Tournament can recover from partial batch failure."""
    # - Run batch where some games fail
    # - Verify successful games are saved
    # - Verify failed games don't corrupt data
```

### 6. Mock/Stub Infrastructure Needed

```python
# MockLLMClient - Returns deterministic responses
class MockLLMClient:
    def __init__(self, responses: List[str]):
        self.responses = responses
        self.call_index = 0

    def query(self, prompt):
        response = self.responses[self.call_index % len(self.responses)]
        self.call_index += 1
        return response, 0.001, 100  # response, cost, tokens

# MockGameRunner - Simulates game completion without API calls
class MockGameRunner:
    def run_game(self, players):
        # Return deterministic results based on player names
        scores = {p: hash(p) % 10 for p in players}
        winner = max(scores, key=scores.get)
        return {"winner": winner, "scores": scores}

# StubCatanatronGame - Provides canned game states
class StubCatanatronGame:
    def __init__(self, scripted_turns):
        self.turns = scripted_turns
        # ...
```

---

## Priority Order

1. **HIGH**: `test_parallel_elo_updates` - Most critical, caused data loss
2. **HIGH**: `test_session_id_uniqueness` - Caused file overwrites
3. **MEDIUM**: `test_batch_parallel_isolation` - Verify batch works correctly
4. **MEDIUM**: `test_mini_tournament` - End-to-end validation
5. **LOW**: Other granular tests

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_elo_concurrency.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```
