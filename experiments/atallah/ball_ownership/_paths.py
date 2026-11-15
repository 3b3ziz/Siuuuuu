"""Put prep/, starter/, evaluation/ and experiments/atallah/ on sys.path (INTERFACES.md)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))      # repo root
for sub in ("prep", "starter", "evaluation", os.path.join("experiments", "atallah")):
    p = os.path.join(ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)
