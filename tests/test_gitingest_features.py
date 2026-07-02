import os
import pytest
from unittest.mock import patch, MagicMock

from src.collector import FileTask
from src.token_utils import estimate_tokens
from src.tree_utils import generate_tree
from src.git_utils import clone_repo
from src.merger import merge_files


# 1. Token Counting Tests
def test_estimate_tokens_with_tiktoken():
    # Test text estimation with the actual tiktoken package
    text = "Hello world! This is a test."
    tokens = estimate_tokens(text)
    assert tokens > 0
    # Tiktoken count for this string should be around 8 tokens
    assert tokens < 15


@patch("tiktoken.encoding_for_model")
def test_estimate_tokens_fallback(mock_enc_model):
    # Force tiktoken failure to trigger character count fallback
    mock_enc_model.side_effect = Exception("Mock Error")

    text = "Hello world! This is a test."
    # 28 characters -> crude estimate len(text) // 4 = 7
    tokens = estimate_tokens(text)
    assert tokens == 7


# 2. Directory Tree Tests
def test_generate_tree():
    # Create mock FileTasks
    tasks = [
        FileTask(index=0, path="/foo/bar/a.txt", display_name="a.txt", size=10, kind="text"),
        FileTask(index=1, path="/foo/bar/dir/b.txt", display_name="dir/b.txt", size=20, kind="text"),
        FileTask(index=2, path="/foo/bar/dir/sub/c.txt", display_name="dir/sub/c.txt", size=30, kind="text"),
    ]
    tree_str = generate_tree(tasks, "/foo/bar")

    # Assert unicode tree formatting
    assert "├── a.txt" in tree_str
    assert "└── dir" in tree_str
    assert "    ├── b.txt" in tree_str
    assert "    └── sub" in tree_str
    assert "        └── c.txt" in tree_str


# 3. Git Repo Cloning Tests
@patch("git.Repo.clone_from")
def test_clone_repo_success(mock_clone):
    mock_repo = MagicMock()
    mock_clone.return_value = mock_repo

    target_dir = "/tmp/repo"
    # Basic clone
    clone_repo("https://github.com/octocat/Hello-World", target_dir)
    mock_clone.assert_called_once_with("https://github.com/octocat/Hello-World", target_dir, depth=1)


@patch("git.Repo.clone_from")
def test_clone_repo_with_token(mock_clone):
    mock_repo = MagicMock()
    mock_clone.return_value = mock_repo

    target_dir = "/tmp/repo"
    clone_repo("https://github.com/octocat/Hello-World", target_dir, token="my-token-123")
    # Verify token is inserted into URL
    mock_clone.assert_called_once_with("https://my-token-123@github.com/octocat/Hello-World", target_dir, depth=1)


@patch("git.Repo.clone_from")
def test_clone_repo_checkout_ref(mock_clone):
    mock_repo = MagicMock()
    mock_clone.return_value = mock_repo

    target_dir = "/tmp/repo"
    # Clone with branch (not commit hash)
    clone_repo("https://github.com/octocat/Hello-World", target_dir, branch="dev")
    mock_clone.assert_called_once_with("https://github.com/octocat/Hello-World", target_dir, depth=1, branch="dev")


@patch("git.Repo.clone_from")
def test_clone_repo_checkout_commit(mock_clone):
    mock_repo = MagicMock()
    mock_clone.return_value = mock_repo

    target_dir = "/tmp/repo"
    # commit hash (40-char hex)
    commit_hash = "abcdef0123456789abcdef0123456789abcdef01"
    clone_repo("https://github.com/octocat/Hello-World", target_dir, commit=commit_hash)
    # Clone default first, then checkout commit
    mock_clone.assert_called_once_with("https://github.com/octocat/Hello-World", target_dir, depth=1)
    mock_repo.git.checkout.assert_called_once_with(commit_hash)


# 4. Merger Integration Tests
def test_merge_files_with_tree(tmp_path, mocker):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("Hello")
    (src_dir / "file2.txt").write_text("World")

    out_dir = tmp_path / "out"

    mock_conf = {
        "output_file": "merged.txt",
        "output_dir": str(out_dir),
        "ignored_dirs": [],
        "ignored_extensions": [],
        "ignored_files": [],
        "include_tree": True
    }
    mocker.patch("src.merger.load_config", return_value=mock_conf)

    res = merge_files(str(src_dir), output_file="merged.txt", use_gitignore=False)

    assert res is not None
    assert res["file_count"] == 2
    assert res["token_count"] > 0

    merged_file = out_dir / "merged.txt"
    assert merged_file.exists()

    content = merged_file.read_text(encoding="utf-8")
    # Check that tree structure is prepended
    assert "Directory Structure:" in content
    assert "├── file1.txt" in content
    assert "└── file2.txt" in content
    assert "--- File Contents ---" in content
    assert "Hello" in content
    assert "World" in content


@patch("src.git_utils.clone_repo")
def test_merge_files_git_integration(mock_clone, tmp_path, mocker):
    # Setup a mock local repo directory that git clone will "create"
    cloned_dir = tmp_path / "cloned"
    cloned_dir.mkdir()
    (cloned_dir / "file_in_git.txt").write_text("Git Content")

    # Mock clone_repo to write files inside the destination target_dir
    def mock_clone_side_effect(url, target_dir, **kwargs):
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, "file_in_git.txt"), "w") as f:
            f.write("Git Content")
        return MagicMock()

    mock_clone.side_effect = mock_clone_side_effect

    out_dir = tmp_path / "out_git"

    mock_conf = {
        "output_file": "git_merged.txt",
        "output_dir": str(out_dir),
        "ignored_dirs": [],
        "ignored_extensions": [],
        "ignored_files": [],
        "include_tree": True
    }
    mocker.patch("src.merger.load_config", return_value=mock_conf)

    res = merge_files(
        "https://github.com/fake/repo",
        output_file="git_merged.txt",
        use_gitignore=False,
        is_git=True
    )

    assert res is not None
    assert res["file_count"] == 1
    assert res["token_count"] > 0

    merged_file = out_dir / "git_merged.txt"
    assert merged_file.exists()
    content = merged_file.read_text(encoding="utf-8")
    assert "file_in_git.txt" in content
    assert "Git Content" in content


def test_merge_files_dry_run_token_count(tmp_path, mocker):
    src_dir = tmp_path / "src_dry"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("Hello World!")

    out_dir = tmp_path / "out_dry"

    mock_conf = {
        "output_file": "dry_merged.txt",
        "output_dir": str(out_dir),
        "ignored_dirs": [],
        "ignored_extensions": [],
        "ignored_files": [],
        "include_tree": False
    }
    mocker.patch("src.merger.load_config", return_value=mock_conf)

    res = merge_files(str(src_dir), output_file="dry_merged.txt", use_gitignore=False, dry_run=True)

    assert res is not None
    assert res["file_count"] == 1
    assert res["token_count"] > 0
    merged_file = out_dir / "dry_merged.txt"
    assert not merged_file.exists()
