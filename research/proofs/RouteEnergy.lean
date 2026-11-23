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
                                      `E = α_r·x + α_a·x_flat + β·(h₊ − ε·h₋)` plus the work
                                      against the air on the climbs, exactly, with `ε` the
                                      drop-weighted mean refund;
   `law_bracket`,
   `steady_climb_air_le`    (A.3)     that work lies between nothing, which is F2, and the
                                      reference-speed bill, which is F1; on a steady climb it
                                      is at most what the engine's `vc` mode charges;
4. `closed_form_of_newton`            1 and 3 joined: equation of motion in, closed form out;
5. `coast_ceiling`,
   `refund_of_coaster`      (A9)      a rider who pedals only when gravity cannot hold the
                                      reference speed collects `ε = min(1, s⋆/s)`, `s⋆ = α/β`;
6. `refund_le_ceiling`      (A.6)     no rider collects more on a real descent, because legs
                                      cannot return energy.

Then, beyond the appendix, what kinetic energy does to the elevation that has to be paid for:

7. `Obeys.energyLine`,
   `Obeys.free_lift`                  kinetic energy is height: the ledger sees speed only as
                                      the head `v²/2g` added to the elevation;
8. `leg_energy_ge_ascent`,
   `leg_energy_eq_ascent`             leg energy is at least `β` times the ascent of the energy
                                      line, and exactly that for a rider who never brakes and
                                      pedals at once;
9. `deadband_isLeast`                 the deadband filter of `engines.py` has the least ascent
                                      of any profile within `τ` of the recording;
10. `leg_energy_ge_deadband`          so a rider whose kinetic head stays within `τ` of a level
                                      pays at least for the `τ`-filtered ascent.

Then paper 3's question, the cost of one graph edge (`research/article/paper3-edge-cost.md`):

11. `Obeys.edge`, `edge_ge_ideal`,
    `edge_eq_ideal`, `edge_le_bill`   the ledger of one edge: it costs at least
                                      `max 0 (α·Δx + β·ΔH)`, exactly that for the ideal coaster,
                                      and at most the flat bill plus the climb when ridden no
                                      faster than the reference speed;
12. `edge_sum_le_energy`,
    `energy_eq_edge_sum`              summed over a path whose nodes are passed at one speed:
                                      paper 3's E1 at zero deficit and without the climb gate;
13. `edge_sum_eq_ascent`,
    `ideal_sum_coarsen`,
    `edge_sum_ge_deadband`            the ideal edge sum is `β` times the ascent of the tilted
                                      road, never falls when the mesh is refined, and is never
                                      below the deadband-filtered ascent of 9 and 10;
14. `v2Edge_descent`, `v2_descent_eq`,
    `v2_eq_ideal`, `floor_le_v2`      the deployed cost: its own clamp is dead code for all
                                      constants, its descent arm is the ideal edge plus a
                                      deficit charge `min(ε₀·β·d, α·Δx)`, and it never bills
                                      less than rolling and gravity;
15. `law_sum_eq_route`,
    `eFEdge_eq_clamped_law`,
    `clamp_is_ceiling`, `clamp_mass`  the flat-`ε` family: the route law is an edge sum, `eF1`
                                      and `eF2` are that sum clamped edge by edge, and the
                                      clamp is the coasting ceiling of 5;
16. `lawEdge_reduced_ge`,
    `v2_reduced_ge`, `v2_path_ge`,
    `v2_path_ge_rate`,
    `rolling_bound_fails`             potential energy is a feasible potential, for the
                                      unclamped law too; the lower bounds a search may use;
                                      and `α_r·d` is not one of them;
17. `valley_toll`                     two arms of the valley toll `min(D, H, buffer)`, as
                                      bounds on the kinetic head a valley carries into its climb.

What is assumed, and where. The equation of motion is paper 1's eq. (3) with a brake force added;
nothing else enters `ledger`. The closed form then needs two riding assumptions, each a named
hypothesis of `closed_form_of_newton`: on flat stretches the air is paid at the reference speed
(`flat_aero`), and off the descents nobody brakes (`no_brake`). Under those the law is an
identity, not an approximation: its kinetic-energy remainder and the work against the air on
the climbs are printed in the statement. F2's third assumption, that the air costs nothing on a
climb, is the choice to drop that last term.

What is not proved, because it is not a theorem. How much of the ceiling a real rider collects
(the coasting deficit `ε₀`), the deadband threshold `τ` and the noise rate `c` are measurements.
They correct for riding that departs from the three assumptions and for elevation data that is
not the road. Nothing here says how large those departures are. In particular 7–10 show that a
kinetic-energy buffer acts as a deadband of half its width; they do not show that the deadband
fitted to recorded rides is that buffer and nothing else.

The same holds for 11–17. The equation of motion gives the ideal edge cost. The deficit `ε₀`,
the climb gate, the map scalar `k_s` and `eF4`'s noise rate enter as parameters, and the
statements about `v2Edge` and `eFEdge` are algebra about those formulas, which are defined here
branch for branch as `r1d_v2_edge` and `edge_form` compute them. Whether the formulas match
riders is paper 3's measurement.

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

/-- Paper 1's F2 for a route cut into flat segments `F`, climbs `C` and descents `D`:
`α_r·x + α_a·x_flat + β·(h₊ − ε·h₋)` plus the net change in kinetic energy, with `α_r = R/k`,
`α_a = A/k`, `β = W/k`, `x_flat` the distance off the climbs and `ε` the drop-weighted mean
refund. -/
noncomputable def lawF2 (F C D : Finset ι) (R A W k : ℝ) (x up dn waste q : ι → ℝ) : ℝ :=
  R / k * (∑ i ∈ F, x i + ∑ i ∈ C, x i + ∑ i ∈ D, x i)
    + A / k * (∑ i ∈ F, x i + ∑ i ∈ D, x i)
    + W / k * ((∑ i ∈ F, up i + ∑ i ∈ C, up i) - meanRefund D W dn waste * ∑ i ∈ D, dn i)
    + (∑ i ∈ F, q i + ∑ i ∈ C, q i + ∑ i ∈ D, q i) / k

/-- **The three-term law, and its fourth term.** Segment `i` has run `x i`, rise `up i` or drop
`dn i`, leg energy `e i` and kinetic-energy change `q i`. Suppose its ledger entry is

* on a flat: rolling, air at the reference speed, and the rise;
* on a climb: rolling, the rise, and whatever work `air i` the air took;
* on a descent: rolling and air at the reference speed, less the drop, plus what is wasted.

Then the leg energy of the route is F2 plus the work done against the air on the climbs. Nothing
is assumed about that work: paper 1's forms are the two ways of closing it. F2 sets it to zero,
and F1 charges it at the reference speed, `α_a·x_climb`. -/
theorem three_term_law (F C D : Finset ι) {R A W k : ℝ} (hk : k ≠ 0) (hW : W ≠ 0)
    {x up dn e waste q air : ι → ℝ} (hdn : ∀ i ∈ D, 0 < dn i)
    (flat : ∀ i ∈ F, k * e i = R * x i + A * x i + W * up i + q i)
    (climb : ∀ i ∈ C, k * e i = R * x i + air i + W * up i + q i)
    (desc : ∀ i ∈ D, k * e i = R * x i + A * x i - W * dn i + waste i + q i) :
    ∑ i ∈ F, e i + ∑ i ∈ C, e i + ∑ i ∈ D, e i
      = lawF2 F C D R A W k x up dn waste q + (∑ i ∈ C, air i) / k := by
  have eF : k * ∑ i ∈ F, e i
      = R * ∑ i ∈ F, x i + A * ∑ i ∈ F, x i + W * ∑ i ∈ F, up i + ∑ i ∈ F, q i := by
    rw [mul_sum, sum_congr rfl flat]
    simp only [sum_add_distrib, mul_sum]
  have eC : k * ∑ i ∈ C, e i
      = R * ∑ i ∈ C, x i + ∑ i ∈ C, air i + W * ∑ i ∈ C, up i + ∑ i ∈ C, q i := by
    rw [mul_sum, sum_congr rfl climb]
    simp only [sum_add_distrib, mul_sum]
  have eD : k * ∑ i ∈ D, e i
      = R * ∑ i ∈ D, x i + A * ∑ i ∈ D, x i - W * ∑ i ∈ D, dn i + ∑ i ∈ D, waste i
        + ∑ i ∈ D, q i := by
    rw [mul_sum, sum_congr rfl desc]
    simp only [sum_add_distrib, sum_sub_distrib, mul_sum]
  unfold lawF2
  rw [meanRefund_mul_drop D hW hdn]
  apply mul_left_cancel₀ hk
  field_simp
  linear_combination eF + eC + eD

