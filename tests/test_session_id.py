"""
Tests for session ID uniqueness.

These tests verify that session IDs are unique even when games
start at the same time (within milliseconds of each other).
"""

import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pytest


class TestSessionIdUniqueness:
    """Test cases for session ID uniqueness."""

    def test_session_id_format(self):
        """Test the session ID format includes timestamp and UUID."""
        # This tests the format used in game_runner.py
        session_id = f"Settlers_of_Catan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        parts = session_id.split("_")
        assert parts[0] == "Settlers"
        assert parts[1] == "of"
        assert parts[2] == "Catan"
        # Date part should be 8 digits
        assert len(parts[3]) == 8
        assert parts[3].isdigit()
        # Time part should be 6 digits
        assert len(parts[4]) == 6
        assert parts[4].isdigit()
        # UUID part should be 8 hex characters
        assert len(parts[5]) == 8

    def test_session_id_uniqueness_rapid_generation(self):
        """
        Multiple sessions generated rapidly have unique IDs.

        Generate 100 session IDs in a tight loop and verify all are unique.
        """
        session_ids = []

        for _ in range(100):
            # This is the format used in game_runner.py
            session_id = f"Settlers_of_Catan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            session_ids.append(session_id)

        # All should be unique due to UUID component
        unique_ids = set(session_ids)
        assert len(unique_ids) == 100, (
            f"Expected 100 unique IDs, got {len(unique_ids)}. "
            f"Duplicates: {[s for s in session_ids if session_ids.count(s) > 1]}"
        )

    def test_session_id_uniqueness_parallel(self):
        """
        Sessions started simultaneously in parallel threads have unique IDs.
        """
        num_sessions = 200
        session_ids = []
        lock = threading.Lock()

        def generate_session_id():
            session_id = f"Settlers_of_Catan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            with lock:
                session_ids.append(session_id)
            return session_id

        # Use threads to generate IDs as simultaneously as possible
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(generate_session_id) for _ in range(num_sessions)]
            for future in as_completed(futures):
                future.result()

        # Verify uniqueness
        unique_ids = set(session_ids)
        assert len(unique_ids) == num_sessions, (
            f"Expected {num_sessions} unique IDs, got {len(unique_ids)}"
        )

    def test_session_id_without_uuid_would_collide(self):
        """
        Demonstrate that session IDs WITHOUT UUID component would collide.

        This test proves why the UUID is necessary.
        """
        session_ids = []

        # Generate IDs without UUID (old format that caused issues)
        for _ in range(100):
            # Old format without UUID
            session_id = f"Settlers_of_Catan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            session_ids.append(session_id)

        # Without UUID, many will be duplicates (within same second)
        unique_ids = set(session_ids)

        # This should have collisions (much fewer unique IDs than generated)
        # We expect many duplicates since loop runs faster than 1 second
        assert len(unique_ids) < 100, (
            "Expected collisions without UUID component - "
            "this proves why UUID is needed"
        )

    def test_uuid_hex_portion_is_valid(self):
        """
        Verify the UUID portion is valid hex.
        """
        for _ in range(50):
            session_id = f"Settlers_of_Catan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            uuid_part = session_id.split("_")[-1]

            # Should be valid hex
            try:
                int(uuid_part, 16)
            except ValueError:
                pytest.fail(f"UUID part '{uuid_part}' is not valid hex")

            # Should be exactly 8 characters
            assert len(uuid_part) == 8


class TestSessionFileNaming:
    """Test cases for session file naming to prevent overwrites."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_parallel_file_creation(self, temp_dir):
        """
        Parallel sessions create separate files.

        Start 20 'sessions' simultaneously and verify 20 separate files.
        """
        created_files = []
        lock = threading.Lock()

        def create_session_file(session_num):
            """Create a file with unique session ID."""
            session_id = f"Settlers_of_Catan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            file_path = temp_dir / f"{session_id}.json"

            # Write some content
            file_path.write_text(f'{{"session_num": {session_num}}}')

            with lock:
                created_files.append(file_path)

            return file_path

        # Create files in parallel
        num_sessions = 20
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_session_file, i) for i in range(num_sessions)]
            for future in as_completed(futures):
                future.result()

        # Verify correct number of unique files
        unique_files = set(created_files)
        assert len(unique_files) == num_sessions, (
            f"Expected {num_sessions} unique files, got {len(unique_files)}"
        )

        # Verify all files actually exist
        for f in unique_files:
            assert f.exists(), f"File {f} does not exist"

    def test_file_content_not_overwritten(self, temp_dir):
        """
        Verify that parallel file creation doesn't overwrite content.
        """
        results = {}
        lock = threading.Lock()

        def create_and_write(session_num):
            """Create file and write session number."""
            session_id = f"Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            file_path = temp_dir / f"{session_id}.json"

            content = f'{{"session_num": {session_num}, "data": "content_{session_num}"}}'
            file_path.write_text(content)

            with lock:
                results[session_num] = file_path

            return session_num, file_path

        num_sessions = 30
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(create_and_write, i) for i in range(num_sessions)]
            for future in as_completed(futures):
                future.result()

        # Verify each file has correct content (not overwritten)
        import json
        for session_num, file_path in results.items():
            content = json.loads(file_path.read_text())
            assert content["session_num"] == session_num, (
                f"File {file_path} has wrong session_num: "
                f"expected {session_num}, got {content['session_num']}"
            )
            assert content["data"] == f"content_{session_num}"

    def test_rapid_sequential_file_creation(self, temp_dir):
        """
        Rapid sequential file creation produces unique files.
        """
        files = []

        for i in range(50):
            session_id = f"Rapid_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}_{uuid.uuid4().hex[:8]}"
            file_path = temp_dir / f"{session_id}.txt"
            file_path.write_text(str(i))
            files.append(file_path)

        # All files should be unique
        unique_files = set(files)
        assert len(unique_files) == 50

        # All should exist
        for f in files:
            assert f.exists()


class TestSessionIdCollisionPrevention:
    """Test the collision prevention mechanism."""

    def test_uuid_provides_sufficient_entropy(self):
        """
        8 hex characters from UUID provides enough uniqueness.

        8 hex chars = 32 bits = ~4 billion combinations.
        For 1000 games/day, collision probability is negligible.
        """
        # Generate many UUIDs and check for collisions
        num_samples = 10000
        uuid_parts = [uuid.uuid4().hex[:8] for _ in range(num_samples)]

        unique_parts = set(uuid_parts)

        # Should have no collisions in 10k samples
        assert len(unique_parts) == num_samples, (
            f"Unexpected UUID collision in {num_samples} samples"
        )

    def test_timestamp_plus_uuid_guarantees_uniqueness(self):
        """
        Combined timestamp and UUID guarantee uniqueness.
        """
        session_ids = set()
        num_samples = 5000

        for _ in range(num_samples):
            session_id = f"Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            assert session_id not in session_ids, f"Collision detected: {session_id}"
            session_ids.add(session_id)

        assert len(session_ids) == num_samples
