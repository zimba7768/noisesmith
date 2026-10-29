"""Build the Claude Desktop extension: dist/noisesmith-<version>.mcpb

Run with:  uv run python scripts/build_mcpb.py
Needs Node.js (it uses Anthropic's official `@anthropic-ai/mcpb` packer via npx).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "dist" / "mcpb-staging"
MCPB_CLI = "@anthropic-ai/mcpb@2.1.2"  # pinned so builds are repeatable


def main() -> None:
    npx = shutil.which("npx")
    if not npx:
        sys.exit("Node.js (npx) is required to build the extension.")

    # 1. Copy just the files the extension needs into a clean staging folder.
    if STAGING.exists():
        shutil.rmtree(STAGING)
    (STAGING / "src").mkdir(parents=True)
    shutil.copytree(
        ROOT / "src" / "noisesmith",
        STAGING / "src" / "noisesmith",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy2(ROOT / name, STAGING / name)
    shutil.copy2(ROOT / "mcpb" / "manifest.json", STAGING / "manifest.json")
    (STAGING / ".mcpbignore").write_text(".venv\n__pycache__\n*.pyc\n", encoding="utf-8")

    # 2. Check the manifest version matches the Python package version.
    manifest = json.loads((STAGING / "manifest.json").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if f'version = "{manifest["version"]}"' not in pyproject:
        sys.exit(f"Version mismatch: manifest says {manifest['version']}, pyproject.toml differs.")

    # 3. Validate and pack with the official tool.
    out = ROOT / "dist" / f"noisesmith-{manifest['version']}.mcpb"
    subprocess.run([npx, "--yes", MCPB_CLI, "validate", "manifest.json"], cwd=STAGING, check=True)
    subprocess.run([npx, "--yes", MCPB_CLI, "pack", ".", str(out)], cwd=STAGING, check=True)
    print(f"\nBuilt {out}")


if __name__ == "__main__":
    main()
