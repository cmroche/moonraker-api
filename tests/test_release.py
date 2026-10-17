"""Exercise the publishing gate against real Git histories."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


CHECK_RELEASE = Path(__file__).resolve().parents[1] / ".github/scripts/check-release.py"


@pytest.fixture
def release_repo(tmp_path):
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        )

    git("init", "--initial-branch=main")
    git("config", "user.email", "release@example.invalid")
    git("config", "user.name", "Release test")
    git("config", "commit.gpgsign", "false")
    git("config", "tag.gpgsign", "false")
    (tmp_path / "setup.cfg").write_text("[metadata]\nversion = 1.2.3\n")
    git("add", "setup.cfg")
    git("commit", "-m", "Initial release")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    return tmp_path, git


def check_release(repo, ref):
    return subprocess.run(
        [sys.executable, str(CHECK_RELEASE)],
        cwd=repo,
        env={**os.environ, "GITHUB_REF": ref},
        capture_output=True,
        text=True,
    )


def test_release_accepts_matching_tag_on_main(release_repo):
    repo, git = release_repo
    git("tag", "v1.2.3")
    git("commit", "--allow-empty", "-m", "Main advanced after release")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("checkout", "v1.2.3")
    result = check_release(repo, "refs/tags/v1.2.3")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "ref",
    [
        "refs/heads/main",
        "refs/heads/v1.2.3",
        "refs/tags/v1.2.3-beta.1",
        "refs/tags/v1.2",
        "refs/tags/v01.2.3",
    ],
)
def test_release_rejects_nonstable_or_branch_refs(release_repo, ref):
    repo, _ = release_repo
    result = check_release(repo, ref)
    assert result.returncode != 0
    assert "stable vMAJOR.MINOR.PATCH tag" in result.stderr


def test_release_rejects_version_mismatch(release_repo):
    repo, _ = release_repo
    result = check_release(repo, "refs/tags/v1.2.4")
    assert result.returncode != 0
    assert "does not match setup.cfg version" in result.stderr


def test_release_rejects_commit_outside_main(release_repo):
    repo, git = release_repo
    git("checkout", "-b", "unreleased")
    git("commit", "--allow-empty", "-m", "Unmerged change")
    git("tag", "v1.2.3")
    result = check_release(repo, "refs/tags/v1.2.3")
    assert result.returncode != 0
