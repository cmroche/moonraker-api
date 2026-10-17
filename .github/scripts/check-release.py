"""Reject releases unless a stable tag matches the package version on main."""

import configparser
import os
import re
import subprocess


ref = os.environ["GITHUB_REF"]
match = re.fullmatch(
    r"refs/tags/v((?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2})", ref
)
if match is None:
    raise SystemExit("Publishing requires a stable vMAJOR.MINOR.PATCH tag")

config = configparser.ConfigParser()
config.read("setup.cfg")
if config["metadata"]["version"] != match[1]:
    raise SystemExit("Release tag does not match setup.cfg version")

subprocess.run(
    ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"], check=True
)
print(f"Validated {ref}: matching package version and commit on main")
