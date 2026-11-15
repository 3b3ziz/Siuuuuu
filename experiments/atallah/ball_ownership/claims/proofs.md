# Claims: Lean proofs (proofs/)

Pure properties of the pipeline, proven in Lean 4 (v4.34.1, core only, no mathlib) under
`experiments/atallah/ball_ownership/proofs/`. Verified on 15 Nov 2026: `lake build` from clean in
4.3 s (0.2 s warm), 76 theorems in 4 files, no `sorry`, `admit` or `axiom` anywhere, no warnings.
Everything is Nat/Int arithmetic (`omega`, `decide`) and structural induction on lists.

- `IoU.lean`: a predicted spell shifted by e against a truth spell of length L, the IoU
  thresholds 3/10..7/10 as integer inequalities, and the merged-spell loss.
- `Segment.lean`: a pure list model of `prep/sticky.py` `sticky_segment`, with the length,
  dead-frame, all-home and blind-spot theorems, and the `date_back` clamp of `rules.segment_labels`.
- `Gap.lean`: the midpoint of an uncertainty gap minimises the worst-case boundary error.
- `Degrade.lean`: a per-team column permutation is a bijection and keeps each frame's multiset
  of positions.

```farabi
claims:
  - id: p1
    text: test_proofs.py runs lake build in proofs/, asserts exit 0 and no warning, asserts no .lean source contains sorry, admit or axiom, and prints every theorem as file:line name
    evidence:
      - file: experiments/atallah/ball_ownership/test_proofs.py:30-50
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p2
    text: The Lean project depends on no package (core Lean only) and builds the four roots IoU, Segment, Gap, Degrade
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/lakefile.toml:1-9
      - file: experiments/atallah/ball_ownership/proofs/lake-manifest.json:1-6
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p3
    text: "IoU: a truth spell [0, L) and the same spell shifted late by e < L intersect in L - e frames and their union is L + e frames"
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/IoU.lean:28-32
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p4
    text: "IoU >= 7/10 for the shifted spell holds iff 17 e <= 3 L, and the thresholds 6/10, 5/10, 4/10, 3/10 are 4 e <= L, 3 e <= L, 7 e <= 3 L, 13 e <= 7 L"
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/IoU.lean:44-57
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p5
    text: "Corollaries: at 0.5 the spell survives iff 3 e <= L and at 0.3 iff 13 e <= 7 L; a stricter threshold tolerates less shift"
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/IoU.lean:60-70
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p6
    text: "Merged spells: truth spells A and B with gap G predicted as one spell of length A+G+B have intersections A and B and union A+G+B, so IoU A/(A+G+B) and B/(A+G+B)"
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/IoU.lean:82-92
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p7
    text: With A = B = 300 and G = 500 both merged IoUs are below 3/10 (10 * 300 < 3 * 1100)
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/IoU.lean:103-106
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p8
    text: Segment.stickySegment is a list model of sticky_segment with near as List (Option Team), dead as List Bool and the switch count k, built from the inner loop (switches), the stretch painter (paint) and a walk over stretches (go)
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Segment.lean:42-100
      - file: prep/sticky.py:66-91
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p9
    text: Five concrete cases of the model (blind spot, confirmed away run, dead frame, carried team, nothing confirmed) are checked by decide against the Python behaviour
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Segment.lean:104-116
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p10
    text: The output of stickySegment has the same length as the input when near and dead have the same length (length_eq)
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Segment.lean:136-139
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p11
    text: Every dead frame is labelled D (dead_is_D)
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Segment.lean:166-175
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p12
    text: With k = 1, no dead frame and home near the ball on every frame, every label is H (all_home), for every length n
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Segment.lean:218-225
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p13
    text: "Blind spot, general form: a live stretch whose away frames form one run of b < k frames, with arbitrary non-away frames before and after, never gets an A label (blind_spot); blind_spot_k8 is the k = 8, 7-frame instance"
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Segment.lean:328-345
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p14
    text: "date_back clamp of rules.segment_labels (sw = min(max(sw + date_back, start, lo), stop, hi)): the dated switch min(max(run_start + d, start, lo), stop, hi) is inside the stretch and between its neighbours, equals max(start, run_start + d) when it has no neighbours and no end clamp, and equals run_start when d = 0"
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Segment.lean:354-377
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p15
    text: "Gap: for an integer interval [g0, g1], the midpoint (g0 + g1) / 2 minimises the worst-case error max over s* in the interval of |s - s*|, and that minimum is (g1 - g0 + 1) / 2"
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Gap.lean:25-48
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p16
    text: Any s inside the interval bounds both neighbouring boundary errors by g1 - g0, and any s outside has a worst case larger than g1 - g0
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Gap.lean:52-63
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p17
    text: A per-team column permutation (Degrade.Perm, a Fin n -> Fin n with an inverse) is injective and surjective, has an inverse permutation and composes
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Degrade.lean:15-46
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p18
    text: After a column permutation each frame holds the same multiset of positions (the position list is a List.Perm of the original, so every count and membership is unchanged)
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Degrade.lean:88-108
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
  - id: p19
    text: Composing per-interval permutations as idsse.permute_slots does (frame t uses sigma t) keeps every frame's multiset of positions, degrading twice is one degradation by the composed permutations, and the two teams are permuted on their own columns
    evidence:
      - file: experiments/atallah/ball_ownership/proofs/Degrade.lean:113-143
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_proofs.py
```
