"""Answer keys in the organisers' "controlled possession" style (CHALLENGE.md).

The Bundesliga keys (DFL's own ball-owning team) flip on every touch: about half their
possessions last under 3 s. The organisers say a touch without control, a deflection or an aerial
duel without control is not a change of possession, and give "a player keeps the ball for a few
seconds" as a proxy. So: a possession shorter than MIN_S seconds goes to the team before it
(same live stretch), or to the team after it at the start of a stretch. Mean possession then
lands at 9-15 s (raw DFL keys: 5.5-9 s). Bench only: a second yardstick, never a submission.
"""

from team_fixes import merge_short

MIN_S = 2.0


def controlled(gt, min_s=MIN_S):
    return merge_short(gt, min_s)
