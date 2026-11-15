/-!
# Placing a possession boundary inside an uncertainty gap

When team X was last confirmed near the ball at frame g0 and team Y is first confirmed at frame
g1 > g0, the true change of possession s* is somewhere in the integer interval [g0, g1]. The
labeller has to pick one frame s. Its error on the end of X's spell and on the start of Y's
spell is the same number |s - s*|. Everything here is on naturals and decided by `omega`.
-/

namespace Gap

/-- |a - b| on naturals. -/
def adist (a b : Nat) : Nat := max (a - b) (b - a)

theorem adist_comm (a b : Nat) : adist a b = adist b a := by unfold adist; omega

theorem adist_self (a : Nat) : adist a a = 0 := by unfold adist; omega

theorem adist_eq_natAbs (a b : Nat) : adist a b = ((a : Int) - b).natAbs := by unfold adist; omega

/-- The worst error of placing the boundary at s when the truth can be anywhere in [g0, g1]. -/
def worst (g0 g1 s : Nat) : Nat := max (adist s g0) (adist s g1)

/-- The error against any truth inside the interval is at most the worst case. -/
theorem adist_le_worst (g0 g1 s t : Nat) (h0 : g0 ≤ t) (h1 : t ≤ g1) : adist s t ≤ worst g0 g1 s := by
  unfold worst adist; omega

/-- The worst case is attained at one of the two ends. -/
theorem worst_attained (g0 g1 s : Nat) : worst g0 g1 s = adist s g0 ∨ worst g0 g1 s = adist s g1 := by
  unfold worst adist; omega

/-- The midpoint of the gap (rounded down). -/
def mid (g0 g1 : Nat) : Nat := (g0 + g1) / 2

theorem mid_in_interval (g0 g1 : Nat) (h : g0 ≤ g1) : g0 ≤ mid g0 g1 ∧ mid g0 g1 ≤ g1 := by
  unfold mid; omega

/-- The midpoint's worst error is half the gap, rounded up. -/
theorem worst_mid (g0 g1 : Nat) (h : g0 ≤ g1) : worst g0 g1 (mid g0 g1) = (g1 - g0 + 1) / 2 := by
  unfold worst adist mid; omega

/-- No choice of s does better than half the gap, rounded up. -/
theorem worst_lower_bound (g0 g1 s : Nat) (h : g0 ≤ g1) : (g1 - g0 + 1) / 2 ≤ worst g0 g1 s := by
  unfold worst adist; omega

/-- The midpoint minimises the worst-case error over every choice of s. -/
theorem mid_minimises (g0 g1 s : Nat) (h : g0 ≤ g1) : worst g0 g1 (mid g0 g1) ≤ worst g0 g1 s := by
  unfold worst adist mid; omega

/-- Any s inside the gap is within g1 - g0 of both ends, so both neighbouring boundary errors
(the end of X's spell and the start of Y's spell) are bounded by the gap width. -/
theorem inside_bounds_errors (g0 g1 s : Nat) (h0 : g0 ≤ s) (h1 : s ≤ g1) :
    adist s g0 ≤ g1 - g0 ∧ adist s g1 ≤ g1 - g0 := by
  unfold adist; omega

/-- Any s inside the gap is within g1 - g0 of every truth inside the gap. -/
theorem inside_bounds_truth (g0 g1 s t : Nat) (h0 : g0 ≤ s) (h1 : s ≤ g1) (t0 : g0 ≤ t) (t1 : t ≤ g1) :
    adist s t ≤ g1 - g0 := by
  unfold adist; omega

/-- Any s outside the gap has a worst case larger than the gap width: never choose outside. -/
theorem outside_worse (g0 g1 s : Nat) (h : g0 ≤ g1) (hs : s < g0 ∨ g1 < s) : g1 - g0 < worst g0 g1 s := by
  unfold worst adist; omega

end Gap
