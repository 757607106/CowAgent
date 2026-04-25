#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parent / "platform" / "run_real_integration_matrix.py"),
        run_name="__main__",
    )
