/-!
# A pure model of `prep/sticky.py` `sticky_segment`

The Python labels one half frame by frame. `near[i]` is the team whose player is alone (or
clearly closest) within the zone of the ball, or nothing. `dead[i]` marks stoppages. The rules:

* dead frames are `D`;
* inside each maximal live stretch, a team that is `near` for `k` frames in a row
  (`SWITCH_FRAMES`) is a confirmed switch, dated to the first of those frames, and only
  recorded when it differs from the previous confirmed team;
* the frames before the first confirmed switch of a stretch get that team (a restart belongs to
  the team that is first confirmed in it); each later switch holds until the next;
* a stretch with no confirmed switch keeps the team carried out of the previous stretch, or
  stays `D` when no team was confirmed yet.

`stickySegment` below is that algorithm on lists: `switches` is the inner loop, `paint` the
labelling of one stretch, `go` the walk over stretches. The theorems prove the shape properties
the rest of the pipeline relies on. `rules.segment_labels` generalises the same loop; the
`date_back` clamp it adds is modelled at the end of the file.
-/

namespace Segment

inductive Team | H | A
  deriving DecidableEq, Repr

inductive Label | H | A | D
  deriving DecidableEq, Repr

def Team.label : Team → Label
  | .H => .H
  | .A => .A

/-- The team carried into a stretch, as a label: nothing confirmed yet is `D`. -/
def carried : Option Team → Label
  | none => .D
  | some t => t.label

/-! ## The inner loop: confirmed switches of one live stretch -/

/-- State of the inner loop. Offsets count from the start of the stretch. -/
structure SwState where
  i : Nat                    -- offset of the frame about to be read
  runTeam : Option Team      -- `run_team`; `none` is the Python ''
  runStart : Nat             -- `run_start`
  acc : List (Nat × Team)    -- `switches`, in order of confirmation
  deriving DecidableEq, Repr

/-- Team of the last confirmed switch. -/
def lastTeam (acc : List (Nat × Team)) : Option Team := acc.getLast?.map Prod.snd

/-- `if near[i] != run_team: run_start = i`. -/
def newStart (st : SwState) (n : Option Team) : Nat :=
  if n = st.runTeam then st.runStart else st.i

/-- `if run_team and i - run_start + 1 == k and (no switches or last team differs): append`. -/
def newAcc (k : Nat) (st : SwState) (n : Option Team) : List (Nat × Team) :=
  match n with
  | none => st.acc
  | some t =>
    if st.i - newStart st n + 1 = k ∧ lastTeam st.acc ≠ some t then st.acc ++ [(newStart st n, t)]
    else st.acc

/-- One iteration of the inner loop on frame `n = near[i]`. -/
def swStep (k : Nat) (st : SwState) (n : Option Team) : SwState :=
  ⟨st.i + 1, n, newStart st n, newAcc k st n⟩

/-- The confirmed switches of one stretch: (offset, team), in order. -/
def switches (k : Nat) (near : List (Option Team)) : List (Nat × Team) :=
  (near.foldl (swStep k) ⟨0, none, 0, []⟩).acc

/-! ## Painting one stretch -/

/-- The team holding offset i: the last switch at or before i, else `first`. -/
def holder (first : Team) : List (Nat × Team) → Nat → Team
  | [], _ => first
  | (s, t) :: rest, i => if s ≤ i then holder t rest i else first

/-- Labels of a stretch of `len` frames from its switches; `team` is the team carried in. -/
def paint (team : Option Team) (sw : List (Nat × Team)) (len : Nat) : List Label :=
  match sw with
  | [] => List.replicate len (carried team)
  | (_, t₀) :: _ => (List.range len).map fun i => (holder t₀ sw i).label

/-- One live stretch: its labels and the team carried out of it. -/
def stretch (k : Nat) (team : Option Team) (near : List (Option Team)) : List Label × Option Team :=
  (paint team (switches k near) near.length, (lastTeam (switches k near)).or team)

/-! ## Walking the half -/

