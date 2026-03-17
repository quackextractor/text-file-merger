import os
import json
import pytest
from merge_texts import load_config, merge_files


def test_load_config_default(tmp_path):
    # Test loading default config when file doesn't exist
    config_path = str(tmp_path / "nonexistent.json")
    config = load_config(config_path)
    assert config["output_file"] == "Mono.txt"
    assert config["output_dir"] == "out"
    assert "node_modules" in config["ignored_dirs"]


def test_load_config_custom(tmp_path):
    # Test loading custom config from file
    config_data = {
        "output_file": "Custom.txt",
        "output_dir": "custom_out",
        "ignored_dirs": ["test_dir"]
    }
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    config = load_config(str(config_path))
    assert config["output_file"] == "Custom.txt"
    assert config["output_dir"] == "custom_out"
    assert "test_dir" in config["ignored_dirs"]


def test_merge_logic(tmp_path, mocker):
    # Setup test directory
    test_dir = tmp_path / "test_merge"
    test_dir.mkdir()
    (test_dir / "a.txt").write_text("A")
    (test_dir / "b.log").write_text("B")

    # Setup out directory
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # Mock load_config to use our temporary out_dir
    mocker.patch("merge_texts.load_config", return_value={
        "output_file": "final.txt",
        "output_dir": str(out_dir),
        "ignored_dirs": [],
        "ignored_files": [],
        "ignored_extensions": [".log"],
        "skip_css_if_no_ext": True
    })

    merge_files(str(test_dir), output_file="final.txt")

    final_path = out_dir / "final.txt"
    assert final_path.exists()
    content = final_path.read_text()
    assert "a.txt" in content
    assert "A" in content
    assert "b.log" not in content  # Ignored extension
