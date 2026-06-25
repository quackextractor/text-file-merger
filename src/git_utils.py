import os
import shutil
import git
from typing import Optional


def clone_repo(
    url: str,
    target_dir: str,
    branch: Optional[str] = None,
    tag: Optional[str] = None,
    commit: Optional[str] = None,
    token: Optional[str] = None
) -> git.Repo:
    """Clones a remote Git repository to the target directory.

    Supports shallow clone, ref checkouts (branch, tag, or commit), and automatic fallback
    to full clone if shallow checkout is not possible. Also handles GitHub tokens.
    """
    token = token or os.environ.get("GITHUB_TOKEN")
    if token and "github.com" in url and "@" not in url:
        url = url.replace("https://", f"https://{token}@")
        url = url.replace("http://", f"http://{token}@")

    ref = branch or tag or commit
    is_commit = commit is not None or (ref and all(c in "0123456789abcdefABCDEF" for c in ref) and (7 <= len(ref) <= 40))

    if ref and not is_commit:
        try:
            # Attempt shallow clone of branch/tag
            return git.Repo.clone_from(url, target_dir, depth=1, branch=ref)
        except Exception:
            # Clean up target directory and attempt full clone fallback
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            return git.Repo.clone_from(url, target_dir, branch=ref)
    else:
        try:
            # Attempt shallow clone of default branch, then checkout the commit
            repo = git.Repo.clone_from(url, target_dir, depth=1)
            if ref:
                repo.git.checkout(ref)
            return repo
        except Exception:
            # Clean up target directory and attempt full clone fallback
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            repo = git.Repo.clone_from(url, target_dir)
            if ref:
                repo.git.checkout(ref)
            return repo