/-- `cur` is the live stretch being collected; a dead frame closes it and is labelled `D`. -/
def go (k : Nat) (team : Option Team) (cur : List (Option Team)) :
    List (Option Team × Bool) → List Label
  | [] => (stretch k team cur).1
  | (_, true) :: rest => (stretch k team cur).1 ++ Label.D :: go k (stretch k team cur).2 [] rest
  | (n, false) :: rest => go k team (cur ++ [n]) rest

/-- `sticky_segment(near, dead)` with `SWITCH_FRAMES = k`. -/
def stickySegment (k : Nat) (near : List (Option Team)) (dead : List Bool) : List Label :=
  go k none [] (near.zip dead)

/-! ## Sanity checks against the Python behaviour (k = 3 or 2) -/

example : stickySegment 3 [some .H, some .H, some .H, some .A, some .A, some .H, some .H, some .H]
    (List.replicate 8 false) = List.replicate 8 .H := by decide

example : stickySegment 3 [some .H, some .H, some .H, some .A, some .A, some .A, some .H]
    (List.replicate 7 false) = [.H, .H, .H, .A, .A, .A, .A] := by decide

example : stickySegment 2 [some .H, some .H, none, some .A, some .A] [false, false, true, false, false]
    = [.H, .H, .D, .A, .A] := by decide

example : stickySegment 2 [none, some .H, some .H, none, none] [true, false, false, true, false]
    = [.D, .H, .H, .D, .H] := by decide

example : stickySegment 2 [none, some .H, none] [false, true, false] = [.D, .D, .D] := by decide

/-! ## Output length equals input length -/

theorem paint_length (team : Option Team) (sw : List (Nat × Team)) (len : Nat) :
    (paint team sw len).length = len := by
  cases sw with
  | nil => simp [paint]
  | cons p rest => obtain ⟨s, t⟩ := p; simp [paint]

theorem stretch_length (k : Nat) (team : Option Team) (near : List (Option Team)) :
    (stretch k team near).1.length = near.length := by
  simp [stretch, paint_length]

theorem go_length (k : Nat) : ∀ (rest : List (Option Team × Bool)) (team : Option Team)
    (cur : List (Option Team)), (go k team cur rest).length = cur.length + rest.length
  | [], team, cur => by simp [go, stretch_length]
  | (_, true) :: rest, team, cur => by simp [go, stretch_length, go_length k rest] <;> omega
  | (n, false) :: rest, team, cur => by simp [go, go_length k rest] <;> omega

theorem length_eq (k : Nat) (near : List (Option Team)) (dead : List Bool)
    (h : near.length = dead.length) : (stickySegment k near dead).length = near.length := by
  simp [stickySegment, go_length, List.length_zip, h]

/-! ## Every dead frame is D -/

theorem go_dead (k : Nat) : ∀ (rest : List (Option Team × Bool)) (team : Option Team)
    (cur : List (Option Team)) (i : Nat) (n : Option Team),
    rest[i]? = some (n, true) → (go k team cur rest)[cur.length + i]? = some .D
  | [], _, _, i, _, h => by simp at h
  | (m, true) :: rest, team, cur, 0, n, _ => by
    simp only [go]
    rw [List.getElem?_append_right (by simp [stretch_length])]
    simp [stretch_length]
  | (m, true) :: rest, team, cur, i + 1, n, h => by
    simp only [go]
    rw [List.getElem?_append_right (by simp [stretch_length])]
    have hidx : cur.length + (i + 1) - (stretch k team cur).1.length = i + 1 := by
      simp [stretch_length]
    rw [hidx, List.getElem?_cons_succ]
    have := go_dead k rest (stretch k team cur).2 [] i n (by simpa using h)
    simpa using this
  | (m, false) :: rest, team, cur, 0, n, h => by simp at h
  | (m, false) :: rest, team, cur, i + 1, n, h => by
    simp only [go]
    have := go_dead k rest team (cur ++ [m]) i n (by simpa using h)
    rw [List.length_append, List.length_singleton] at this
    rw [show cur.length + (i + 1) = cur.length + 1 + i by omega]
    exact this