/-- **F2 and F1 bracket the truth.** If the air takes some work on every climb, and at most
`cap i`, the route's leg energy lies between F2 and F2 plus the caps. With `cap i = A·x i`,
which holds when climbs are ridden no faster than the reference speed, the upper end is F1.
With the cap of `steady_climb_air_le` it is the `vc` mode of `engines.py`. -/
theorem law_bracket (F C D : Finset ι) {R A W k : ℝ} (hk : 0 < k) (hW : W ≠ 0)
    {x up dn e waste q air cap : ι → ℝ} (hdn : ∀ i ∈ D, 0 < dn i)
    (flat : ∀ i ∈ F, k * e i = R * x i + A * x i + W * up i + q i)
    (climb : ∀ i ∈ C, k * e i = R * x i + air i + W * up i + q i)
    (desc : ∀ i ∈ D, k * e i = R * x i + A * x i - W * dn i + waste i + q i)
    (hair : ∀ i ∈ C, 0 ≤ air i ∧ air i ≤ cap i) :
    lawF2 F C D R A W k x up dn waste q ≤ ∑ i ∈ F, e i + ∑ i ∈ C, e i + ∑ i ∈ D, e i
      ∧ ∑ i ∈ F, e i + ∑ i ∈ C, e i + ∑ i ∈ D, e i
          ≤ lawF2 F C D R A W k x up dn waste q + (∑ i ∈ C, cap i) / k := by
  rw [three_term_law F C D hk.ne' hW hdn flat climb desc]
  have lo : 0 ≤ (∑ i ∈ C, air i) / k :=
    div_nonneg (sum_nonneg fun i hi => (hair i hi).1) hk.le
  have hi : (∑ i ∈ C, air i) / k ≤ (∑ i ∈ C, cap i) / k := by
    gcongr with i hi
    exact (hair i hi).2
  constructor <;> linarith

/-- **A steady climb is slower than its power suggests.** Holding speed `v` up a grade `s`
against rolling `R`, weight `W` and drag `a·v²`, the equation of motion reads
`k·P/v = R + a·v² + W·s`. So `v ≤ k·P/(R + W·s)`: the speed computed without the air, which is
what the `vc` mode of `engines.py` uses, is never too low. -/
theorem steady_climb_speed_le {R W a k P s v : ℝ} (hv : 0 < v) (ha : 0 ≤ a)
    (hRW : 0 < R + W * s) (bal : k * P / v = R + a * v ^ 2 + W * s) :
    v ≤ k * P / (R + W * s) := by
  rw [le_div_iff₀ hRW]
  have hP : k * P = v * (R + a * v ^ 2 + W * s) := by
    field_simp at bal
    linarith
  have h3 : 0 ≤ a * v ^ 3 := mul_nonneg ha (pow_pos hv 3).le
  nlinarith [h3]

/-- Hence the air's force on a steady climb is at most what the `vc` mode charges. -/
theorem steady_climb_air_le {R W a k P s v : ℝ} (hv : 0 < v) (ha : 0 ≤ a)
    (hRW : 0 < R + W * s) (bal : k * P / v = R + a * v ^ 2 + W * s) :
    a * v ^ 2 ≤ a * (k * P / (R + W * s)) ^ 2 :=
  mul_le_mul_of_nonneg_left
    (pow_le_pow_left₀ hv.le (steady_climb_speed_le hv ha hRW bal) 2) ha

/-! ## 4. Equation of motion in, closed form out -/

/-- Increment of a cumulative quantity `f` over segment `i` of a route cut at `s 0, s 1, …`. -/
def seg (f : ℝ → ℝ) (s : ℕ → ℝ) (i : ℕ) : ℝ := f (s (i + 1)) - f (s i)

/-- **The closed form follows from the equation of motion.** Take a ride obeying `newton`, as in
`ledger`, and cut its route at `s 0, …, s n` into flat stretches `F`, climbs `C` and descents `D`.
Assume only that

* `flat_aero`: on flat stretches the air costs what it would at the reference speed, `A` per
  horizontal metre (`A = ½·ρ·C_dA·v_f²` in still air);
* `no_brake`: there is no braking off the descents.

Then the leg energy is `α_r·x + α_a·x_flat + W_air,climbs/k + β·(h₊ − ε·h₋) + ΔKE/k`, where
`α_r = C_rr·m·g/k`, `α_a = A/k`, `β = m·g/k`, `ε` is the drop-weighted mean refund of the
descents, and `W_air,climbs` is the work actually done against the air on the climbs. F2 is the
case where that work is neglected. A ride that ends at the speed it started loses the last
term. -/
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
    (no_brake : ∀ i ∈ F ∪ C, seg Wb s i = 0) :
    E (s n) - E (s 0)
      = Crr * m * g / k * (X (s n) - X (s 0))
        + A / k * ∑ i ∈ F ∪ D, seg X s i
        + (∑ i ∈ C, seg Wa s i) / k
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
    (q := seg (fun t => m * v t ^ 2 / 2) s) (air := seg Wa s)
    (fun i hi => by have := hdrop i hi; unfold seg; linarith)
    (fun i hi => by
      have := bal i (memF i hi)
      rw [flat_aero i hi, no_brake i (mem_union_left _ hi)] at this
      linarith)
    (fun i hi => by
      have := bal i (memC i hi)
      rw [no_brake i (mem_union_right _ hi)] at this
      linarith)
    (fun i hi => by linarith [bal i (memD i hi)])
  unfold lawF2 at law
  rw [← split, ← split, ← split, tele, tele, tele] at law
  rw [sum_union hFD, sum_union hFC]
  linarith

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

/-! ## 6. Kinetic energy and the deadband -/

/-- The hypotheses of `ledger`, bundled: on the stretch `[a, b]` the ride obeys the equation of
motion, for some speed gradient, road geometry, pedal power, drag force and brake force. -/
def Obeys (m g Crr k : ℝ) (v X h E Wa Wb : ℝ → ℝ) (a b : ℝ) : Prop :=
  ∃ v' c σ P drag brake : ℝ → ℝ,
    HasRateOn v v' a b ∧ HasRateOn X c a b ∧ HasRateOn h σ a b ∧
    HasRateOn E (fun s => P s / v s) a b ∧ HasRateOn Wa drag a b ∧ HasRateOn Wb brake a b ∧
    ∀ s ∈ Set.Ico a b, m * v s * v' s
      = k * (P s / v s) - Crr * m * g * c s - drag s - m * g * σ s - brake s

theorem Obeys.mono {m g Crr k : ℝ} {v X h E Wa Wb : ℝ → ℝ} {a b a' b' : ℝ}
    (ride : Obeys m g Crr k v X h E Wa Wb a b) (ha : a ≤ a') (hb : b' ≤ b) :
    Obeys m g Crr k v X h E Wa Wb a' b' := by
  obtain ⟨v', c, σ, P, drag, brake, hv, hX, hh, hE, hWa, hWb, newton⟩ := ride
  exact ⟨v', c, σ, P, drag, brake, hv.mono ha hb, hX.mono ha hb, hh.mono ha hb, hE.mono ha hb,
    hWa.mono ha hb, hWb.mono ha hb, fun s hs => newton s (Set.Ico_subset_Ico ha hb hs)⟩

/-- The **energy line**: elevation, plus the kinetic head `v²/2g`, plus the head already lost to
rolling resistance (`C_rr` per horizontal metre) and to the air. On a steady ride it is the
elevation profile tilted up by the flat-resistance grade `s⋆ = α/β`. -/
noncomputable def energyLine (m g Crr : ℝ) (v X h Wa : ℝ → ℝ) (t : ℝ) : ℝ :=
  h t + v t ^ 2 / (2 * g) + Crr * X t + Wa t / (m * g)

/-- **Kinetic energy is height.** The ledger sees speed only through the kinetic head `v²/2g`,
added to the elevation: leg energy raises the energy line, braking lowers it, and nothing else
moves it. -/
theorem Obeys.energyLine {m g Crr k : ℝ} {v X h E Wa Wb : ℝ → ℝ} {a b : ℝ}
    (ride : Obeys m g Crr k v X h E Wa Wb a b) (hab : a ≤ b) (hm : m ≠ 0) (hg : g ≠ 0) :
    k * (E b - E a)
      = m * g * (energyLine m g Crr v X h Wa b - energyLine m g Crr v X h Wa a)
        + (Wb b - Wb a) := by
  obtain ⟨v', c, σ, P, drag, brake, hv, hX, hh, hE, hWa, hWb, newton⟩ := ride
  rw [ledger hab hv hX hh hE hWa hWb newton]
  unfold RouteEnergy.energyLine
  field_simp
  ring

/-- **Free lift.** On a stretch ridden without braking, speed given up is height gained: a
climb of `H` entered at `v a` and left at `v b` costs the legs what a climb of
`H − (v a² − v b²)/2g` would at constant speed. -/
theorem Obeys.free_lift {m g Crr k : ℝ} {v X h E Wa Wb : ℝ → ℝ} {a b : ℝ}
    (ride : Obeys m g Crr k v X h E Wa Wb a b) (hab : a ≤ b) (hm : m ≠ 0) (hg : g ≠ 0)
    (no_brake : Wb b = Wb a) :
    k * (E b - E a)
      = Crr * m * g * (X b - X a) + (Wa b - Wa a)
        + m * g * ((h b - h a) - (v a ^ 2 - v b ^ 2) / (2 * g)) := by
  rw [ride.energyLine hab hm hg, no_brake]
  unfold RouteEnergy.energyLine
  field_simp
  ring

/-- Total ascent of a sampled profile over its first `n` steps. -/
noncomputable def ascent (n : ℕ) (f : ℕ → ℝ) : ℝ := ∑ i ∈ range n, max (f (i + 1) - f i) 0

/-- **Leg energy is at least the ascent of the energy line.** Cut the ride at `s 0, …, s n`.
Legs only ever add energy and brakes only ever remove it, so the legs pay for every metre the
energy line rises between cuts. -/
theorem leg_energy_ge_ascent {m g Crr k : ℝ} (hm : 0 < m) (hg : 0 < g) (hk : 0 ≤ k)
    {v X h E Wa Wb : ℝ → ℝ} (s : ℕ → ℝ) (hs : Monotone s) (n : ℕ)
    (ride : Obeys m g Crr k v X h E Wa Wb (s 0) (s n))
    (legs : ∀ i < n, E (s i) ≤ E (s (i + 1)))
    (brakes : ∀ i < n, Wb (s i) ≤ Wb (s (i + 1))) :
    m * g * ascent n (fun i => energyLine m g Crr v X h Wa (s i)) ≤ k * (E (s n) - E (s 0)) := by
  have hmg : 0 < m * g := mul_pos hm hg
  rw [← sum_range_sub (fun i => E (s i)) n, ascent, mul_sum, mul_sum]
  refine sum_le_sum fun i hi => ?_
  have hi' := mem_range.1 hi
  have bal := (ride.mono (hs (Nat.zero_le i)) (hs hi')).energyLine (hs (Nat.le_succ i))
    hm.ne' hg.ne'
  have hE := legs i hi'
  have hB := brakes i hi'
  rcases le_total (energyLine m g Crr v X h Wa (s (i + 1)) - energyLine m g Crr v X h Wa (s i)) 0
    with hY | hY
  · rw [max_eq_right hY, mul_zero]
    exact mul_nonneg hk (by linarith)
  · rw [max_eq_left hY]
    linarith

/-- **And exactly that ascent, for a rider who never brakes and pedals on the same stretch.** -/
theorem leg_energy_eq_ascent {m g Crr k : ℝ} (hm : 0 < m) (hg : 0 < g) (hk : 0 ≤ k)
    {v X h E Wa Wb : ℝ → ℝ} (s : ℕ → ℝ) (hs : Monotone s) (n : ℕ)
    (ride : Obeys m g Crr k v X h E Wa Wb (s 0) (s n))
    (legs : ∀ i < n, E (s i) ≤ E (s (i + 1)))
    (brakes : ∀ i < n, Wb (s i) ≤ Wb (s (i + 1)))
    (never_both : ∀ i < n, Wb (s (i + 1)) = Wb (s i) ∨ E (s (i + 1)) = E (s i)) :
    k * (E (s n) - E (s 0)) = m * g * ascent n (fun i => energyLine m g Crr v X h Wa (s i)) := by
  have hmg : 0 < m * g := mul_pos hm hg
  rw [← sum_range_sub (fun i => E (s i)) n, ascent, mul_sum, mul_sum]
  refine sum_congr rfl fun i hi => ?_
  have hi' := mem_range.1 hi
  have bal := (ride.mono (hs (Nat.zero_le i)) (hs hi')).energyLine (hs (Nat.le_succ i))
    hm.ne' hg.ne'
  have hE := legs i hi'
  have hB := brakes i hi'
  rcases never_both i hi' with hb | he
  · -- no braking: the legs' energy is the rise of the line, which is therefore a rise
    have hpos : 0 ≤ k * (E (s (i + 1)) - E (s i)) := mul_nonneg hk (by linarith)
    have hY : 0 ≤ energyLine m g Crr v X h Wa (s (i + 1)) - energyLine m g Crr v X h Wa (s i) := by
      by_contra hneg
      have := mul_neg_of_pos_of_neg hmg (not_le.1 hneg)
      linarith
    rw [max_eq_left hY]
    linarith
  · -- no pedalling: the line can only fall
    have hY : energyLine m g Crr v X h Wa (s (i + 1)) - energyLine m g Crr v X h Wa (s i) ≤ 0 := by
      by_contra hpos
      have := mul_pos hmg (not_le.1 hpos)
      rw [he] at bal
      linarith
    rw [max_eq_right hY, he]
    ring

/-- The **deadband filter** of `engines.py` (`deadband`), a backlash: the output starts at the
input, stays put while the input is within `τ` of it, and otherwise follows at a distance `τ`. -/
noncomputable def deadband (τ : ℝ) (u : ℕ → ℝ) : ℕ → ℝ
  | 0 => u 0
  | i + 1 => max (u (i + 1) - τ) (min (u (i + 1) + τ) (deadband τ u i))

/-- The definition above is the three-way branch the code runs. -/
theorem deadband_succ {τ : ℝ} (hτ : 0 ≤ τ) (u : ℕ → ℝ) (i : ℕ) :
    deadband τ u (i + 1) =
      if deadband τ u i + τ < u (i + 1) then u (i + 1) - τ
      else if u (i + 1) < deadband τ u i - τ then u (i + 1) + τ
      else deadband τ u i := by
  simp only [deadband, max_def, min_def]
  split_ifs <;> linarith

/-- The filtered profile never strays more than `τ` from the recorded one. -/
theorem abs_deadband_sub_le {τ : ℝ} (hτ : 0 ≤ τ) (u : ℕ → ℝ) (i : ℕ) :
    |deadband τ u i - u i| ≤ τ := by
  cases i with
  | zero => simpa [deadband] using hτ
  | succ i =>
    rw [abs_le]
    simp only [deadband, max_def, min_def]
    constructor <;> split_ifs <;> linarith

/-- One step of the filter against one step of any profile `p → q` that ends inside the band
`[L, U]` the filter is clamped to. -/
theorem deadband_step {a p q L U : ℝ} (hL : L ≤ q) (hU : q ≤ U) :
    max (max L (min U a) - a) 0 + max (q - max L (min U a)) 0
      ≤ max (q - p) 0 + max (p - a) 0 := by
  have h1 : q - p ≤ max (q - p) 0 := le_max_left _ _
  have h2 : p - a ≤ max (p - a) 0 := le_max_left _ _
  have h3 : 0 ≤ max (q - p) 0 := le_max_right _ _
  have h4 : 0 ≤ max (p - a) 0 := le_max_right _ _
  rcases le_total a L with haL | haL
  · -- the filter is pushed up to `L`
    have hb : max L (min U a) = L := by rw [min_eq_right (by linarith), max_eq_left haL]
    rw [hb, max_eq_left (by linarith), max_eq_left (by linarith)]
    linarith
  · rcases le_total a U with haU | haU
    · -- the filter stays where it is
      have hb : max L (min U a) = a := by rw [min_eq_right haU, max_eq_right haL]
      rw [hb, sub_self, max_self]
      rcases le_total (q - a) 0 with h | h
      · rw [max_eq_right h]; linarith
      · rw [max_eq_left h]; linarith
    · -- the filter is pushed down to `U`
      have hb : max L (min U a) = U := by rw [min_eq_left haU, max_eq_right (by linarith)]
      rw [hb, max_eq_right (by linarith), max_eq_right (by linarith)]
      linarith

/-- **No profile within `τ` of the recording climbs less than the filtered one.** For any `w`
that stays within `τ` of `u`, the filter's ascent is at most `w`'s, plus whatever head start `w`
has over the recording at the first sample. -/
theorem ascent_deadband_le {τ : ℝ} (u w : ℕ → ℝ) (n : ℕ) (hw : ∀ i ≤ n, |w i - u i| ≤ τ) :
    ascent n (deadband τ u) ≤ ascent n w + max (w 0 - u 0) 0 := by
  have key : ∀ j ≤ n, ascent j (deadband τ u) + max (w j - deadband τ u j) 0
      ≤ ascent j w + max (w 0 - u 0) 0 := by
    intro j
    induction j with
    | zero => intro _; simp [ascent, deadband]
    | succ j ih =>
      intro hj
      have ih := ih (Nat.le_of_succ_le hj)
      have hb := abs_le.1 (hw (j + 1) hj)
      have step := deadband_step (a := deadband τ u j) (p := w j) (q := w (j + 1))
        (L := u (j + 1) - τ) (U := u (j + 1) + τ) (by linarith) (by linarith)
      have unfold : deadband τ u (j + 1)
          = max (u (j + 1) - τ) (min (u (j + 1) + τ) (deadband τ u j)) := by rw [deadband]
      rw [← unfold] at step
      simp only [ascent, sum_range_succ] at ih ⊢
      linarith
  have := key n le_rfl
  have hpos : 0 ≤ max (w n - deadband τ u n) 0 := le_max_right _ _
  linarith

/-- **The deadband is the least ascent in its band.** Among all profiles that start where the
recording starts and stay within `τ` of it, the filtered profile is one, and none climbs less. -/
theorem deadband_isLeast {τ : ℝ} (hτ : 0 ≤ τ) (u : ℕ → ℝ) (n : ℕ) :
    IsLeast {A | ∃ w : ℕ → ℝ, w 0 = u 0 ∧ (∀ i ≤ n, |w i - u i| ≤ τ) ∧ ascent n w = A}
      (ascent n (deadband τ u)) := by
  refine ⟨⟨deadband τ u, rfl, fun i _ => abs_deadband_sub_le hτ u i, rfl⟩, ?_⟩
  rintro A ⟨w, h0, hw, rfl⟩
  have := ascent_deadband_le u w n hw
  rw [h0, sub_self, max_self] at this
  linarith

/-- **A kinetic-energy buffer is a deadband.** If, at the cuts, the rider's kinetic head
`v²/2g` stays within `τ` of some level `κ`, the legs pay at least for the ascent of the
`τ`-deadband-filtered road, where the road is the elevation plus the head lost to rolling and
air. The correction term vanishes for a ride that starts at the middle of its band or slower. -/
theorem leg_energy_ge_deadband {m g Crr k : ℝ} (hm : 0 < m) (hg : 0 < g) (hk : 0 ≤ k)
    {v X h E Wa Wb : ℝ → ℝ} (s : ℕ → ℝ) (hs : Monotone s) (n : ℕ)
    (ride : Obeys m g Crr k v X h E Wa Wb (s 0) (s n))
    (legs : ∀ i < n, E (s i) ≤ E (s (i + 1)))
    (brakes : ∀ i < n, Wb (s i) ≤ Wb (s (i + 1)))
    {τ κ : ℝ} (band : ∀ i ≤ n, |v (s i) ^ 2 / (2 * g) - κ| ≤ τ) :
    m * g * (ascent n (deadband τ fun i => h (s i) + Crr * X (s i) + Wa (s i) / (m * g))
        - max (v (s 0) ^ 2 / (2 * g) - κ) 0)
      ≤ k * (E (s n) - E (s 0)) := by
  have hmg : 0 < m * g := mul_pos hm hg
  have base := leg_energy_ge_ascent hm hg hk s hs n ride legs brakes
  -- the energy line, lowered by `κ`, is a profile within `τ` of the road
  have shift : ascent n (fun i => energyLine m g Crr v X h Wa (s i))
      = ascent n (fun i => energyLine m g Crr v X h Wa (s i) - κ) := by
    simp [ascent]
  have tube := ascent_deadband_le (τ := τ)
    (fun i => h (s i) + Crr * X (s i) + Wa (s i) / (m * g))
    (fun i => energyLine m g Crr v X h Wa (s i) - κ) n
    (fun i hi => by
      have := band i hi
      simp only [energyLine]
      rwa [show h (s i) + v (s i) ^ 2 / (2 * g) + Crr * X (s i) + Wa (s i) / (m * g) - κ
          - (h (s i) + Crr * X (s i) + Wa (s i) / (m * g)) = v (s i) ^ 2 / (2 * g) - κ by ring])
  have h0 : energyLine m g Crr v X h Wa (s 0) - κ
      - (h (s 0) + Crr * X (s 0) + Wa (s 0) / (m * g)) = v (s 0) ^ 2 / (2 * g) - κ := by
    simp only [energyLine]; ring
  simp only [h0] at tube
  rw [← shift] at tube
  nlinarith [mul_le_mul_of_nonneg_left tube hmg.le]

/-! ## 7. From the route to the edge (paper 3)

Paper 3 turns the law into a cost per graph edge. This section derives from the equation of
motion what such a cost must look like, and then proves the algebra of the two families the
paper deploys: `v2Edge` (its E1 and E2) and the flat-`ε` family `eF1`, `eF2`, `eF4`. -/

/-- Total head: elevation plus the kinetic head `v²/2g`. -/
noncomputable def totalHead (g : ℝ) (v h : ℝ → ℝ) (t : ℝ) : ℝ := h t + v t ^ 2 / (2 * g)

/-- The **ideal edge cost**: the flat bill plus the climb, or nothing once gravity pays for
both. `α` is the flat bill per horizontal metre and `β` the cost of a metre of climb. -/
noncomputable def idealEdge (α β Δx Δh : ℝ) : ℝ := max 0 (α * Δx + β * Δh)

/-- **The ledger of one edge.** Between two nodes the legs pay for rolling, for the rise in
total head, and for whatever the air and the brakes take. Speed enters only through the head
at the two nodes. -/
theorem Obeys.edge {m g Crr k : ℝ} {v X h E Wa Wb : ℝ → ℝ} {a b : ℝ}
    (ride : Obeys m g Crr k v X h E Wa Wb a b) (hab : a ≤ b) (hm : m ≠ 0) (hg : g ≠ 0) :
    k * (E b - E a)
      = Crr * m * g * (X b - X a) + m * g * (totalHead g v h b - totalHead g v h a)
        + (Wa b - Wa a) + (Wb b - Wb a) := by
  rw [ride.energyLine hab hm hg]
  unfold RouteEnergy.energyLine totalHead
  field_simp
  ring

/-- **An edge costs at least the ideal edge cost.** If the air and the brakes together take at
least the reference air bill `A` per metre, which they do whenever the edge is ridden no slower
than the reference speed, and the legs only add energy, then the edge costs at least
`max 0 (α·Δx + β·ΔH)`, with `ΔH` the rise in total head. With `A = 0` this is the floor that
holds for every rider: rolling and gravity alone. -/
theorem edge_ge_ideal {m g Crr k A : ℝ} (hm : 0 < m) (hg : 0 < g) (hk : 0 < k)
    {v X h E Wa Wb : ℝ → ℝ} {a b : ℝ} (hab : a ≤ b)
    (ride : Obeys m g Crr k v X h E Wa Wb a b)
    (legs : E a ≤ E b)
    (waste : A * (X b - X a) ≤ (Wa b - Wa a) + (Wb b - Wb a)) :
    idealEdge ((Crr * m * g + A) / k) (m * g / k) (X b - X a)
        (totalHead g v h b - totalHead g v h a) ≤ E b - E a := by
  have bal := ride.edge hab hm.ne' hg.ne'
  unfold idealEdge
  refine max_le (by linarith) ?_
  rw [div_mul_eq_mul_div, div_mul_eq_mul_div, ← add_div, div_le_iff₀ hk]
  linarith

/-- **And exactly the ideal edge cost, for the ideal coaster**: on each edge either the air
takes the reference bill and nothing is braked, or the legs do nothing. -/
theorem edge_eq_ideal {m g Crr k A : ℝ} (hm : 0 < m) (hg : 0 < g) (hk : 0 < k)
    {v X h E Wa Wb : ℝ → ℝ} {a b : ℝ} (hab : a ≤ b)
    (ride : Obeys m g Crr k v X h E Wa Wb a b)
    (legs : E a ≤ E b)
    (waste : A * (X b - X a) ≤ (Wa b - Wa a) + (Wb b - Wb a))
    (ideal : (Wa b - Wa a) + (Wb b - Wb a) = A * (X b - X a) ∨ E b = E a) :
    E b - E a = idealEdge ((Crr * m * g + A) / k) (m * g / k) (X b - X a)
        (totalHead g v h b - totalHead g v h a) := by
  refine le_antisymm ?_ (edge_ge_ideal hm hg hk hab ride legs waste)
  have bal := ride.edge hab hm.ne' hg.ne'
  unfold idealEdge
  rcases ideal with hw | he
  · refine le_trans (le_of_eq ?_) (le_max_right _ _)
    rw [div_mul_eq_mul_div, div_mul_eq_mul_div, ← add_div, eq_div_iff hk.ne']
    linarith
  · rw [he, sub_self]
    exact le_max_left _ _

/-- **And at most the flat bill plus the climb**, on an edge where the air and the brakes
together take no more than the reference air bill: a climb ridden no faster than the reference
speed. Paper 3's gated climb arm is the floor above with `A = 0`; its ungated arm is this. -/
theorem edge_le_bill {m g Crr k A : ℝ} (hm : 0 < m) (hg : 0 < g) (hk : 0 < k)
    {v X h E Wa Wb : ℝ → ℝ} {a b : ℝ} (hab : a ≤ b)
    (ride : Obeys m g Crr k v X h E Wa Wb a b)
    (waste : (Wa b - Wa a) + (Wb b - Wb a) ≤ A * (X b - X a)) :
    E b - E a ≤ (Crr * m * g + A) / k * (X b - X a)
        + m * g / k * (totalHead g v h b - totalHead g v h a) := by
  have bal := ride.edge hab hm.ne' hg.ne'
  rw [div_mul_eq_mul_div, div_mul_eq_mul_div, ← add_div, le_div_iff₀ hk]
  linarith

/-- **The edge sum is a lower bound on the ride.** Cut the ride at the graph's nodes and
suppose the rider passes every node at the same speed. Then the sum of ideal edge costs, read
off the map's own `Δx` and `Δh`, is at most what the legs deliver. -/
theorem edge_sum_le_energy {m g Crr k A : ℝ} (hm : 0 < m) (hg : 0 < g) (hk : 0 < k)
    {v X h E Wa Wb : ℝ → ℝ} (s : ℕ → ℝ) (hs : Monotone s) (n : ℕ)
    (ride : Obeys m g Crr k v X h E Wa Wb (s 0) (s n))
    (steady : ∀ i < n, v (s (i + 1)) = v (s i))
    (legs : ∀ i < n, E (s i) ≤ E (s (i + 1)))
    (waste : ∀ i < n, A * seg X s i ≤ seg Wa s i + seg Wb s i) :
    ∑ i ∈ range n, idealEdge ((Crr * m * g + A) / k) (m * g / k) (seg X s i) (seg h s i)
      ≤ E (s n) - E (s 0) := by
  rw [← sum_range_sub (fun i => E (s i)) n]
  refine sum_le_sum fun i hi => ?_
  have hi' := mem_range.1 hi
  have key := edge_ge_ideal hm hg hk (hs (Nat.le_succ i))
    (ride.mono (hs (Nat.zero_le i)) (hs hi')) (legs i hi') (waste i hi')
  have hH : totalHead g v h (s (i + 1)) - totalHead g v h (s i) = seg h s i := by
    unfold totalHead seg
    rw [steady i hi']
    ring
  rw [hH] at key
  exact key

/-- **The edge sum is the ride, for the ideal coaster.** Under the same node condition, a rider
who on every edge either holds the reference air bill without braking or does not pedal spends
exactly the sum of ideal edge costs. This is the derivation of paper 3's E1 at zero deficit
and without the climb gate. -/
theorem energy_eq_edge_sum {m g Crr k A : ℝ} (hm : 0 < m) (hg : 0 < g) (hk : 0 < k)
    {v X h E Wa Wb : ℝ → ℝ} (s : ℕ → ℝ) (hs : Monotone s) (n : ℕ)
    (ride : Obeys m g Crr k v X h E Wa Wb (s 0) (s n))
    (steady : ∀ i < n, v (s (i + 1)) = v (s i))
    (legs : ∀ i < n, E (s i) ≤ E (s (i + 1)))
    (waste : ∀ i < n, A * seg X s i ≤ seg Wa s i + seg Wb s i)
    (ideal : ∀ i < n, seg Wa s i + seg Wb s i = A * seg X s i ∨ E (s (i + 1)) = E (s i)) :
    E (s n) - E (s 0)
      = ∑ i ∈ range n, idealEdge ((Crr * m * g + A) / k) (m * g / k) (seg X s i) (seg h s i) := by
  rw [← sum_range_sub (fun i => E (s i)) n]
  refine sum_congr rfl fun i hi => ?_
  have hi' := mem_range.1 hi
  have key := edge_eq_ideal hm hg hk (hs (Nat.le_succ i))
    (ride.mono (hs (Nat.zero_le i)) (hs hi')) (legs i hi') (waste i hi') (ideal i hi')
  have hH : totalHead g v h (s (i + 1)) - totalHead g v h (s i) = seg h s i := by
    unfold totalHead seg
    rw [steady i hi']
    ring
  rw [hH] at key
  exact key

/-! ### The edge sum and the mesh -/

/-- The ideal edge cost is `β` times the rise of the road tilted by the flat-resistance grade
`s⋆ = α/β`. -/
theorem idealEdge_eq_rise {α β : ℝ} (hβ : 0 < β) (Δx Δh : ℝ) :
    idealEdge α β Δx Δh = β * max (Δh + α / β * Δx) 0 := by
  have e : β * (Δh + α / β * Δx) = α * Δx + β * Δh := by
    field_simp
    ring
  rw [idealEdge, mul_max_of_nonneg _ _ hβ.le, mul_zero, e, max_comm]

/-- **The ideal edge sum is the ascent of the tilted road**, sampled at the nodes. -/
theorem edge_sum_eq_ascent {α β : ℝ} (hβ : 0 < β) (x h : ℕ → ℝ) (n : ℕ) :
    ∑ i ∈ range n, idealEdge α β (x (i + 1) - x i) (h (i + 1) - h i)
      = β * ascent n (fun i => h i + α / β * x i) := by
  simp only [ascent, mul_sum]
  refine sum_congr rfl fun i _ => ?_
  rw [idealEdge_eq_rise hβ]
  congr 2
  ring

/-- A rise between two samples is at most the ascent of the samples between them. -/
theorem rise_le_ascent_Ico (f : ℕ → ℝ) {a b : ℕ} (hab : a ≤ b) :
    max (f b - f a) 0 ≤ ∑ i ∈ Ico a b, max (f (i + 1) - f i) 0 := by
  induction b, hab using Nat.le_induction with
  | base => simp
  | succ b hab ih =>
    rw [sum_Ico_succ_top hab]
    have h1 : f (b + 1) - f b ≤ max (f (b + 1) - f b) 0 := le_max_left _ _
    have h2 : 0 ≤ max (f (b + 1) - f b) 0 := le_max_right _ _
    have h3 : f b - f a ≤ max (f b - f a) 0 := le_max_left _ _
    have h4 : 0 ≤ max (f b - f a) 0 := le_max_right _ _
    refine max_le ?_ ?_ <;> linarith

/-- **A coarser mesh never finds more ascent.** Keep only the samples `φ 0 ≤ φ 1 ≤ …` of a
profile: the ascent of what is kept is at most the ascent of the whole. -/
theorem ascent_coarsen (f : ℕ → ℝ) {φ : ℕ → ℕ} (hφ : Monotone φ) (m : ℕ) :
    ascent m (fun j => f (φ j)) ≤ ascent (φ m) f := by
  induction m with
  | zero =>
    have h0 : ascent 0 (fun j => f (φ j)) = 0 := by simp [ascent]
    rw [h0]
    exact sum_nonneg fun i _ => le_max_right _ _
  | succ m ih =>
    have step := rise_le_ascent_Ico f (hφ (Nat.le_succ m))
    have split := sum_range_add_sum_Ico (fun i => max (f (i + 1) - f i) 0) (hφ (Nat.le_succ m))
    simp only [ascent, sum_range_succ] at ih ⊢
    linarith

/-- **Refining the mesh never lowers the ideal edge sum.** The same route costed on a finer
mesh costs at least as much: the edge sum does not converge downwards as `Δx → 0`. -/
theorem ideal_sum_coarsen {α β : ℝ} (hβ : 0 < β) (x h : ℕ → ℝ) {φ : ℕ → ℕ} (hφ : Monotone φ)
    (m : ℕ) :
    ∑ j ∈ range m, idealEdge α β (x (φ (j + 1)) - x (φ j)) (h (φ (j + 1)) - h (φ j))
      ≤ ∑ i ∈ range (φ m), idealEdge α β (x (i + 1) - x i) (h (i + 1) - h i) := by
  rw [edge_sum_eq_ascent hβ (fun j => x (φ j)) (fun j => h (φ j)) m,
    edge_sum_eq_ascent hβ x h (φ m)]
  exact mul_le_mul_of_nonneg_left (ascent_coarsen (fun i => h i + α / β * x i) hφ m) hβ.le

/-- The filtered profile climbs no more than the recorded one. -/
theorem ascent_deadband_le_self {τ : ℝ} (hτ : 0 ≤ τ) (u : ℕ → ℝ) (n : ℕ) :
    ascent n (deadband τ u) ≤ ascent n u := by
  have h := ascent_deadband_le (τ := τ) u u n (fun i _ => by simpa using hτ)
  simpa using h

/-- **What the edge sum cannot see.** On any mesh the ideal edge sum is at least `β` times the
deadband-filtered ascent of the tilted road: the least a rider with a kinetic buffer can pay
(section 6). The difference is the kinetic term, and by `ideal_sum_coarsen` a finer mesh does
not bring the edge sum down towards it. -/
theorem edge_sum_ge_deadband {α β τ : ℝ} (hβ : 0 < β) (hτ : 0 ≤ τ) (x h : ℕ → ℝ) (n : ℕ) :
    β * ascent n (deadband τ fun i => h i + α / β * x i)
      ≤ ∑ i ∈ range n, idealEdge α β (x (i + 1) - x i) (h (i + 1) - h i) := by
  rw [edge_sum_eq_ascent hβ x h n]
  exact mul_le_mul_of_nonneg_left (ascent_deadband_le_self hτ _ n) hβ.le

/-! ### The deployed cost, `v2Edge` (E1, E2) -/

/-- The grade-local refund of the deployed cost (E2): the coasting ceiling less the deficit
`ε₀`, floored at zero. -/
noncomputable def epsEdge (ε₀ sstar s : ℝ) : ℝ := max 0 (epsCoast sstar s - ε₀)

theorem epsEdge_nonneg (ε₀ sstar s : ℝ) : 0 ≤ epsEdge ε₀ sstar s := le_max_left _ _

theorem epsEdge_le_one {ε₀ : ℝ} (hε₀ : 0 ≤ ε₀) (sstar s : ℝ) : epsEdge ε₀ sstar s ≤ 1 := by
  unfold epsEdge epsCoast
  exact max_le zero_le_one (by linarith [min_le_left (1 : ℝ) (sstar / s)])

/-- Paper 3 writes E2 with a clamp to `[0, 1]`. Its upper half never acts. -/
theorem epsEdge_eq_clamp {ε₀ : ℝ} (hε₀ : 0 ≤ ε₀) (sstar s : ℝ) :
    max 0 (min 1 (epsCoast sstar s - ε₀)) = epsEdge ε₀ sstar s := by
  unfold epsEdge epsCoast
  rw [min_eq_right (by linarith [min_le_left (1 : ℝ) (sstar / s)])]

/-- The **deployed edge cost** (E1), branch for branch as `r1d_v2_edge` computes it. `αr` and
`αa` are the rolling and air parts of the flat bill, `θ` the climb gate, `ε₀` the coasting
deficit, and `γ` is `β` scaled by the map scalar `k_s`, which the deployed router applies to
the two gravity arms but not to the grade `s⋆ = α/β` inside the refund. -/
noncomputable def v2Edge (αr αa β γ θ ε₀ Δx Δh : ℝ) : ℝ :=
  if 0 ≤ Δh then αr * Δx + (if Δh < θ * Δx then αa * Δx else 0) + γ * Δh
  else max 0 ((αr + αa) * Δx - epsEdge ε₀ ((αr + αa) / β) (-Δh / Δx) * γ * (-Δh))

/-- The credit at the coasting ceiling never exceeds the flat bill. -/
theorem ceiling_credit_le {α β Δx d : ℝ} (hβ : 0 < β) (hΔx : 0 < Δx) (hd : 0 < d) :
    epsCoast (α / β) (d / Δx) * β * d ≤ α * Δx := by
  have h := coast_ceiling (α := α) hβ hΔx hd
  have := le_max_left 0 (α * Δx - β * d)
  linarith

/-- **A descent edge never costs less than `ε₀` of the flat bill**, whatever the constants. -/
theorem v2_descent_ge {α β γ ε₀ Δx d : ℝ} (hα : 0 ≤ α) (hβ : 0 < β) (hγβ : γ ≤ β)
    (hε₀ : 0 ≤ ε₀) (hε₁ : ε₀ ≤ 1) (hΔx : 0 < Δx) (hd : 0 < d) :
    ε₀ * (α * Δx) ≤ α * Δx - epsEdge ε₀ (α / β) (d / Δx) * γ * d := by
  have hc0 : 0 ≤ epsCoast (α / β) (d / Δx) :=
    le_min zero_le_one (div_nonneg (div_nonneg hα hβ.le) (div_nonneg hd.le hΔx.le))
  have hc1 : epsCoast (α / β) (d / Δx) ≤ 1 := min_le_left _ _
  have he0 := epsEdge_nonneg ε₀ (α / β) (d / Δx)
  -- the refund is at most `(1 − ε₀)` of the ceiling
  have he : epsEdge ε₀ (α / β) (d / Δx) ≤ (1 - ε₀) * epsCoast (α / β) (d / Δx) := by
    unfold epsEdge
    refine max_le (mul_nonneg (by linarith) hc0) ?_
    nlinarith
  have h1 : epsEdge ε₀ (α / β) (d / Δx) * γ * d ≤ epsEdge ε₀ (α / β) (d / Δx) * β * d :=
    mul_le_mul_of_nonneg_right (mul_le_mul_of_nonneg_left hγβ he0) hd.le
  have h2 : epsEdge ε₀ (α / β) (d / Δx) * (β * d)
      ≤ (1 - ε₀) * epsCoast (α / β) (d / Δx) * (β * d) :=
    mul_le_mul_of_nonneg_right he (mul_pos hβ hd).le
  have h3 : (1 - ε₀) * (epsCoast (α / β) (d / Δx) * β * d) ≤ (1 - ε₀) * (α * Δx) :=
    mul_le_mul_of_nonneg_left (ceiling_credit_le hβ hΔx hd) (by linarith)
  linarith

/-- **E1's own clamp is dead code**, for every choice of constants with `0 ≤ ε₀ ≤ 1` and
`k_s ≤ 1`: the descent arm is already non-negative. -/
theorem v2Edge_descent {αr αa β γ θ ε₀ Δx Δh : ℝ} (hα : 0 ≤ αr + αa) (hβ : 0 < β)
    (hγβ : γ ≤ β) (hε₀ : 0 ≤ ε₀) (hε₁ : ε₀ ≤ 1) (hΔx : 0 < Δx) (hΔh : Δh < 0) :
    v2Edge αr αa β γ θ ε₀ Δx Δh
      = (αr + αa) * Δx - epsEdge ε₀ ((αr + αa) / β) (-Δh / Δx) * γ * (-Δh) := by
  unfold v2Edge
  rw [ite_eq_right (not_le.2 hΔh)]
  exact max_eq_right (le_trans (mul_nonneg hε₀ (mul_nonneg hα hΔx.le))
    (v2_descent_ge hα hβ hγβ hε₀ hε₁ hΔx (by linarith)))

/-- **The deployed descent is the ideal coaster plus a deficit charge.** With `k_s = 1`, a
descent of run `Δx` and drop `d` costs the ideal edge cost plus `min(ε₀·β·d, α·Δx)`. So the
cost is `α·Δx − (1 − ε₀)·β·d` on a gentle descent, `ε₀·β·d` between the grades `s⋆` and
`s⋆/ε₀`, and the flat bill `α·Δx` beyond. -/
theorem v2_descent_eq {α β ε₀ Δx d : ℝ} (hβ : 0 < β) (hε₁ : ε₀ ≤ 1)
    (hΔx : 0 < Δx) (hd : 0 < d) :
    α * Δx - epsEdge ε₀ (α / β) (d / Δx) * β * d
      = idealEdge α β Δx (-d) + min (ε₀ * β * d) (α * Δx) := by
  have hβd : 0 < β * d := mul_pos hβ hd
  have hr : α / β / (d / Δx) * (β * d) = α * Δx := by field_simp
  unfold epsEdge epsCoast idealEdge
  set r := α / β / (d / Δx)
  rcases le_total 1 r with h1 | h1
  · -- gentle: the ceiling is 1
    have hle := mul_le_mul_of_nonneg_right h1 hβd.le
    have hε := mul_le_mul_of_nonneg_right hε₁ hβd.le
    rw [min_eq_left h1, max_eq_right (by linarith), max_eq_right (by linarith),
      min_eq_left (by linarith)]
    ring
  · have hle := mul_le_mul_of_nonneg_right h1 hβd.le
    rw [min_eq_right h1]
    rcases le_total ε₀ r with h2 | h2
    · -- between `s⋆` and `s⋆/ε₀`
      have hε := mul_le_mul_of_nonneg_right h2 hβd.le
      rw [max_eq_right (by linarith), max_eq_left (by linarith), min_eq_left (by linarith)]
      linarith
    · -- beyond `s⋆/ε₀`: the refund is floored at zero
      have hε := mul_le_mul_of_nonneg_right h2 hβd.le
      rw [max_eq_left (by linarith), max_eq_left (by linarith), min_eq_right (by linarith)]
      ring

/-- **At zero deficit the deployed cost is the ideal edge cost** on every edge below the climb
gate. The deficit `ε₀` and the gate are what E1 adds to the derivation. -/
theorem v2_eq_ideal {αr αa β θ Δx Δh : ℝ} (hα : 0 ≤ αr + αa) (hβ : 0 < β) (hΔx : 0 < Δx)
    (below : Δh < θ * Δx) :
    v2Edge αr αa β β θ 0 Δx Δh = idealEdge (αr + αa) β Δx Δh := by
  rcases lt_or_ge Δh 0 with h | h
  · rw [v2Edge_descent hα hβ le_rfl le_rfl zero_le_one hΔx h,
      v2_descent_eq hβ zero_le_one hΔx (by linarith), neg_neg, zero_mul, zero_mul,
      min_eq_left (mul_nonneg hα hΔx.le), add_zero]
  · unfold v2Edge idealEdge
    rw [ite_eq_left h, ite_eq_left below, max_eq_right (by nlinarith [mul_nonneg hα hΔx.le, mul_nonneg hβ.le h])]
    ring

/-- **The deployed cost never bills less than rolling and gravity.** With `k_s = 1`, every edge
costs at least the floor of `edge_ge_ideal`. On a gated climb it is exactly that floor. -/
theorem floor_le_v2 {αr αa β θ ε₀ Δx Δh : ℝ} (hαr : 0 ≤ αr) (hαa : 0 ≤ αa) (hβ : 0 < β)
    (hε₀ : 0 ≤ ε₀) (hε₁ : ε₀ ≤ 1) (hΔx : 0 < Δx) :
    idealEdge αr β Δx Δh ≤ v2Edge αr αa β β θ ε₀ Δx Δh := by
  have hx := mul_nonneg hαa hΔx.le
  rcases lt_or_ge Δh 0 with h | h
  · rw [v2Edge_descent (by linarith) hβ le_rfl hε₀ hε₁ hΔx h,
      v2_descent_eq hβ hε₁ hΔx (by linarith), neg_neg]
    have hmin : 0 ≤ min (ε₀ * β * -Δh) ((αr + αa) * Δx) :=
      le_min (mul_nonneg (mul_nonneg hε₀ hβ.le) (by linarith))
        (mul_nonneg (by linarith) hΔx.le)
    have hmono : idealEdge αr β Δx Δh ≤ idealEdge (αr + αa) β Δx Δh := by
      unfold idealEdge
      exact max_le_max le_rfl (by linarith)
    linarith
  · unfold v2Edge idealEdge
    rw [ite_eq_left h]
    refine max_le ?_ ?_
    · have := mul_nonneg hαr hΔx.le
      have := mul_nonneg hβ.le h
      split_ifs <;> linarith
    · split_ifs <;> linarith

/-! ### The flat-`ε` family, `eF1`, `eF2`, `eF4` -/

/-- **The route law charged edge by edge**, with one flat `ε` and no clamp. On a steep descent
it is negative. -/
noncomputable def lawEdge (α β ε Δx Δh : ℝ) : ℝ := α * Δx + β * (max Δh 0 - ε * max (-Δh) 0)

/-- **The route law is an edge sum.** Summed along a path, the unclamped edge law is the
route-level law on the path's own totals: `α·x + β·(h₊ − ε·h₋)`. -/
theorem law_sum_eq_route (α β ε : ℝ) (x h : ℕ → ℝ) (n : ℕ) :
    ∑ i ∈ range n, lawEdge α β ε (x (i + 1) - x i) (h (i + 1) - h i)
      = α * (x n - x 0) + β * (ascent n h - ε * ascent n (fun i => -h i)) := by
  have term : ∀ i ∈ range n, lawEdge α β ε (x (i + 1) - x i) (h (i + 1) - h i)
      = α * (x (i + 1) - x i) + β * max (h (i + 1) - h i) 0
        - β * ε * max (-h (i + 1) - -h i) 0 := by
    intro i _
    unfold lawEdge
    rw [show -(h (i + 1) - h i) = -h (i + 1) - -h i by ring]
    ring
  rw [sum_congr rfl term, sum_sub_distrib, sum_add_distrib, ← mul_sum, ← mul_sum, ← mul_sum,
    sum_range_sub]
  simp only [ascent]
  ring

/-- Paper 3's **flat-`ε` edge family**, as `edge_form` in `e73_gridpath.py` computes it. `eF1`
is `gated = false`, `eF2` is `gated = true`, and `eF4` is `eF2` with `c` metres of climb per
metre of road taken off both gravity arms. -/
noncomputable def eFEdge (gated : Bool) (αr αa β θ ε c Δx Δh : ℝ) : ℝ :=
  if 0 ≤ Δh then
    αr * Δx + (if gated = true ∧ θ * Δx ≤ Δh then 0 else αa * Δx) + β * max 0 (Δh - c * Δx)
  else max 0 ((αr + αa) * Δx - ε * β * max 0 (-Δh - c * Δx))

/-- **`eF1` and `eF2` are the route law, clamped at zero edge by edge.** The air part of the
flat bill is dropped on the gated climbs of `eF2`, as in the route form F2. -/
theorem eFEdge_eq_clamped_law {αr αa β ε Δx Δh : ℝ} (gated : Bool) (θ : ℝ) (hαr : 0 ≤ αr)
    (hαa : 0 ≤ αa) (hβ : 0 ≤ β) (hΔx : 0 ≤ Δx) :
    eFEdge gated αr αa β θ ε 0 Δx Δh
      = max 0 (lawEdge (αr + if gated = true ∧ 0 ≤ Δh ∧ θ * Δx ≤ Δh then 0 else αa)
          β ε Δx Δh) := by
  have hr := mul_nonneg hαr hΔx
  have ha := mul_nonneg hαa hΔx
  unfold eFEdge lawEdge
  simp only [zero_mul, sub_zero]
  rcases lt_or_ge Δh 0 with h | h
  · have h' : ¬ (0 ≤ Δh) := not_le.2 h
    rw [ite_eq_right h', ite_eq_right (fun hc => h' hc.2.1), max_eq_right (show (0 : ℝ) ≤ -Δh by linarith),
      max_eq_right (show Δh ≤ 0 from h.le), max_eq_left (show (0 : ℝ) ≤ -Δh by linarith)]
    congr 1
    ring
  · have hb := mul_nonneg hβ h
    rw [ite_eq_left h, max_eq_right h, max_eq_left h, max_eq_right (show -Δh ≤ 0 by linarith)]
    by_cases hg : gated = true ∧ θ * Δx ≤ Δh
    · rw [ite_eq_left hg, ite_eq_left ⟨hg.1, h, hg.2⟩, max_eq_right (by nlinarith)]
      ring
    · rw [ite_eq_right hg, ite_eq_right (fun hc => hg ⟨hc.1, hc.2.2⟩), max_eq_right (by nlinarith)]
      ring

/-- **The clamp is the coasting ceiling.** Flooring a flat-`ε` descent at zero is the same as
refunding `min(ε, s⋆/s)`: the flat `ε` up to the grade `s⋆/ε`, the ceiling of section 5 beyond
it. The floor is the statement that legs cannot return energy. -/
theorem clamp_is_ceiling {α β ε Δx d : ℝ} (hβ : 0 < β) (hΔx : 0 < Δx) (hd : 0 < d) :
    max 0 (α * Δx - ε * β * d) = α * Δx - min ε (α / β / (d / Δx)) * β * d := by
  have hβd : 0 < β * d := mul_pos hβ hd
  have hr : α / β / (d / Δx) * (β * d) = α * Δx := by field_simp
  set r := α / β / (d / Δx)
  rcases le_total ε r with h | h
  · have := mul_le_mul_of_nonneg_right h hβd.le
    rw [min_eq_left h, max_eq_right (by linarith)]
  · have := mul_le_mul_of_nonneg_right h hβd.le
    rw [min_eq_right h, max_eq_left (by linarith)]
    linarith

/-- **What the clamp costs.** A clamped sum is the unclamped sum plus the mass the clamp
refused: `eF# − F#` in paper 3's tables. -/
theorem clamp_mass (a : ℕ → ℝ) (n : ℕ) :
    ∑ i ∈ range n, max 0 (a i) = ∑ i ∈ range n, a i + ∑ i ∈ range n, max 0 (-a i) := by
  rw [← sum_add_distrib]
  refine sum_congr rfl fun i _ => ?_
  rcases le_total 0 (a i) with h | h
  · rw [max_eq_right h, max_eq_left (by linarith)]
    ring
  · rw [max_eq_left h, max_eq_right (by linarith)]
    ring

/-! ### Potential energy, and what a search may assume -/

/-- Taking a multiple of the elevation off every edge changes a path's cost by a constant
that depends only on its two ends, so it changes no shortest path. -/
theorem path_potential (c h : ℕ → ℝ) (γ : ℝ) (n : ℕ) :
    ∑ i ∈ range n, c i
      = ∑ i ∈ range n, (c i - γ * (h (i + 1) - h i)) + γ * (h n - h 0) := by
  rw [sum_sub_distrib, ← mul_sum, sum_range_sub]
  ring

/-- With potential energy taken off, what is left of the unclamped law is the flat bill plus
the wasted share of the descent. -/
theorem lawEdge_reduced (α β ε Δx Δh : ℝ) :
    lawEdge α β ε Δx Δh - β * Δh = α * Δx + (1 - ε) * β * max (-Δh) 0 := by
  unfold lawEdge
  rcases le_total 0 Δh with h | h
  · rw [max_eq_left h, max_eq_right (show -Δh ≤ 0 by linarith)]
    ring
  · rw [max_eq_right h, max_eq_left (show (0 : ℝ) ≤ -Δh by linarith)]
    ring

/-- **The unclamped law needs no clamp to be searched.** For `ε ≤ 1`, potential energy `β·h`
is a feasible potential: every reduced edge cost is at least the flat bill, so non-negative. -/
theorem lawEdge_reduced_ge {α β ε Δx Δh : ℝ} (hβ : 0 ≤ β) (hε : ε ≤ 1) :
    α * Δx ≤ lawEdge α β ε Δx Δh - β * Δh := by
  rw [lawEdge_reduced]
  have : 0 ≤ (1 - ε) * β * max (-Δh) 0 :=
    mul_nonneg (mul_nonneg (by linarith) hβ) (le_max_right _ _)
  linarith

/-- **The same potential serves the deployed cost**, scaled by `k_s` like its gravity arms:
every reduced edge cost is at least the rolling bill. -/
theorem v2_reduced_ge {αr αa β γ θ ε₀ Δx Δh : ℝ} (hαa : 0 ≤ αa) (hγ : 0 ≤ γ) (hε₀ : 0 ≤ ε₀)
    (hΔx : 0 ≤ Δx) :
    αr * Δx ≤ v2Edge αr αa β γ θ ε₀ Δx Δh - γ * Δh := by
  have hx := mul_nonneg hαa hΔx
  unfold v2Edge
  split_ifs with h1 h2
  · linarith
  · linarith
  · have hε := epsEdge_le_one hε₀ ((αr + αa) / β) (-Δh / Δx)
    have hpre := le_max_right 0
      ((αr + αa) * Δx - epsEdge ε₀ ((αr + αa) / β) (-Δh / Δx) * γ * (-Δh))
    have : 0 ≤ (1 - epsEdge ε₀ ((αr + αa) / β) (-Δh / Δx)) * (γ * (-Δh)) :=
      mul_nonneg (by linarith) (mul_nonneg hγ (by linarith))
    linarith

/-- **A lower bound a search may use.** Any path costs at least the rolling bill on its length
plus `k_s·β` times its net climb. -/
theorem v2_path_ge {αr αa β γ θ ε₀ : ℝ} (hαa : 0 ≤ αa) (hγ : 0 ≤ γ) (hε₀ : 0 ≤ ε₀)
    (x h : ℕ → ℝ) (hx : Monotone x) (n : ℕ) :
    αr * (x n - x 0) + γ * (h n - h 0)
      ≤ ∑ i ∈ range n, v2Edge αr αa β γ θ ε₀ (x (i + 1) - x i) (h (i + 1) - h i) := by
  have key := sum_le_sum fun i (_ : i ∈ range n) =>
    v2_reduced_ge (αr := αr) (β := β) (θ := θ) (Δh := h (i + 1) - h i) hαa hγ hε₀
      (sub_nonneg.2 (hx (Nat.le_succ i)))
  rw [sum_sub_distrib, ← mul_sum, ← mul_sum, sum_range_sub, sum_range_sub] at key
  linarith

/-- **Every edge costs at least `min(ε₀·α, α_r)` per metre.** -/
theorem v2_ge_rate {αr αa β γ θ ε₀ Δx Δh : ℝ} (hαr : 0 ≤ αr) (hαa : 0 ≤ αa) (hβ : 0 < β)
    (hγ : 0 ≤ γ) (hγβ : γ ≤ β) (hε₀ : 0 ≤ ε₀) (hε₁ : ε₀ ≤ 1) (hΔx : 0 < Δx) :
    min (ε₀ * (αr + αa)) αr * Δx ≤ v2Edge αr αa β γ θ ε₀ Δx Δh := by
  rcases lt_or_ge Δh 0 with h | h
  · rw [v2Edge_descent (by linarith) hβ hγβ hε₀ hε₁ hΔx h]
    have h1 := v2_descent_ge (α := αr + αa) (by linarith) hβ hγβ hε₀ hε₁ hΔx
      (by linarith : 0 < -Δh)
    have h2 : min (ε₀ * (αr + αa)) αr * Δx ≤ ε₀ * (αr + αa) * Δx :=
      mul_le_mul_of_nonneg_right (min_le_left _ _) hΔx.le
    linarith
  · have hred := v2_reduced_ge (αr := αr) (β := β) (γ := γ) (θ := θ) (Δh := Δh) hαa hγ hε₀
      hΔx.le
    have h2 : min (ε₀ * (αr + αa)) αr * Δx ≤ αr * Δx :=
      mul_le_mul_of_nonneg_right (min_le_right _ _) hΔx.le
    have := mul_nonneg hγ h
    linarith

/-- The same, along a path: the distance-only bound a search may use. -/
theorem v2_path_ge_rate {αr αa β γ θ ε₀ : ℝ} (hαr : 0 ≤ αr) (hαa : 0 ≤ αa) (hβ : 0 < β)
    (hγ : 0 ≤ γ) (hγβ : γ ≤ β) (hε₀ : 0 ≤ ε₀) (hε₁ : ε₀ ≤ 1)
    (x h : ℕ → ℝ) (hx : StrictMono x) (n : ℕ) :
    min (ε₀ * (αr + αa)) αr * (x n - x 0)
      ≤ ∑ i ∈ range n, v2Edge αr αa β γ θ ε₀ (x (i + 1) - x i) (h (i + 1) - h i) := by
  have key := sum_le_sum fun i (_ : i ∈ range n) =>
    v2_ge_rate (θ := θ) (Δh := h (i + 1) - h i) hαr hαa hβ hγ hγβ hε₀ hε₁
      (sub_pos.2 (hx (Nat.lt_succ_self i)))
  rw [← mul_sum, sum_range_sub] at key
  exact key

/-- **The rolling bill alone is not a lower bound.** A descent at exactly the grade `s⋆`
costs `ε₀·α` per metre, so whenever `ε₀·α < α_r` there is an edge cheaper than rolling
resistance over its own length. Paper 3's planned heuristic `α_r·d` is not admissible on the
deployed costs; `v2_path_ge` and `v2_path_ge_rate` are the bounds that are. -/
theorem rolling_bound_fails {αr αa β θ ε₀ Δx : ℝ} (hβ : 0 < β) (hα : 0 < αr + αa)
    (hε₀ : 0 ≤ ε₀) (hε₁ : ε₀ ≤ 1) (hΔx : 0 < Δx) (h : ε₀ * (αr + αa) < αr) :
    v2Edge αr αa β β θ ε₀ Δx (-((αr + αa) / β * Δx)) < αr * Δx := by
  have hd : 0 < (αr + αa) / β * Δx := mul_pos (div_pos hα hβ) hΔx
  have hβd : β * ((αr + αa) / β * Δx) = (αr + αa) * Δx := by field_simp
  set d := (αr + αa) / β * Δx
  have hε := mul_le_mul_of_nonneg_right hε₁ (mul_pos hβ hd).le
  rw [v2Edge_descent hα.le hβ le_rfl hε₀ hε₁ hΔx (by linarith), neg_neg,
    v2_descent_eq hβ hε₁ hΔx hd]
  unfold idealEdge
  rw [show (αr + αa) * Δx + β * -d = 0 by linarith, max_self, min_eq_left (by linarith),
    zero_add]
  have e : ε₀ * β * d = ε₀ * (αr + αa) * Δx := by rw [mul_assoc, hβd, mul_assoc]
  rw [e]
  exact mul_lt_mul_of_pos_right h hΔx

/-! ### The valley toll -/

/-- **What a valley can save.** A descent `a → b` is coasted and the climb `b → c` follows.
The legs pay for the climb less the kinetic head spent on it, and that head is at most the
drop of the descent and at most the buffer `κe − κc`: the head at the fastest the rider is at
the bottom, less the head at the slowest the rider is at the top. These are two of the three
arms of paper 3's valley toll `min(D, H, buffer)`. The third, the rise `H`, is the statement
that the legs' energy on the climb is not negative. -/
theorem valley_toll {m g Crr k : ℝ} (hm : 0 < m) (hg : 0 < g) (hCrr : 0 ≤ Crr)
    {v X h E Wa Wb : ℝ → ℝ} {a b c : ℝ} (hab : a ≤ b) (hbc : b ≤ c)
    (ride : Obeys m g Crr k v X h E Wa Wb a c)
    (coast : E b = E a)
    (hX : X a ≤ X b) (hWa : Wa a ≤ Wa b)
    (hWb₁ : Wb a ≤ Wb b) (hWb₂ : Wb b ≤ Wb c)
    {κe κc : ℝ}
    (bottom : v b ^ 2 / (2 * g) ≤ κe)
    (top : κc ≤ v c ^ 2 / (2 * g))
    (exit : v a ^ 2 / (2 * g) ≤ v c ^ 2 / (2 * g)) :
    m * g * ((h c - h b) - min (h a - h b) (κe - κc))
        + Crr * m * g * (X c - X b) + (Wa c - Wa b)
      ≤ k * (E c - E b) := by
  have hmg : 0 < m * g := mul_pos hm hg
  have down := (ride.mono le_rfl hbc).edge hab hm.ne' hg.ne'
  have up := (ride.mono hab le_rfl).edge hbc hm.ne' hg.ne'
  unfold totalHead at down up
  rw [coast, sub_self, mul_zero] at down
  -- kinetic head gained on the coasted descent is at most the drop
  have hroll : 0 ≤ Crr * m * g * (X b - X a) :=
    mul_nonneg (mul_nonneg (mul_nonneg hCrr hm.le) hg.le) (by linarith)
  have gain : m * g * (v b ^ 2 / (2 * g) - v a ^ 2 / (2 * g)) ≤ m * g * (h a - h b) := by
    nlinarith
  have gain' : v b ^ 2 / (2 * g) - v a ^ 2 / (2 * g) ≤ h a - h b :=
    le_of_mul_le_mul_left gain hmg
  -- so the head spent on the climb is at most the toll
  have spent : v b ^ 2 / (2 * g) - v c ^ 2 / (2 * g) ≤ min (h a - h b) (κe - κc) :=
    le_min (by linarith) (by linarith)
  have := mul_le_mul_of_nonneg_left spent hmg.le
  nlinarith

end RouteEnergy
