# Claims: idsse.py (TIKI-14)

Extra practice set from the DFL / Sportec IDSSE open data (Bassek et al. 2025, CC BY 4.0), two
Bundesliga matches (J03WMX Köln vs Bayern, J03WN1 Bochum vs Leverkusen), degraded to look like
our match. Built and checked on 15 Nov 2026: 287528 frames, 1011 truth possessions; the raw XML
(418.5 MB and 391.7 MB) came from the figshare API in 17 s and 16 s, kloppy parses each match in
68 s, the cached set loads in 0.3 s. `closest_row8` through `harness.run`: degraded fixed 0.3355
(533/1011 spells), degraded oracle 0.3995 (476), clean fixed 0.4262 (670), clean oracle 0.4891
(624). Re-running `degrade` on the clean cache reproduces the degraded pickle exactly.

```farabi
claims:
  - id: i1
    text: The raw meta and tracking XML are downloaded from https://api.figshare.com/v2/file/download/<id> into data/idsse/raw/, retrying while figshare answers 202, and are not downloaded again when a non-empty file is present
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:137-163
  - id: i2
    text: Frames are parsed with kloppy sportec.load_tracking with coordinates="metrica" and only_alive=False, so dead frames are kept and coordinates are 0 to 1 with the origin top left and y down, converted from Sportec metres centred on the pitch
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:166-172
      - file: experiments/atallah/ball_ownership/idsse.py:25-32
  - id: i3
    text: The build keeps frame_id, period_id, ball_x, ball_y and <id>_x, <id>_y for the tracked players only, dropping unused substitutes that have no column in to_df, and refuses coordinates outside -0.2 to 1.2
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:175-203
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/idsse.py check
  - id: i4
    text: Truth labels are D where ball_state is not alive, else H or A from ball_owning_team_id against the home and away team ids, with an alive frame lacking an owner taking the previous frame's label in its period
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:206-222
  - id: i5
    text: The degradation is seeded with numpy default_rng(0) and blanks the ball in contiguous blocks of exponential length with mean 2 s until 41 percent of alive frames have no ball, drawing block starts with weight 3 where 3 or more players stand within 3 m of the ball and 1 elsewhere
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:120-127
      - file: experiments/atallah/ball_ownership/idsse.py:226-259
      - file: experiments/atallah/ball_ownership/idsse.py:285-299
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/idsse.py check
  - id: i6
    text: After the dropouts the player columns of each team are permuted within random intervals of exponential length with mean 90 s
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:262-282
  - id: i7
    text: Per match the clean frame, the degraded frame, the label array and a meta.json with pitch size, team lists, segments, licence and degradation statistics are cached under data/idsse/<match_id>/
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:308-347
  - id: i8
    text: load(clean=False) returns one object with .df .gt_labels .gt_codes .runs .segments .teams .dead and .pitch over the two matches concatenated with row offsets, where dead["fixed"] is dead_from_ball_out OR dead_from_players from prep and dead["oracle"] is the truth's D frames
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:367-386
      - file: experiments/atallah/ball_ownership/idsse.py:413-442
  - id: i9
    text: The runs handed to the harness are the valid runs cut at every period boundary, so no spell or abstention fill crosses a half or a match
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:357-364
      - file: experiments/atallah/ball_ownership/idsse.py:376-380
  - id: i10
    text: idsse.py check prints per match the frame count, periods, alive share, dead-run count, truth possession count and mean length, ball visible share before and after degradation and the permutation interval count, aggregates only
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:447-478
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/idsse.py check
  - id: i11
    text: The data licence is CC BY 4.0 and the citation is Bassek et al. 2025, Scientific Data 12, 195, both recorded in the module and in every meta.json
    evidence:
      - file: experiments/atallah/ball_ownership/idsse.py:3-5
      - file: experiments/atallah/ball_ownership/idsse.py:117
      - file: experiments/atallah/ball_ownership/idsse.py:342-347
```