theorem dead_is_D (k : Nat) (near : List (Option Team)) (dead : List Bool) (i : Nat)
    (hi : i < near.length) (hd : dead[i]? = some true) :
    (stickySegment k near dead)[i]? = some .D := by
  unfold stickySegment
  have hz : (near.zip dead)[i]? = some (near[i], true) := by
    rw [List.getElem?_zip_eq_some]
    exact ⟨by simp, hd⟩
  have := go_dead k (near.zip dead) none [] i near[i] hz
  simpa using this

/-! ## A fully live stretch -/

theorem zip_false (l : List (Option Team)) :
    l.zip (List.replicate l.length false) = l.map (fun x => (x, false)) := by
  induction l with
  | nil => rfl
  | cons x l ih => simp [List.replicate_succ, List.zip_cons_cons, ih]

theorem go_alive (k : Nat) (team : Option Team) : ∀ (l : List (Option Team)) (cur : List (Option Team)),
    go k team cur (l.map fun x => (x, false)) = (stretch k team (cur ++ l)).1
  | [], cur => by simp [go]
  | x :: l, cur => by simp [go, go_alive k team l (cur ++ [x])]

/-- With no stoppage the half is one stretch and no team is carried in. -/
theorem live_labels (k : Nat) (near : List (Option Team)) :
    stickySegment k near (List.replicate near.length false) = (stretch k none near).1 := by
  simp [stickySegment, zip_false, go_alive]

/-! ## Facts about the inner loop -/

/-- Continuing a run of team t for m frames with no frame reaching length k changes nothing but i. -/
theorem foldl_cont (k : Nat) : ∀ (m i rs : Nat) (t : Team) (acc : List (Nat × Team)),
    (∀ j, j < m → i + j - rs + 1 ≠ k) →
    (List.replicate m (some t)).foldl (swStep k) ⟨i, some t, rs, acc⟩ = ⟨i + m, some t, rs, acc⟩
  | 0, i, rs, t, acc, _ => by simp
  | m + 1, i, rs, t, acc, h => by
    rw [List.replicate_succ, List.foldl_cons]
    have h0 : i - rs + 1 ≠ k := by have := h 0 (by omega); omega
    have hstep : swStep k ⟨i, some t, rs, acc⟩ (some t) = ⟨i + 1, some t, rs, acc⟩ := by
      simp [swStep, newStart, newAcc, h0]
    rw [hstep, foldl_cont k m (i + 1) rs t acc (fun j hj => by have := h (j + 1) (by omega); omega)]
    congr 1
    omega

/-- k = 1 and the whole stretch is home: exactly one switch, home at offset 0. -/
theorem switches_all_home (n : Nat) : switches 1 (List.replicate (n + 1) (some .H)) = [(0, .H)] := by
  unfold switches
  rw [List.replicate_succ, List.foldl_cons]
  have hstep : swStep 1 ⟨0, none, 0, []⟩ (some .H) = ⟨1, some .H, 0, [(0, .H)]⟩ := by decide
  rw [hstep, foldl_cont 1 n 1 0 .H [(0, .H)] (fun j _ => by omega)]

