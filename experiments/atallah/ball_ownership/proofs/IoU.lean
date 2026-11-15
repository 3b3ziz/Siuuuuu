/-!
# IoU of a predicted possession spell against the truth

Frames are naturals. A truth spell occupies the half-open interval [0, L) (length L frames).
A prediction of the same length that starts e frames late occupies [e, L + e). With e < L the
two overlap:

    intersection = L - e,   union = L + e,   IoU = (L - e) / (L + e).

The evaluation keeps a predicted spell when IoU is at least a threshold t/10. Each threshold
is written as the integer inequality `10 * intersection ≥ t * union`, so no division or
rational numbers are needed and everything is decided by `omega`.
-/

namespace IoU

/-- Frames shared by [a0, a1) and [b0, b1) (0 when they do not meet). -/
def inter (a0 a1 b0 b1 : Nat) : Nat := min a1 b1 - max a0 b0

/-- Frames covered by [a0, a1) ∪ [b0, b1) when the two intervals meet (their hull). -/
def union (a0 a1 b0 b1 : Nat) : Nat := max a1 b1 - min a0 b0

/-- `IoU ≥ t/10`, as an integer statement about an intersection and a union. -/
def iouGe (inter union t : Nat) : Prop := 10 * inter ≥ t * union

/-! ## A spell of length L predicted e frames late -/

theorem shifted_inter (L e : Nat) (h : e < L) : inter 0 L e (L + e) = L - e := by
  unfold inter; omega

theorem shifted_union (L e : Nat) : union 0 L e (L + e) = L + e := by
  unfold union; omega

/-- Shifted by L or more, the prediction misses the truth entirely. -/
theorem shifted_no_overlap (L e : Nat) (h : L ≤ e) : inter 0 L e (L + e) = 0 := by
  unfold inter; omega

/-- Inclusion-exclusion: intersection + union = 2L for every shift e < L. -/
theorem shifted_inter_add_union (L e : Nat) (h : e < L) : (L - e) + (L + e) = 2 * L := by
  omega

/-! ## Thresholds 3/10 .. 7/10 as bounds on the shift e -/

theorem ge_7_10 (L e : Nat) (h : e < L) : iouGe (L - e) (L + e) 7 ↔ 17 * e ≤ 3 * L := by
  unfold iouGe; omega

theorem ge_6_10 (L e : Nat) (h : e < L) : iouGe (L - e) (L + e) 6 ↔ 4 * e ≤ L := by
  unfold iouGe; omega

theorem ge_5_10 (L e : Nat) (h : e < L) : iouGe (L - e) (L + e) 5 ↔ 3 * e ≤ L := by
  unfold iouGe; omega

theorem ge_4_10 (L e : Nat) (h : e < L) : iouGe (L - e) (L + e) 4 ↔ 7 * e ≤ 3 * L := by
  unfold iouGe; omega

theorem ge_3_10 (L e : Nat) (h : e < L) : iouGe (L - e) (L + e) 3 ↔ 13 * e ≤ 7 * L := by
  unfold iouGe; omega

/-- Corollary at 0.5: the spell survives iff the shift is at most a third of its length. -/
theorem half_iff (L e : Nat) (h : e < L) : 2 * (L - e) ≥ L + e ↔ 3 * e ≤ L := by
  omega

/-- Corollary at 0.3: the spell survives iff 13 e ≤ 7 L (a shift of up to 7/13 of its length). -/
theorem three_tenths_iff (L e : Nat) (h : e < L) : 10 * (L - e) ≥ 3 * (L + e) ↔ 13 * e ≤ 7 * L := by
  omega

/-- A stricter threshold tolerates less shift: 0.7 ⇒ 0.5 ⇒ 0.3. -/
theorem threshold_chain (L e : Nat) :
    (17 * e ≤ 3 * L → 3 * e ≤ L) ∧ (3 * e ≤ L → 13 * e ≤ 7 * L) := by
  omega

/-- At 25 fps a 5 s spell (125 frames) survives the 0.5 threshold up to a 41-frame (1.64 s) shift. -/
theorem budget_125_at_half : 3 * 41 ≤ 125 ∧ ¬ 3 * 42 ≤ 125 := by decide

/-! ## Two truth spells merged into one prediction

Truth spells A = [0, A) and B = [A + G, A + G + B) are separated by a gap of G frames (the other
team's spell, or a stoppage). A prediction that never notices the change is the single spell
[0, A + G + B). It fully contains each truth spell, so the intersection is the truth spell's own
length and the union is the merged length. -/

theorem merged_inter_A (A G B : Nat) : inter 0 A 0 (A + G + B) = A := by
  unfold inter; omega

theorem merged_union_A (A G B : Nat) : union 0 A 0 (A + G + B) = A + G + B := by
  unfold union; omega

theorem merged_inter_B (A G B : Nat) : inter (A + G) (A + G + B) 0 (A + G + B) = B := by
  unfold inter; omega

theorem merged_union_B (A G B : Nat) : union (A + G) (A + G + B) 0 (A + G + B) = A + G + B := by
  unfold union; omega

/-- Truth spell A is lost at 0.3 exactly when 7 A < 3 (G + B). -/
theorem merged_A_below_3_10 (A G B : Nat) : ¬ iouGe A (A + G + B) 3 ↔ 7 * A < 3 * (G + B) := by
  unfold iouGe; omega

/-- Truth spell B is lost at 0.3 exactly when 7 B < 3 (A + G). -/
theorem merged_B_below_3_10 (A G B : Nat) : ¬ iouGe B (A + G + B) 3 ↔ 7 * B < 3 * (A + G) := by
  unfold iouGe; omega

/-- Two 12 s spells (300 frames) merged across a 20 s gap (500 frames): both are below 0.3. -/
theorem merged_300_500_300 : ¬ iouGe 300 (300 + 500 + 300) 3 ∧ ¬ iouGe 300 (300 + 500 + 300) 3 := by
  unfold iouGe; decide

theorem merged_300_500_300_arith : 10 * 300 < 3 * 1100 := by decide

end IoU
