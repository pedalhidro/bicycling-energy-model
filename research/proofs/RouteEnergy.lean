/-
# The route-energy law, derived from the equation of motion

Paper 1's Appendix A (`research/article/paper1-closed-form.md`) and the derivations of
`research/notes/original_notes.md`, checked by machine. The statements, in the order of the
derivation:

1. `ledger`                 (A1)      the work–energy identity is a first integral of Newton's
                                      equation along the road;
2. `refund_eq_balance`      (A3–A5)   the refund fraction of a descent, defined from what the
                                      descent wastes, equals the balance a power meter measures;
3. `three_term_law`         (A6–A8)   summing the segment ledgers gives
                                      `E = α_r·x + α_a·x_flat + β·(h₊ − ε·h₋)`, exactly, with `ε`
                                      the drop-weighted mean refund;
4. `closed_form_of_newton`            1 and 3 joined: equation of motion in, closed form out;
5. `coast_ceiling`,
   `refund_of_coaster`      (A9)      a rider who pedals only when gravity cannot hold the
                                      reference speed collects `ε = min(1, s⋆/s)`, `s⋆ = α/β`;
6. `refund_le_ceiling`      (A.6)     no rider collects more on a real descent, because legs
                                      cannot return energy.

What is assumed, and where. The equation of motion is paper 1's eq. (3) with a brake force added;
nothing else enters `ledger`. The closed form then needs three riding assumptions, each a named
hypothesis of `closed_form_of_newton`: on flat stretches the air is paid at the reference speed
(`flat_aero`), on climbs it is neglected (`climb_aero`), and off the descents nobody brakes
(`no_brake`). Under those the law is an identity, not an approximation, and its kinetic-energy
remainder is printed in the statement.

What is not proved, because it is not a theorem. How much of the ceiling a real rider collects
(the coasting deficit `ε₀`), the deadband threshold `τ` and the noise rate `c` are measurements.
They correct for riding that departs from the three assumptions and for elevation data that is
not the road. Nothing here says how large those departures are.

To check it: `lake exe cache get && lake build` in this directory. The Lean and Mathlib versions
are pinned by `lean-toolchain` and `lake-manifest.json`.
-/
module

public import Mathlib

@[expose] public section

open Finset

namespace RouteEnergy

/-! ## 1. The ledger (A1) -/

