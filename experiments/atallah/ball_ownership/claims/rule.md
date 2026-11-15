# Claims: ball-ownership rule (TIKI-13)

`features.py` + `ball_rule.py`: team-level possession from touches (direction or speed change of the
smoothed ball while a slot is inside a 1 m zone), on top of `rules.segment_labels`. Verified on
15 Nov 2026 with the test command below (all eight checks pass). Scores with the defaults, against
row 8 (`closest_row8`): clean 0.6240 vs 0.5025, noisy 0.5087 vs 0.4444, clean oracle 0.7325 vs
0.5932, noisy oracle 0.6264 vs 0.5631, idsse 0.4020 vs 0.3355 (oracle 0.4961 vs 0.3995); fewer
missed spells at IoU 0.5 on every set (rows in `RESULTS.md`, note "TIKI-13").

```farabi
claims:
  - id: b1
    text: ball_rule.ball_ownership(df, teams, segments, dead, pitch, **params) returns a '<U1' array of len(df) with 'X' outside the segments and segment_labels output inside them
    evidence:
      - file: experiments/atallah/ball_ownership/ball_rule.py:195-220
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_rules.py
  - id: b2
    text: Every tunable has a default in the single dict DEFAULTS and an unknown keyword raises ValueError
    evidence:
      - file: experiments/atallah/ball_ownership/ball_rule.py:41-54
      - file: experiments/atallah/ball_ownership/ball_rule.py:185-192
  - id: b3
    text: The ball track is smoothed with Savitzky-Golay order 2 window 7 per contiguous visible run and NaN frames stay NaN
    evidence:
      - file: experiments/atallah/ball_ownership/features.py:54-60
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_rules.py
  - id: b4
    text: near is the team with a slot inside zone_m of the smoothed ball while the other team has no slot inside zone_m + exit_m and the frame is not a duel (both inside duel_m); otherwise ""
    evidence:
      - file: experiments/atallah/ball_ownership/ball_rule.py:78-82
  - id: b5
    text: A gain is registered at an extremum frame (vertex of the direction change or speed change, or the closest approach of a slot while the ball turns) when max(in, out) speed exceeds min_speed_ms and the turn exceeds turn_deg or the speed change exceeds dspeed_ms
    evidence:
      - file: experiments/atallah/ball_ownership/ball_rule.py:85-97
  - id: b6
    text: A touch vertex with no slot inside zone_m within two frames is ignored as noise, and one with both teams inside zone_m + exit_m is a duel and writes nothing
    evidence:
      - file: experiments/atallah/ball_ownership/ball_rule.py:99-112
  - id: b7
    text: A slot whose step into or out of a frame implies more than swap_ms is not a candidate on that frame, and player_velocity blanks the same slot-frames and counts them
    evidence:
      - file: experiments/atallah/ball_ownership/ball_rule.py:72-74
      - file: experiments/atallah/ball_ownership/features.py:90-114
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_rules.py
  - id: b8
    text: Ball velocity is the central difference of the smoothed track in m/s with NaN wherever a neighbour is missing, and direction_change is the angle between the 3-frame mean velocities before and after the frame
    evidence:
      - file: experiments/atallah/ball_ownership/features.py:70-78
      - file: experiments/atallah/ball_ownership/features.py:131-142
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_rules.py
  - id: b9
    text: Inside a ball gap the team is held, and when the first confirmed holder after the gap differs from the last evidence before it and is within reality_m of the ball at reappearance, an instant switch is written at the extrapolated arrival (last ball velocity for at most gap_extrap_s, within reality_m of a new-team slot), else at the gap midpoint, clamped to the gap
    evidence:
      - file: experiments/atallah/ball_ownership/ball_rule.py:120-182
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_rules.py
  - id: b10
    text: A teammate pass never switches, an interception switches within two frames of the touch, and a deflection that returns to the original team within min_spell frames does not switch
    evidence:
      - file: experiments/atallah/ball_ownership/test_rules.py:99-151
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_rules.py
  - id: b11
    text: A 30 m slot jump gives NaN player velocity and keeps the holder, a 10-frame ball gap keeps the holder, and a gap followed by a team change places the one switch inside the gap
    evidence:
      - file: experiments/atallah/ball_ownership/test_rules.py:154-196
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_rules.py
  - id: b12
    text: rules.segment_labels with default arguments equals sticky.sticky_segment on 40 random near/dead pairs
    evidence:
      - file: experiments/atallah/ball_ownership/test_rules.py:199-212
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_rules.py
  - id: b13
    text: The rule is deterministic and reads only df, teams, segments, dead and pitch; no randomness, clock or file I/O is used
    evidence:
      - file: experiments/atallah/ball_ownership/ball_rule.py:28-36
      - file: experiments/atallah/ball_ownership/features.py:19-24
  - id: b14
    text: The real-match runner accepts the variant and prints only aggregates; with the defaults it reports stoppage share 43 percent, 153 stoppages (the stoppage mask's own run count) and 330 possessions against row 8's 420
    evidence:
      - file: experiments/atallah/ball_ownership/RESULTS.md
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/run_real_variant.py --variant ball_ownership --name ball_ownership_v1
```
