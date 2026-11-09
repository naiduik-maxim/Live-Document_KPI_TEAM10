"""Run the Django and Vitest cases assigned to one functional module."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", choices=["1", "2", "3", "4"])
    tag = "module" + parser.parse_args().module
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(root), env.get("PYTHONPATH")])
    )
    env.setdefault("USE_SQLITE", "1")
    backend = subprocess.run(
        [
            sys.executable,
            "manage.py",
            "test",
            "core",
            "tests.backend",
            "--tag",
            tag,
            "--noinput",
        ],
        cwd=root / "backend",
        env=env,
    )
    frontend = subprocess.run(
        [
            "node",
            "node_modules/vitest/vitest.mjs",
            "run",
            "--pool=threads",
            "--maxWorkers=1",
            "-t",
            tag,
        ],
        cwd=root / "frontend",
    )
    return backend.returncode or frontend.returncode


if __name__ == "__main__":
    sys.exit(main())
