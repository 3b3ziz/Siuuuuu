# How data companies define "who has the ball"

Research notes, Nov 2026. Question: how do football data companies, leagues and federations define and count ball possession, and where do their rules disagree with the challenge's rule? Every claim links to the document that owns it. Where I only saw a search snippet, or couldn't reach the page, I say so. Nothing here is about our own match.

## What matters for us

- Nobody publishes the exact rule behind a per-frame "which team has the ball" flag in tracking data. Not DFL, not Metrica, not LaLiga. We have to learn it from data.
- DFL's paper says its flag follows "the player in control of the ball". In practice it flips at the first touch. On our 7 Bundesliga games it switched to the defending team on 17 of 20 blocked shots, a median of about 0.16 s after the shot.
- So our Bundesliga training labels switch on blocks and touches, while the challenge says a touch without control isn't a switch. Expect the two keys to disagree on blocks, parries and loose balls.
- FIFA counts a third state, "in contest", for loose balls, blocks, rebounds off a save and aerial duels. The challenge has no such state: those frames stay with the last team that had the ball.
- Metrica, the organisers' company, says a player has the ball "as soon as they touch" it. But an opponent's touch doesn't count if the pass still arrives. Their event list also files blocks and saves as the defending team "recovering" the ball. Our practice answer key copies that, so it flips on blocks and saves too.
- Two tracking companies document a simple rule. SkillCorner switches only when the other team's player has the ball under control, and keeps the last team through loose spells. Second Spectrum's flag is literally "last touch".
- Event companies (Opta, StatsBomb, Wyscout) only switch possession when the other team gains control. Wyscout says outright that lost duels and quick rebounds don't break a possession. They only disagree on stoppages: Opta lets a possession run on through a corner, while the challenge always ends it at a stoppage.

## Words used

- **Event data**: a list of on-ball actions (pass, shot, tackle) typed in by human operators, each with a time and a player.
- **Tracking data**: x, y positions of all players and the ball, 25 times a second, from cameras.
- **Per-frame possession flag**: a column in tracking data that names a team (home or away) for every frame.
- **Ball status / alive-dead flag**: a per-frame column saying whether play is running.
- **Sequence** (Opta): one team's spell on the ball, ended by a defensive action, a stoppage or a shot. A **possession** is one or more sequences in a row by the same team.
- **In contest** (FIFA): ball in play, but neither team has it under control.
- **Player possession** (SkillCorner): a player has the ball under control, from first touch to last touch.

---

## 1. DFL / Sportec Solutions (our training data)

**What's published:**

