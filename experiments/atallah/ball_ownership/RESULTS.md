# Results log

Append-only log of every scored run of `harness.py` on the practice match (Metrica Sample
Game 3) and any registered set. `set` is the data (`clean` = full ball, `noisy` = ball hidden
41% of live frames like the real match); `mode` is the stoppage mask (`fixed` = ball out or
players slow, `oracle` = the truth's D frames: the ceiling for the ownership rule alone).
spellF1 is the mean possession-spell F1 over IoU 0.3-0.7 (`evaluation/possession_metrics.py`).
Reference: row 8 (`closest_row8`) scores 0.5025 clean / 0.4444 noisy, 321 possessions vs 381.

| date | set | mode | variant | params | spellF1 | n_pred/n_gt | matched/missed/spurious @0.5 | note |
|---|---|---|---|---|---|---|---|---|
| 2026-11-15 | clean | fixed | closest_row8 | - | 0.5025 | 411/381 | 202/179/209 | TIKI-11 baseline: row 8 reproduced; oracle = truth D |
| 2026-11-15 | clean | oracle | closest_row8 | - | 0.5932 | 381/381 | 232/149/149 | TIKI-11 baseline: row 8 reproduced; oracle = truth D |
| 2026-11-15 | noisy | fixed | closest_row8 | - | 0.4444 | 321/381 | 159/222/162 | TIKI-11 baseline: row 8 reproduced; oracle = truth D |
| 2026-11-15 | noisy | oracle | closest_row8 | - | 0.5631 | 291/381 | 196/185/95 | TIKI-11 baseline: row 8 reproduced; oracle = truth D |
| 2026-11-15 | noisy | fixed | closest | switch_frames=6 | 0.4106 | 409/381 | 163/218/246 | harness smoke: sweep+bootstrap+write |
| 2026-11-15 | noisy | fixed | closest | switch_frames=10 | 0.4196 | 272/381 | 137/244/135 | harness smoke: sweep+bootstrap+write |
| 2026-11-15 | clean | fixed | closest_row8 | - | 0.5025 | 411/381 | 202/179/209 | TIKI-11 deliverable 4: harness verified; oracle = ownership ceiling |
| 2026-11-15 | clean | oracle | closest_row8 | - | 0.5932 | 381/381 | 232/149/149 | TIKI-11 deliverable 4: harness verified; oracle = ownership ceiling |
| 2026-11-15 | noisy | fixed | closest_row8 | - | 0.4444 | 321/381 | 159/222/162 | TIKI-11 deliverable 4: harness verified; oracle = ownership ceiling |
| 2026-11-15 | noisy | oracle | closest_row8 | - | 0.5631 | 291/381 | 196/185/95 | TIKI-11 deliverable 4: harness verified; oracle = ownership ceiling |

## Loss table, row 8 (TIKI-12, `errors.py`, 2026-11-15)

Unmatched truth possessions at IoU 0.5 by category (`errors.py --variant closest_row8`). 381 truth
possessions; categories tested in this order, first hit wins. Per-spell rows in
`data/sample/cache/errors_closest_row8_<set>_<mode>.csv`.

| category | clean fixed | clean oracle | noisy fixed | noisy oracle |
|---|---|---|---|---|
| matched | 202 | 232 | 159 | 196 |
| merged by missed stoppage | 29 | 0 | 56 | 0 |
| flip-flop | 18 | 16 | 10 | 8 |
| wrong team | 25 | 25 | 21 | 27 |
| missed switch | 35 | 36 | 54 | 61 |
| missed switch (short, < 16 frames) | 15 | 27 | 15 | 27 |
| late switch | 5 | 0 | 5 | 0 |
| early switch | 23 | 26 | 24 | 33 |
| late or early end | 29 | 19 | 36 | 29 |
| other | 0 | 0 | 1 | 0 |
| unmatched total | 179 | 149 | 222 | 185 |

- Missed switches dominate once the stoppage mask is fixed (noisy oracle: 61 + 27 short = 48% of
  the losses). The "short" ones are 1-frame truth spells (median 0.04 s): 32 of the 381 truth
  possessions are under 8 frames and no sticky rule can recover them. The other missed switches
  have median length 2.0-2.2 s: real possessions the rule never flipped to.
- Merged stoppages are the second loss on the noisy fixed set (56): the ball hidden around
  restarts leaves `dead_from_ball_out` blind, so possessions either side of a stoppage fuse.
- Switch offset (predicted H<->A switch minus truth, tol 50): clean fixed n=158, median 0,
  p10 -24.6, p90 +24.3; noisy fixed n=104, median +1, p10 -13, p90 +30.7; 127 (clean) and 181
  (noisy) of 285 truth switches have no predicted H<->A switch within 50 frames. The late tail
  (+16 to +27) is the 8-frame confirmation plus a late first touch; the early tail is the rule
  switching on the nearest player before the truth switch.
- First touch (truth switch minus first frame the new team is within 1 m, clean frame): n=279,
  median 0, p10 -2, p90 +22; 26 of them sit at the +24/25 window edge (the receiver was already
  on the ball through the window); 6 switches have no touch within 1 m in +/-25 frames.
- Sandwiches (predicted A B A, frame-adjacent), noisy fixed: 9-15 frames 6 written (83% overlap a
  same-team truth spell, 3 in truth), 16-25 frames 11 (27%, 8 in truth), 26-50 frames 21 (62%,
  37 in truth). Short sandwiches are rare and mostly real; the 16-25 bin is the one to suppress.
- idsse (two DFL open matches, degraded, 1011 truth possessions), row 8: fixed 264 matched, oracle
  296. Unmatched fixed / oracle: merged stoppage 163 / 1, flip-flop 15 / 13, wrong team 62 / 85,
  missed switch 215 / 261 (+27 / 39 short), late switch 9 / 4, early switch 123 / 163, late or
  early end 130 / 149, other 3 / 0. Same ranking as the practice match: missed switches first,
  then early switches and spell ends. Switch offset median -2, p10 -21.5, p90 +40; 626 of 802
  truth switches have no predicted switch within 50 frames. The first-touch histogram there runs
  on the degraded frame (311 of 802 switches have no player within 1 m in the window), so read it
  on the practice set only.
| 2026-11-15 | clean | fixed | ball_ownership | - | 0.6240 | 351/381 | 233/148/118 | TIKI-13 defaults |
| 2026-11-15 | clean | oracle | ball_ownership | - | 0.7325 | 324/381 | 263/118/61 | TIKI-13 defaults |
| 2026-11-15 | noisy | fixed | ball_ownership | - | 0.5087 | 289/381 | 174/207/115 | TIKI-13 defaults |
| 2026-11-15 | noisy | oracle | ball_ownership | - | 0.6264 | 262/381 | 207/174/55 | TIKI-13 defaults |
| 2026-11-15 | idsse | fixed | closest_row8 | - | 0.3355 | 533/1011 | 264/747/269 | TIKI-13 row 8 reference on idsse |
| 2026-11-15 | idsse | oracle | closest_row8 | - | 0.3995 | 476/1011 | 296/715/180 | TIKI-13 row 8 reference on idsse |
| 2026-11-15 | idsse | fixed | closest_row8 | - | 0.3355 | 533/1011 | 264/747/269 | TIKI-14 close-out |
| 2026-11-15 | idsse | oracle | closest_row8 | - | 0.3995 | 476/1011 | 296/715/180 | TIKI-14 close-out |
| 2026-11-15 | idsse | fixed | ball_ownership | - | 0.4020 | 572/1011 | 323/688/249 | TIKI-13 defaults |
| 2026-11-15 | idsse | oracle | ball_ownership | - | 0.4961 | 534/1011 | 395/616/139 | TIKI-13 defaults |
| 2026-11-15 | clean | fixed | ball_ownership | turn_deg=10,zone_m=1.0 | 0.6240 | 351/381 | 233/148/118 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | oracle | ball_ownership | turn_deg=10,zone_m=1.0 | 0.7325 | 324/381 | 263/118/61 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | fixed | ball_ownership | turn_deg=10,zone_m=1.0 | 0.5087 | 289/381 | 174/207/115 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | oracle | ball_ownership | turn_deg=10,zone_m=1.0 | 0.6264 | 262/381 | 207/174/55 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | fixed | ball_ownership | turn_deg=15,zone_m=1.0 | 0.6263 | 349/381 | 233/148/116 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | oracle | ball_ownership | turn_deg=15,zone_m=1.0 | 0.7351 | 322/381 | 263/118/59 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | fixed | ball_ownership | turn_deg=15,zone_m=1.0 | 0.5087 | 289/381 | 173/208/116 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | oracle | ball_ownership | turn_deg=15,zone_m=1.0 | 0.6264 | 262/381 | 206/175/56 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | fixed | ball_ownership | turn_deg=10,zone_m=1.25 | 0.5951 | 351/381 | 224/157/127 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | oracle | ball_ownership | turn_deg=10,zone_m=1.25 | 0.6958 | 329/381 | 252/129/77 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | fixed | ball_ownership | turn_deg=10,zone_m=1.25 | 0.4895 | 294/381 | 169/212/125 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | oracle | ball_ownership | turn_deg=10,zone_m=1.25 | 0.6012 | 271/381 | 199/182/72 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | fixed | ball_ownership | turn_deg=15,zone_m=1.25 | 0.5967 | 349/381 | 224/157/125 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | oracle | ball_ownership | turn_deg=15,zone_m=1.25 | 0.6977 | 327/381 | 252/129/75 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | fixed | ball_ownership | turn_deg=15,zone_m=1.25 | 0.4889 | 294/381 | 168/213/126 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | oracle | ball_ownership | turn_deg=15,zone_m=1.25 | 0.6006 | 271/381 | 198/183/73 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | fixed | ball_ownership | turn_deg=10,zone_m=1.5 | 0.5648 | 374/381 | 220/161/154 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | oracle | ball_ownership | turn_deg=10,zone_m=1.5 | 0.6580 | 346/381 | 247/134/99 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | fixed | ball_ownership | turn_deg=10,zone_m=1.5 | 0.4684 | 303/381 | 166/215/137 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | oracle | ball_ownership | turn_deg=10,zone_m=1.5 | 0.5829 | 273/381 | 196/185/77 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | fixed | ball_ownership | turn_deg=15,zone_m=1.5 | 0.5639 | 373/381 | 219/162/154 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | oracle | ball_ownership | turn_deg=15,zone_m=1.5 | 0.6573 | 345/381 | 246/135/99 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | fixed | ball_ownership | turn_deg=15,zone_m=1.5 | 0.4668 | 302/381 | 165/216/137 | TIKI-13 sweep zone x turn |
| 2026-11-15 | noisy | oracle | ball_ownership | turn_deg=15,zone_m=1.5 | 0.5813 | 272/381 | 195/186/77 | TIKI-13 sweep zone x turn |
| 2026-11-15 | clean | fixed | ball_ownership | dspeed_ms=4,min_spell=0 | 0.6290 | 356/381 | 237/144/119 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | oracle | ball_ownership | dspeed_ms=4,min_spell=0 | 0.7402 | 328/381 | 268/113/60 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | fixed | ball_ownership | dspeed_ms=4,min_spell=0 | 0.5087 | 289/381 | 174/207/115 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | oracle | ball_ownership | dspeed_ms=4,min_spell=0 | 0.6295 | 262/381 | 208/173/54 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | fixed | ball_ownership | dspeed_ms=4,min_spell=8 | 0.6264 | 354/381 | 235/146/119 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | oracle | ball_ownership | dspeed_ms=4,min_spell=8 | 0.7378 | 326/381 | 266/115/60 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | fixed | ball_ownership | dspeed_ms=4,min_spell=8 | 0.5087 | 289/381 | 174/207/115 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | oracle | ball_ownership | dspeed_ms=4,min_spell=8 | 0.6295 | 262/381 | 208/173/54 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | fixed | ball_ownership | dspeed_ms=4,min_spell=12 | 0.6259 | 352/381 | 234/147/118 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | oracle | ball_ownership | dspeed_ms=4,min_spell=12 | 0.7378 | 326/381 | 266/115/60 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | fixed | ball_ownership | dspeed_ms=4,min_spell=12 | 0.5087 | 289/381 | 174/207/115 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | oracle | ball_ownership | dspeed_ms=4,min_spell=12 | 0.6295 | 262/381 | 208/173/54 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | fixed | ball_ownership | dspeed_ms=5,min_spell=0 | 0.6267 | 353/381 | 235/146/118 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | oracle | ball_ownership | dspeed_ms=5,min_spell=0 | 0.7349 | 326/381 | 265/116/61 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | fixed | ball_ownership | dspeed_ms=5,min_spell=0 | 0.5087 | 289/381 | 174/207/115 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | oracle | ball_ownership | dspeed_ms=5,min_spell=0 | 0.6264 | 262/381 | 207/174/55 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | fixed | ball_ownership | dspeed_ms=5,min_spell=8 | 0.6240 | 351/381 | 233/148/118 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | oracle | ball_ownership | dspeed_ms=5,min_spell=8 | 0.7325 | 324/381 | 263/118/61 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | fixed | ball_ownership | dspeed_ms=5,min_spell=8 | 0.5087 | 289/381 | 174/207/115 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | oracle | ball_ownership | dspeed_ms=5,min_spell=8 | 0.6264 | 262/381 | 207/174/55 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | fixed | ball_ownership | dspeed_ms=5,min_spell=12 | 0.6236 | 349/381 | 232/149/117 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | oracle | ball_ownership | dspeed_ms=5,min_spell=12 | 0.7325 | 324/381 | 263/118/61 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | fixed | ball_ownership | dspeed_ms=5,min_spell=12 | 0.5087 | 289/381 | 174/207/115 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | noisy | oracle | ball_ownership | dspeed_ms=5,min_spell=12 | 0.6264 | 262/381 | 207/174/55 | TIKI-13 sweep dspeed x min_spell |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=-6,hold_frames=4 | 0.5126 | 486/381 | 227/154/259 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=-6,hold_frames=4 | 0.6238 | 466/381 | 270/111/196 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=-6,hold_frames=4 | 0.4420 | 381/381 | 171/210/210 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=-6,hold_frames=4 | 0.5514 | 356/381 | 206/175/150 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=-6,hold_frames=6 | 0.6101 | 375/381 | 237/144/138 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=-6,hold_frames=6 | 0.7151 | 349/381 | 267/114/82 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=-6,hold_frames=6 | 0.5112 | 306/381 | 181/200/125 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=-6,hold_frames=6 | 0.6257 | 280/381 | 212/169/68 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=-6,hold_frames=8 | 0.6235 | 351/381 | 234/147/117 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=-6,hold_frames=8 | 0.7302 | 324/381 | 263/118/61 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=-6,hold_frames=8 | 0.5069 | 289/381 | 173/208/116 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=-6,hold_frames=8 | 0.6252 | 262/381 | 206/175/56 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=-3,hold_frames=4 | 0.5144 | 486/381 | 227/154/259 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=-3,hold_frames=4 | 0.6274 | 467/381 | 273/108/194 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=-3,hold_frames=4 | 0.4441 | 381/381 | 172/209/209 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=-3,hold_frames=4 | 0.5528 | 357/381 | 207/174/150 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=-3,hold_frames=6 | 0.6106 | 375/381 | 236/145/139 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=-3,hold_frames=6 | 0.7162 | 349/381 | 267/114/82 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=-3,hold_frames=6 | 0.5118 | 306/381 | 181/200/125 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=-3,hold_frames=6 | 0.6263 | 280/381 | 212/169/68 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=-3,hold_frames=8 | 0.6235 | 351/381 | 233/148/118 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=-3,hold_frames=8 | 0.7313 | 324/381 | 263/118/61 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=-3,hold_frames=8 | 0.5075 | 289/381 | 173/208/116 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=-3,hold_frames=8 | 0.6258 | 262/381 | 206/175/56 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=0,hold_frames=4 | 0.5200 | 486/381 | 230/151/256 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=0,hold_frames=4 | 0.6330 | 467/381 | 277/104/190 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=0,hold_frames=4 | 0.4488 | 381/381 | 175/206/206 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=0,hold_frames=4 | 0.5556 | 357/381 | 210/171/147 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=0,hold_frames=6 | 0.6127 | 375/381 | 236/145/139 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=0,hold_frames=6 | 0.7195 | 349/381 | 268/113/81 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=0,hold_frames=6 | 0.5135 | 306/381 | 182/199/124 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=0,hold_frames=6 | 0.6275 | 280/381 | 213/168/67 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=0,hold_frames=8 | 0.6240 | 351/381 | 233/148/118 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=0,hold_frames=8 | 0.7325 | 324/381 | 263/118/61 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=0,hold_frames=8 | 0.5087 | 289/381 | 174/207/115 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=0,hold_frames=8 | 0.6264 | 262/381 | 207/174/55 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=3,hold_frames=4 | 0.5241 | 486/381 | 233/148/253 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=3,hold_frames=4 | 0.6392 | 467/381 | 281/100/186 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=3,hold_frames=4 | 0.4499 | 381/381 | 176/205/205 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=3,hold_frames=4 | 0.5577 | 357/381 | 211/170/146 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=3,hold_frames=6 | 0.6138 | 375/381 | 237/144/138 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=3,hold_frames=6 | 0.7205 | 349/381 | 269/112/80 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=3,hold_frames=6 | 0.5141 | 306/381 | 182/199/124 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=3,hold_frames=6 | 0.6281 | 280/381 | 213/168/67 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=3,hold_frames=8 | 0.6251 | 351/381 | 234/147/117 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=3,hold_frames=8 | 0.7330 | 324/381 | 264/117/60 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=3,hold_frames=8 | 0.5093 | 289/381 | 174/207/115 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=3,hold_frames=8 | 0.6264 | 262/381 | 207/174/55 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=6,hold_frames=4 | 0.5236 | 486/381 | 233/148/253 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=6,hold_frames=4 | 0.6418 | 466/381 | 281/100/185 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=6,hold_frames=4 | 0.4457 | 381/381 | 174/207/207 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=6,hold_frames=4 | 0.5561 | 357/381 | 211/170/146 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=6,hold_frames=6 | 0.6138 | 375/381 | 237/144/138 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=6,hold_frames=6 | 0.7211 | 349/381 | 269/112/80 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=6,hold_frames=6 | 0.5106 | 306/381 | 181/200/125 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=6,hold_frames=6 | 0.6257 | 280/381 | 213/168/67 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | fixed | ball_ownership | date_back=6,hold_frames=8 | 0.6257 | 351/381 | 234/147/117 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | clean | oracle | ball_ownership | date_back=6,hold_frames=8 | 0.7336 | 324/381 | 264/117/60 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | fixed | ball_ownership | date_back=6,hold_frames=8 | 0.5075 | 289/381 | 173/208/116 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | noisy | oracle | ball_ownership | date_back=6,hold_frames=8 | 0.6252 | 262/381 | 207/174/55 | TIKI-13 sweep date_back x hold |
| 2026-11-15 | idsse | fixed | closest_row8 | - | 0.3355 | 533/1011 | 264/747/269 | TIKI-13 reference (also logged by harness) |
| 2026-11-15 | real | fixed | ball_ownership | - | n/a | 330 poss, 153 stoppages, 43% D | TIKI-13 real-match ballpark via run_real_variant.py (row 8: 420 poss, 152 stoppages, 43% D). Turnover bursts under 25 frames 5 (row 8: 14), spells under 12 frames 4 (3), spell p10/p50/p90 1.5/7.7/25.6 s (1.2/5.2/20.8), home share 0.60 (0.58). 153 = the dead mask's own D-run count; row 8 shows 152 because it leaves the first 267 live frames of the second half as D. Public 5-min score is a pipeline check only. |
| 2026-11-15 | summary | both | ball_ownership | defaults | - | - | - | TIKI-13 sweeps (zone 1.0/1.25/1.5 x turn 10/15; dspeed 4/5 x min_spell 0/8/12; date_back -6..6 x hold 4/6/8): zone 1.0 clearly best (1.25: -0.03, 1.5: -0.06); every other knob moves spellF1 by under 0.012 (noise); hold 4 over-fragments (486 spells). Defaults kept. Defaults vs row 8: clean 0.6240/0.5025, noisy 0.5087/0.4444, clean oracle 0.7325/0.5932, noisy oracle 0.6264/0.5631, idsse 0.4020/0.3355, idsse oracle 0.4961/0.3995; missed@0.5 lower on all six. |
| 2026-11-15 | clean | fixed | ball_ownership | - | 0.6240 | 351/381 | 233/148/118 | TIKI-13 confirm on committed harness |
| 2026-11-15 | clean | oracle | ball_ownership | - | 0.7325 | 324/381 | 263/118/61 | TIKI-13 confirm on committed harness |
| 2026-11-15 | noisy | fixed | ball_ownership | - | 0.5087 | 289/381 | 174/207/115 | TIKI-13 confirm on committed harness |
| 2026-11-15 | noisy | oracle | ball_ownership | - | 0.6264 | 262/381 | 207/174/55 | TIKI-13 confirm on committed harness |
| 2026-11-15 | idsse | fixed | ball_ownership | - | 0.4020 | 572/1011 | 323/688/249 | TIKI-13 confirm on committed harness |
| 2026-11-15 | idsse | oracle | ball_ownership | - | 0.4961 | 534/1011 | 395/616/139 | TIKI-13 confirm on committed harness |
