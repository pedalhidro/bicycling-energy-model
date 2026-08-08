<!-- Claim annotations for this article live in paper3-edge-cost.meta.ttl, keyed to the
     invisible @c-<id> anchors in the text below. See that file for the rationale. -->

<!--
  paper3-edge-cost.md — SCAFFOLD (not a draft). Third paper of the series.

  Working question: how do you discretize the ride-level closed form of paper 1
  into a per-edge cost usable inside a shortest-path search (Dijkstra and
  variants) for minimum-energy routing — and what breaks when you do?

  Status: outline + evidence inventory + registered gaps. Every section carries
  either the existing evidence (journal entry / harness) or a TODO naming the
  experiment that would fill it. Numbers here are placeholders quoted from the
  lab journal — nothing is gated for this paper yet; a paper-2 gate battery is
  itself a TODO.

  Relation to paper 1 (paper1-closed-form.md): inherits the frozen constants protocol
  (Crr 0.008, CdA 0.40, ρ 1.13, k_eff 0.98, wind 0, G 9.7864), the behavioural
  constants (ε₀ = 0.13, c ≈ 3 m/km, climb threshold 2%) and the four-form
  family. Paper 1 validates the law per ride; this paper asks whether the same
  physics survives being chopped into 30 m edges and summed by a router.
-->

# From a Ride-Level Energy Law to an Edge Cost: Discretizing the Closed Form for Minimum-Energy Bicycle Routing

**Status: scaffold.** Sections below are the intended IMRAD skeleton; `TODO`
marks work not yet done, `[E##]` cites the lab journal entry (and harness)
holding the evidence that already exists.

## Abstract (sketch)

Minimum-energy bicycle routing needs a per-edge cost, but the energy law of
the companion paper is a *ride-level* statement: its elevation treatment
(deadband smoothing) is sequential over the whole profile, its ε is a
route-aggregate, and its aero split needs a climbing share. We propose and
validate an edge realisation — grade-local recovery
ε(s) = clamp₀₁(min(1, (α/β)/s) − ε₀), aero gated off climb edges, the scalar
noise correction in place of the (non-local) deadband — that is additive,
non-negative, direction-asymmetric, and cheap enough for Dijkstra over a
metropolitan DEM grid. TODO: headline validation numbers (edge-sum vs measured
∫P·dt over the paper-1 corpora; parity/attribution claims). We document the
pitfalls: every behavioural constant is a function of the elevation-sampling
scale; the deadband cannot be pushed into an edge weight; naive clamping
double-counts on steep descents; and DEM noise enters *per edge*, not per
ride. The realisation is deployed in an open-source energy-field router
(Simujaules); all code and gates are published.


<!-- The two claims A3 must eventually carry. Neither has a value yet. -->


## 1. Introduction

- **1.1 The routing problem.** Minimum-energy (not minimum-distance/time)
  routing over an 8-connected DEM grid; asymmetric costs (A→B ≠ B→A) make the
  field a directed one; why energy fields (isochrone-style reachability in kJ)
  rather than single routes. Existing tools route by distance/time/“hilliness”
  heuristics; TODO literature pass (energy-aware routing, e-bike routing,
  Sobek/Brouter-style cost functions — extend `research/notes/literature-context.md`
  and `simujaules-literature-context.md`).
- **1.2 What the ride-level law provides.** Recap of paper 1's form 3/4 and
  the coasting-deficit ε; why it cannot be used as-is per edge (three
  non-local ingredients: deadband, route-aggregate ε, climbing share).
  **Update [E63–E69]: the deadband's non-locality is now decomposed** —
  roughly seven-eighths of its explanatory work is a kinetic-energy valley
  toll min(D, H, h_KE) computable from the profile's descent→climb valleys
  (buffer h_KE = (v_e² − v_c²)/2g from the branch fixed points), the rest a
  measurable noise floor plus a fitted residue shown to be corpus-absorbing
  (non-stationary within riders, non-transferable across them). The
  physically load-bearing part of the filter is therefore *graph-computable*:
  valleys are known at graph-build time. The dynamical scale that a strictly
  edge-local cost drops is the KE boundary layer — recovery length
  L_rec = m·v_f²/(C_rr·m·g + 3·½ρC_dA·v_f²) ≈ 90 m at the shared constants,
  i.e. ~3 edges at 30 m pitch — which is exactly why kinetic continuity
  between edges cannot be recovered by re-weighting single edges and needs a
  per-valley (two-edge-window) term instead.
