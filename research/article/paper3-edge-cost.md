<!-- Claim annotations for this article live in paper3-edge-cost.meta.ttl, keyed to the
     invisible @c-<id> anchors in the text below. See that file for the rationale. -->

<!--
  paper3-edge-cost.md — PARTIAL DRAFT (refactored from the scaffold 2026-08-24).
  Third paper of the series.

  Working question: how do you discretize the ride-level closed form of paper 1
  into a per-edge cost usable inside a shortest-path search (Dijkstra and
  variants) for minimum-energy routing — and what breaks when you do?

  Status: §3.1 (edge-grain fidelity and scale, Entry 72) and §3.2 (the
  discrete-routing ladder, Entries 73–74) are MEASURED and gated
  (bootstrap_ci.py sections 3k and 3l); §3.3 (route divergence), the
  literature pass, the Discussion and the Appendix are PLANNED and marked so
  in place. "Planned:" paragraphs name the experiment that would fill them.

  Sources of truth: research/journal/MODEL_COMPARISON_JOURNAL.md Entries 72–74
  (+ the E63–E69 decomposition), src/harness/e72_edgegrain.py and
  src/harness/e73_gridpath.py (the instruments), src/harness/bootstrap_ci.py
  (gates 3k/3l). Style inherits paper 1: display equations tagged (E1)…,
  journal citations as (lab journal, Entry N), accuracy AND signed bias with
  95% CIs.

  Relation to the series: inherits paper 1's physics split, frozen-constants
  protocol and form family F1–F4; runs the deployed behavioural bundle
  (ε₀ = 0.13, τ = 2 m chain conventions, 2% climb gate) where the deployed
  cost is scored. Paper 1 validates the law per ride; paper 2 prescribes the
  elevation chain at route grain; this paper asks whether the same physics
  survives being chopped into 30 m edges and summed by a router.
-->

# From a Ride-Level Energy Law to an Edge Cost: Discretizing the Closed Form for Minimum-Energy Bicycle Routing

**Danilo Lessa Bernardineli** — Dynamical Systems Group; Pedal Hidrográfico, São Paulo

