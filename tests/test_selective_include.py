import os
import pytest
import subprocess
import sys
from unittest.mock import patch, MagicMock
from src.collector import collect_files
from src.merger import merge_files


def test_collect_files_with_include_list_recursive(tmp_path):
    # Setup temp directory structure
    d = tmp_path / "include_test"
    d.mkdir()
    (d / "fileA.txt").write_text("A")
    (d / "fileB.txt").write_text("B")
    sub = d / "subdir"
    sub.mkdir()
    (sub / "fileC.txt").write_text("C")

    # Recursive collection only including fileA and subdir/fileC
    include_list = ["fileA.txt", "subdir/fileC.txt"]
    tasks = collect_files(
        directory=str(d),
        extension=None,
        recursive=True,
        ignore_set=set(),
        ignored_ext_tuple=(),
        ignored_files=set(),
        include_list=include_list
    )

    assert len(tasks) == 2
    names = [t.display_name for t in tasks]
    assert "fileA.txt" in names
    assert "subdir/fileC.txt" in names
    assert "fileB.txt" not in names


def test_collect_files_with_include_list_flat(tmp_path):
    d = tmp_path / "include_test_flat"
    d.mkdir()
    (d / "fileA.txt").write_text("A")
    (d / "fileB.txt").write_text("B")

    # Flat collection only including fileB
    include_list = ["fileB.txt"]
    tasks = collect_files(
        directory=str(d),
        extension=None,
        recursive=False,
        ignore_set=set(),
        ignored_ext_tuple=(),
        ignored_files=set(),
        include_list=include_list
    )

    assert len(tasks) == 1
    assert tasks[0].display_name == "fileB.txt"


def test_merge_files_with_include_list(tmp_path, mocker):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("One")
    (src_dir / "file2.txt").write_text("Two")
    (src_dir / "file3.txt").write_text("Three")

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

    # Run merge only including file1 and file3
    res = merge_files(
        directory=str(src_dir),
        output_file="merged.txt",
        use_gitignore=False,
        include_list=["file1.txt", "file3.txt"]
    )

    assert res is not None
    assert res["file_count"] == 2

    # Verify output contents
    merged_file = out_dir / "merged.txt"
    assert merged_file.exists()
    content = merged_file.read_text()
    assert "file1.txt" in content
    assert "One" in content
    assert "file3.txt" in content
    assert "Three" in content
    assert "file2.txt" not in content
    assert "Two" not in content


def test_cli_execution_with_include(tmp_path):
    src_dir = tmp_path / "cli_src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("ContentA")
    (src_dir / "b.txt").write_text("ContentB")

    out_dir = tmp_path / "cli_out"
    out_dir.mkdir()

    # We must run main.py as a subprocess using the current python executable
    cmd = [
        sys.executable,
        "main.py",
        str(src_dir),
        "-o",
        str(out_dir / "merged.txt"),
        "--include",
        "a.txt",
        "--no-tree"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0

    # Wait, where does CLI save the merged output?
    # By default, merge_files saves it in `out/` relative to directory or config,
    # but since we passed an absolute output path, out_dir/merged.txt might be inside `out/` directory defined by config.
    # Let's see: merge_files constructs out_path using:
    # `out_path = os.path.join(out_dir, os.path.basename(raw_out_path))`
    # So the filename is `merged.txt` inside the config's `output_dir` (which defaults to `out`).
    # Wait! Let's check `out/merged.txt` or whatever was printed.
    # Let's inspect stdout of the subprocess to verify output.
    assert "Files merged: 1" in result.stdout