- **1.3 The proposed edge realisation ("v2Edge").** [E17–E18,
  `regime_compare.py::r1d_v2_edge`] For an edge of length Δx and grade s:
  - climb edge (s ≥ 2%): E = α_r·Δx + β·k_s·Δh (aero gated off);
  - flat edge: E = (α_r + α_a)·Δx;
  - descent edge: E = α_r·Δx + β·k_s·(1 − ε(s))·|Δh| with grade-local
    ε(s) = clamp₀₁(min(1, (α/β)/s) − ε₀), floored at 0;
  - k_s scales β only (the scalar stand-in for the deadband).
  State the required cost-function properties for the search to be exact:
  additivity, non-negativity (ε ≤ 1 guarantees it), locality, and why
  direction-asymmetry is fine for Dijkstra but rules out bidirectional/A*
  without an admissible heuristic (TODO: derive the trivial lower-bound
  heuristic α_r·d and check admissibility).
- **1.4 Hypotheses.** TODO — pre-register before running anything new.
  Candidates: (H1) edge-sum over a measured ride's own path reproduces the
  ride-level form 3 within the paper-1 CI at the calibration scale; (H2) the
  edge cost's error grows monotonically as DEM resolution departs from the
  30 m calibration scale unless constants are re-fitted or the raster
  pre-smoothed [E19–E21 partial]; (H3) minimum-energy routes differ
  materially from minimum-distance ones only above a hilliness threshold
  (detour experiments, [E26 `e26_detour.py`]); (H4) the two elevation repairs
  do not stack at edge grain either — pre-smoothing the raster and re-weighting
  portal edges remove the same artifact, so applying both over-corrects, as
  measured at route grain in [E41] (§3.2 below). H4's edge-grain twist: a bridge
  may span one or two cells, so its vertical curve is sub-resolution and the
  straight-deck over-correction could be *larger* here than the −2.43 m
  [−3.26, −1.68] measured per touched ride at route grain.
  **New candidates from the E63–E69 programme:** (H5) a *valley patch* — the
  KE toll applied at graph-build time to each descent→climb node, replacing
  k_s's scalar stand-in for the deadband — reproduces the ride-level filtered
  form at edge grain without any non-local pass; the route-grain evidence
  (toll alone carries ~half the filter's benefit, toll + measured floor
  matches it, the fitted remainder is absorbing and NOT worth reproducing per
  edge) sets the expected ceiling before any run. (H6) the interruption
  component of ε₀ becomes *computable* here: the router knows junction
  density and node degree — precisely the collection-truncation information
  the ride-level calibration never had — so a per-node truncation term
  should explain part of the urban/highway ε split [E60–E61] from graph
  structure alone. (H7) the cost bundle's constants follow the measured-pin
  doctrine [E68–E69]: noise floors measured per chain (paper 2's rates),
  buffer from rider physics, ε the single fitted scalar — any constant
  *fitted* at edge grain is presumed absorbing until it survives a
  LORO-style transfer gate.

## 2. Methods

- **2.1 The engines.** Python reference `r1d_v2_edge` (in
  `src/harness/regime_compare.py`); the deployed mirrors (applet +
  Simujaules `energy-worker.js`, JS/Rust bit-parity). The mirror-set rule:
  any change lands in all copies.
- **2.2 Grids and DEMs.** FABDEM / DEM-SP; 8-connected grid, diagonal edge
  lengths; per-edge grade from cell elevations. Elevation-noise model per
  edge (paper 1 §2.4's per-sample jitter — here it hits *every edge
  independently*, no cancellation over a profile). [E6, E19]
- **2.3 Validation corpora and protocol.** Two populations under paper 1's
  A-chain per-ride physics [E52/E57]: the *IGC population* (D3–D5 rides whose
  track lies inside the IGC-SP 2010 survey) carries every arm; the *FABDEM
  population* (D3–D6 — FABDEM is global, so the European corpus joins) carries
  the FABDEM arms. Score edge-sum vs measured ∫P·dt AND vs the route-level
  estimate (paper 1's published F4 on the same chain's polyline profile) with
  the same median/CI/gate conventions (mulberry32, seeds 42/43, B = 10⁴).
  **Map-matching** (the E73 quantizer, `src/harness/e73_gridpath.py`): each
  ride's GPS line, resampled to a 5 m arc grid, is followed by a deterministic
  greedy walker over the terrain raster's own lattice using the deployed
  move sets (`buildMoves` mirrored: classic 8 first, Farey/mediant ladder at
  levels {16:1, 32:2, 64:3, 128:4}; long moves sub-sampled at
  2·max(|Δr|,|Δc|) points). Each step picks the move whose endpoint best
  chases the polyline one move-length ahead, verified by exact projection;
  acceptance requires chainage advance ≥ 5% of the move length and endpoint
  lateral ≤ one cell diagonal; infeasible steps (switchbacks tighter than the
  lattice) jump one pitch and are counted — a ride is dropped from an arm
  when jumps exceed 0.5% of its nodes. n = 1 is the un-quantized polyline at
  lattice pitch (the [E72] profile — the parity anchor). Registered sanity
  gates: the synthetic azimuth fan must reproduce each move set's analytic
  metrication factor (√2 at n = 4, 1.082 at n = 8, → 1 by n = 128); per-ride
  length-inflation medians monotone non-increasing in n; lateral p95 bounded
  by construction; h₊(path)/h₊(n = 1) within [0.90, 1.15]; per-ride parity of
  the n = 1 arms against [E41]'s DEM columns and [E72]'s own-profile columns.
- **2.4 Scale experiments.** The existing chain: IGC 5 m ground truth
  [E19 `igc_resolution_test.py`], σ-smoothing calibration
  [E20 `goal_calibration.py`, `goal_smooth_rasters.py`], the
  resolution × smoothing × threshold trio [E21 `scale_trio.py`]. The
  ROUTE-grain prescription (DEM source → σ → constants) is paper 2's
  deliverable (paper2-dem-deployment.md, a letter this paper cites); this
  paper keeps only the EDGE-grain consequences (per-edge grade error,
  cost-surface stability under σ).
  **DONE — cite, do not re-derive** [E41]: paper 2's Table 2 IS that
  prescription (source × polyline step × σ → the c to use → the measured
  accuracy band), with σ applied to the *profile* rather than the raster —
  validated against E20's raster-space smoothing to −1.1% of h₊ (p90 6.9%).
  Its measured per-source noise rates are the numbers to inherit: barometric
  3.10 m/km [3.01, 3.18], IGC-SP 5 m 4.95 [4.89, 5.00], FABDEM sampled at
  30 m 7.52 [7.12, 7.76], FABDEM oversampled at 5 m 10.14 [9.86, 10.59].
  Two route-grain results this paper must NOT assume carry over unchanged:
  (i) the penalty is terrain-dependent (bias shift +0.7 pp on gentle terrain
  vs +20.1 pp on mountain brevets), so an edge-grain scale rule fitted on
  urban grids will not hold on escarpments; (ii) oversampling a coarse DEM
  is itself a cost (FABDEM at 5 m steps doubles h₊ vs 30 m steps and costs
  0.7 pp accuracy / 2.3 pp bias) — a router on an 8-connected grid samples
  at the grid pitch, so this is a *grid-design* parameter here, not a free
  choice.
- **2.5 Sanity gates.** Synthetic gates already exist (`SANITY=1
  regime_compare.py`; scale/goal per-gate blocks, two documented-benign
  failures). TODO: a paper-2 `bootstrap_ci`-style battery re-deriving every
  number this paper will publish.

## 3. Results (first tranche measured — Entry 72; routing results still planned)

- **3.1 Edge-sum vs ride-level law vs measurement — MEASURED** [E72
  `e72_edgegrain.py`, 2,039 rides of D3–D6 at the paper-1 A-chain physics,
  each ride's own recorded profile so no DEM error mixes in]:

  | arm (grid pitch) | med \|Δ%\| [95% CI] | signed [95% CI] |
  |---|--:|--:|
  | v2Edge @ 5 m | 4.62 [4.43, 4.93] | +3.39 [+3.08, +3.96] |
  | v2Edge @ 10 m | 4.13 [3.92, 4.36] | +2.99 [+2.61, +3.36] |
  | **v2Edge @ 30 m (deployed scale)** | **3.75 [3.53, 3.97]** | +1.33 [+1.09, +1.61] |
  | v2Edge @ 60 m | 3.96 [3.73, 4.23] | −0.05 [−0.27, +0.16] |
  | v2Edge @ 90 m | 4.15 [3.91, 4.37] | −0.93 [−1.11, −0.70] |
  | route-level twin (F2 · ε_geom @ 5 m) | 4.31 [4.13, 4.54] | +1.25 [+0.96, +1.66] |
  | valley patch @ 30 m (§3.3) | 3.29 [3.12, 3.50] | −0.08 [−0.34, +0.08] |
  | **F4 as published** (paper 1: flat ε = 0.409 · c = 1.10) | **2.72 [2.58, 2.86]** | −0.35 [−0.51, −0.11] |
  | F4 all-measured (ε_geom · article-2 c = 3.01) | 5.66 [5.42, 5.80] | −3.80 [−4.11, −3.50] |

  **Fidelity (H1):** at 5 m the edge-sum sits a median **+1.83 pp
  (med |gap| 1.8 pp)**<!--@c-a3.discretisation.fidelity--> above its own
  route-level integral — the grade-local ε and the per-edge clamp floor,
  which only bind on descents, are the entire discretisation gap, and it is
  bias-shaped (systematically above), not noise. **Scale (H2):** the error
  is U-shaped in grid pitch with its minimum exactly at the 30 m
  calibration scale ([fig-p3-scale](figs/fig-p3-scale.svg)) — finer grids
  over-charge because the edge cost carries *no deadband* to eat jitter
  (+3.4% bias at 5 m), coarser grids under-resolve (−0.9% at 90 m); the
  bias crosses zero near 60 m, which is *aliasing cancelling noise*, not
  accuracy — the med|Δ%| there is already worse than at 30 m.
  **The valley patch (H5, first look — not the pre-registered arm):** at the
  deployed scale, replacing the scalar k_s stand-in with the Entry-63 KE
  valley toll (per descent→climb node, floor 0, never-brake cap; median
  toll 20.3 m/ride at 30 m) takes the deployed cost from 3.75 · +1.33 to
  **3.29 · −0.08** — closer on 1,131 of 2,038 rides (sign p < 10⁻⁴). The
  toll is a graph-node term: additive over the search, computable at
  build time, no non-local pass.
  **The comparator rows (Danilo's addition) reorder the hierarchy.** Paper
  1's published F4 — one flat ε and its jointly-fitted c — is the strongest
  route-level number in the table, beating the deployed edge cost at its own
  calibration scale and the valley patch: F4-pub (2.72) > patch (3.29) >
  v2Edge@30 (3.75) > twin (4.31). The flat-vs-dynamic lesson (paper 1's E51)
  lands at edge grain: the grade-local ε machinery loses to one flat
  constant. Two caveats travel with that reading. *Locality:* published F4
  clamps k = max(0, 1 − c·x/h₊) at ROUTE level — not strictly an edge
  weight; the per-edge realisation is the unclamped linearisation (subtract
  β·c per metre from the gravity charge), valid where h₊ > c·x and
  pathological on near-flat routes — so F4's row is a route-level benchmark,
  not a drop-in edge cost. *Pairing:* the all-measured variant (ε_geom with
  article 2's measured c = 3.01) over-corrects to −3.8% bias — each constant
  individually principled, never calibrated jointly; the (α, ε) bundle rule
  extends to (ε, c), and "measured" does not exempt a constant from
  travelling with its pair.
- **3.2 The discrete-routing ladder — MEASURED** [E73 `e73_gridpath.py`;
  gate section 3l; protocol §2.3]. Four axes varied one at a time on the
  matched ridden path, per ride against measured ∫P·dt and the route-level
  estimate. The model axis is the deployable **eF family** (flat ε per
  paper 1's recommendation; per-edge max(0,·) clamp), traced to paper 1:
  F1 → eF1 (aero ungated) · F2 → eF2 · F3 → eF2 on a σ-treated map ·
  F4 → eF4 (eF2 + per-edge deduction of c metres/km on both gravity arms, at
  the chain's MEASURED c(τ=2) pin) · F5 → out of scope. With identical
  constants, eF# − F# is exactly the clamped-edge mass. The deployed
  grade-local-ε v2Edge is the status-quo reference. Two populations,
  all-arms-complete: IGC (D3–D5 in-survey, n = 1,034) and FABDEM (D3–D6,
  n = 1,844).

  **(a) Directions (n = 1 polyline → 4…128).** eF2 med|Δ%| [95% CI] · signed:

  | n | IGC 5 m σ10 | signed | α·Δx pp | FABDEM 30 m | signed | α·Δx pp |
  |--:|---|---|--:|---|---|--:|
  | 1 | 7.71 [7.21, 8.37] | +7.68 | 0.0 | 15.82 [15.35, 16.21] | +15.80 | 0.0 |
  | 4 | 34.12 [33.68, 34.68] | +34.12 | 23.7 | 114.84 [113.25, 117.65] | +114.84 | 20.6 |
  | 8 | 12.71<!--@c-a3.dirs.ladder--> [12.10, 13.07] | +12.70 | 4.7 | 48.23 [47.09, 49.30] | +48.21 | 3.8 |
  | 16 | 8.76 [8.20, 9.48] | +8.75 | 0.9 | 34.32 [33.66, 35.23] | +34.29 | 0.0 |
  | 128 | 7.52 [6.89, 8.24] | +7.45 | −0.3 | 27.16 [26.32, 27.87] | +27.10 | −1.4 |

  The ladder is **chain-shaped**. On the smoothed chain the n = 4/8 penalty
  is essentially all path-length inflation (median len_ratio
  1.0543<!--@c-a3.quantisation.length--> at n = 8, 1.2737 at n = 4 — the α·Δx
  column absorbs nearly the whole penalty; H2's oscillation mechanism is
  refuted *there*). On raw FABDEM the same rungs carry almost no length
  share: the lattice path reads ×1.417 the polyline's h₊ at n = 8 (×2.38 at
  n = 4) — per-pixel noise read by a zigzag path. Which discretisation error
  dominates is a property of the terrain source. n = 8 → 16 recovers 76% of
  the n = 8 → 128 gap.

  The full family × n cross (med|Δ%| (signed); CIs for the quoted cells in
  gate 3l; eF2\* = eF2 on the σ-treated map; eF4L = the LORO pin):

  | n | eF1 | eF2 | eF2\*σ10 | eF2\*σ30 | eF4L |
  |--:|---|---|---|---|---|
  | *IGC-SP 5 m:* | | | | | |
  | 1 | 17.40 (+17.37) | 11.36 (+11.31) | 7.71 (+7.68) | 4.06 (+3.76) | 7.11 (+7.05) |
  | 8 | 48.32 (+48.32) | 35.66 (+35.66) | 12.71 (+12.70) | 9.21 (+9.16) | 30.55 (+30.54) |
  | 16 | 22.94 (+22.90) | 15.93 (+15.88) | 8.76 (+8.75) | 5.11 (+4.94) | 11.59 (+11.56) |
  | 128 | 17.87 (+17.80) | 11.59 (+11.57) | 7.52 (+7.45) | 4.06 (+3.75) | 7.35 (+7.29) |
  | *FABDEM 30 m:* | | | | | |
  | 1 | 25.97 (+25.96) | 15.82 (+15.80) | — | 5.39 (+5.12) | 9.58 (+9.47) |
  | 8 | 59.08 (+59.08) | 48.23 (+48.21) | — | 11.49 (+11.40) | 41.08 (+41.06) |
  | 16 | 46.22 (+46.22) | 34.32 (+34.29) | — | 6.46 (+6.29) | 26.90 (+26.89) |
  | 128 | 39.25 (+39.23) | 27.16 (+27.10) | — | 4.79 (+4.16) | 19.94 (+19.87) |

  Read column-wise: map treatment (eF2\*) is worth more than any cost-function
  change at every n; the pin (eF4L) is the best *untreated* cost at every n
  except the 4–8 metrication corner; and the treated chains make the pin
  itself transferable — the per-rider c spread collapses from 6.3–11.5 m/km
  (raw FABDEM) to 3.50–3.68 after σ30, which is why the LORO pin costs
  nothing there.

  **(b) Models and map treatment.** At the base configs, med|Δ%| [95% CI]
  (signed):

  | model | igc5s10 · n = 8 | fab30 · n = 8 |
  |---|---|---|
  | v2Edge (deployed) | 9.60 [9.1, 10.8] (+9.59) | 53.01 [51.8, 54.4] (+53.01) |
  | eF1 | 17.36 (+17.35) | 59.08 (+59.08) |
  | eF2 | 12.71 [12.1, 13.1] (+12.70) | 48.23 [47.0, 49.4] (+48.21) |
  | **eF4L (LORO pin)** | 9.75 [9.3, 10.3] (+9.73) | 41.08<!--@c-a3.edge.pin--> [39.7, 42.3] (+41.06) |
  | eF4 (pooled pin, sensitivity) | 9.71 [9.3, 10.2] (+9.70) | 41.62 [40.3, 42.7] (+41.61) |
  | F3 (route algebra) | 5.24 [5.0, 5.6] (+4.78) | 7.01 [6.7, 7.3] (+6.51) |

  The quoted eF4 arm is **out-of-sample by construction**: each ride's pin is
  the median c of the OTHER riders of its region (leave-one-rider-out — the
  pooled-pin row, which shares geometry with the scored rides, is kept only
  as sensitivity; the two differ by ≤ 0.5 pp everywhere). eF4L beats eF2 on
  **all six** DEM chains — the per-edge deduction at the measured pin earns
  its term and is the best deployable cost on FABDEM by 6–11 pp. An ε-side
  robustness slice (the calibration split's test half only) preserves every
  ordering (IGC: eF4L 10.25 < v2 11.10 < eF2 12.91; FAB: eF4L 39.69 < eF2
  47.39 < v2 51.97). The flat-vs-geometric ε contest is chain-dependent at edge grain:
  grade-local wins on the smoothed chain, flat wins on raw FABDEM. In the
  joint per-ride pairing the route forms win almost every ride (eF closer on
  14–375 of 1,034; clamp mass ~3.4 pp at σ10, ~21 pp on raw FABDEM). And the
  deadband keeps a unique share at edge grain: F3 on the RAW chain,
  5.67<!--@c-a3.deadband.residual--> med|Δ%|, beats eF2 on the σ30-treated
  map (9.21) — 7.01 vs 11.49 on FABDEM — so map pre-treatment is
  load-bearing (35.7 → 9.2 on raw igc5) but does not substitute for the
  filter; the ~3.5–4.5 pp residual is [E63–E67]'s unique share at edge
  grain. Measured c pins (m/km, τ = 2): own 3.04 BR / 1.26 EU · igc5 4.89 ·
  σ10 3.66 · σ30 2.56 · igc30 3.75 · fab30 7.58 BR / 5.73 EU · fab30+σ30
  3.57 BR / 2.96 EU (worst disagreement with [E71]'s rates 0.14 m/km).

  **(c) Portals (axis 4).** The straight deck on the base path helps
  860<!--@c-a3.portals.edge-->/883 span-touched rides (sign p < 10⁻⁴), eF2
  11.81 → 11.05, F3 5.22 → 5.15 at σ10 — and, refuting the registered H4
  carry-over, it STILL helps on the σ30-treated chain (802/880 closer, eF2
  8.95 → 8.51): the route-grain "correct or smooth, but not both" does not
  hold at edge grain, where scoring is against measured energy rather than
  in-span barometric ascent. Figures: `figs/fig-p3-dirs.svg`,
  `figs/fig-p3-chain.svg`.

  **(d) The deployable default.** The measured cross fixes the
  recommendation: **eF2 on a σ30-treated map at n = 16** — med|Δ%|
  5.11<!--@c-a3.default--> (+4.94) on the local 5 m survey and 6.46 (+6.29)
  on FABDEM — with **n = 8 as the fast choice** (9.21 / 11.49; the deployed
  engine's own cost table puts n = 16 at 1.5–2.4× the n = 8 runtime) and a
  marginality note: beyond n = 32 the accuracy gain is at most ~0.6 pp
  (0.30 IGC, 0.60 FABDEM over the whole 32 → 128 span) while runtime grows
  ≥ 2× per rung. This default needs no site
  measurement at all — the treatment is a fixed filter and eF2's constants
  are paper 1's.

  **Registered carry-over from [E41] — the repairs do not stack.** At route
  grain, σ-smoothing and the bridge/tunnel (portal) deck correction address
  the SAME artifact: after σ = 30 m the profile's in-span ascent already
  matches the barometer (+0.05 m [−0.29, +0.28]), and applying the deck as
  well subtracts twice and makes energy significantly worse (400/935 rides
  closer, p < 10⁻⁴). Both levers exist at edge grain too — the raster can be
  pre-smoothed AND portal edges re-weighted — so the same double-subtraction
  is available and must be tested, not assumed away. Related: the straight
  deck is a known-sign OVER-correction, because a road bridge carries a
  vertical curve the rider climbs and a chord erases it — measured against
  the ride's own barometer, −2.43 m [−3.26, −1.68] on bridges vs −0.29
  [−0.40, −0.20] on tunnels. At edge grain a bridge may span only one or two
  cells, so the crown is sub-resolution and the error could be larger, not
  smaller. TODO: an H4 pre-registering both.
- **3.3 Route studies.** Detour/portal experiments [E26]; minimum-energy vs
  minimum-distance routes on real Pedal Hidrográfico territory; energy-field
  maps (Simujaules). TODO: quantify H3.
- **3.4 Pitfall inventory (each with a demonstration).**
  - the dead `max(0,·)` clamp (deployed quirk — document, and what fixing it
    changes) [E18];
  - aero-gate discontinuity at the 2% threshold (cost jumps as an edge
    crosses the threshold; effect on route stability);
  - non-negativity vs steep-descent recovery (why ε ≤ 1 keeps Dijkstra
    honest; what a negative-cost variant would require — Johnson-style
    reweighting or a potential function γ·h, TODO: show mgh/k_eff *is* such a
    potential and what remains after subtracting it). Note the deliberate
    asymmetry with paper 1: the *ride-level* ε_d is published unclamped
    (its floor never binds on ride means — paper-1 Appendix A / journal
    Entry 32), but the *edge-level* ε(s) keeps its floor, because single
    30 m edges beyond the floor grade (≈ 15%) are common even where ride
    means are not — the floor is edge-scale model content, not dead code;
  - per-edge noise (no profile-level cancellation; expected inflation as a
    function of edge length — connect to c);
  - asymmetry and turn costs (out of scope for the physics, but state what
    the router must not assume);
  - momentum non-locality (paper-1 journal Entry 37): kinetic energy worth
    h_KE = v²/2g ≈ 2–6 m of climb carries across edges, and no per-edge cost
    can transport it — closely-spaced rollers (within the dissipation length
    λ = m/(ρ·C_dA) ≈ 200 m) are over-charged by construction. h_KE and λ
    bound the error's scale and the raster pre-smoothing that would absorb
    it; the deadband τ ≈ η·v_f²/2g reading makes the filter speed-dependent,
    which a deployment must either accept as calibrated-at-one-speed or
    parameterise;
  - the grade-resolved deficit (paper-1 journal Entry 34): pedalling occupancy
    fades monotonically with cell grade for all riders while intensity is
    rider-level — a per-EDGE ε₀(s) = ε₀·g(s) is therefore physically licensed
    at exactly this paper's grain, where paper 1's ride-level test could not
    profit from it. Candidate refinement of the edge ε(s) beyond the constant
    deficit; needs the paper-1 held-out discipline at edge grain.

## 4. Discussion (planned)

- What transfers from paper 1 unchanged (the physics split, the frozen
  constants, ε₀'s recurrence) vs what is genuinely new risk (scale coupling,
  locality restrictions). The refined ε₀(Δx) idea (paper 1 §4.4) is this
  paper's natural contribution if the scale experiments support a functional
  form. Limitations: one metropolitan region; grid model excludes surface
  type per edge (TODO: OSM surface tags as a C_rr field — privacy rule:
  Overpass queries must never derive from ride endpoints).

## 5. Conclusions (placeholder)

TODO after 3.1.

## Appendix (planned)

- A. Derivation: from the paper-1 integral formalism to the edge sum; the
  exact discretization error terms (what vanishes as Δx → 0, what does not —
  the deadband term does not).
- B. Admissible heuristic for A* (if 1.3's TODO pans out).
- C. Bit-parity protocol between JS and Rust engines.