- The open dataset paper says the ball's position data carries `BallPossession` (1 = home, 2 = away) and `BallStatus` (0 = inactive, 1 = active). "The ball possession is defined by the player in control of the ball. The match state is inactive when the match is interrupted by the referee, for example after a foul or during a substitution" ([Bassek et al. 2025, Sci. Data](https://www.nature.com/articles/s41597-025-04505-y)).
- The tracking is TRACAB Gen5, 16-20 cameras at 25 Hz. "All data are visually controlled by live operators for plausibility and undergo a final quality check after the game" ([Bassek et al. 2025](https://www.nature.com/articles/s41597-025-04505-y)). The paper does **not** say whether `BallPossession` comes from operators, an algorithm or both.
- All data categories are "defined in the Catalogue of Definitions published by the DFL", cited as *Catalogue of Definitions Official Match Data, Version 5.1* (DFL, 2020) ([Bassek et al. 2025](https://www.nature.com/articles/s41597-025-04505-y)). Another paper using DFL data cites the German version as "document not publicly accessible" ([Frontiers in Psychology 2023](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1197039/full)). **I could not find a public copy.**
- That same paper defines a possession (its own reading, not DFL's wording) as "a phase where one team is controlling the ball", ended when the opponent gains control or play stops: "foul, offside, goal, final whistle, ball out of bounds" ([Frontiers 2023](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1197039/full)).
- A 2025 proposal for a common football data format adds optional per-frame fields `ball_poss_team_id` and `ball_poss_status`, "the level of control (e.g., controlled, contested, …)" ([CDF paper, Appendix B.4, Table 10](https://arxiv.org/abs/2505.15820)). So the industry does think of "contested" as a separate state. The DFL files we have don't carry it.

**What our own 7 games show** (my check, not a published rule; script reads the raw DFL XML in `data/bundesliga/`):

- `BallPossession` still names a team on dead-ball frames. That matches the challenge note that their tracking "names a team even while the ball is out of play — whoever will restart, or touched it last" (`CHALLENGE.md`).
- **Shots.** DFL shot events carry a `CalculatedFrame` that lines up with the tracking, so we can see what the flag does right after a shot.
  - How I checked: start at the shot's `CalculatedFrame` and step forward up to 5 s while `BallStatus` = 1. A "switch" is the first frame where `BallPossession` isn't the shooter's team. "Held" means it stayed that way for 1 s or until play stopped.
  - I kept only the 101 shots where the flag pointed at the shooter's team on the shot frame. Left out: 42 shot events my parser couldn't read a team from, and 12 where the flag already pointed at the other team when the shot was taken. My parser found no synced frame for 16 more of the paper's 171 shots.

| Shot result (DFL event) | Flag switched to the defending team while ball still live | Median time to switch | Stayed with shooter |
|---|---|---|---|
| Blocked shot | 17 of 20 (14 held; 3 came back within 1 s) | 4 frames (0.16 s) | 3 |
| Saved shot (catches and parries together) | 28 of 29 | 24 frames (1 s; *my guess: mostly the ball's flight to the keeper*) | 1 |
| Off woodwork | 2 of 2 | 13 frames | 0 |
| Goal | 3 of 13 | – | 10 (ball went dead first) |
| Wide | 3 of 36 | – | 33 (ball went dead first) |

  So the DFL flag hands a block to the blocker's team within a fraction of a second, whether or not they then control it. The challenge says a touch without control isn't a switch.
- **Duels.** DFL's event data puts an explicit `PossessionChange` true/false on every duel (`TacklingGame`). Of 328 aerial duels in the 7 games, 215 are tagged `PossessionChange="false"`. The commonest is a header won "withoutBallControl" (119). So DFL's own event operators agree that most won headers don't change possession. These duel events have no synced frame, so I didn't check the per-frame flag around them.
- This fits the team's earlier finding (`docs/notes.md`): 40-50% of DFL possessions are under 3 s, so the flag flips on single touches.

**Snippet only, not confirmed:** a search snippet of a Tübingen PhD thesis on Bundesliga data described "manually collected attributes: ball possession and status of play" ([thesis PDF](https://publikationen.uni-tuebingen.de/xmlui/bitstream/handle/10900/124679/Dissertation_PBA_Publication_version.pdf)). The download failed twice, so I couldn't check the wording. If true, the flag is typed in by operators, not computed.

## 2. FIFA: Enhanced Football Intelligence (EFI) "possession control"

- Four states over the match: Team A, Team B, **In Contest** ("in play but with neither team in controlled possession") and Out of Play. "These Possession States are calculated based on the sequence of events performed by the players on the pitch" ([EFI explanation v1.1, July 2023, p.1](https://fifatrainingcentre.com/media/native/tournaments/womens-world-cup/2023/FIFA%20Enhanced%20Football%20Intelligence%20(EFI)%20Explainations_EN%20v1.1.pdf); same text in [v1.0, Oct 2022](https://www.fifatrainingcentre.com/media/native/world-cup-2022/Enhanced%20Football%20Intelligence%20EN.pdf)). So it's **event-chain based and time-weighted**, not a pass count.
- What starts "in contest", from the same page: in an aerial duel, "contact on the ball by a player during the contest will initiate a loose ball state". When "a defender performs a defensive action, blocking a pass from reaching its intended target", the ball "enters a loose ball state". "Several other events" do the same, but they aren't listed.
- FIFA's glossary adds triggers: "duels, aerial duels and physical duels", and a ball "played into space" with two players racing for it. The ball stays in contest "when neither competing player gains controlled possession". This happens "when a ball falls loose following a duel, after a clearance, if the ball rebounds from a goalkeeper who initially saves a shot, or from a block or deflection. Misplaced passes can also leave the ball in contest" ([FIFA Training Centre, "In contest"](https://www.fifatrainingcentre.com/en/resources-tools/football-language/in-contest/in-contest.php)). The page doesn't say what ends the state. Presumably someone gaining control.
- No minimum duration or pass count is published.
- **Ball recovery time** is measured from a team's "last ball control event" to its "first ball control event" of the next possession. In between there can be an opponent possession "and/or a ball in contest state" ([EFI v1.1, p.7](https://fifatrainingcentre.com/media/native/tournaments/womens-world-cup/2023/FIFA%20Enhanced%20Football%20Intelligence%20(EFI)%20Explainations_EN%20v1.1.pdf)). So FIFA ties possession to *control* events, not touches.
- **Outside reimplementation (a master's thesis, not FIFA's code):** it used FIFA-supplied World Cup 2022 tracking, which "already provides raw possession information, labeling frames as either home team in-possession or away team in-possession". It then marked a frame "in contest" when at least two opponents were within a 2 m circle of the ball (tuned between 1 and 2.5 m). FIFA's published in-contest shares for the three matches it checked were 7.6-15% of ball-in-play time ([Univ. Zurich thesis, Sections 5.1-5.2 and 6.1](https://capuana.ifi.uzh.ch/publications/PDFs/24098_An_Open_Source_Implementation_of_FIFA_s_Enhanced_Football_Intelligence.pdf)). So FIFA's raw tracking also has only a two-team flag. "In contest" is a layer on top.
- **For us:** the challenge folds "in contest" into "last team that had it". So roughly 8-15% of live time is exactly where the challenge's key and a touch-based flag can differ.

## 3. Metrica Sports (the organisers)

From Metrica's public event definitions ([events-definitions.pdf](https://github.com/metrica-sports/sample-data/blob/master/documentation/events-definitions.pdf)):

- **Possession starts at a touch:** "a player is regarded as being in possession as soon as they touch the ball or make a conscious decision to hold off on collecting the ball". Possession ends when "another player takes over possession", "a shot is deflected off the goal's woodwork or another player", "the ball is significantly deflected by the referee", or "the ball goes out of play".
- **But a touch by an opponent isn't always a loss:** "Possession is not considered lost when an opposing player's interference does not have a significant impact, i.e. when the opponent manages to get a touch in, but the attempted play still reaches its intended target or the player originally in possession retains control of the ball." This matches the challenge's "deflection of a pass that doesn't intercept it" rule.
- **RECOVERY** = "The player significantly interferes with the opponent's possession". Its subtypes include **BLOCKED** (a defender, not the last in line, "deflects a SHOT significantly; they may continue to keep possession") and **SAVED** (the keeper or last defender "averts a SHOT that is ON TARGET").
- **CHALLENGE** subtypes include **AERIAL** ("two or more players engage in a duel when receiving the ball at shoulder height or higher").
- No pass-count or time threshold appears in the event document.
- **The tracking-side rule (how Metrica's owning-team flag is made) is not published.** The challenge only says the answer key is "derived from corrected tracking data … a frame is `D` where the corrected tracking marks the ball dead, and otherwise takes the team the tracking names as owning it" (`CHALLENGE.md`). It also says the owner field holds "whoever will restart, or touched it last" while the ball is dead.
- **Practice-key consequence:** our Metrica Sample Game 3 answer key (`prep/sample_game.py`) hands the ball to the team of every RECOVERY. In that game, 6 RECOVERY events are SAVED and 3 are BLOCKED. So the practice key flips on saves and blocks, where the challenge's definition might not. It's a small number, but worth knowing.

## 4. LaLiga / Mediacoach

- LaLiga's "Beyond Stats" page says its data points "are processed by MediaCoach". It defines metrics built on possessions ("Players per possession", "Dangerous possessions": "Possessions that end with an unblocked shot on goal"). It **does not define a possession** ([LaLiga Beyond Stats](https://www.laliga.com/en-GB/beyondstats)).
- A club research blog (not LaLiga's own page) says Mediacoach physical data came from TRACAB ("El rendimiento físico fue recogido mediante el sistema de tracking TRACAB utilizado por Mediacoach"). It defines effective playing time as match time minus pauses, substitutions, goals and injuries ([Barça Innovation Hub blog](https://barcainnovationhub.fcbarcelona.com/es/blog/corren-menos-los-jugadores-cuando-su-equipo-tiene-la-posesion-del-balon/)).
- TRACAB's raw format carries a per-frame ball owner (H/A) and Alive/Dead ([kloppy TRACAB parser](https://github.com/PySport/kloppy/blob/a9651eba7c4dbbe2d2fc6d4cffb4aea63fadac11/kloppy/infra/serializers/tracking/tracab/parsers/raw_data/dat.py#L111-L114)). DFL also uses TRACAB.
- **Unconfirmed:** whether the challenge's LaLiga tracking is TRACAB, and whether its owner flag follows the same rule as DFL's. If it does, DFL's touch-based behaviour (section 1) is the best guide we have to the answer key. Looking at how the 5 public minutes handle a block is fine (CHALLENGE.md invites it). But it must not be used to pick between our versions or tune anything (team rule).
- I found no public LaLiga or Mediacoach definition of possession percentage.

## 5. Other tracking companies

### SkillCorner (broadcast tracking)

The clearest published tracking-based rule I found.

- **Player possession:** "the player needs to be in control of the ball, i.e. able to do a pass, shot or carry. A player possession starts from the first touch of the player up to the last touch … If a player is not in control of the ball then it does not qualify as a player possession. Typically, if a player intercepts the ball without controlling it afterward, like for blocks, it does not count as a player possession" ([Dynamic Events spec](https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Dynamic%20Events/20250216%20-%20Dynamic%20Events%20CSV%20Specifications.pdf), "Event Definitions").
- **Team possession, from player possessions** ([Phases of Play spec, "How It Works"](https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Phases%20of%20Play/20250216%20-%20Phases%20of%20Play%20CSV%20Specifications.pdf)):
  1. When a player has possession, their team is in possession.
  2. Two player possessions in a row by Team A: Team A keeps it in between.
  3. Possession shifts from A to B "at the start of their player possession event".
  4. More than 30 s with no player possession, set piece or goal: ball treated as out.
- **Disruption:** "when a defender blocks a shot and unsuccessfully attempts to clear the ball, allowing the attacking team to regain possession", the defender's spell is labelled 'Disruption'. Such "temporary disruptions are not considered as ending the team possession" ([same spec](https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Phases%20of%20Play/20250216%20-%20Phases%20of%20Play%20CSV%20Specifications.pdf); [Dynamic Events spec](https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Dynamic%20Events/20250216%20-%20Dynamic%20Events%20CSV%20Specifications.pdf)).
- **"Chaotic" phase** = "a short contested possession". To avoid it, a phase needs "at least three passes with no more than one header" **or** "at least 5 seconds of possession". "Clearances under pressure are always considered chaotic" (Phases of Play spec). These are the same two proxies the challenge suggests (more than two passes, a few seconds).
- In the open tracking files, each frame has `possession: {player_id, group}` ([SkillCorner opendata README](https://github.com/SkillCorner/opendata)). kloppy treats a frame with no possessing group as dead ball ([kloppy SkillCorner parser](https://github.com/PySport/kloppy/blob/a9651eba7c4dbbe2d2fc6d4cffb4aea63fadac11/kloppy/infra/serializers/tracking/skillcorner.py#L103-L106)).

### Second Spectrum

- In Second Spectrum's tracking JSON, the per-frame owning team comes from a field called `lastTouch` ("home"/"away"), and ball state from `live` ([kloppy Second Spectrum parser, lines 99-102](https://github.com/PySport/kloppy/blob/a9651eba7c4dbbe2d2fc6d4cffb4aea63fadac11/kloppy/infra/serializers/tracking/secondspectrum.py#L99-L102)). By its name it's a last-touch rule. **I found no Second Spectrum document defining it**, so treat "last touch" as inferred from the field name.

## 6. Event-data companies and competitions

### Opta / Stats Perform

- **Sequences and possessions:** "Sequences are defined as passages of play which belong to one team and are ended by defensive actions, stoppages in play or a shot." "A sequence starts with a player making a controlled action on the ball. This includes passes but not defensive events such as tackles and interceptions" (unless followed by a controlled action). "Possessions are defined as one or more sequences in a row belonging to the same team." "A possession is ended by the opposition gaining control of the ball" ([The Analyst, "Sequences and Possessions"](https://theanalyst.com/articles/possessions-and-sequences-in-football); same in [Opta stats definitions](https://theanalyst.com/articles/opta-football-stats-definitions)).
- **Stoppages don't end an Opta possession.** Their example: a saved shot that goes out for a corner ends the sequence, but the possession goes on until the opponent gains control. "The save … does not initiate a sequence" ([The Analyst](https://theanalyst.com/articles/possessions-and-sequences-in-football)). That's the opposite of the challenge, where a stoppage always ends a possession.
- Other definitions ([Opta stats definitions](https://theanalyst.com/articles/opta-football-stats-definitions)). **Recovery**: "a player recovers the ball in a situation where neither team has possession". **Duel**: "a 50-50 contest between two players of opposing sides". **Aerial duel**: "The player that wins the ball is deemed to have won the duel". **Touches**: every event where a player touches the ball.
- **Possession %:** traditionally the share of passes. A search snippet of a Stats Perform page says: "the most commonly used method was to look at the share of passes that a team has in a game. This forms the Possession % figure that is commonplace in most box scores" ([Stats Perform, Phases of Play intro](https://www.statsperform.com/resource/phases-of-play-an-introduction)). **Snippet only: the page returned 403 to me.** Whether Opta's current possession % is still pass-share is unconfirmed.

### StatsBomb (Hudl)

- `possession`: "A single possession denotes a period of play in which the ball is in play and a single team is in control of the ball." "New possession are triggered after a team demonstrate they've established control of the ball." "A new possession can begin even if the same team has possession of the ball, for example, a blocked pass goes out for a throw in for the same team" ([StatsBomb Open Data Specification v1.1](https://github.com/statsbomb/open-data/blob/master/doc/StatsBomb%20Open%20Data%20Specification%20v1.1.pdf), event attributes). That matches the challenge: a stoppage ends a possession even if the same team restarts.
- `possession_team` is "the team that started this possession in control of the ball", and it also appears "on opposition events like tackles attempted during the possession" (same spec). So a tackle attempt or lost duel doesn't switch it.
- Outcomes show touch ≠ control. 50/50 "Success To Opposition" = "wins the 50/50 contest but knocks the ball for their opponent's possession". Tackle "Won" = "ended up in possession of the tackler", vs "Lost In Play". Interception "Success In Play" = "knocked the ball to a teammate" (same spec).
- Possession % method: **not found** in a primary source.

### Wyscout (Hudl)

- **Time-based.** "Wyscout uses a ball possession percentage calculation approach based on pure time spent in possession of the ball. A Possession is a sequence of events with the ball of the same team. Time where the ball is out of play … is not counted as possession for any of the two teams. Opponent actions that do not constitute a meaningful ball possession, like lost duels, missed balls and rebounds that are immediately picked up, do not break possessions." The page also notes "other data providers might use a simpler algorithm, which only takes into account accurate passes" ([Wyscout glossary, Ball possession](https://dataglossary.wyscout.com/ball_possession/)).
- Open-play possession lengths: short 0-10 s, medium 10-20 s, long 20-45 s, very long 45 s+ (same page).
- **Loss:** "Events where the ball goes off the field off a player are, by definition, losses. Every unsuccessful pass is a loss … Suffered foul, while ending a possession, is not considered a loss" ([Wyscout, Loss](https://dataglossary.wyscout.com/loss/)).
- **Recovery** is recorded "at the point where the player of the team beginning the possession touches the ball". Possessions starting after the ball goes out or after a foul aren't recoveries ([Wyscout, Recovery](https://dataglossary.wyscout.com/recovery/)).
- **Aerial duel** is won by "the player who touches the ball first, no matter what happens next". But a lost duel doesn't break the possession (above) ([Wyscout, Aerial duel](https://dataglossary.wyscout.com/aerial_duel/)).

### UEFA

- UEFA's 2025/26 Champions League physical report uses Hawk-Eye tracking plus **Opta's** sequence and possession definitions word for word. "Ball in play: the ball is considered in play whenever it is inside the field of play and the match has not been stopped by the referee." "Ball recoveries: … Full control must be established and the player who is deemed to have the first controlled action is awarded the ball recovery event." Across that competition, possession changed **1.46 times per minute** on average ([UEFA UCL Physical Analysis 2025/26, methodology and glossary](https://editorial.uefa.com/resources/02a9-218eac6a2763-c71506c6e226-1000/ucl_physical-analysis_2026.pdf)). That rate uses Opta's definition, where possessions run on through stoppages, so it isn't directly comparable to ours.
- How the possession % on UEFA's match centre is computed: **not found**.

### Sofascore

- Only a Sofascore article describing possession as "the amount of time a team dominates the ball" ([Sofascore news](https://www.sofascore.com/news/understanding-the-effect-of-possession-pass-success-percentage-and-shots-on-target-in-football-matches), search snippet only). No method document found. **Unconfirmed.**

---

## Edge cases: where the rules disagree

"Challenge" is our reading of `CHALLENGE.md`. "Not stated" means the source doesn't say. *Italics* = my inference, not the source's words. "DFL flag" is what the per-frame flag did on our 7 games (section 1).

| Situation | Challenge | Metrica events | FIFA EFI | Opta | StatsBomb | Wyscout | SkillCorner | DFL flag (observed) | Second Spectrum |
|---|---|---|---|---|---|---|---|---|---|
| **Blocked shot, ball loose** | No switch unless the blocker's team then controls it | Shooter's possession ends. Blocker gets RECOVERY/BLOCKED (our practice key switches) | In contest | Shot ends the sequence; possession ends only when the opponent gains control. *A block likely doesn't start a sequence, like a save* (stated for the save only) | New possession only once control is "established" | "Rebounds that are immediately picked up do not break possessions" | Block without control isn't a player possession *→ no switch*; a failed clearance after a block = "Disruption", possession not ended | Switches to blockers in 17/20, median 0.16 s after the shot | *Switches (last touch)* |
| **Keeper parry, ball stays live** | *No switch unless the keeper's team then controls it* (not stated) | RECOVERY/SAVED (our practice key switches) | In contest ("rebounds from a goalkeeper who initially saves") | Save doesn't start a sequence | Not stated | *Rebound picked up at once = no break* | *Not a player possession unless controlled* | Saved shots: 28/29 switch (catches and parries not separated) | *Switches* |
| **Keeper catches** | Switch (controlled) | RECOVERY/SAVED | *Keeper's team* | *Keeper's team* | *Keeper's team* | *Keeper's team* | Keeper possession (hand pass field exists) | Switches | *Switches* |
| **50/50 header, ball loose** | No switch unless the winner's team then controls it | Touch = possession by the definition; CHALLENGE/AERIAL logged (our practice key: no switch) | In contest | Winner = player who "wins the ball"; *not a controlled action, so no new sequence* | 50/50 outcomes separate "to team" vs "to opposition" | Duel won by first touch, but a lost duel "do[es] not break possessions" | Not stated (headers can be possessions; 2+ headers makes a phase "chaotic") | Not measured. DFL *events* tag 215/328 aerial duels `PossessionChange="false"` | *Switches to header's team* |
| **Pass deflected but still reaches teammate** | No switch | Not lost: "attempted play still reaches its intended target" | *In contest briefly* ("block or deflection") | Not stated | `possession_team` stays | "Missed balls" don't break | Touch without control isn't a player possession | Not measured | *Brief switch* |
| **Tackle pokes ball loose** | No switch until someone controls | Not stated | In contest | Tackles don't start a sequence unless followed by a controlled action | Tackle "Won" vs "Lost In Play" | Recovery recorded when the new team's player touches it | No switch until a player possession | Not measured | *Switches* |
| **Defender fouls attacker** | Dead ball (D). Restart has a clear possessor | FAULT RECEIVED, play out | Out of play | Stoppage ends the sequence, not the possession | Not stated | "Suffered foul … is not considered a loss" | Not stated | BallStatus 0 (Bassek: inactive "after a foul") | `live` false |
| **Foul throw** | Not stated. Laws: "retaken by the opposing team" ([IFAB Law 15](https://www.theifab.com/laws/latest/the-throw-in/)), so *D, then the other team restarts* | Not stated (RETAKEN subtype exists) | Not stated | Not stated | Not stated | Not stated | Not stated | Not measured | Not stated |
| **Clearance into touch** | Live until out: *stays with the attackers unless the clearer controlled it*, then D | BALL OUT on the clearer | *In contest* ("after a clearance"), then out of play | Stoppage ends the sequence; possession goes to whoever controls next | Same team restarting after a block out = new possession | Ball off a player into touch = "by definition" a loss | "Clearances under pressure are always considered chaotic" | Not measured | *Clearer's team (last touch)* |
| **Shot hits the woodwork, stays live** | *No switch* (no one else touched it) | Possession ends ("deflected off the goal's woodwork") | Not stated | Shot ends the sequence | Not stated | Not stated | Not stated | 2/2 switched (tiny sample, unclear who touched next) | *Shooter's team* |
| **Long pass in flight** | Passer's team until the other team controls it | Passer's possession until "another player takes over" | Not stated | Not stated | Not stated | Loss recorded at the pass's end point | Switches "at the start of" the receiver's player possession | Not measured | Passer's team until touched |

**What to take from the table:**

- The challenge is closest to **SkillCorner's** written rule (switch only at the start of the other team's *controlled* possession, carry the last team through loose spells) and to **Wyscout/StatsBomb** in spirit.
- Our two practice keys are both more trigger-happy than the challenge text. **DFL's flag** flips at a touch (blocks, saves). **Our Metrica practice key** flips on RECOVERY/BLOCKED and RECOVERY/SAVED.
- The challenge's answer key comes from a per-frame tracking flag, like DFL's. So it may *also* be touch-based in practice, whatever the written definition says. We can't tell without seeing it. The challenge's own words point both ways: "touched it last" for dead balls, "controlled" for live ones.

## Open questions

- Is the LaLiga tracking behind the answer key TRACAB, and is its owner flag made by operators or by an algorithm? Is it touch-based like DFL's, or control-based?
- Can we get the DFL *Catalogue of Definitions Official Match Data* (v5.1)? It's cited as not public.
- Does the Tübingen thesis really say DFL's possession flag is manually collected? The PDF wouldn't download.
- A cheap extra check: sync DFL duel events (`TacklingGame` with `PossessionChange="false"`) to tracking, using the offset from nearby shots' `CalculatedFrame`. Then see whether the per-frame flag flips on won headers too.

## Only seen in snippets, or not confirmed

- Stats Perform quote on pass-share possession % (page returned 403) ([link](https://www.statsperform.com/resource/phases-of-play-an-introduction)).
- Tübingen thesis: "manually collected attributes: ball possession and status of play" ([link](https://publikationen.uni-tuebingen.de/xmlui/bitstream/handle/10900/124679/Dissertation_PBA_Publication_version.pdf)).
- Hudl StatsBomb phases of play: "open play possessions begin in transition and can accumulate into control over time" ([Hudl blog](https://www.hudl.com/blog/phases-of-play-hudl-statsbomb)).
- DFL page saying its official data includes "ball possession" ([DFL, STS data feeds](https://www.dfl.de/en/innovation/the-sts-data-feeds-supply-match-information-in-even-greater-detail/)).
- Third-party blogs claiming Opta switched from pass share to a possessions-based method in 2017, and that Sofascore counts on-ball events. No primary source found. Not used.

## Sources

- Bassek et al. 2025, *An integrated dataset of spatiotemporal and event data in elite soccer*, Sci. Data: https://www.nature.com/articles/s41597-025-04505-y
- Frontiers in Psychology 2023 (DFL data, possession definition, catalogue citation): https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1197039/full
- Common Data Format (CDF) paper, 2025: https://arxiv.org/abs/2505.15820
- FIFA EFI explanation v1.1 (July 2023): https://fifatrainingcentre.com/media/native/tournaments/womens-world-cup/2023/FIFA%20Enhanced%20Football%20Intelligence%20(EFI)%20Explainations_EN%20v1.1.pdf
- FIFA EFI explanation v1.0 (Oct 2022): https://www.fifatrainingcentre.com/media/native/world-cup-2022/Enhanced%20Football%20Intelligence%20EN.pdf
- FIFA Training Centre, "In contest": https://www.fifatrainingcentre.com/en/resources-tools/football-language/in-contest/in-contest.php
- Univ. Zurich master's thesis, open-source EFI implementation: https://capuana.ifi.uzh.ch/publications/PDFs/24098_An_Open_Source_Implementation_of_FIFA_s_Enhanced_Football_Intelligence.pdf
- Metrica Sports event definitions: https://github.com/metrica-sports/sample-data/blob/master/documentation/events-definitions.pdf
- LaLiga Beyond Stats: https://www.laliga.com/en-GB/beyondstats
- Barça Innovation Hub blog (Mediacoach uses TRACAB): https://barcainnovationhub.fcbarcelona.com/es/blog/corren-menos-los-jugadores-cuando-su-equipo-tiene-la-posesion-del-balon/
- kloppy parsers (commit a9651eb): [TRACAB](https://github.com/PySport/kloppy/blob/a9651eba7c4dbbe2d2fc6d4cffb4aea63fadac11/kloppy/infra/serializers/tracking/tracab/parsers/raw_data/dat.py#L111-L114), [Second Spectrum](https://github.com/PySport/kloppy/blob/a9651eba7c4dbbe2d2fc6d4cffb4aea63fadac11/kloppy/infra/serializers/tracking/secondspectrum.py#L99-L102), [SkillCorner](https://github.com/PySport/kloppy/blob/a9651eba7c4dbbe2d2fc6d4cffb4aea63fadac11/kloppy/infra/serializers/tracking/skillcorner.py#L282-L290)
- SkillCorner open data README: https://github.com/SkillCorner/opendata
- SkillCorner Dynamic Events spec: https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Dynamic%20Events/20250216%20-%20Dynamic%20Events%20CSV%20Specifications.pdf
- SkillCorner Phases of Play spec: https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Phases%20of%20Play/20250216%20-%20Phases%20of%20Play%20CSV%20Specifications.pdf
- Opta / The Analyst, sequences and possessions: https://theanalyst.com/articles/possessions-and-sequences-in-football
- Opta / The Analyst, stats definitions: https://theanalyst.com/articles/opta-football-stats-definitions
- StatsBomb Open Data Specification v1.1: https://github.com/statsbomb/open-data/blob/master/doc/StatsBomb%20Open%20Data%20Specification%20v1.1.pdf
- Wyscout glossary: [Ball possession](https://dataglossary.wyscout.com/ball_possession/), [Loss](https://dataglossary.wyscout.com/loss/), [Recovery](https://dataglossary.wyscout.com/recovery/), [Aerial duel](https://dataglossary.wyscout.com/aerial_duel/)
- UEFA Champions League Physical Analysis 2025/26: https://editorial.uefa.com/resources/02a9-218eac6a2763-c71506c6e226-1000/ucl_physical-analysis_2026.pdf
- IFAB Law 15, the throw-in: https://www.theifab.com/laws/latest/the-throw-in/
- Related, already in `possession-without-ball.md`: Vidal-Codina et al. 2022 (https://arxiv.org/abs/2202.00804), Link & Hoernig 2017 (https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0179953)