/-- `f` is continuous on `[a, b]` and changes at rate `f'` on `[a, b)`, the rate taken from the
right. Kinks are allowed, so a polyline elevation profile, a pedal power that steps between
regimes and brakes that switch on and off all qualify. -/
def HasRateOn (f f' : ℝ → ℝ) (a b : ℝ) : Prop :=
  ContinuousOn f (Set.Icc a b) ∧ ∀ s ∈ Set.Ico a b, HasDerivWithinAt f (f' s) (Set.Ici s) s

/-- A function differentiable everywhere qualifies. -/
theorem HasRateOn.of_hasDerivAt {f f' : ℝ → ℝ} (h : ∀ s, HasDerivAt f (f' s) s) (a b : ℝ) :
    HasRateOn f f' a b :=
  ⟨fun s _ => (h s).continuousAt.continuousWithinAt, fun s _ => (h s).hasDerivWithinAt⟩

/-- A rate on a stretch is a rate on any part of it. -/
theorem HasRateOn.mono {f f' : ℝ → ℝ} {a b a' b' : ℝ} (h : HasRateOn f f' a b)
    (ha : a ≤ a') (hb : b' ≤ b) : HasRateOn f f' a' b' :=
  ⟨h.1.mono (Set.Icc_subset_Icc ha hb), fun s hs => h.2 s (Set.Ico_subset_Ico ha hb hs)⟩

/-- **The work–energy ledger is a first integral of the equation of motion.**

Everything is a function of distance `s` along the road, from `a` to `b`. `v` is speed, `X`
horizontal position (`dX/ds = cos θ`) and `h` elevation (`dh/ds = sin θ`). `E` is the energy the
legs have delivered: `dE/dt = P` and `dt = ds / v`, so `dE/ds = P / v`. `Wa` and `Wb` are the
work done against the air and by the brakes; their forces `drag` and `brake` are left
arbitrary, so wind and any drag law are covered. Reading `P / v` as leg energy per metre
needs the bicycle to be moving; the algebra does not.

`newton` is paper 1's eq. (3) with a brake force,
`m·v·dv/ds = k·P/v − C_rr·m·g·cos θ − drag − m·g·sin θ − brake`.
The conclusion is (A1): the leg energy the drivetrain delivers equals the change in kinetic
energy plus the work against rolling resistance, air, gravity and the brakes. Rolling
resistance comes out exact in the horizontal distance, on any grade. -/
theorem ledger {m g Crr k a b : ℝ} (hab : a ≤ b)
    {v v' X c h σ E P Wa Wb drag brake : ℝ → ℝ}
    (hv : HasRateOn v v' a b) (hX : HasRateOn X c a b) (hh : HasRateOn h σ a b)
    (hE : HasRateOn E (fun s => P s / v s) a b)
    (hWa : HasRateOn Wa drag a b) (hWb : HasRateOn Wb brake a b)
    (newton : ∀ s ∈ Set.Ico a b, m * v s * v' s
      = k * (P s / v s) - Crr * m * g * c s - drag s - m * g * σ s - brake s) :
    k * (E b - E a)
      = (m * v b ^ 2 / 2 - m * v a ^ 2 / 2)
        + Crr * m * g * (X b - X a)
        + (Wa b - Wa a)
        + m * g * (h b - h a)
        + (Wb b - Wb a) := by
  -- the ledger's imbalance is continuous with right derivative zero, so it is constant
  have cont : ContinuousOn
      (fun s => k * E s - m * v s ^ 2 / 2 - Crr * m * g * X s - Wa s - m * g * h s - Wb s)
      (Set.Icc a b) := by
    have := hv.1; have := hX.1; have := hh.1; have := hE.1; have := hWa.1; have := hWb.1
    fun_prop
  have key : ∀ s ∈ Set.Ico a b, HasDerivWithinAt
      (fun s => k * E s - m * v s ^ 2 / 2 - Crr * m * g * X s - Wa s - m * g * h s - Wb s) 0
      (Set.Ici s) s := by
    intro s hs
    have hKE : HasDerivWithinAt (fun s => m * v s ^ 2 / 2) (m * v s * v' s) (Set.Ici s) s :=
      ((((hv.2 s hs).pow 2).const_mul m).div_const 2).congr_deriv (by simp; ring)
    exact ((((((hE.2 s hs).const_mul k).sub hKE).sub ((hX.2 s hs).const_mul (Crr * m * g))).sub
      (hWa.2 s hs)).sub ((hh.2 s hs).const_mul (m * g))).sub (hWb.2 s hs) |>.congr_deriv
        (by beta_reduce; linarith [newton s hs])
  have hconst := constant_of_has_deriv_right_zero cont key b (Set.right_mem_Icc.2 hab)
  beta_reduce at hconst
  linarith

/-- Sanity check that the hypotheses of `ledger` can be met, and the flat-match anchor: on a flat
road at constant speed `v₀` against a constant drag force `D`, the power that balances the forces
satisfies the equation of motion, and the ledger returns the flat bill `k·E = (C_rr·m·g + D)·L`. -/
example {m g Crr k D v₀ L : ℝ} (hk : k ≠ 0) (hv₀ : v₀ ≠ 0) (hL : 0 ≤ L) :
    k * (v₀ * (Crr * m * g + D) / k / v₀ * L - v₀ * (Crr * m * g + D) / k / v₀ * 0)
      = (Crr * m * g + D) * L := by
  have h := ledger (m := m) (g := g) (Crr := Crr) (k := k) hL
    (v := fun _ => v₀) (v' := fun _ => 0) (X := fun s => s) (c := fun _ => 1)
    (h := fun _ => 0) (σ := fun _ => 0)
    (E := fun s => v₀ * (Crr * m * g + D) / k / v₀ * s) (P := fun _ => v₀ * (Crr * m * g + D) / k)
    (Wa := fun s => D * s) (Wb := fun _ => 0) (drag := fun _ => D) (brake := fun _ => 0)
    (.of_hasDerivAt (fun s => hasDerivAt_const s v₀) 0 L)
    (.of_hasDerivAt (fun s => hasDerivAt_id' s) 0 L)
    (.of_hasDerivAt (fun s => hasDerivAt_const s 0) 0 L)
    (.of_hasDerivAt (fun s => by simpa using (hasDerivAt_id' s).const_mul _) 0 L)
    (.of_hasDerivAt (fun s => by simpa using (hasDerivAt_id' s).const_mul D) 0 L)
    (.of_hasDerivAt (fun s => hasDerivAt_const s 0) 0 L)
    (fun s _ => by field_simp; ring)
  linarith

/-! ## 2. One descent: the refund (A3–A5) -/

/-- **The refund in balance form.** On a descent of drop `d` and run `x` the ledger reads
`k·e = R·x + A·x − W·d + waste`, where `R` is the rolling force, `A` the air force at the
reference speed, `W` the weight, and `waste` what the descent loses to air drag above the
reference bill and to the brakes. The refund fraction `ε = 1 − waste/(W·d)` of (A3) is then the
leg energy saved against riding `x` on the flat, as a share of the potential energy released:
`ε = (α·x − e)/(β·d)` with `α = (R + A)/k` and `β = W/k`. That is (A5), and its right-hand side
is measurable with a power meter. -/
theorem refund_eq_balance {R A W k x d e waste : ℝ} (hk : k ≠ 0) (hW : W ≠ 0) (hd : d ≠ 0)
    (bal : k * e = R * x + A * x - W * d + waste) :
    1 - waste / (W * d) = ((R + A) / k * x - e) / (W / k * d) := by
  have hw : waste = k * e - R * x - A * x + W * d := by linarith
  rw [hw]
  field_simp
  ring

/-! ## 3. The whole route: the three-term law (A6–A8) -/

variable {ι : Type*}

/-- Refund fraction of descent segment `i`, (A3). -/
noncomputable def refund (W : ℝ) (dn waste : ι → ℝ) (i : ι) : ℝ :=
  1 - waste i / (W * dn i)

/-- The route's single `ε`: the drop-weighted mean of its descents' refunds, (A7). -/
noncomputable def meanRefund (D : Finset ι) (W : ℝ) (dn waste : ι → ℝ) : ℝ :=
  (∑ i ∈ D, refund W dn waste i * dn i) / ∑ i ∈ D, dn i

/-- The weight in (A7) is the drop because that is what makes the total credit come out right. -/
theorem meanRefund_mul_drop (D : Finset ι) {W : ℝ} (hW : W ≠ 0) {dn waste : ι → ℝ}
    (hdn : ∀ i ∈ D, 0 < dn i) :
    meanRefund D W dn waste * ∑ i ∈ D, dn i = ∑ i ∈ D, dn i - (∑ i ∈ D, waste i) / W := by
  have hterm : ∀ i ∈ D, refund W dn waste i * dn i = dn i - waste i / W := by
    intro i hi
    have := (hdn i hi).ne'
    unfold refund
    field_simp
  unfold meanRefund
  rw [sum_congr rfl hterm, sum_sub_distrib, ← sum_div]
  rcases D.eq_empty_or_nonempty with rfl | hne
  · simp
  · exact div_mul_cancel₀ _ (sum_pos hdn hne).ne'

/-- **The three-term law.** Cut the route into flat segments `F`, climbs `C` and descents `D`.
Segment `i` has run `x i`, rise `up i` or drop `dn i`, leg energy `e i` and kinetic-energy
change `q i`. Suppose its ledger entry is

* on a flat: rolling, air at the reference speed, and the rise;
* on a climb: rolling and the rise, the air neglected;
* on a descent: rolling and air at the reference speed, less the drop, plus what is wasted.

Then the leg energy of the route is `α_r·x + α_a·x_flat + β·(h₊ − ε·h₋)` plus the net change in
kinetic energy, with `α_r = R/k`, `α_a = A/k`, `β = W/k` and `ε` the drop-weighted mean refund.
With no segment classed as a climb this is paper 1's F1, `(α_r + α_a)·x + β·(h₊ − ε·h₋)`;
otherwise it is F2, and F3 once the elevation totals are filtered. -/
theorem three_term_law (F C D : Finset ι) {R A W k : ℝ} (hk : k ≠ 0) (hW : W ≠ 0)
    {x up dn e waste q : ι → ℝ} (hdn : ∀ i ∈ D, 0 < dn i)
    (flat : ∀ i ∈ F, k * e i = R * x i + A * x i + W * up i + q i)
    (climb : ∀ i ∈ C, k * e i = R * x i + W * up i + q i)
    (desc : ∀ i ∈ D, k * e i = R * x i + A * x i - W * dn i + waste i + q i) :
    ∑ i ∈ F, e i + ∑ i ∈ C, e i + ∑ i ∈ D, e i
      = R / k * (∑ i ∈ F, x i + ∑ i ∈ C, x i + ∑ i ∈ D, x i)
        + A / k * (∑ i ∈ F, x i + ∑ i ∈ D, x i)
        + W / k * ((∑ i ∈ F, up i + ∑ i ∈ C, up i)
            - meanRefund D W dn waste * ∑ i ∈ D, dn i)
        + (∑ i ∈ F, q i + ∑ i ∈ C, q i + ∑ i ∈ D, q i) / k := by
  have eF : k * ∑ i ∈ F, e i
      = R * ∑ i ∈ F, x i + A * ∑ i ∈ F, x i + W * ∑ i ∈ F, up i + ∑ i ∈ F, q i := by
    rw [mul_sum, sum_congr rfl flat]
    simp only [sum_add_distrib, mul_sum]
  have eC : k * ∑ i ∈ C, e i = R * ∑ i ∈ C, x i + W * ∑ i ∈ C, up i + ∑ i ∈ C, q i := by
    rw [mul_sum, sum_congr rfl climb]
    simp only [sum_add_distrib, mul_sum]
  have eD : k * ∑ i ∈ D, e i
      = R * ∑ i ∈ D, x i + A * ∑ i ∈ D, x i - W * ∑ i ∈ D, dn i + ∑ i ∈ D, waste i
        + ∑ i ∈ D, q i := by
    rw [mul_sum, sum_congr rfl desc]
    simp only [sum_add_distrib, sum_sub_distrib, mul_sum]
  rw [meanRefund_mul_drop D hW hdn]
  apply mul_left_cancel₀ hk
  field_simp
  linear_combination eF + eC + eD

/-! ## 4. Equation of motion in, closed form out -/

/-- Increment of a cumulative quantity `f` over segment `i` of a route cut at `s 0, s 1, …`. -/
def seg (f : ℝ → ℝ) (s : ℕ → ℝ) (i : ℕ) : ℝ := f (s (i + 1)) - f (s i)

/-- **The closed form follows from the equation of motion.** Take a ride obeying `newton`, as in
`ledger`, and cut its route at `s 0, …, s n` into flat stretches `F`, climbs `C` and descents `D`.
Assume only that

* `flat_aero`: on flat stretches the air costs what it would at the reference speed, `A` per
  horizontal metre (`A = ½·ρ·C_dA·v_f²` in still air);
* `climb_aero`: on climbs the air costs nothing;
* `no_brake`: there is no braking off the descents.

Then the leg energy is `α_r·x + α_a·x_flat + β·(h₊ − ε·h₋) + ΔKE/k`, where `α_r = C_rr·m·g/k`,
`α_a = A/k`, `β = m·g/k`, and `ε` is the drop-weighted mean refund of the descents. A ride that
ends at the speed it started loses the last term. -/
theorem closed_form_of_newton {m g Crr k : ℝ} (hk : k ≠ 0) (hmg : m * g ≠ 0)
    {v v' X c h σ E P Wa Wb drag brake : ℝ → ℝ}
    (s : ℕ → ℝ) (hs : Monotone s) (n : ℕ)
    (hv : HasRateOn v v' (s 0) (s n)) (hX : HasRateOn X c (s 0) (s n))
    (hh : HasRateOn h σ (s 0) (s n)) (hE : HasRateOn E (fun t => P t / v t) (s 0) (s n))
    (hWa : HasRateOn Wa drag (s 0) (s n)) (hWb : HasRateOn Wb brake (s 0) (s n))
    (newton : ∀ t ∈ Set.Ico (s 0) (s n), m * v t * v' t
      = k * (P t / v t) - Crr * m * g * c t - drag t - m * g * σ t - brake t)
    (F C D : Finset ℕ)
    (hcover : F ∪ C ∪ D = range n)
    (hFC : Disjoint F C) (hFD : Disjoint F D) (hCD : Disjoint C D)
    (hdrop : ∀ i ∈ D, h (s (i + 1)) < h (s i))
    (A : ℝ)
    (flat_aero : ∀ i ∈ F, seg Wa s i = A * seg X s i)
    (climb_aero : ∀ i ∈ C, seg Wa s i = 0)
    (no_brake : ∀ i ∈ F ∪ C, seg Wb s i = 0) :
    E (s n) - E (s 0)
      = Crr * m * g / k * (X (s n) - X (s 0))
        + A / k * ∑ i ∈ F ∪ D, seg X s i
        + m * g / k * (∑ i ∈ F ∪ C, seg h s i
            - meanRefund D (m * g) (fun i => -seg h s i)
                (fun i => seg Wa s i - A * seg X s i + seg Wb s i)
              * ∑ i ∈ D, -seg h s i)
        + (m * v (s n) ^ 2 / 2 - m * v (s 0) ^ 2 / 2) / k := by
  -- the ledger on each segment
  have bal : ∀ i ∈ range n, k * seg E s i
      = seg (fun t => m * v t ^ 2 / 2) s i + Crr * m * g * seg X s i + seg Wa s i
        + m * g * seg h s i + seg Wb s i := by
    intro i hi
    have lo : s 0 ≤ s i := hs (Nat.zero_le i)
    have hi' : s (i + 1) ≤ s n := hs (mem_range.1 hi)
    exact ledger (hs (Nat.le_succ i)) (hv.mono lo hi') (hX.mono lo hi') (hh.mono lo hi')
      (hE.mono lo hi') (hWa.mono lo hi') (hWb.mono lo hi')
      (fun t ht => newton t (Set.Ico_subset_Ico lo hi' ht))
  -- the route is the disjoint union of its three kinds of segment
  have split : ∀ f : ℕ → ℝ,
      ∑ i ∈ range n, f i = ∑ i ∈ F, f i + ∑ i ∈ C, f i + ∑ i ∈ D, f i := by
    intro f
    rw [← hcover, sum_union (disjoint_union_left.2 ⟨hFD, hCD⟩), sum_union hFC]
  have memF : ∀ i ∈ F, i ∈ range n := fun i hi =>
    hcover ▸ mem_union_left _ (mem_union_left _ hi)
  have memC : ∀ i ∈ C, i ∈ range n := fun i hi =>
    hcover ▸ mem_union_left _ (mem_union_right _ hi)
  have memD : ∀ i ∈ D, i ∈ range n := fun i hi => hcover ▸ mem_union_right _ hi
  have tele : ∀ f : ℝ → ℝ, ∑ i ∈ range n, seg f s i = f (s n) - f (s 0) := fun f =>
    sum_range_sub (fun i => f (s i)) n
  have law := three_term_law F C D (R := Crr * m * g) (A := A) (W := m * g) hk hmg
    (x := seg X s) (up := seg h s) (dn := fun i => -seg h s i) (e := seg E s)
    (waste := fun i => seg Wa s i - A * seg X s i + seg Wb s i)
    (q := seg (fun t => m * v t ^ 2 / 2) s)
    (fun i hi => by have := hdrop i hi; unfold seg; linarith)
    (fun i hi => by
      have := bal i (memF i hi)
      rw [flat_aero i hi, no_brake i (mem_union_left _ hi)] at this
      linarith)
    (fun i hi => by
      have := bal i (memC i hi)
      rw [climb_aero i hi, no_brake i (mem_union_right _ hi)] at this
      linarith)
    (fun i hi => by linarith [bal i (memD i hi)])
  rw [← split, ← split, ← split, tele, tele, tele] at law
  rw [sum_union hFD, sum_union hFC]
  exact law

/-! ## 5. How large can the refund be? (A9, A.6) -/

/-- The coasting ceiling as a function of descent grade `s`, with `sstar = α/β` the grade whose
gravity exactly pays the flat bill. -/
noncomputable def epsCoast (sstar s : ℝ) : ℝ := min 1 (sstar / s)

/-- **The ceiling is what an ideal coaster collects.** A rider who pedals only as much as is
needed to hold the reference speed, and not at all once gravity suffices, spends
`max 0 (α·x − β·d)` on a descent of run `x` and drop `d`. That is the flat bill less a refund of
exactly `min(1, s⋆/s)` of the drop. Freewheeling and braking give the same figure: both leave
the legs idle. -/
theorem coast_ceiling {α β x d : ℝ} (hβ : 0 < β) (hx : 0 < x) (hd : 0 < d) :
    max 0 (α * x - β * d) = α * x - epsCoast (α / β) (d / x) * β * d := by
  have hgrade : α / β / (d / x) = α * x / (β * d) := by field_simp
  have hpos : 0 < β * d := by positivity
  unfold epsCoast
  rw [hgrade]
  rcases le_total (β * d) (α * x) with hle | hle
  · rw [max_eq_right (by linarith), min_eq_left ((one_le_div hpos).2 hle)]
    ring
  · rw [max_eq_left (by linarith), min_eq_right ((div_le_one hpos).2 hle)]
    field_simp
    ring

/-- **(A9) in ledger terms.** For that ideal coaster the refund fraction of (A3), the one the
three-term law averages, is the ceiling: a function of the descent's grade alone. -/
theorem refund_of_coaster {R A W k x d e waste : ℝ} (hk : 0 < k) (hW : 0 < W) (hx : 0 < x)
    (hd : 0 < d) (bal : k * e = R * x + A * x - W * d + waste)
    (coast : e = max 0 ((R + A) / k * x - W / k * d)) :
    1 - waste / (W * d) = epsCoast ((R + A) / k / (W / k)) (d / x) := by
  rw [refund_eq_balance hk.ne' hW.ne' hd.ne' bal, coast, coast_ceiling (div_pos hW hk) hx hd,
    sub_sub_cancel, mul_assoc]
  exact mul_div_cancel_right₀ _ (by positivity)

/-- **No rider beats the ceiling on a real descent.** Legs cannot return energy, `e ≥ 0`, so on
a descent at least as steep as `s⋆` the measured refund `(α·x − e)/(β·d)` is at most
`min(1, s⋆/s)`. Braking does not enter: a brake is a refund not collected, never a charge. -/
theorem refund_le_ceiling {α β x d e : ℝ} (hβ : 0 < β) (hx : 0 < x) (hd : 0 < d) (he : 0 ≤ e)
    (hsteep : α * x ≤ β * d) :
    (α * x - e) / (β * d) ≤ epsCoast (α / β) (d / x) := by
  have hgrade : α / β / (d / x) = α * x / (β * d) := by field_simp
  have hpos : 0 < β * d := by positivity
  unfold epsCoast
  rw [hgrade, min_eq_right ((div_le_one hpos).2 hsteep)]
  gcongr
  linarith

end RouteEnergy
