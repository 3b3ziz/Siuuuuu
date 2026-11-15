/-!
# Slot permutation in the practice-match degradation

`idsse.permute_slots` cuts the match into intervals and, in each interval, permutes the player
columns of each team at random. This file shows what that does and does not change: a column
permutation is a bijection on the n slots of a team (it has an inverse), permutations compose,
and after any such permutation every frame still holds the same multiset of positions per team,
only in different columns. Nothing about where the players are is lost; only which column
carries which player.
-/

namespace Degrade

/-- A permutation of the n slots (columns) of one team, carried with its inverse. -/
structure Perm (n : Nat) where
  toFun : Fin n → Fin n
  invFun : Fin n → Fin n
  left_inv : ∀ i, invFun (toFun i) = i
  right_inv : ∀ i, toFun (invFun i) = i

namespace Perm

variable {n : Nat}

/-- The identity: the columns stay as they are. -/
def id (n : Nat) : Perm n := ⟨fun i => i, fun i => i, fun _ => rfl, fun _ => rfl⟩

/-- The inverse permutation. -/
def symm (p : Perm n) : Perm n := ⟨p.invFun, p.toFun, p.right_inv, p.left_inv⟩

/-- `p.comp q` applies q first, then p. -/
def comp (p q : Perm n) : Perm n :=
  ⟨fun i => p.toFun (q.toFun i), fun i => q.invFun (p.invFun i),
   fun i => by simp [p.left_inv, q.left_inv], fun i => by simp [q.right_inv, p.right_inv]⟩

theorem injective (p : Perm n) (i j : Fin n) (h : p.toFun i = p.toFun j) : i = j := by
  have := congrArg p.invFun h
  rwa [p.left_inv, p.left_inv] at this

theorem surjective (p : Perm n) (j : Fin n) : ∃ i, p.toFun i = j :=
  ⟨p.invFun j, p.right_inv j⟩

/-- A column permutation is a bijection: injective and surjective. -/
theorem bijective (p : Perm n) :
    (∀ i j, p.toFun i = p.toFun j → i = j) ∧ (∀ j, ∃ i, p.toFun i = j) :=
  ⟨p.injective, p.surjective⟩

theorem symm_symm (p : Perm n) : p.symm.symm = p := rfl

theorem comp_toFun (p q : Perm n) (i : Fin n) : (p.comp q).toFun i = p.toFun (q.toFun i) := rfl

/-- The list of slot indices, sent through a permutation, is a rearrangement of itself. -/
theorem finRange_perm (p : Perm n) : ((List.finRange n).map p.toFun).Perm (List.finRange n) := by
  rw [List.perm_iff_count]
  intro a
  rw [List.count_eq_countP, List.countP_map, List.countP_congr (q := fun x => x == p.invFun a)]
  · rw [← List.count_eq_countP, (List.nodup_finRange n).count_of_mem (List.mem_finRange _),
      (List.nodup_finRange n).count_of_mem (List.mem_finRange _)]
  · intro x _
    simp only [Function.comp_apply, beq_iff_eq]
    constructor
    · intro h; rw [← h, p.left_inv]
    · intro h; rw [h, p.right_inv]

end Perm

variable {n : Nat} {Pos : Type}

/-- Degrading one team's frame: column i now carries what column `p i` carried. -/
def permute (p : Perm n) (f : Fin n → Pos) : Fin n → Pos := fun i => f (p.toFun i)

/-- The positions a frame holds, as a list (one entry per column): the frame's multiset. -/
def positions (f : Fin n → Pos) : List Pos := (List.finRange n).map f

theorem permute_id (f : Fin n → Pos) : permute (Perm.id n) f = f := rfl

/-- Two degradations in a row are one degradation by the composed permutation. -/
theorem permute_permute (p q : Perm n) (f : Fin n → Pos) :
    permute p (permute q f) = permute (q.comp p) f := rfl

/-- The inverse permutation restores the frame. -/
theorem permute_symm (p : Perm n) (f : Fin n → Pos) : permute p.symm (permute p f) = f := by
  funext i
  show f (p.toFun (p.invFun i)) = f i
  rw [p.right_inv]

/-- The multiset of positions is unchanged: the permuted list is a rearrangement of the original. -/
theorem positions_permute_perm (p : Perm n) (f : Fin n → Pos) :
    (positions (permute p f)).Perm (positions f) := by
  have h := (p.finRange_perm).map f
  rw [List.map_map] at h
  exact h

/-- Each position occurs in the degraded frame exactly as often as in the clean one. -/
theorem count_unchanged [BEq Pos] (p : Perm n) (f : Fin n → Pos) (x : Pos) :
    (positions (permute p f)).count x = (positions f).count x :=
  (positions_permute_perm p f).count_eq x

/-- The set of positions is unchanged. -/
theorem mem_unchanged (p : Perm n) (f : Fin n → Pos) (x : Pos) :
    x ∈ positions (permute p f) ↔ x ∈ positions f :=
  (positions_permute_perm p f).mem_iff

/-- Same statement without lists: some column holds x after iff some column held x before. -/
theorem range_unchanged (p : Perm n) (f : Fin n → Pos) (x : Pos) :
    (∃ i, permute p f i = x) ↔ (∃ i, f i = x) :=
  ⟨fun ⟨i, h⟩ => ⟨p.toFun i, h⟩,
   fun ⟨j, h⟩ => ⟨p.invFun j, by show f (p.toFun (p.invFun j)) = x; rw [p.right_inv]; exact h⟩⟩

/-! ## Per-interval permutations over a whole match -/

/-- Frame t uses the permutation `σ t`; `σ` is constant on each interval but need not be here. -/
def degrade (σ : Nat → Perm n) (F : Nat → Fin n → Pos) : Nat → Fin n → Pos :=
  fun t => permute (σ t) (F t)

/-- Composing per-interval permutations keeps every frame's multiset of positions. -/
theorem degrade_perm (σ : Nat → Perm n) (F : Nat → Fin n → Pos) (t : Nat) :
    (positions (degrade σ F t)).Perm (positions (F t)) :=
  positions_permute_perm (σ t) (F t)

theorem degrade_count_unchanged [BEq Pos] (σ : Nat → Perm n) (F : Nat → Fin n → Pos) (t : Nat) (x : Pos) :
    (positions (degrade σ F t)).count x = (positions (F t)).count x :=
  count_unchanged (σ t) (F t) x

/-- Degrading twice is degrading once by the frame-wise composed permutations. -/
theorem degrade_degrade (σ τ : Nat → Perm n) (F : Nat → Fin n → Pos) :
    degrade τ (degrade σ F) = degrade (fun t => (σ t).comp (τ t)) F := rfl

/-! ## Both teams -/

/-- One frame of both teams, n columns each. -/
structure TeamFrame (n : Nat) (Pos : Type) where
  home : Fin n → Pos
  away : Fin n → Pos

/-- A per-team permutation acts on each team's own columns and never mixes the teams. -/
def permuteTeams (ph pa : Perm n) (fr : TeamFrame n Pos) : TeamFrame n Pos :=
  ⟨permute ph fr.home, permute pa fr.away⟩

theorem teams_unchanged (ph pa : Perm n) (fr : TeamFrame n Pos) :
    (positions (permuteTeams ph pa fr).home).Perm (positions fr.home) ∧
    (positions (permuteTeams ph pa fr).away).Perm (positions fr.away) :=
  ⟨positions_permute_perm ph fr.home, positions_permute_perm pa fr.away⟩

end Degrade