/-- With k = 1, no dead frame and home near the ball on every frame, every label is H. -/
theorem all_home (n : Nat) :
    stickySegment 1 (List.replicate n (some .H)) (List.replicate n false) = List.replicate n .H := by
  rw [show List.replicate n false = List.replicate (List.replicate n (some Team.H)).length false by simp,
    live_labels]
  cases n with
  | zero => rfl
  | succ m =>
    simp [stretch, switches_all_home, paint, holder, Team.label, List.map_const', List.length_replicate]

/-! ## The blind spot: an opponent run shorter than k is never labelled -/

/-- Every confirmed switch so far is home. -/
def allH (acc : List (Nat × Team)) : Prop := ∀ p ∈ acc, p.2 = Team.H

theorem allH_append (acc : List (Nat × Team)) (rs : Nat) (h : allH acc) : allH (acc ++ [(rs, .H)]) := by
  intro p hp
  rw [List.mem_append, List.mem_singleton] at hp
  rcases hp with hp | rfl
  · exact h p hp
  · rfl

/-- A frame that is not an away frame can only ever confirm home. -/
theorem swStep_allH (k : Nat) (st : SwState) (n : Option Team) (hn : n ≠ some .A) (h : allH st.acc) :
    allH (swStep k st n).acc := by
  show allH (newAcc k st n)
  match n with
  | none => exact h
  | some .A => exact absurd rfl hn
  | some .H =>
    simp only [newAcc]
    split
    · exact allH_append st.acc _ h
    · exact h

theorem foldl_allH (k : Nat) : ∀ (l : List (Option Team)) (st : SwState),
    (∀ x ∈ l, x ≠ some .A) → allH st.acc → allH (l.foldl (swStep k) st).acc
  | [], _, _, h => h
  | n :: l, st, hl, h => by
    rw [List.foldl_cons]
    exact foldl_allH k l _ (fun x hx => hl x (by simp [hx])) (swStep_allH k st n (hl n (by simp)) h)

theorem foldl_runTeam (k : Nat) : ∀ (l : List (Option Team)) (st : SwState),
    (∀ x ∈ l, x ≠ some .A) → st.runTeam ≠ some .A → (l.foldl (swStep k) st).runTeam ≠ some .A
  | [], _, _, h => h
  | n :: l, st, hl, _ => by
    rw [List.foldl_cons]
    exact foldl_runTeam k l _ (fun x hx => hl x (by simp [hx])) (hl n (by simp))

/-- An away run of b < k frames, entered from a non-away frame, confirms nothing. -/
theorem foldl_away_short (k b : Nat) (st : SwState) (h0 : st.runTeam ≠ some .A) (hb : b < k) :
    ((List.replicate b (some .A)).foldl (swStep k) st).acc = st.acc := by
  cases b with
  | zero => simp
  | succ m =>
    rw [List.replicate_succ, List.foldl_cons]
    have h0' : some Team.A ≠ st.runTeam := fun h => h0 h.symm
    have h1 : (1 : Nat) ≠ k := by omega
    have hstep : swStep k st (some .A) = ⟨st.i + 1, some .A, st.i, st.acc⟩ := by
      simp [swStep, newStart, newAcc, h0', h1]
    rw [hstep, foldl_cont k m (st.i + 1) st.i .A st.acc (fun j hj => by omega)]

/-- Switches of a stretch whose only away frames form one run shorter than k are all home. -/
theorem switches_allH (k b : Nat) (pre post : List (Option Team))
    (hpre : ∀ x ∈ pre, x ≠ some .A) (hpost : ∀ x ∈ post, x ≠ some .A) (hb : b < k) :
    allH (switches k (pre ++ List.replicate b (some .A) ++ post)) := by
  unfold switches
  rw [List.foldl_append, List.foldl_append]
  have h1 : allH (pre.foldl (swStep k) ⟨0, none, 0, []⟩).acc :=
    foldl_allH k pre _ hpre (by simp [allH])
  have h2 : (pre.foldl (swStep k) ⟨0, none, 0, []⟩).runTeam ≠ some .A :=
    foldl_runTeam k pre _ hpre (by simp)
  exact foldl_allH k post _ hpost (by rw [foldl_away_short k b _ h2 hb]; exact h1)

theorem holder_mem (first : Team) : ∀ (sw : List (Nat × Team)) (i : Nat),
    holder first sw i = first ∨ ∃ p ∈ sw, holder first sw i = p.2
  | [], _ => Or.inl rfl
  | (s, t) :: rest, i => by
    simp only [holder]
    split
    · rcases holder_mem t rest i with h | ⟨p, hp, h⟩
      · exact Or.inr ⟨(s, t), by simp, h⟩
      · exact Or.inr ⟨p, by simp [hp], h⟩
    · exact Or.inl rfl

/-- If no switch is away and no away team is carried in, no frame is labelled A. -/
theorem paint_no_A (team : Option Team) (sw : List (Nat × Team)) (len : Nat)
    (hteam : team ≠ some .A) (hsw : allH sw) : Label.A ∉ paint team sw len := by
  cases sw with
  | nil =>
    intro h
    simp only [paint, List.mem_replicate] at h
    obtain ⟨_, h⟩ := h
    cases team with
    | none => simp [carried] at h
    | some t =>
      cases t with
      | H => simp [carried, Team.label] at h
      | A => exact hteam rfl
  | cons p rest =>
    obtain ⟨s, t₀⟩ := p
    intro h
    simp only [paint, List.mem_map, List.mem_range] at h
    obtain ⟨i, _, hi⟩ := h
    rcases holder_mem t₀ ((s, t₀) :: rest) i with h | ⟨q, hq, h⟩
    · have ht : t₀ = .H := hsw (s, t₀) (by simp)
      rw [h, ht] at hi
      exact absurd hi (by decide)
    · rw [h, hsw q hq] at hi
      exact absurd hi (by decide)

/-- Blind spot. A live stretch (no dead frame) in which the away team is near the ball for one
run of b < k frames, with anything but away frames before and after it, never gets an A label:
the run is too short to confirm, so sticky possession stays with home (or D before any
confirmation). -/
theorem blind_spot (k b : Nat) (pre post : List (Option Team))
    (hpre : ∀ x ∈ pre, x ≠ some .A) (hpost : ∀ x ∈ post, x ≠ some .A) (hb : b < k) :
    let near := pre ++ List.replicate b (some .A) ++ post
    Label.A ∉ stickySegment k near (List.replicate near.length false) := by
  intro near
  rw [live_labels]
  exact paint_no_A none _ _ (by simp) (switches_allH k b pre post hpre hpost hb)

/-- The concrete shape of the Python default: k = 8, a 7-frame away run inside a home spell. -/
theorem blind_spot_k8 (a c : Nat) :
    let near := List.replicate a (some .H) ++ List.replicate 7 (some .A) ++ List.replicate c (some .H)
    Label.A ∉ stickySegment 8 near (List.replicate near.length false) :=
  blind_spot 8 7 _ _ (fun x hx => by rw [List.mem_replicate] at hx; rw [hx.2]; decide)
    (fun x hx => by rw [List.mem_replicate] at hx; rw [hx.2]; decide) (by decide)

/-! ## `date_back` in `rules.segment_labels`

The generalised loop moves each near-confirmed switch by `date_back` frames and clamps it:
`sw = min(max(run_start + date_back, start, lo), stop, hi)`, where [start, stop) is the live
stretch and lo, hi are the neighbouring switches (start and stop when there is none). Frame
numbers are integers here because `date_back` may be negative. -/

def datedSwitch (start stop lo hi runStart d : Int) : Int :=
  min (min (max (max (runStart + d) start) lo) stop) hi

/-- The dated switch is inside the stretch. -/
theorem datedSwitch_in_stretch (start stop lo hi runStart d : Int)
    (h1 : start ≤ lo) (h2 : lo ≤ hi) (h3 : hi ≤ stop) :
    start ≤ datedSwitch start stop lo hi runStart d ∧ datedSwitch start stop lo hi runStart d ≤ stop := by
  unfold datedSwitch; omega

/-- The dated switch stays between its neighbours, so switches never reorder. -/
theorem datedSwitch_between (start stop lo hi runStart d : Int) (h1 : lo ≤ hi) (h2 : hi ≤ stop) :
    lo ≤ datedSwitch start stop lo hi runStart d ∧ datedSwitch start stop lo hi runStart d ≤ hi := by
  unfold datedSwitch; omega

/-- With no neighbours (lo = start, hi = stop) and no clamp at the end, the switch frame is
`max(stretch_start, run_start + d)`. -/
theorem datedSwitch_first (start stop runStart d : Int) (hs : start ≤ stop) (h : runStart + d ≤ stop) :
    datedSwitch start stop start stop runStart d = max start (runStart + d) := by
  unfold datedSwitch; omega

/-- `date_back = 0` leaves a switch inside its stretch where `sticky_segment` put it. -/
theorem datedSwitch_zero (start stop runStart : Int) (h0 : start ≤ runStart) (h1 : runStart ≤ stop) :
    datedSwitch start stop start stop runStart 0 = runStart := by
  unfold datedSwitch; omega

end Segment
