"""Checks the Lean proofs in proofs/: `lake build` exits 0 and no source contains a proof hole.

    uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py

Prints the last line of the build output with its wall time, then every theorem found, one per
line as `proofs/<File>.lean:<line> <name>`, then OK. Exit 1 on any failure.
"""

import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROOFS = os.path.join(HERE, "proofs")
HOLES = re.compile(r"\b(sorry|admit|axiom)\b")
THEOREM = re.compile(r"^\s*(?:private\s+|protected\s+)?theorem\s+([^\s:({\[]+)")


def lean_sources():
    for root, dirs, files in os.walk(PROOFS):
        dirs[:] = [d for d in dirs if d != ".lake"]
        for f in sorted(files):
            if f.endswith(".lean"):
                yield os.path.join(root, f)


def main():
    sources = list(lean_sources())
    assert sources, "no .lean files under " + PROOFS

    t0 = time.time()
    r = subprocess.run(["lake", "build"], cwd=PROOFS, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    print(out.splitlines()[-1] if out else "(no output)", f"[{time.time() - t0:.1f}s]")
    assert r.returncode == 0, f"lake build exited {r.returncode}:\n{out}"
    assert "sorry" not in out.lower(), "lake build warned about a proof hole:\n" + out
    assert "warning" not in out.lower(), "lake build printed a warning:\n" + out

    theorems = []
    for path in sources:
        rel = os.path.relpath(path, HERE)
        with open(path) as fh:
            for n, line in enumerate(fh, 1):
                hole = HOLES.search(line)
                assert not hole, f"{rel}:{n}: forbidden token {hole.group(1)!r}"
                m = THEOREM.match(line)
                if m:
                    theorems.append((rel, n, m.group(1)))
    assert theorems, "no theorems found"
    for rel, n, name in theorems:
        print(f"{rel}:{n} {name}")
    print(f"OK: {len(theorems)} theorems in {len(sources)} files, lake build exit 0, no sorry/admit/axiom")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
