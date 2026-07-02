import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock

from src.config import load_config
from src.filters import _is_file_included, _get_ignore_config, GitIgnoreFilter
from src.merger import merge_files
from src.gui import MergeApp

# Fixture to provide a standard configuration for tests


@pytest.fixture
def base_config():
    return {
        "output_file": "test_out.txt",
        "output_dir": "test_dir",
        "ignored_dirs": ["node_modules", ".git"],
        "ignored_files": ["package-lock.json"],
        "ignored_extensions": [".png", ".jpg"],
        "use_gitignore": True
    }

# Configuration Tests


def test_load_config_default(mocker):
    # Mock os.path.exists to simulate no config.json file
    mocker.patch("os.path.exists", return_value=False)
    config = load_config("non_existent.json")
    assert config["output_file"] == "Mono.txt"
    assert "node_modules" in config["ignored_dirs"]


def test_load_config_with_file(mocker):
    # Mock a custom config file
    mock_data = json.dumps({"output_file": "custom.txt"})
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data=mock_data))

    config = load_config("config.json")
    assert config["output_file"] == "custom.txt"
    # Ensure it still has default values for other keys
    assert ".git" in config["ignored_dirs"]

# Filtering Logic Tests


@pytest.mark.parametrize("filename, ext, expected", [
    ("script.py", ".py", True),
    ("image.png", None, False),       # Ignored extension
    ("style.css", None, True),
    ("style.css", ".css", True),       # Target extension specified
    ("package-lock.json", None, False)  # Ignored file
])
def test_is_file_included(filename, ext, expected):
    ignore_set = {"node_modules"}
    ignored_ext_set = {".png", ".jpg"}
    ignored_files = {"package-lock.json"}

    result = _is_file_included(
        filename, "root", "root", ext,
        ignore_set, ignored_ext_set, ignored_files
    )
    assert result == expected

# GitIgnore Filter Tests


def test_gitignore_filter(tmp_path):
    # Create a dummy .gitignore
    d = tmp_path / "project"
    d.mkdir()
    gitignore = d / ".gitignore"
    gitignore.write_text("*.log\n/temp/")

    filter_obj = GitIgnoreFilter(str(d))

    # Check if .log files are ignored
    assert filter_obj.is_ignored(str(d / "test.log"), False) is True
    # Check if other files are allowed
    assert filter_obj.is_ignored(str(d / "main.py"), False) is False
    # Check directory ignore
    assert filter_obj.is_ignored(str(d / "temp"), True) is True

# Core Logic Tests


def test_merge_files_execution(tmp_path, mocker):
    # Setup source directory
    src_dir = tmp_path / "src_dir"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("Hello")
    (src_dir / "file2.txt").write_text("World")

    out_dir = tmp_path / "out"

    # Mock config to point to our temp output directory
    mock_conf = {
        "output_file": "merged.txt",
        "output_dir": str(out_dir),
        "ignored_dirs": [],
        "ignored_extensions": [],
        "ignored_files": []
    }
    mocker.patch("src.merger.load_config", return_value=mock_conf)

    # Run merge
    merge_files(str(src_dir), output_file="merged.txt", use_gitignore=False)

    # Verify output
    merged_file = out_dir / "merged.txt"
    assert merged_file.exists()
    content = merged_file.read_text()
    assert "file1.txt" in content
    assert "Hello" in content
    assert "World" in content


def test_collect_files(tmp_path):
    from src.collector import collect_files
    d = tmp_path / "collect_project"
    d.mkdir()
    (d / "fileA.txt").write_text("A")
    (d / "fileB.txt").write_text("B")
    sub = d / "subdir"
    sub.mkdir()
    (sub / "fileC.txt").write_text("C")

    tasks_flat = collect_files(str(d), extension=None, recursive=False, ignore_set=set(), ignored_ext_tuple=(), ignored_files=set())
    assert len(tasks_flat) == 2
    assert tasks_flat[0].display_name == "fileA.txt"
    assert tasks_flat[1].display_name == "fileB.txt"

    tasks_rec = collect_files(str(d), extension=None, recursive=True, ignore_set=set(), ignored_ext_tuple=(), ignored_files=set())
    assert len(tasks_rec) == 3
    assert tasks_rec[0].display_name == "fileA.txt"
    assert tasks_rec[1].display_name == "fileB.txt"
    assert tasks_rec[2].display_name.replace("\\", "/") == "subdir/fileC.txt"


def test_gitignore_filter_regex_cache(tmp_path):
    from src.filters import GitIgnoreFilter
    d = tmp_path / "git_cache"
    d.mkdir()
    (d / ".gitignore").write_text("*.log\ntemp/")

    f_obj = GitIgnoreFilter(str(d))
    rules = f_obj._load_rules(str(d))
    assert len(rules) == 2
    negate, rule_is_dir, rule_type, r1, r2 = rules[0]
    assert negate is False
    assert rule_is_dir is False
    assert rule_type == 'name'

    rules_cached = f_obj._load_rules(str(d))
    assert rules is rules_cached


def test_parallel_merge_equivalence(tmp_path, mocker):
    from src.merger import merge_files

    src_dir = tmp_path / "equivalence"
    src_dir.mkdir()
    for i in range(10):
        (src_dir / f"file{i}.txt").write_text(f"Content {i}")

    out_dir = tmp_path / "out_eq"
    out_dir.mkdir()

    mock_conf_par = {
        "output_file": "merged_par.txt",
        "output_dir": str(out_dir),
        "ignored_dirs": [],
        "ignored_extensions": [],
        "ignored_files": [],
        "performance": {
            "min_tasks_for_parallel": 5,
            "max_workers": 2,
            "large_file_threshold_mb": 1
        }
    }
    mocker.patch("src.merger.load_config", return_value=mock_conf_par)

    merge_files(str(src_dir), output_file="merged_par.txt", use_gitignore=False)

    mock_conf_seq = {
        "output_file": "merged_seq.txt",
        "output_dir": str(out_dir),
        "ignored_dirs": [],
        "ignored_extensions": [],
        "ignored_files": [],
        "performance": {
            "min_tasks_for_parallel": 50,
            "max_workers": 2,
            "large_file_threshold_mb": 1
        }
    }
    mocker.patch("src.merger.load_config", return_value=mock_conf_seq)

    merge_files(str(src_dir), output_file="merged_seq.txt", use_gitignore=False)

    out_par = out_dir / "merged_par.txt"
    out_seq = out_dir / "merged_seq.txt"

    assert out_par.read_text() == out_seq.read_text()


def test_atomic_output_and_cancellation(tmp_path, mocker):
    import threading
    from src.merger import merge_files

    src_dir = tmp_path / "cancel_dir"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("Hello")

    out_dir = tmp_path / "out_cancel"
    out_dir.mkdir()

    cancel_ev = threading.Event()
    cancel_ev.set()

    mock_conf = {
        "output_file": "merged_cancel.txt",
        "output_dir": str(out_dir),
        "ignored_dirs": [],
        "ignored_extensions": [],
        "ignored_files": []
    }
    mocker.patch("src.merger.load_config", return_value=mock_conf)

    merge_files(str(src_dir), output_file="merged_cancel.txt", cancel_event=cancel_ev, use_gitignore=False)

    out_file = out_dir / "merged_cancel.txt"
    assert not out_file.exists()

    tmp_files = list(out_dir.glob("*.tmp"))
    assert len(tmp_files) == 0
