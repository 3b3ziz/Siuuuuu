# Claims

What each sub-task of `experiments/atallah/ball_ownership/` says about itself, in a form
[farabi](https://github.com/midspiral/farabi) can check. A claim is one fact with evidence: the
file and lines where it is implemented, and a test command whose exit code proves it. Farabi
reads the claims, checks that every cited file and line range exists, runs every allowlisted test
command, and prints a verdict (`pass`, `fail`, `needs_human`) with a hashed receipt.

## Convention

- One file per sub-task: `claims/<task>.md` (`runner.md`, `harness.md`, `errors.md`, `proofs.md`).
  Prose first (what, when, measured numbers), then one fenced ```farabi block.
- One fact per claim. If a sentence has an "and" that could be false on its own, split it.
- Evidence: `file: <repo-relative path>:<line>` or `:<start>-<end>` pointing at the lines that
  implement the fact, plus `test: <command>` for the command that proves it. Paths are relative
  to the repo root (farabi runs from there), so `experiments/atallah/ball_ownership/...`, never a
  bare filename.
- Put `text` in quotes when it contains `#`, or YAML cuts it there and the block is a `fail`.
- Line numbers go stale when the cited file changes. Re-run `verify.sh` after editing and fix the
  ranges; a wrong range is a `fail`, not a warning.

## Allowed test commands

Only these run (`command.allow` in `/farabi.yaml`; a claim command must equal one of them or
start with one followed by a space, with no shell syntax):

```
uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_rules.py
uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/errors.py
uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/idsse.py
uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/run_real_variant.py
lake build
```

Any of them may take arguments (`idsse.py check`, `run_real_variant.py --variant ...`). `lake build`
is listed but cannot pass from the repo root (lake resolves its toolchain from the working directory
and elan has no default here), so cite `test_proofs.py`, which runs it inside `proofs/`. The
proofs test also runs on every verification (`command.always`), so a broken Lean proof fails every
claims file. The AI review is off (`llm.enabled: false`): a verdict here is deterministic checks only.

## Running

```
experiments/atallah/ball_ownership/verify.sh              # every claims file
experiments/atallah/ball_ownership/verify.sh proofs.md    # one file
farabi receipt <hash>                                     # show a saved receipt
```

`verify.sh` uses `farabi verify text:<file>`; see the comment at the top of the script for why not
`git:worktree` while the tree is uncommitted. A `pass` means every cited line exists and every
cited command exited 0. It does not mean the text is true: that is on the author, and a reviewer
can read the receipt's excerpts to check.

## Proofs

`proofs.md` claims are Lean 4 theorems in `proofs/`. The test command there (`test_proofs.py`)
runs `lake build`, asserts exit 0 and no warning, greps every `.lean` file for `sorry`, `admit` and
`axiom`, and lists the theorems with their line numbers, which are the `file:` citations.