**Status: partial draft.** The results of [§3.1](#3.1)–[§3.2](#3.2) are measured and gate-checked; paragraphs marked *Planned* name work not yet done.

## Abstract

Minimum-energy bicycle routing needs a per-edge cost, but the energy law of the companion papers is a *ride-level* statement: its elevation treatment (the deadband filter) is sequential over the whole profile, its recovery factor is a route aggregate, and its aero split needs a climbing share. We evaluate the edge realisation the *Simujaules* router deploys — grade-local recovery, aero gated off climb edges, a scalar climb-term correction in place of the non-local filter — against the measured energy of 2,039 power-metered rides, on each ride's own profile and on matched lattice paths over two terrain rasters. Three results are measured. **Fidelity:** at 5 m pitch the edge sum sits a median +1.83 pp above its own route-level integral — the grade-local recovery and the per-edge clamp floor are the entire discretisation gap. **Scale:** the error is U-shaped in grid pitch with its minimum exactly at the deployed 30 m, and a kinetic-energy valley toll computable at graph-build time takes the deployed cost from 3.75% · +1.33 to 3.29% · −0.08. **The routing ladder:** direction count, terrain lattice, map smoothing and bridge/tunnel repairs are separated on matched ridden paths — map treatment is worth more than any cost-function change, a per-edge noise deduction (a distinct cost family) at a measured, leave-one-rider-out pin is the best untreated-chain cost, and the route-grain rule "correct portals or smooth, but not both" does *not* carry to edge grain. The measured cross fixes a deployable default needing no engine change: the grade-local cost on a σ = 30 m-treated map at 16 directions with portals on. How often minimum-energy routes actually diverge from minimum-distance ones on a real network remains the registered open measurement. All code and gates are published.

**Keywords:** energy-optimal routing, edge cost, discretization, digital elevation models, Dijkstra, cycling energetics, terrain sampling scale, open science

<a id="1"></a>

## 1. Introduction

<a id="1.1"></a>

### 1.1 The routing problem

A router that minimises *energy* rather than distance or time answers a different question — not "which way is shortest?" but "which way can I afford?" — and for cycling the two diverge wherever relief does, because the climb term dominates every other cost. Writing $\beta$ for the energy per metre climbed and $\alpha = \alpha_r + \alpha_a$ for the flat cost per metre at the reference speed (rolling plus air; paper 1 eq. 2), a metre of climb buys $\beta/\alpha \approx 69$ m of distance at a 50 W reference, rising past 120 as speed falls. The deployed context here is an energy *field* rather than a single route: isochrone-style reachability in kJ over an 8-connected DEM grid, which is what the *Simujaules* router serves. Costs are direction-asymmetric (A→B ≠ B→A, since one direction climbs what the other descends), so the field is a directed one.

Production tools route by distance, time, or "hilliness" heuristics; research prototypes that cost energy per edge exist but leave route-level accuracy against measured power unpublished (paper 1 §1.1 and §4.2 survey them). *Planned:* a dedicated literature pass on energy-aware and e-bike routing cost functions, extending the project's `literature-context` notes.

<a id="1.2"></a>

### 1.2 What the ride-level law provides, and why it cannot be used as-is

Paper 1 validates the closed form $E = \alpha_r x + \alpha_a x_{\mathrm{flat}} + \beta(\tilde h_+ - \varepsilon\,\tilde h_-)$ — F3, with F4 its totals-only variant — to simulation parity on 2,039 rides [paper 1]. Three of its ingredients are non-local, and each obstructs a per-edge realisation in its own way: the deadband filter — elevation changes below a threshold $\tau$ ignored when summing ascent — is a sequential pass over the whole profile; $\varepsilon$ is a route aggregate; and the aero split needs a climbing share the edge does not know. (Paper 1's re-fitted deadband is 6 m; the deployed chain convention this paper's noise rates are measured under is $\tau = 2$ m — [paper 2] §1.1 reconciles the two.)

The deadband's non-locality has since been decomposed (lab journal, Entries 63–69; paper 1 §4.4.4). About half of its explanatory work is reproduced by a **kinetic-energy valley toll**, $\min(D,\ H,\ h_{KE} - 2\tau_n)$ per descent→climb valley — $D$ the descent's drop, $H$ the following climb's rise, $h_{KE} = v^2/2g$ the rider's kinetic-energy height, $\tau_n$ the chain's noise floor — computed from the dynamics' own fixed points; and of what the toll explains, roughly seven-eighths the filter also explains, so the two are substantially the same term. The rest is the measurable noise floor plus a fitted residue shown to be corpus-absorbing. The physically load-bearing part of the filter is therefore *graph-computable*: valleys are known at graph-build time. What a strictly edge-local cost still drops is the KE boundary layer — paper 1's recovery length $L_{\mathrm{rec}} \approx 90$ m at the shared constants, about three edges at 30 m pitch — which is exactly why kinetic continuity cannot be recovered by re-weighting single edges and needs a per-valley (two-edge-window) term instead. [§3.1](#3.1) measures what that term buys.

<a id="1.3"></a>

### 1.3 The proposed edge realisation: v2Edge

The deployed realisation — **v2Edge**, from the lab journal's Entries 17–18, with `r1d_v2_edge` in `src/harness/regime_compare.py` as its Python reference — costs an edge of length $\Delta x$, rise $\Delta h$ and grade $s = \Delta h/\Delta x$ as

$$E_{\mathrm{edge}} \;=\; \begin{cases} \alpha_r\,\Delta x + \beta\,\Delta h & s \geq 2\% \text{ (climb: aero gated off)}\\[2pt] (\alpha_r + \alpha_a)\,\Delta x + \beta\,\Delta h & 0 \leq s < 2\% \text{ (flat band)}\\[2pt] \max\!\big(0,\ (\alpha_r + \alpha_a)\,\Delta x \;-\; \varepsilon(s)\,\beta\,\lvert\Delta h\rvert\big) & s < 0 \text{ (descent),} \end{cases} \tag{E1}$$

so a descent edge pays the full flat bill — rolling *and* air at the reference speed — minus the refund, never less than zero. The grade-local recovery is

$$\varepsilon(s) \;=\; \mathrm{clamp}_{01}\!\Big(\min\big(1,\ \tfrac{\alpha/\beta}{\lvert s\rvert}\big) - \varepsilon_0\Big), \tag{E2}$$

paper 1's coasting ceiling (its eq. 6) less the frozen coasting deficit $\varepsilon_0 = 0.13$, floored at 0, with $\alpha = \alpha_r + \alpha_a$ evaluated at the flat reference speed. The deployed router additionally scales the two gravity arms by a per-map scalar $k_s$ — its edge-local stand-in for the deadband's noise removal, F4's $c$ in multiplier form; the runs in this paper take each profile as given, and it is exactly this stand-in that [§3.1](#3.1)'s valley patch replaces. E2's floor is deliberate model content at this grain: paper 1 publishes its *ride-level* estimator unclamped because ride-mean grades never reach the floor grade $s_*/\varepsilon_0$, but single 30 m edges beyond it (≈ 11–15%, depending on the flat reference speed) are common even where ride means are not (paper 1 Appendix A.6). E1's own $\max(0,\cdot)$, by contrast, is dead code at the deployed constants — [§3.4](#3.4).

For the search to be exact the cost must be additive, non-negative ($\varepsilon \leq 1$ guarantees it), and local; direction-asymmetry is fine for Dijkstra but rules out bidirectional search and A* without an admissible heuristic. *Planned:* derive the trivial lower-bound heuristic $\alpha_r \cdot d$ and check admissibility (Appendix B).

<a id="1.4"></a>

### 1.4 Hypotheses and their status

Seven hypotheses organise the paper; the measured sections resolve five of them (H5 as a first look).

- **H1 — fidelity** (measured, [§3.1](#3.1)): the edge sum over a measured ride's own path reproduces the ride-level form within paper 1's CI at the calibration scale. *Answered, negatively at fine pitch:* the gap is +1.83 pp at 5 m, bias-shaped, and attributable entirely to the descent side.
- **H2 — scale** (measured, [§3.1](#3.1), [§3.2.1](#3.2.1)): the edge cost's error grows as the sampling scale departs from the 30 m calibration scale unless constants are re-fitted or the raster pre-smoothed — the hypothesized mechanism being lattice oscillation reading elevation noise as relief. *Confirmed at ride grain* (the U-curve); the direction-count version of the mechanism is *chain-dependent* — refuted on smoothed chains, where the penalty is path-length inflation instead.
- **H3 — divergence** (planned, [§3.3](#3.3)): minimum-energy routes differ materially from minimum-distance ones only above a hilliness threshold.
- **H4 — repairs do not stack** (refuted at edge grain, [§3.2.3](#3.2.3)): the route-grain result that σ-smoothing and the portal deck remove the same artifact, so applying both over-corrects [paper 2], was registered to carry over. It does not: against measured energy, the deck still helps on a σ30-treated chain.
- **H5 — the valley patch** (first look measured, [§3.1](#3.1)): the KE toll of [§1.2](#1.2), applied per descent→climb node at graph-build time, reproduces most of what the ride-level filter buys, with no non-local pass.
- **H6 — interruptions from graph structure** (open): the router knows junction density and node degree — the collection-truncation information the ride-level calibration never had — so a per-node truncation term should explain part of the regional $\varepsilon$ split, interrupted urban riding against sustained descents (paper 1 §3.1.5; lab journal, Entries 60–61), from graph structure alone.
- **H7 — the measured-pin doctrine** (supported, [§3.2.2](#3.2.2)): constants follow the rule established in Entries 68–69 — noise floors measured per chain (paper 2's rates), buffers from rider physics, $\varepsilon$ the single fitted scalar; any constant *fitted* at edge grain is presumed corpus-absorbing until it survives a leave-one-rider-out transfer gate.

<a id="2"></a>

## 2. Methods

<a id="2.1"></a>

### 2.1 The engines

The Python reference for the deployed cost is `r1d_v2_edge` in `src/harness/regime_compare.py`; the deployed mirrors are the study applet and Simujaules' `energy-worker.js` (JS, with a bit-parity Rust backend). The mirror-set rule applies: any change to the cost lands in all copies. The edge-family variants introduced in [§3.2](#3.2) (eF1–eF4) live in the Entry-73 harness and map one-to-one onto paper 1's forms.

<a id="2.2"></a>

### 2.2 Grids and terrain sources

Two rasters: the local 5 m aerophotogrammetric survey (IGC-SP 2010) and the global 30 m FABDEM — the same two sources paper 2 characterises at route grain. A **chain** below is a raster plus its treatment: the survey raw (igc5), Gaussian-smoothed at σ = 10 or 30 m (igc5σ10, igc5σ30) or resampled at its 30 m step (igc30), and FABDEM raw (fab30) or smoothed (fab30σ30). The graph is 8-connected (extended to higher direction counts in [§2.3](#2.3)), with diagonal edge lengths and per-edge grade from cell elevations. One property separates edge grain from route grain: elevation noise enters *per edge*, with none of the along-profile cancellation a route-level total enjoys (lab journal, Entries 6 and 19) — which is why map treatment is a first-class axis of [§3.2](#3.2) rather than preprocessing trivia.

For the route-grain prescription — which source, which smoothing σ, which noise rate $c$ — this paper **cites paper 2's Table 2 rather than re-deriving it**: σ applied to the profile reproduces raster-space smoothing to −1.1% of $h_+$, and each chain's measured $c$ is the number to inherit. Two of its route-grain results were registered as *not* assumed to carry over unchanged: the penalty is terrain-dependent (so an edge-grain scale rule fitted on urban grids will not hold on escarpments), and oversampling a coarse DEM is itself a cost — on an 8-connected grid the sampling step *is* the grid pitch, so what was a free choice at route grain is a grid-design parameter here.

<a id="2.3"></a>

### 2.3 Validation corpora, map-matching, and protocol

The corpora are paper 1's (its Table 1): D3–D5 are three São Paulo riders' full histories (441, 219 and 636 rides) and D6 the open four-rider European deposit (743). Two populations run under paper 1's per-ride physics (its §2.2; lab journal, Entries 52 and 57): the **IGC population** — D3–D5 rides whose track lies inside the local survey, the $n = 1{,}034$ of them with every arm complete — carries every arm; the **FABDEM population** — D3–D6, since FABDEM is global and the European corpus joins, the $n = 1{,}844$ with every FABDEM arm complete — carries the FABDEM arms (map-matching's jump rule and raster coverage, below, account for the rides an arm loses). Each arm's edge-sum is scored against the measured $\int P\,dt$ *and* against the route-level estimate on the same chain's profile, with the project's median/CI/gate conventions (mulberry32, seeds 42/43, $B = 10^4$); noise-rate pins are measured under the deployed $\tau = 2$ m chain convention ([paper 2] §1.1).

**Map-matching** (the Entry-73 quantizer, `src/harness/e73_gridpath.py`) turns each ride's GPS line into a lattice path a router could actually produce. The line, resampled to a 5 m arc grid, is followed by a deterministic greedy walker over the raster's own lattice using the deployed move sets — the classic 8 directions first, then a Farey-ladder extension at $n$ = 16, 32, 64, 128 directions (each level inserts the mediant directions between neighbours), long moves sub-sampled along their length. All rungs are run and gated; the tables below print the informative 1/4/8/16/128 subset, and [§3.2.4](#3.2.4) cites FABDEM's $n = 32$ optimum from the full grid. Each step picks the move whose endpoint best chases the polyline one move-length ahead, verified by exact projection; acceptance requires chainage advance ≥ 5% of the move length and endpoint lateral error ≤ one cell diagonal; infeasible steps (switchbacks tighter than the lattice) jump one pitch and are counted, and a ride is dropped from an arm when jumps exceed 0.5% of its nodes. The $n = 1$ arm is the un-quantized polyline at lattice pitch — the parity anchor against [§3.1](#3.1)'s profiles.

Registered sanity gates hold the instrument itself to account: a synthetic azimuth fan must reproduce each move set's analytic metrication factor ($\sqrt 2$ at $n = 4$, 1.082 at $n = 8$, → 1 by $n = 128$); the median per-ride length inflation must be monotone non-increasing for $n \geq 4$; lateral error is bounded by construction; the median $h_+(\mathrm{path})/h_+(n{=}1)$ must stay within [0.90, 1.15] on the smoothed chain; and the $n = 1$ arms must reproduce their published counterparts per ride — paper 2's DEM columns for the DEM chains, [§3.1](#3.1)'s own-profile arms for the recorded profile.

<a id="2.4"></a>

### 2.4 Gates

Synthetic gates for the engines pre-date this paper (`SANITY=1 regime_compare.py`; the DEM chain's per-gate blocks, with two documented-benign failures). Every number published in [§3.1](#3.1)–[§3.2](#3.2) is re-derived by the project's gate battery — `src/harness/bootstrap_ci.py`, sections 3k (Entry 72) and 3l (Entries 73–74) — which exits non-zero on any mismatch.

<a id="3"></a>

## 3. Results

<a id="3.1"></a>

### 3.1 Edge-sum vs ride-level law vs measurement (measured — Entry 72)

The first tranche isolates pure discretisation: v2Edge summed over each ride's **own recorded profile** — no DEM, no lattice, no routing — at five grid pitches, against measured energy, on all 2,039 rides of D3–D6 at paper 1's per-ride physics. Two comparators need introducing. $\varepsilon_{\mathrm{geom}}$ is paper 1's geometry-only recovery evaluated on the ride's own profile — the drop-weighted coasting ceiling less the deficit $\varepsilon_0$ (its eq. 6 and §4.4.2), the route-level counterpart of E2 — and the **route-level twin** is F2, paper 1's unfiltered split form, run with that $\varepsilon_{\mathrm{geom}}$: the exact route-level integral of the edge cost, so edge-sum minus twin is pure discretisation error. Rows derive from `e72_edgegrain.csv`; the F4 comparators come from paper 1's published chain.

| arm (grid pitch) | med \|Δ%\| [95% CI] | signed [95% CI] |
|---|--:|--:|
| v2Edge @ 5 m | 4.62 [4.43, 4.93] | +3.39 [+3.08, +3.96] |
| v2Edge @ 10 m | 4.13 [3.92, 4.36] | +2.99 [+2.61, +3.36] |
| **v2Edge @ 30 m (deployed scale)** | **3.75 [3.53, 3.99]** | +1.33 [+1.08, +1.69] |
| v2Edge @ 60 m | 3.96 [3.73, 4.23] | −0.05 [−0.27, +0.16] |
| v2Edge @ 90 m | 4.15 [3.91, 4.37] | −0.93 [−1.11, −0.70] |
| route-level twin (F2 · $\varepsilon_{\mathrm{geom}}$ @ 5 m) | 4.31 [4.13, 4.54] | +1.25 [+0.96, +1.66] |
| valley patch @ 30 m | 3.29 [3.12, 3.50] | −0.08 [−0.34, +0.08] |
| **F4 as published** (paper 1: flat $\varepsilon$ = 0.409 · $c$ = 1.10) | **2.72 [2.58, 2.86]** | −0.35 [−0.51, −0.11] |
| F4 all-measured ($\varepsilon_{\mathrm{geom}}$ · paper-2 $c$ = 3.01) | 5.66 [5.42, 5.80] | −3.80 [−4.11, −3.50] |

**Fidelity (H1).** At 5 m the edge sum sits a median **+1.83 pp (med |gap| 1.84 pp)**<!--@c-a3.discretisation.fidelity--> above its route-level twin. The grade-local $\varepsilon(s)$ and E2's clamp floor, which only bind on descents, are the entire discretisation gap, and it is bias-shaped (systematically above), not noise.

**Scale (H2).** The error is U-shaped in grid pitch with its minimum exactly at the deployed 30 m ([Figure 1](#fig-p3-scale)). Finer grids over-charge because the edge cost carries *no deadband* to eat jitter (+3.4% bias at 5 m); coarser grids under-resolve (−0.9% at 90 m). The bias crosses zero near 60 m, which is *aliasing cancelling noise*, not accuracy — the med|Δ%| there is already worse than at 30 m.

**The valley patch (H5, first look — not the pre-registered arm, which is H5's full edge-grain test).** At the deployed scale, replacing the scalar $k_s$ stand-in with the Entry-63 KE valley toll — per descent→climb node, floored at 0, its brake-speed parameter frozen at the never-brake limit; median toll 20.3 m/ride at 30 m — takes the deployed cost from 3.75 · +1.33 to **3.29 · −0.08**, closer on 1,131 of the 2,038 rides carrying both arms (sign $p < 10^{-4}$). The toll is a graph-node term: additive over the search, computable at build time, no non-local pass.

**The route-level comparators reorder the hierarchy.** Paper 1's published F4 — one flat $\varepsilon$ and its jointly fitted $c$ — is the strongest number in the table, beating the deployed edge cost at its own calibration scale and the valley patch: published F4 (2.72) beats the patch (3.29), which beats v2Edge@30 (3.75), which beats the twin (4.31). Paper 1's flat-vs-dynamic lesson lands at edge grain: the grade-local $\varepsilon$ machinery loses to one flat constant. Two caveats travel with that reading. *Locality:* published F4 clamps its correction at route level, so its row is a route-level benchmark, not a drop-in edge weight — the per-edge linearisation (subtract $\beta c$ per metre from the gravity charge) is valid where $h_+ > c\,x$ and pathological on near-flat routes. *Pairing:* the all-measured variant — geometric $\varepsilon$ with paper 2's measured $c = 3.01$ — over-corrects to −3.8% bias despite each constant being individually principled. Paper 1's ($\alpha$, $\varepsilon$) pairing rule extends to ($\varepsilon$, $c$): "measured" does not exempt a constant from travelling with its pair.

<a id="fig-p3-scale"></a>

![**Figure 1.** Edge-grain error vs grid pitch (Entry 72): median |Δ%| and signed bias of v2Edge summed over each ride's own profile at 5–90 m. The minimum sits at the deployed 30 m; the zero-bias crossing near 60 m is aliasing cancelling noise, not accuracy.](figs/fig-p3-scale.svg)

<a id="3.2"></a>

### 3.2 The discrete-routing ladder (measured — Entries 73–74)

Section [§3.1](#3.1) scored profiles; this section scores *paths a router would take*. Four axes are varied one at a time on the matched ridden path ([§2.3](#2.3)): the direction count $n$, the terrain chain (source × smoothing σ), the cost family, and the portal (bridge/tunnel) repair. The cost families map one-to-one onto paper 1's forms — **eF1** (aero ungated) ← F1, **eF2** ← F2, **eF2 on a σ-treated map** ← F3's role, **eF4** ← F4 (eF2 plus a per-edge deduction of $c$ metres per kilometre on both gravity arms, at the chain's *measured* $c$ pin) — each carrying its form's published flat $\varepsilon$ from paper 1 (eF2: F2's fitted 0.462) and the per-edge $\max(0,\cdot)$ clamp, so eF# − F# isolates exactly the clamped-edge mass. The deployed grade-local v2Edge is the status-quo reference. Rows derive from `e73_gridpath.csv`; gate section 3l.

<a id="3.2.1"></a>

#### 3.2.1 Direction count

eF2's error against measured energy, by direction count $n$ ($n = 1$ is the un-quantized polyline at lattice pitch); the α·Δx column is the share of the penalty carried by pure path-length inflation:

| n | IGC 5 m σ10 | signed | α·Δx pp | FABDEM 30 m | signed | α·Δx pp |
|--:|---|---|--:|---|---|--:|
| 1 | 7.71 [7.21, 8.37] | +7.68 | 0.0 | 15.82 [15.35, 16.21] | +15.80 | 0.0 |
| 4 | 34.12 [33.68, 34.68] | +34.12 | 23.7 | 114.84 [113.25, 117.65] | +114.84 | 20.6 |
| 8 | 12.71<!--@c-a3.dirs.ladder--> [12.10, 13.07] | +12.70 | 4.7 | 48.23 [47.09, 49.30] | +48.21 | 3.8 |
| 16 | 8.76 [8.20, 9.48] | +8.75 | 0.9 | 34.32 [33.66, 35.23] | +34.29 | 0.0 |
| 128 | 7.52 [6.89, 8.24] | +7.45 | −0.3 | 27.16 [26.32, 27.87] | +27.10 | −1.4 |

The ladder is **chain-shaped** ([Figure 2](#fig-p3-dirs)). On the smoothed chain the $n$ = 4/8 penalty is essentially all path-length inflation: the 8-direction lattice inflates the ridden line by a median factor 1.0543<!--@c-a3.quantisation.length--> (1.2737 at $n = 4$), and the α·Δx column absorbs nearly the whole penalty — H2's oscillation mechanism is refuted *there*. On raw FABDEM the same rungs carry almost no length share: the lattice path reads 1.417× the polyline's $h_+$ at $n = 8$ (2.38× at $n = 4$) — per-pixel noise read by a zigzag path. Which discretisation error dominates is a property of the terrain source. Moving $n$ = 8 → 16 recovers 76% of the $n$ = 8 → 128 gap on the smoothed chain (66% on raw FABDEM).

<a id="fig-p3-dirs"></a>

![**Figure 2.** The direction-count ladder (Entry 73): eF2's error vs measured energy as the move set grows from 4 to 128 directions, on the smoothed local survey and on raw FABDEM. The same rungs are dominated by path-length inflation on one chain and by noise-reading on the other.](figs/fig-p3-dirs.svg)

<a id="3.2.2"></a>

#### 3.2.2 Cost families and map treatment

The full family × $n$ cross (med|Δ%| (signed); CIs for the quoted cells in gate 3l; eF2\* = eF2 on the σ-treated map; eF4L = eF4 at the leave-one-rider-out pin):

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

(The FABDEM rows carry no σ10 column: 10 m is below the raster's 30 m pitch, so that arm is not defined there.)

Read column-wise ([Figure 3](#fig-p3-chain)): **map treatment (eF2\*) is worth more than any cost-function change at every $n$**; the pin (eF4L) is the best *untreated* cost family at every tabulated $n$; and the treated chains make the pin itself transferable — the per-rider $c$ spread among the São Paulo riders collapses from 6.3–11.5 m/km on raw FABDEM to 3.50–3.68 after σ30 (the European pins move 5.73 → 2.96 alike), which is why the leave-one-rider-out pin costs nothing there.

At the base configurations ($n = 8$), med|Δ%| [95% CI] (signed):

| model | igc5 σ10 · n = 8 | fab30 · n = 8 |
|---|---|---|
| v2Edge (deployed) | 9.60 [9.1, 10.8] (+9.59) | 53.01 [51.8, 54.4] (+53.01) |
| eF1 | 17.36 (+17.35) | 59.08 (+59.08) |
| eF2 | 12.71 [12.1, 13.1] (+12.70) | 48.23 [47.0, 49.4] (+48.21) |
| **eF4L (LORO pin)** | 9.75 [9.3, 10.3] (+9.73) | 41.08<!--@c-a3.edge.pin--> [39.7, 42.3] (+41.06) |
| eF4 (pooled pin, sensitivity) | 9.71 [9.3, 10.2] (+9.70) | 41.62 [40.3, 42.7] (+41.61) |
| F3 (route algebra) | 5.24 [5.0, 5.6] (+4.78) | 7.01 [6.7, 7.3] (+6.51) |

Three findings. **First, the measured pin earns its term out of sample.** The quoted eF4 arm is out-of-sample by construction: each ride's pin is the median $c$ of the *other* riders of its region (leave-one-rider-out; the pooled-pin row, which shares geometry with the scored rides, is kept only as sensitivity, and the two differ by ≤ 0.6 pp everywhere). eF4L beats eF2 on **all six** DEM chains ([§2.2](#2.2)'s igc5, igc5σ10, igc5σ30, igc30, fab30, fab30σ30) and is the best Dijkstra-deployable cost on FABDEM by 6–11 pp — H7's doctrine in action. An $\varepsilon$-side robustness slice (scored on paper 1's held-out split only) preserves every ordering (IGC: eF4L 10.25 < v2Edge 11.10 < eF2 12.91; FABDEM: eF4L 39.69 < eF2 47.39 < v2Edge 51.97).

**Second, the deadband keeps a unique share at edge grain.** F3 on the *raw* chain — 5.67<!--@c-a3.deadband.residual--> med|Δ%| on IGC — beats eF2 on the σ30-*treated* map (9.21), and 7.01 against 11.49 on FABDEM: map pre-treatment is load-bearing (35.7 → 9.2 on raw IGC at $n = 8$) but does not substitute for the filter; the ~3.5–4.5 pp residual is the edge-grain sibling of the Entries 63–67 unique-share result. In the joint per-ride pairing the route forms win almost every ride (the edge family closer on 14–375 of 1,034; the clamp mass — what the per-edge $\max(0,\cdot)$ floor costs against the route algebra — is ~3.4 pp at σ10 and ~21 pp on raw FABDEM).

**Third, the pins are measurements, and they agree with the letter.** The measured $c$ pins (m/km, at the 2 m chain convention): own recording 3.04 BR / 1.26 EU · igc5 4.89 · σ10 3.66 · σ30 2.56 · igc30 3.75 · fab30 7.58 BR / 5.73 EU · fab30+σ30 3.57 BR / 2.96 EU — worst disagreement with the letter's independently measured rates (paper 2, Entry 71): 0.14 m/km.

<a id="fig-p3-chain"></a>

![**Figure 3.** The chain × cost-family cross (Entry 73): error against measured energy per elevation chain and cost family at the base direction counts. Map treatment dominates every cost-function change; the measured-pin deduction is the best untreated-chain cost.](figs/fig-p3-chain.svg)

<a id="3.2.3"></a>

#### 3.2.3 Portals

The straight-deck repair for bridges and tunnels — replacing the raster's heights across a mapped span with a chord [paper 2] — helps on the base path: 860<!--@c-a3.portals.edge--> of 883 span-touched rides (sign $p < 10^{-4}$), eF2 11.81 → 11.05 and F3 5.22 → 5.15 at σ10, medians over the span-touched subset rather than the full-population cells of [§3.2.2](#3.2.2). And, **refuting the registered H4 carry-over, it still helps on the σ30-treated chain** (802 of 880 closer, eF2 8.95 → 8.51). The route-grain rule — "correct or smooth, but not both" [paper 2] — does not hold at edge grain, where scoring is against measured energy rather than in-span barometric ascent. The deck remains a known-sign over-correction (a road bridge carries a vertical curve a chord erases — measured at route grain as −2.43 m [−3.26, −1.68] per touched ride on bridges against −0.29 [−0.40, −0.20] on tunnels), and at edge grain a bridge may span only one or two cells, so the sub-resolution crown could make that residual larger, not smaller.

<a id="3.2.4"></a>

#### 3.2.4 The deployable default

The measured cross plus a five-policy descent-$\varepsilon$ contest (lab journal, Entry 74) fix the recommendation: **the deployed grade-local cost — v2Edge's $\varepsilon(s)$ — on a σ30-treated map at $n = 16$ directions, portals on**, reading med|Δ%| 3.31<!--@c-a3.default--> (+2.41) on the local 5 m survey and 5.05 (+3.34) on FABDEM, with $n = 8$ as the fast choice (6.57 / 8.52; the deployed engine's own cost table puts $n = 16$ at 1.5–2.4× the $n = 8$ runtime). Marginality: past $n = 16$ the med|Δ%| stops improving — $n = 16$ is the measured optimum on the local survey and sits 0.20 pp from FABDEM's $n = 32$ optimum — while runtime grows ≈ 2× per rung; only the signed bias keeps falling (+2.41 → +1.36 by $n = 128$). The portal deck is policy-independent and still worth ~0.4 pp on span-touched rides after σ30. This default needs no site measurement and **no engine change**: it is the deployed cost itself, with two configuration defaults moved (smoothing σ10 → σ30, now applied to coarse sources too; directions 8 → 16).

The $\varepsilon$ contest behind the policy choice ran five policies in the identical edge skeleton, constants frozen from their producing CSVs. The grade-local $\varepsilon(s)$ wins **every** treated-map cell — against paper 1's published flat $\varepsilon_2 = 0.462$ (5.11 at this cell), the regionally honest flat $\varepsilon_{SP} = 0.239$ (10.24 — about 5 pp *worse*: the treated-chain bias is already positive and a stingier constant raises it), the Entry-45 grade-inverse deficit (6.17) and its occupancy mechanism curve (9.01) — while on raw chains the ordering inverts and flat $\varepsilon_2$ wins (35.66 vs 38.20 on raw IGC). Adaptive recovery and untreated noise do not mix, because noise manufactures steep micro-descents that a grade-local policy refuses to credit. (The two flat constants are paper 1's own numbers at its published precision: $\varepsilon_2$ its F2 fitted value, $\varepsilon_{SP}$ its São Paulo regional pool; the harness pins them from the producing CSVs.)

<a id="3.3"></a>

### 3.3 Route studies (planned)

*Planned:* the H3 measurement — how often, on a real network, the energy-optimal path departs from the distance-optimal one, and by how much. This is the mission-level number: energy-optimal routing is accessible routing only if the two actually diverge in practice. The distance trade is settled analytically by $\beta/\alpha$ ([§1.1](#1.1)); only the *frequency* on a real network is empirical. Entry 26's detour and portal experiments are seed evidence gathered for a different purpose; the quantification needs real network routing on Pedal Hidrográfico territory and energy-field maps from the deployed router.

<a id="3.4"></a>

### 3.4 Pitfall inventory

Each pitfall is stated with the evidence that demonstrates it; together they are the "what breaks" half of the paper's question.

- **Two clamps, one dead and one loaded.** The deployed cost's whole-edge $\max(0,\cdot)$ in E1 is dead code — Entry 18 shows it never binds at the deployed constants, and it is documented rather than removed. The eF family's per-edge clamp, by contrast, carries real mass against the route algebra: ~3.4 pp on smoothed chains, ~21 pp on raw FABDEM ([§3.2.2](#3.2.2)) — the clamp cost is a property of the cost family, not of clamping as such.
- **Aero-gate discontinuity**: the cost jumps as an edge crosses the 2% threshold; the effect on route stability is undemonstrated. *Planned:* a perturbation experiment.
- **Non-negativity vs steep-descent recovery**: $\varepsilon \leq 1$ keeps every edge cost non-negative and Dijkstra honest; a negative-cost variant would need Johnson-style reweighting or a potential function. *Planned:* show $mgh/k_{\mathrm{eff}}$ *is* such a potential and what remains after subtracting it (Appendix A). The clamp-floor asymmetry with paper 1 is deliberate ([§1.3](#1.3)).
- **Per-edge noise**: no profile-level cancellation exists at edge grain, so expected inflation grows with edge count rather than averaging out — the mechanism behind the raw-chain columns of [§3.2.2](#3.2.2), and the connection between the noise rate $c$ and edge length.
- **Asymmetry and turn costs**: direction-asymmetry is physics and the search must honor it; turn costs are out of scope, but a router must not assume cost symmetry when reusing relaxations.
- **Momentum non-locality** (lab journal, Entry 37; paper 1 §4.4.4): kinetic energy worth $h_{KE} = v^2/2g \approx 2$–6 m of climb carries across edges, and no per-edge cost can transport it — closely spaced rollers (within the dissipation length $\lambda = m/\rho C_dA \approx 200$ m) are over-charged by construction. $h_{KE}$ and $\lambda$ bound the error's scale; the valley patch of [§3.1](#3.1) is the two-edge-window repair, and raster pre-smoothing absorbs part of the rest. The speed-dependence this implies means a deployment either accepts the filter as calibrated-at-one-speed or parameterises it.
- **The grade-resolved deficit** (registered in lab journal Entry 34, measured in Entry 44): pedalling occupancy fades monotonically with cell grade for all riders while intensity is rider-level — a per-edge $\varepsilon_0(s) = \varepsilon_0 \cdot \varphi(s)$, with $\varphi(s)$ the measured occupancy fade, is therefore physically licensed at exactly this paper's grain, where paper 1's ride-level test could not profit from it. A candidate refinement of eq. (E2) beyond the constant deficit; it needs paper 1's held-out discipline at edge grain.

<a id="4"></a>

## 4. Discussion (planned)

*Planned.* The shape is fixed by the results so far: what transfers from papers 1–2 unchanged (the physics split, the frozen constants, the deficit's recurrence, the per-chain measured scales) versus what is genuinely new risk at edge grain (scale coupling, locality restrictions, the clamp mass); the grade-resolved deficit as this paper's natural refinement if it survives held-out discipline; and limitations — one metropolitan region plus one European deposit, and a grid model with no per-edge surface type (OSM surface tags as a $C_{rr}$ field are future work; the project's privacy rule applies — Overpass queries must never derive from ride endpoints).

<a id="5"></a>

## 5. Conclusions (planned)

*Planned* — after [§3.3](#3.3). The measured half already supports: the discretisation gap is real, descent-side, and bias-shaped (H1); the deployed 30 m scale is the measured optimum, not an accident (H2); the valley toll moves the deadband's load-bearing physics into the graph (H5); map treatment dominates cost-function choice, measured pins transfer where fitted constants do not (H7); and a deployable default exists with no engine change. What is missing is the divergence measurement (H3) that makes the routing case quantitative.

## Data and code availability

The instruments are `src/harness/e72_edgegrain.py` and `src/harness/e73_gridpath.py`; each writes one per-ride CSV, and every published number in §3.1–3.2 is re-derived from those CSVs by the project's gate battery (`src/harness/bootstrap_ci.py`, sections 3k/3l), which exits non-zero on any mismatch. All analysis code is public at `github.com/danlessa/bicycling-energy-model` (stdlib-only Python where possible; the Entry-73 harness needs the project's conda environment for the rasters). Per-ride GPS tracks and the independent riders' exports are private by design. The protocols, registrations and deviations are lab-journal Entries 72–74.

## AI-assistance declaration

The analysis harnesses, the lab journal's bookkeeping, and drafts of this text were produced with substantial LLM assistance (Anthropic Claude) under continuous author direction and review; all data collection, modelling decisions and final claims are the author's.

## References

- **[paper 1]** Lessa Bernardineli, D. *A Closed-Form Model for the Mechanical Energy of Cycling a Route, Evaluated Against 2,039 Power-Metered Rides.* Companion paper in this series.
- **[paper 2]** Lessa Bernardineli, D. *A Recipe for Estimating Bicycling Route Energy at Planning Time, with Corrections for the Elevation Source.* Companion letter in this series.

## Appendix (planned)

- **A. Derivation:** from paper 1's integral formalism to the edge sum; the exact discretization error terms — what vanishes as $\Delta x \to 0$ and what does not (the deadband term does not); the $mgh/k_{\mathrm{eff}}$ potential.
- **B. Admissible heuristic for A\***, if [§1.3](#1.3)'s lower bound pans out.
- **C. Bit-parity protocol** between the JS and Rust engines.
