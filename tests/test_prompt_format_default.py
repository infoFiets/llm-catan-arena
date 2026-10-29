"""prompt_format defaults to "toon" everywhere (to-do 196); the phase-1 comparison still runs all three."""
import importlib.util
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.game_runner import CatanGameRunner
from src.prompt_builder import CatanPromptBuilder


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _default(fn):
    return inspect.signature(fn).parameters["prompt_format"].default


def test_prompt_builder_default_is_toon():
    assert CatanPromptBuilder().prompt_format == "toon"


def test_game_runner_default_is_toon():
    assert _default(CatanGameRunner.__init__) == "toon"


def test_player_defaults_are_toon():
    from src.players.text_based import base_player, claude_player, gemini_player, gpt_player

    for mod in (base_player, claude_player, gemini_player, gpt_player):
        classes = [c for _, c in inspect.getmembers(mod, inspect.isclass) if c.__module__ == mod.__name__]
        assert classes, mod.__name__
        for cls in classes:
            if "prompt_format" in inspect.signature(cls.__init__).parameters:
                assert _default(cls.__init__) == "toon", cls


def test_run_tournament_defaults_and_choices():
    mod = _load_script("run_tournament")
    assert _default(mod.run_tournament) == "toon"
    assert _default(mod.run_single_game) == "toon"
    src = (ROOT / "scripts" / "run_tournament.py").read_text()
    assert "choices=['json', 'json-minified', 'toon']" in src
    assert "default='toon'" in src


def test_phase1_comparison_still_runs_all_three_formats():
    mod = _load_script("run_full_tournament")
    fmts = [e["format"] for e in mod.get_format_comparison_config()["experiments"]]
    assert sorted(fmts) == ["json", "json-minified", "toon"]


def test_experiment_format_falls_back_to_toon():
    src = (ROOT / "scripts" / "run_full_tournament.py").read_text()
    assert 'exp.get("format", "toon")' in src
