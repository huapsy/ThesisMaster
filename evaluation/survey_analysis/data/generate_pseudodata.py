from __future__ import annotations

import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "utils")
if UTILS_DIR not in sys.path:
    sys.path.insert(0, UTILS_DIR)

from shared.pseudodata_factory import generate_all_studies


if __name__ == "__main__":
    generate_all_studies()
