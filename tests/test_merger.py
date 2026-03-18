import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock
from merge_texts import (
    load_config,
    _is_file_included,
    _get_ignore_config,
    GitIgnoreFilter,
    merge_files,
    MergeApp
)

# Fixture to provide a standard configuration for tests


@pytest.fixture
def base_config():
    return {
        "output_file": "test_out.txt",
        "output_dir": "test_dir",
        "ignored_dirs": ["node_modules", ".git"],
        "ignored_files": ["package-lock.json"],
        "ignored_extensions": [".png", ".jpg"],
        "skip_css_if_no_ext": True,
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


@pytest.mark.parametrize("filename, ext, skip_css, expected", [
    ("script.py", ".py", False, True),
    ("image.png", None, False, False),       # Ignored extension
    ("style.css", None, True, False),        # skip_css_if_no_ext is True
    ("style.css", ".css", True, True),       # Target extension specified
    ("package-lock.json", None, False, False)  # Ignored file
])
def test_is_file_included(filename, ext, skip_css, expected):
    ignore_set = {"node_modules"}
    ignored_ext_set = {".png", ".jpg"}
    ignored_files = {"package-lock.json"}

    result = _is_file_included(
        filename, "root", "root", ext,
        ignore_set, ignored_ext_set, ignored_files, skip_css
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
    src = tmp_path / "src"
    src.mkdir()
    (src / "file1.txt").write_text("Hello")
    (src / "file2.txt").write_text("World")

    out_dir = tmp_path / "out"

    # Mock config to point to our temp output directory
    mock_conf = {
        "output_file": "merged.txt",
        "output_dir": str(out_dir),
        "ignored_dirs": [],
        "ignored_extensions": [],
        "ignored_files": [],
        "skip_css_if_no_ext": False
    }
    mocker.patch("merge_texts.load_config", return_value=mock_conf)

    # Run merge
    merge_files(str(src), output_file="merged.txt", use_gitignore=False)

    # Verify output
    merged_file = out_dir / "merged.txt"
    assert merged_file.exists()
    content = merged_file.read_text()
    assert "file1.txt" in content
    assert "Hello" in content
    assert "World" in content

# GUI Initialization Test


def test_gui_init(mocker):
    # Mocking tkinter and customtkinter to prevent windows from popping up
    mocker.patch("customtkinter.CTk", return_value=MagicMock())
    mocker.patch("customtkinter.CTkFrame", return_value=MagicMock())
    mocker.patch("customtkinter.CTkLabel", return_value=MagicMock())
    mocker.patch("customtkinter.CTkEntry", return_value=MagicMock())
    mocker.patch("customtkinter.CTkComboBox", return_value=MagicMock())
    mocker.patch("customtkinter.CTkCheckBox", return_value=MagicMock())
    mocker.patch("customtkinter.CTkButton", return_value=MagicMock())
    mocker.patch("customtkinter.CTkTextbox", return_value=MagicMock())
    mocker.patch("customtkinter.CTkProgressBar", return_value=MagicMock())

    root = MagicMock()
    app = MergeApp(root)
    assert app.config is not None
