<!-- Claim annotations for this working paper live in wp1-route-energy.meta.ttl, keyed to the
     invisible @c-<id> anchors in the text below (checked by research/scripts/check_paper_stats.py). -->

<!--
  wp1-route-energy.md — WORKING PAPER WP-1, PRE-DRAFT BODY (2026-11-07).

  What it is: a consolidation of the three companion drafts (paper1-closed-form.md,
  paper2-dem-deployment.md, paper3-edge-cost.md) written after an external review of all
  three. It adds NO measurement. It (i) fixes one parameter anchor for the series, (ii) labels
  every number by the protocol that produced it, (iii) restates the results at ride, map and
  edge grain under those labels, and (iv) lists the measurements still owed, in priority order.
  Length budget: <= 10 pages A4, single column (renders to ~9 at 11 pt, 2.2 cm margins).

  Governance (mission-model/08): this is a state-1 artefact — a machine-produced pre-draft body
  handed over for human writing and diagramming. The human draft is written on top of it.

  Sources of truth: the three drafts (numbers gated by src/harness/bootstrap_ci.py, sections
  1/3i/3j/3k/3l/3p/3q/3r/3s/3t) and research/journal/MODEL_COMPARISON_JOURNAL.md. Numbers that
  appear in none of the three drafts — only in the lab journal, and not re-derived by the
  current gate battery — are marked with a dagger (†) at the point of use. Anchored numbers
  (the invisible @c-<id> markers) are the gated subset; the sidecar maps each to its gate
  section. NB not every number the drafts print is gated (e.g. paper 1's CIs and its 149/305
  sign test are not asserted by section 3q), so "unmarked" means "quoted from a draft", not
  "gated". When a companion draft re-baselines a number, this file is one more restating
  surface (CLAUDE.md, "Verifying a change").

  HEADLINE DISCREPANCY (found while writing this): paper 1 prints the held-out row of the chain
  BEFORE Entry 57's rider-median fallbacks (F3 3.39 [3.03, 3.69] · +0.06, F4 2.85, F_base 3.05,
  149/305), although its §2.2.2 adopts that fallback as the published chain and its CV column is
  the post-57 one. The current chain (e52_build.py default E52_FALLBACK=rider since 1f61fe6;
  Entries 57 and 63; research/data-graph.ttl :o_e52_split) reads F3 3.24 [2.75, 3.50] · +0.07,
  F4 2.86 [2.58, 3.39] · −0.40, F_base 3.19 · −0.10, 152/305, p = 1.00. Gate 3q's expected
  literals are the old ones and its ±0.5 tolerance passes both. This working paper prints the
  current chain (journal-sourced, so †) and anchors none of the four; paper 1 and gate 3q need
  re-baselining (§6 preamble; sidecar claim wp.headline.rebaseline).

  Anchor decision (§3.2): route-grain claims are anchored on paper 1's held-out-selected bundle
  B1 (F3, flat eps = 0.294, tau = 6 m; F4, eps = 0.409, c = 1.10 m/km). The deployed bundle BD
  and the hand-recipe bundle BR are reported as labelled arms. Reversible: if the author anchors
  on BD instead, §3.2, Table 2 and §6 items 1 and 5 change; nothing else does.
-->

# Cycling Route Energy in Closed Form, from Ride to Map to Router: Consolidated Results, Scope and Open Measurements

**Danilo Lessa Bernardineli** — Dynamical Systems Group; Pedal Hidrográfico, São Paulo

*Working paper WP-1 · November 2026 · consolidates three companion drafts — [P1] the route-level law, [P2] elevation from maps, [P3] the per-edge routing cost — and reports no new measurement. Unmarked numbers are quoted from the drafts; numbers found only in the project's lab journal are marked †.*

## Abstract

We consolidate three companion studies of a closed-form law for the mechanical energy of cycling a route, $E \approx \alpha_r x + \alpha_a x_{\mathrm{flat}} + \beta(\tilde h_+ - \varepsilon\,\tilde h_-)$, under one parameter anchor and with every number labelled by the information it used. On 305 held-out rides from seven riders in São Paulo and Western Europe, the selected form reproduces power-meter energy to 3.24%† median absolute error (bias +0.07%), indistinguishable from a forward simulation (3.19%) reading the same inputs. Those inputs include each ride's own regime powers and constants inverted from its own telemetry, which makes the flat part of the energy ledger nearly an identity: the figure measures the consistency of the energy accounting, not prediction. With literature constants instead, the one blind-physics run — 44 of the author's rides — reads 8.2% for the law and 8.4% for the simulation; the rider-level held-out row a planner would face is registered and not yet run. The descent constant absorbs form error (it refits from 0.68 to 0.29 across forms) and sits in a shallow loss basin, so the published transfer penalties — 0.05 points between riders, 0.8–0.9 between landscapes, both inside the ±1-point margin set in advance — cannot tell a rider property from a landscape property. A digital elevation model costs 0.3 points of error on a local 5 m survey and 0.7–1.3 on the global FABDEM, repaired by smoothing the sampled profile and carrying each elevation chain's own noise rate. Cut into edges, the law gains a descent-side bias that a kinetic-energy valley toll removes; whether the edge cost ranks alternative routes correctly is untested. Eleven measurements are owed, most on data already in hand.

**Keywords:** cycling energetics, route planning, energy-optimal routing, power meter data, digital elevation models, closed-form approximation, model validation

<a id="1"></a>

## 1. Purpose

Three companion drafts develop one closed-form law for the mechanical energy of cycling a route: [P1] derives it and validates it against 2,039 power-metered rides; [P2] measures what it costs to take elevation from a map instead of the ride's own barometer; [P3] discretises it into a per-edge cost for an energy-minimising router. Read together, and after an external review of all three, they share three problems no single draft can fix from inside:

- **Three parameter bundles.** [P1] validates one, its hand recipe recommends a second, and [P2] and [P3] score a third — the one the production router ships, whose descent estimator [P1] does not recommend. Two of the three were calibrated on corpora [P1] excludes as non-independent.
- **An accounting-consistency figure that reads like a prediction figure** ([§3.1](#3.1)).
- **Two claims tested with instruments that cannot see them**: transfer of the descent constant, with a loss that is shallow in that constant ([§4.1](#4.1)); and fitness for routing, with ride-energy error on ridden paths instead of choices among alternatives ([§4.3](#4.3)).

This working paper fixes one parameter anchor ([§3.2](#3.2)), labels every number by the information it used ([§3.1](#3.1)), restates the results at ride, map and edge grain ([§4](#4)), and lists the measurements still owed ([§6](#6)).

<a id="2"></a>

## 2. The law and its two realisations

**Ride grain.** Pedalling a route costs energy per metre of distance and per metre climbed, and recovers part of it per metre descended:

$$E \approx \alpha\,x + \beta\,(h_+ - \varepsilon\,h_-),\qquad \alpha = \underbrace{\frac{C_{rr}\,m g}{k_{\mathrm{eff}}}}_{\alpha_r} + \underbrace{\frac{\tfrac12\rho\,C_dA\,(v_f + w)^2}{k_{\mathrm{eff}}}}_{\alpha_a},\qquad \beta = \frac{m g}{k_{\mathrm{eff}}}, \tag{1}$$

with $x$ the distance, $h_\pm$ total ascent and descent, $m$ system mass, $C_{rr}$ the rolling coefficient, $C_dA$ the drag area, $\rho$ air density, $k_{\mathrm{eff}} = 0.98$ drivetrain efficiency, $v_f$ the flat cruising speed, $w$ the headwind (zero throughout) and $g = 9.7864$ m/s². The first two terms are the textbook steady-speed energy integral [di Prampero et al. 1979; Martin et al. 1998]; the refund fraction $\varepsilon$ is the law's own. [P1] derives four forms from the exact route-energy integral: **F1** is eq. (1); **F2** charges air resistance only off climbs, $\alpha_r x + \alpha_a x_{\mathrm{flat}} + \beta(h_+ - \varepsilon h_-)$, with $x_{\mathrm{flat}}$ the distance on grades below 2%; **F3** runs F2 on a deadband-filtered profile, ignoring elevation changes smaller than $\tau$ to give $\tilde h_\pm$; **F4** approximates F3 from route totals, $\tilde h_\pm \approx h_\pm - c\,x$, with $c$ the elevation source's ascent-noise rate in metres per route-kilometre. F1 → F3 is two corrections: F1 bills air resistance at cruising speed on climbs ridden far slower, and counts elevation noise — and micro-relief paid by momentum — as climbing [Rapaport 2011].

**The descent term.** With no pedalling, the per-segment energy balance caps the recoverable share of a descent's potential energy at

$$\varepsilon_{\mathrm{coast}}(s) = \min\!\big(1,\ s_*/s\big),\qquad s_* = \alpha/\beta \;\;(1.8\text{–}2.2\%\ \text{here}). \tag{2}$$

Riders recover less because they pedal downhill; [P1] calls the shortfall the coasting deficit $\varepsilon_0$. Two estimators follow: a **flat** constant $\varepsilon$, fitted; and a **dynamic** $\varepsilon_d$, the drop-weighted ceiling over the route's descents less a frozen $\varepsilon_0$.

**Edge grain.** The *Simujaules* energy-field router deploys *v2Edge* [P3]: an edge of length $\Delta x$, rise $\Delta h$ and grade $s$ costs $\alpha_r\Delta x + \beta\Delta h$ on climbs ($s \geq 2\%$), $\alpha\,\Delta x + \beta\Delta h$ on the flat band, and $\max\!\big(0,\ \alpha\,\Delta x - \varepsilon(s)\,\beta\,\lvert\Delta h\rvert\big)$ on descents, with $\varepsilon(s) = \mathrm{clamp}_{01}\big(\varepsilon_{\mathrm{coast}}(s) - \varepsilon_0\big)$. The deadband, sequential over a whole profile, has no per-edge form; the router substitutes a per-map scalar $k_s$ on the gravity terms.

<a id="3"></a>

## 3. What a number in this series measures

<a id="3.1"></a>

### 3.1 Four protocols

Accuracy is the median over rides of $\lvert\Delta\%\rvert$, with $\Delta\% = (E_{\mathrm{model}} - E_{\mathrm{meas}})/E_{\mathrm{meas}}$ against the meter's $\int P\,dt$, beside the median signed $\Delta\%$ (the bias), with bootstrap 95% intervals. What such a number means depends on what the models read from the ride being scored ([Table 1](#tab1)).

<a id="tab1"></a>

**Table 1.** Protocols, by what the models read from the scored ride. Best figure: median error · bias, in %.

| protocol | physics $m, C_{rr}, C_dA$ | effort | measures | best figure available |
|--------------|------------------|------------------|------------|---------------------------------------|
| **P0** per-ride (all drafts) | inverted from the scored ride | its regime powers; $v_f$ from its flat power | accounting consistency | F3 3.24 [2.75, 3.50] · +0.07; simulation 3.19 · −0.10 (305 held-out rides; current chain†, [§4.1](#4.1)) |
| **Pf** frozen priors | literature priors; logged mass | its regime powers | blind physics | D1 only†: F3·$\varepsilon_d$ 8.2 [4.5, 10.8] · +2.2; simulation 8.4 [5.1, 10.9] · +2.5 (44 rides; 3.5 and 5.2 with informed constants) |
| **P1** rider-level | rider medians, training half | rider-median $v_f$ or regime powers | what a planner gets | not run ([§6](#6), item 2) |
| **P2** blind | as P1 | from a rider power model | forecasting | not attempted |

**P0 is nearly an identity on the flat.** The drag area is inverted from the ride's flat-regime power $P_{\mathrm{flat}}$ at its measured flat speed $v_{\mathrm{meas}}$, and $v_f$ is the speed at which the same flat balance closes. So $v_f = v_{\mathrm{meas}}$, $\alpha = P_{\mathrm{flat}}/v_{\mathrm{meas}}$, and the flat charge $\alpha\,x$ on flat ground is the flat-regime energy the meter recorded, up to how well one speed summarizes flat time. Mass comes from the ride's own climbs on half the rides (31% fully, 19% from a marginal set; the rider median otherwise). A P0 figure therefore tests the remainder: the descent bookkeeping, the partition into grade regimes, and the transients. The simulation reads the same inputs, so engine parity ([§4.1](#4.1)) means that the closed form loses nothing a forward integration would add *given those inputs*. It is not evidence that either engine predicts a ride from a route and a rider description.

**Pf is not a clean blind test.** It still reads the ride's power, and under literature constants the dynamic $\varepsilon_d$'s large refund on gentle terrain partly cancels the prior drag area's over-prediction (Entry 46)†. Its one surviving figure, on 44 of the author's brevets (D1, contained in D5), shows only the order of magnitude: both engines move from 3.5–5% with condition-informed constants to about 8% blind.

**P1 is the missing row, and it needs no new data**: rider-median physics and pace from the training half, scored on the held-out half under a route-grouped split. The closed form then reads nothing of the scored ride but its geometry. Once measured, it belongs in the abstract beside the P0 figure.

<a id="3.2"></a>

### 3.2 Three bundles, one anchor

<a id="tab2"></a>

**Table 2.** The parameter bundles the drafts evaluate. D1 and D2 re-process the author's rides in D5 and are excluded from [P1]'s population as non-independent.

| bundle | descent and smoothing constants | selected on | scored in |
|-----------------|----------------------------------|------------------------|---------------------|
| **B1** selected [P1] — **anchor** | F3: flat $\varepsilon$ = 0.294<!--@c-e52.eps-->, $\tau$ = 6 m · F4: $\varepsilon$ = 0.409, $c$ = 1.10 m/km | cross-validation on D3–D6's training half | [P1] held-out half; [P3] F4 row |
| **BD** deployed | $\varepsilon_d$ with $\varepsilon_0$ = 0.13 · $\tau$ = 2 m · per-map $k_s$ | $\varepsilon_0$ calibrated on D1 (Entry 8)†; its form kept by BIC on 48 rides of D1∪D2 (Entry 47) | all of [P2]; [P3] v2Edge rows |
| **BR** hand recipe | flat $\varepsilon$ = 0.20 · $c$ = 3 m/km · priors $C_{rr}$ 0.008, $C_dA$ 0.40 m² | $\varepsilon$ on the D2 urban census | never, as a bundle |

BD and BR rest on data the series declines to count. **B1 is therefore the anchor** for every route-grain claim — the only bundle selected under held-out discipline on independent data. BD is a labelled arm wherever it was measured; BR is not recommended until it is scored under P1.

The anchor does not settle which descent estimator is right: the two head-to-head comparisons disagree, and neither is clean. At route grain, on a held-out half of D3–D6, a flat constant beat $\varepsilon_d$ by 1.32 points (4.17% · +1.76 against 5.49% · −2.81; flat closer on 560 of 1,006 rides, $p$ = 0.0004; Entry 51†) — but under a drag estimator since superseded. At edge grain, on maps smoothed at σ = 30 m, the grade-local $\varepsilon(s)$ won every cell of a five-policy contest — 3.31% against 5.11% for [P1]'s F2 constant and 10.24% for the São Paulo regional constant — but the contest chose on the population it scored, and on raw maps the order inverts. One consistent reading: smoothed maps are dominated by shallow 1–3% descents, which a grade-local refund credits near its ceiling and a flat constant fitted on deadbanded recordings does not. That is a hypothesis; item 1 of [§6](#6) tests its route-grain half.

<a id="4"></a>

## 4. Results

<a id="4.1"></a>

### 4.1 Ride grain, recorded elevation [P1]

Four corpora, 2,039 rides of at least 20 km with per-second power, seven riders: three São Paulo histories (D3, 441 rides; D4, 219; the author's D5, 636) and an open four-rider European deposit (D6, 743). Fifteen per cent of each corpus was held out once (305 rides); forms and constants were chosen by repeated stratified 5-fold cross-validation on the other 1,734, every parameter refitted in-fold, with AIC agreeing. Protocol P0, bundle B1.

<a id="tab3"></a>

**Table 3.** Selection on the training half and error on the held-out half (P0, B1). CV: mean $\lvert\log(\hat E/E)\rvert$ ± standard error over 20 folds, as printed in [P1]. Held-out error and bias in %, 95% intervals in brackets, for the current chain (Entries 57 and 63†); F1–F2 are not re-reported for it.

| form | CV | fitted $\varepsilon$ [95% CI] | other | held-out error | held-out bias |
|------|-------------:|------------------:|----------------:|------------------:|-------------------:|
| F1 | 0.0711 ± 0.0019 | 0.683 [0.672, 0.700] | — | — | — |
| F2 | 0.0631 ± 0.0018 | 0.462 [0.457, 0.469] | — | — | — |
| **F3** | **0.0541 ± 0.0018** | **0.294** [0.285, 0.304] | $\tau$ = 6 m [4.5, 6.6] | **3.24** [2.75, 3.50] | **+0.07** [−0.31, +0.70] |
| F4 | 0.0629 ± 0.0022 | 0.409 [0.399, 0.417] | $c$ = 1.10 m/km | 2.86 [2.58, 3.39] | −0.40 [−0.73, +0.14] |
| simulation | — | — | — | 3.19 | −0.10 |

**[P1]'s printed held-out row is one entry stale.** [P1] prints 3.39 [3.03, 3.69] · +0.06 for F3, 2.85 for F4, 3.05 for the simulation and a 149-of-305 sign test: the chain *before* rider-median fallbacks replaced the global priors (Entry 57), although its own §2.2.2 adopts those fallbacks and its CV column is theirs. The current chain — the harness default, the lab journal and the project's data graph agree — reads as in Table 3. The gate meant to catch this tolerates ±0.5 points on these medians and passes both; re-baselining [P1] comes before everything in [§6](#6).

**Two corrections carry the improvement** (CV 0.0711 → 0.0631 → 0.0541); F3 alone is within one standard error of the best. F4 reads lower than F3 on the held-out half with overlapping intervals: 305 rides do not separate them.

**Engine parity is internal consistency.** The paired sign test reads 152 of 305 rides ($p$ = 1.00): given the same per-ride inputs, a stateless pass loses nothing to a forward integration that carries velocity between segments. A non-significant test is not equivalence, and [P1]'s registered equivalence test (±1 point) has not been run on this split. Contests under P0 also test input consistency: under an earlier drag estimator the simulation carried a −3.85% bias and lost on 190 of 305 rides, and fixing the estimator alone produced the tie.

**The descent constant is a closure term.** It refits to 0.683, 0.462, 0.294 and 0.409 across F1–F4 because each form loads its residual onto the refund: the climb aero over-charge in F1, phantom ascent whose matching phantom descent a larger refund cancels in F2, the noise F4's scalar leaves behind. So 0.294 is F3's constant on deadbanded recordings at $\tau$ = 6 m, not a measured behaviour, despite the mechanistic reading eq. (2) gives the refund [P1 §4.4.2]. Constants travel as sets: $(\alpha, \varepsilon)$ at ride grain, $(\varepsilon, c)$ at edge grain [P3 §3.1].

**Only the flat resistance is identified.** The inversion falls back to the rider median for $C_{rr}$ on 77% of rides and measures $C_dA$ on 97%. Within a rider $C_dA$ and $C_{rr}$ vary with coefficients of variation 0.45 and 0.36, their combination $\alpha$ with 0.15; a joint linear inversion returns 63 kg against the cascade's 98 (condition number ≈ 330), so the fallbacks mark missing information, not a missing estimator. Total-order Sobol shares of F3's error variance: drag area 0.55, mass 0.46, $C_{rr}$ 0.14, $\varepsilon$ 0.070<!--@c-e50.eps.share-->.

**Transfer is not resolved by the loss.** Moving $\varepsilon$ ±10% inflates the cross-validation loss by 1.1% (drag area: 46.9%); inflating it by half takes 0.22× or 1.79× the fitted value. Rider optima lie between 0.215 and 0.470, −27% to +60% from the pooled 0.294. Both reported penalties — 0.05<!--@c-e54.transfer--> points [0.03, 0.08] when one rider's $\varepsilon$ serves the others, and 0.82 (São Paulo) and 0.92 (Europe) when one $\varepsilon$ serves both landscapes — lie inside the ±1.0-point margin registered as the threshold for mattering, so neither separates a rider property from a landscape property. Three observations say more. One pooled constant biases the regions in opposite directions, −1.31%<!--@c-wp.e60.br.signed--> and +1.95%<!--@c-wp.e60.eu.signed-->, and regional constants (0.239, 0.371) remove both. The regional gap (0.13) is no larger than the spread of rider optima within a region (0.215–0.314 in São Paulo, 0.295–0.470 in Europe), and the São Paulo regional gain is not significant on its own (105 of 189 rides, $p$ = 0.15; Entry 60†). And the simulation, run over both regions' real geometries with one synthetic rider, reproduces 94% of the gap. So $\varepsilon$ differs between these two landscapes and terrain alone can produce the difference; whether it is a property of context rather than of riders is open ([§6](#6), item 4).

**Repeat routes.** 82%<!--@c-e52.twin--> of held-out rides have a same-rider training ride within 5% on distance and 10% on ascent: the headline is a repeat-route error. Under P0 this touches only the choice of $\varepsilon$, $\tau$ and form, because each ride's physics is its own; under P1 it would touch everything, hence the route-grouped split.

<a id="4.2"></a>

### 4.2 Map grain: elevation from a digital elevation model [P2]

[P2] re-walks the São Paulo corpora with travel rides kept (1,164 rides, 1,035 inside the local survey) and D6 (670 rides), changing only the elevation source — a DEM sampled along the recorded track — so each ride is its own control. Protocol P0, bundle **BD**: these are the deployed law's figures, and their re-base to B1 is owed. With a profile, the law runs on it (F3); with route totals only, F4 needs the chain's noise rate $c$ ([Table 4](#tab4)).

<a id="tab4"></a>

**Table 4.** The elevation-source substitution (P0, BD). With a profile: F3·$\varepsilon_d$, error [95% CI] · bias, in %. Totals only: the chain's ascent-noise rate $c$, metres per route-km removed by the 2 m deadband. Survey cells cover 1,035 rides, FABDEM cells 1,160.

| elevation chain | profile: São Paulo | profile: Europe | $c$: São Paulo | $c$: Europe |
|------------------------------|-----------------------:|----------------------:|------------:|-----------:|
| ride's barometer (control) | 3.8 [3.6, 4.1] · −1.9 | 3.4 [3.1, 3.6] · +0.3 | 3.01<!--@c-a2.noise.rate--> | 1.26<!--@c-wp.noise.d6--> |
| local 5 m survey, sampled at 5 m | 4.1<!--@c-a2.swap.cost--> [3.9, 4.4] · +0.3 | — | 4.90 | — |
| … profile smoothed, σ = 30 m | 4.0 [3.8, 4.2] · −1.8 | — | n/a from totals | — |
| local survey, sampled at 30 m | 4.0 [3.8, 4.2] · −0.3 | — | 3.7 | — |
| FABDEM 30 m, sampled at 30 m | 4.5 [4.0, 4.9] · +2.2 | 4.1 [3.9, 4.5] · +3.2 | 7.4 | 5.61 |
| FABDEM 30 m, sampled at 5 m | 5.1 [4.5, 6.0] · +4.3 | 5.5 [5.1, 5.9] · +5.3 | 10.15<!--@c-wp.noise.fab5--> | 7.87 |

**Cheap on a good survey, repairable on a global product.** The 5 m aerophotogrammetric survey costs 0.3 points of error and moves the bias 2.2 points; a Gaussian of σ = 30<!--@c-a2.smoothing.prescription--> m along the sampled profile restores the control's bias to within a tenth of a point, with nothing re-fitted. FABDEM costs 0.7–1.3 points at +2 to +4% bias in São Paulo, and 0.7 points in Europe at its native step; oversampling it manufactures relief.

**The noise rate belongs to the chain**: from 1.26 to 10.15 m/km, a factor of eight, so a totals-only user needs the chain's own $c$. F4's accuracy at each chain's $c$ is not yet reported.

**The penalty depends on terrain**, within one rider and one device: on the author's 84 rides outside the survey's footprint, FABDEM's paired over-charge grows from +5.1 to +7.2 points and its error reaches 7.7% [5.0, 12.1], while the same barometer holds 4.7%. Table 4's bands do not carry to terrain rougher than the calibration mix.

**Three results need re-measurement.** (i) The anomaly screen — FABDEM's error falling from 5.3% to 3.4% on 745 crops free of elevation artefacts — is compared with a barometer scored on all rides, so "better than the barometer" is not a paired claim. (ii) That screen and the bridge-and-tunnel results — including the useful finding that a straight-deck repair and σ = 30 m smoothing remove the same artefact and over-correct when stacked (stacking is closer on only 400 of 935 rides, $p < 10^{-4}$) — were measured on an older population that includes D1 and D2. (iii) A re-gridding bug clips extrema between 5 m nodes on the 30 m arms (median 0.85% of ascent on the survey, 1.2–1.5% on FABDEM). It should be fixed, not disclosed.

<a id="4.3"></a>

### 4.3 Edge grain: the law as a routing cost [P3]

**The object** is a raster lattice — 8 to 128 directions over a DEM — serving an energy field (reachability in kJ), not a street network. On a street graph with 50–300 m edges the direction ladder vanishes and the question becomes how finely to sample each edge's profile, which [Table 5](#tab5)a speaks to and [Table 5](#tab5)b does not.

<a id="tab5"></a>

**Table 5.** The edge cost (P0), error · bias in %. *(a)* Summed over each ride's own recorded profile, all 2,039 rides; no DEM, no lattice. *(b)* On matched ridden paths over the lattice; survey population 1,034 rides (D3–D5), FABDEM population 1,844 (D3–D6). v2Edge rows run without the production $k_s$.

| (a) arm, own profiles | error [95% CI] | bias |
|--------------------------------------------------|-------------------------:|-----------:|
| v2Edge summed at 5 m pitch | 4.62 [4.43, 4.93] | +3.39 |
| v2Edge at 30 m, the deployed pitch | 3.75<!--@c-wp.v2edge.d30--> [3.53, 3.99] | +1.33 |
| v2Edge at 90 m | 4.15 [3.91, 4.37] | −0.93 |
| route-level twin, F2·$\varepsilon_{\mathrm{geom}}$ at 5 m | 4.31 [4.13, 4.54] | +1.25 |
| v2Edge at 30 m with the valley toll | 3.29<!--@c-wp.patch30--> [3.12, 3.50] | −0.08 |
| F4 under B1, route level | 2.72 [2.58, 2.86] | −0.35 |

| (b) cost · map · directions | local 5 m survey | FABDEM 30 m |
|--------------------------------------------------|------------------------:|------------------------:|
| v2Edge as deployed · σ10 survey, raw FABDEM · 8 | 9.60 · +9.59 | 53.01<!--@c-wp.v2edge.fab30--> · +53.01 |
| per-edge noise deduction, leave-one-rider-out $c$ · same · 8 | 9.75 · +9.73 | 41.08 · +41.06 |
| F3 route algebra on the same paths · 8 | 5.24 · +4.78 | 7.01 · +6.51 |
| proposed default: v2Edge · σ30 map · 16 | 3.31<!--@c-a3.default--> [2.94, 3.80] · +2.41 | 5.05 [4.72, 5.35] · +3.34 |
| same, 8 directions (fast) | 6.57 · +6.54 | 8.52 · +8.42 |

**Discretisation costs a descent-side bias.** At 5 m the edge sum sits a median +1.83 points (median $\lvert$gap$\rvert$ 1.84<!--@c-a3.discretisation.fidelity-->) above its own route-level integral, because the grade-local refund and the zero floor bind only on descents.

**The pitch minimum is partly built in.** Of five pitches from 5 to 90 m, 30 m has the lowest error, but $\varepsilon_0$ was calibrated on 30 m descent cells. The flanks are what is informative: finer pitches over-charge because no deadband eats the jitter, coarser ones under-resolve relief.

**The valley toll is the deadband's graph-native part.** A per-valley kinetic-energy toll, $\min(D,\ H,\ h_{KE} - 2\tau_n)$ — $D$ a descent's drop, $H$ the following rise, $h_{KE} = v_f^2/2g$ (2.5–6.3 m at 25–40 km/h), $\tau_n$ the chain's noise floor — is computed at graph-build time and additive over a search. In place of $k_s$ it takes the deployed cost from 3.75% · +1.33 to 3.29% · −0.08, closer on 1,131 of 2,038 rides ($p < 10^{-4}$): a first look, not the registered test. The route-level F4 under B1 still beats every edge realisation in Table 5a.

**Map treatment dominates cost design, and the deployed cost on a raw global map is poor.** Smoothing the map beats any change to the cost function at every direction count. On raw FABDEM at 8 directions the deployed cost reads 53% error, all of it over-charge — lattice zigzags read pixel noise as climbing (path ascent 1.42× the polyline's). These runs omit the production $k_s$, but whether any deployed service evaluates raw FABDEM, and what $k_s$ recovers, should be checked now ([§6](#6), item 6).

**The proposed default is provisional.** The deployed cost on a σ = 30 m map at 16 directions, with bridges and tunnels decked, needs no engine change — but it was chosen by a contest scored on the population it is reported on.

**Nothing here tests routing.** Every figure scores ride energy on paths people actually rode. A router chooses among paths, and a shortest-path search seeks out whatever the cost under-charges — noisy micro-descents, the discontinuity at the 2% gate, lattice artefacts — so the chosen path's predicted energy is biased low against its true cost: the optimizer's curse [Smith & Winkler 2006]. A router needs a ranking property: between the same endpoints, does the cost order alternatives as measured energy, or a reference simulation on each alternative's own profile, orders them — and what does its choice cost against the best? [P3]'s planned divergence measurement should rest on that metric.

<a id="5"></a>

## 5. Scope limits that bound every result

- **Who.** Seven riders on road bicycles with power meters. The ≥ 20 km inclusion filter excludes short urban trips, so commuting and cargo delivery — the uses that motivate the work — lie outside the population. E-bikes, cargo bikes and recumbents are untested.
- **The meter.** Ground truth is the meter's own integral, and in a bench test of 54 power meters the mean deviation was −0.9 ± 3.2%, with 6 units beyond ±5% [Maier et al. 2017]. Under P0 the constants are inverted from the same meter, so its scale error is absorbed: a P0 figure is consistency with the meter, not with true mechanical work, and protocols with external constants inherit the meter's error directly. A hub-mounted meter measures after the drivetrain, whose losses are about 2% [Passfield et al. 2017], so $k_{\mathrm{eff}}$ = 0.98 double-counts them on hub-metered rides. P0 absorbs that too, but it biases the inverted masses by about 2% and passes straight into any protocol with external constants; the corpora's meter placements are unaudited.
- **Wind** is zero throughout; at 20 km/h a 10 km/h headwind more than doubles $\alpha_a$.
- **Scale.** $\tau$ and $c$ belong to 5 m-resampled recordings, $\varepsilon_0$ to 30 m descent cells.
- **Repeat routes**: 82% of held-out rides have a near-twin in training ([§4.1](#4.1)).

<a id="6"></a>

## 6. Open measurements

First, a correction rather than a measurement: [P1]'s held-out row and the gate's expected values must be re-baselined to the current chain, and the gate's tolerance tightened to printed precision ([§4.1](#4.1)). Items 1–4 of [Table 6](#tab6) need no new data and change what the series can claim; they should precede any submission. Item 5 makes [P2], the most self-contained draft, submittable first. Item 8 is the spine [P3] lacks.

<a id="tab6"></a>

**Table 6.** Owed measurements, in priority order. Items 1–9 need no new rides.

| # | measurement | settles |
|---:|------------------------------------------------------------|------------------------------------|
| 1 | BD as an arm on [P1]'s current split, beside B1 | which descent estimator the series validates |
| 2 | P1: rider-median $m$, $C_{rr}$, $C_dA$, $v_f$ (regime powers for the simulation) from the training half, route-grouped split | what a planner gets — the abstract's second number |
| 3 | equivalence test (TOST, ±1 point) of F3 against the simulation on the held-out half | parity as equivalence, not absence of evidence |
| 4 | per-rider $\varepsilon$ with intervals; rider-versus-region variance; leave-one-rider-out and route-grouped headline splits | whether $\varepsilon$ belongs to riders or to landscapes |
| 5 | [P2]: fix the re-gridding bug; re-base the anomaly and bridge results; barometer on the same 745 crops; re-base to B1; F4 at each chain's $c$ | the map recipe under the anchor (one re-walk) |
| 6 | each deployed service's raster, smoothing, direction count and $k_s$, scored as configured | whether a live router sits in the 53% regime |
| 7 | [P3]'s default re-selected on held-out rides | the edge default under [P1]'s discipline |
| 8 | a ranking metric on same-endpoint alternatives and an optimizer's-curse audit of chosen paths; then [P3]'s divergence measurement | fitness for routing (needs network routing) |
| 9 | meter placement per corpus from file metadata; $k_{\mathrm{eff}}$ by placement | a ≈ 2% bias in inverted masses and external-constant protocols |
| 10 | power-metered rides under 20 km | the commuting scope (new rides) |
| 11 | pre-registered blind prediction with a rider power model (P2) | route forecasting |

<a id="7"></a>

## 7. Relation to prior work

The power balance beneath the law is validated at the instantaneous scale [di Prampero et al. 1979; Martin et al. 1998], in road-cycling performance models [Olds et al. 1995] and against speed on real courses [Dahmen et al. 2011]; the series adds the route-level integral in closed form, compared with measured route energy.

The closed form's nearest relatives are in hill walking. Naismith's rule charges time per distance and per height climbed [Naismith 1892]; Langmuir's corrections add a grade-dependent descent term — a credit on gentle descents and a charge on steep ones [Langmuir 1984]; Tobler's hiking function makes walking speed a continuous function of grade, fastest on a slight downhill [Tobler 1993]; and the metabolic cost of walking is lowest near a −10% gradient and rises on steeper descents [Minetti et al. 2002]. $\varepsilon$ and $\varepsilon_d$ are the cycling-energy counterparts of that descent term, and eq. (2) is the physical reason the refund shrinks with steepness. Unlike Langmuir's, the cycling refund never becomes a charge: a rider who brakes forgoes credit rather than paying for the braking [P1 App. A.6].

Energy as an edge weight has precedents in cycling [Shirabe 2008; Hrnčíř et al. 2017; Cakir et al. 2026] and in electric-vehicle routing, where regenerative braking makes edge costs negative [Artmeier et al. 2010]. Eisner et al. [2011] cost an edge as a fixed amount plus the climb, or minus a fraction of the drop — exactly the law's shape, with their recuperation fraction in the place of $\varepsilon$ — and show that node elevation itself serves as the potential that keeps Dijkstra exact; [P3] need not re-derive it. [P1]'s novelty claim is therefore a claim about cycling: a refund fraction derived from the riding dynamics and validated against measured route energy, with these walking and vehicle costs as precedents. Path elongation and direction bias on raster lattices are classical problems of least-cost corridor analysis [Goodchild 1977; Huber & Church 1985; Antikainen 2013], reduced by any-angle search, which frees headings from the lattice directions [Daniel et al. 2010]; [P3]'s direction ladder adds that on noisy terrain the dominant lattice error is noise read as relief, not path length. Ascent inflation from elevation noise is diagnosed by Rapaport [2011], and its growth with DEM resolution measured by Sánchez et al. [2024].

<a id="8"></a>

## 8. Conclusions

Three things are established. Given each ride's own inputs, a closed form with two corrections — air resistance gated off climbs, elevation noise removed — accounts for the measured energy of 305 held-out rides to about 3.2% median error with negligible bias, and a forward simulation fed the same inputs does no better; this is a statement about the energy accounting, not a forecast. A map can replace the barometer at a cost of a fraction of a point, provided the sampled profile is smoothed and each elevation chain carries its own noise rate. And the law can be cut into edges: the discretisation bias is descent-side, a graph-native valley toll removes it, and treating the map matters more than changing the cost.

Three things are not yet established: what a planner without the ride's own power gets, whether the descent constant belongs to riders or to landscapes, and whether the edge cost ranks routes correctly. Each has a measurement, most on data already in hand. Until they are made, the strongest defensible sentence in the series is the first of this section, and its deployment case rests on items 1, 2 and 8 of [§6](#6).

## Data and code availability

Code, simulator, parsers, lab journal and gate battery are public at `github.com/pedalhidro/bicycling-energy-model` (stdlib-only Python, no build step). The gate battery, `src/harness/bootstrap_ci.py`, re-derives the anchored numbers from per-ride outputs; the sidecar `wp1-route-energy.meta.ttl` maps each to its gate section and registers the owed statistics of [§6](#6) as planned claims. Per-ride tracks and the independent riders' exports are private by design. D6 is the scikit-cycling `power_regression` deposit (Zenodo, doi:10.5281/zenodo.1202440, CC BY 4.0); its derived geometry is not published because the tracks begin at the riders' homes.

## AI-assistance declaration

This working paper is a machine-produced pre-draft body, assembled with LLM assistance (Anthropic Claude) from the three companion drafts and the lab journal under the author's direction; the human draft is written on top of it. All data collection, modelling decisions and final claims are the author's.

## References

- **[P1]** Lessa Bernardineli, D. *A Closed-Form Model for the Mechanical Energy of Cycling a Route, Evaluated Against 2,039 Power-Metered Rides.* Companion draft.
- **[P2]** Lessa Bernardineli, D. *A Recipe for Estimating Bicycling Route Energy at Planning Time, with Corrections for the Elevation Source.* Companion draft.
- **[P3]** Lessa Bernardineli, D. *From a Ride-Level Energy Law to an Edge Cost: Discretizing the Closed Form for Minimum-Energy Bicycle Routing.* Companion draft (partial).
- **[Antikainen 2013]** Antikainen, H. (2013). *Comparison of different strategies for determining raster-based least-cost paths with a minimum amount of distortion.* Transactions in GIS 17(1):96–108.
- **[Artmeier et al. 2010]** Artmeier, A., Haselmayr, J., Leucker, M. & Sachenbacher, M. (2010). *The shortest path problem revisited: optimal routing for electric vehicles.* KI 2010, LNCS 6359:309–316.
- **[Cakir et al. 2026]** Cakir, E. et al. (2026). *Physiological energy demand-based routing and accessibility for cycling.* Transp. Res. Interdiscip. Perspect. 35:101777.
- **[Dahmen et al. 2011]** Dahmen, T., Byshko, R., Saupe, D., Röder, M. & Mantler, S. (2011). *Validation of a model and a simulator for road cycling on real tracks.* Sports Engineering 14(2–4):95–110.
- **[di Prampero et al. 1979]** di Prampero, P. E., Cortili, G., Mognoni, P. & Saibene, F. (1979). *Equation of motion of a cyclist.* J. Appl. Physiol. 47(1):201–206.
- **[Daniel et al. 2010]** Daniel, K., Nash, A., Koenig, S. & Felner, A. (2010). *Theta\*: any-angle path planning on grids.* J. Artif. Intell. Res. 39:533–579.
- **[Eisner et al. 2011]** Eisner, J., Funke, S. & Storandt, S. (2011). *Optimal route planning for electric vehicles in large networks.* Proc. AAAI 2011:1108–1113.
- **[Goodchild 1977]** Goodchild, M. F. (1977). *An evaluation of lattice solutions to the problem of corridor location.* Environment and Planning A 9(7):727–738.
- **[Hrnčíř et al. 2017]** Hrnčíř, J., Žilecký, P., Song, Q. & Jakob, M. (2017). *Practical multicriteria urban bicycle routing.* IEEE Trans. Intell. Transp. Syst. 18(3):493–504.
- **[Huber & Church 1985]** Huber, D. L. & Church, R. L. (1985). *Transmission corridor location modeling.* J. Transportation Engineering 111(2):114–130.
- **[Langmuir 1984]** Langmuir, E. (1984). *Mountaincraft and Leadership.* Edinburgh: Scottish Sports Council. (Descent corrections as reproduced in secondary sources; page not checked against the original.)
- **[Maier et al. 2017]** Maier, T., Schmid, L., Müller, B., Steiner, T. & Wehrlin, J. P. (2017). *Accuracy of cycling power meters against a mathematical model of treadmill cycling.* Int. J. Sports Med. 38(6):456–461.
- **[Martin et al. 1998]** Martin, J. C., Milliken, D. L., Cobb, J. E., McFadden, K. L. & Coggan, A. R. (1998). *Validation of a mathematical model for road cycling power.* J. Appl. Biomech. 14(3):276–291.
- **[Minetti et al. 2002]** Minetti, A. E., Moia, C., Roi, G. S., Susta, D. & Ferretti, G. (2002). *Energy cost of walking and running at extreme uphill and downhill slopes.* J. Appl. Physiol. 93(3):1039–1046.
- **[Naismith 1892]** Naismith, W. W. (1892). *Cruach Ardran, Stobinian, and Ben More.* Scottish Mountaineering Club Journal 2(3):135–136.
- **[Olds et al. 1995]** Olds, T. S., Norton, K. I., Lowe, E. L., Olive, S., Reay, F. & Ly, S. (1995). *Modeling road-cycling performance.* J. Appl. Physiol. 78(4):1596–1611.
- **[Passfield et al. 2017]** Passfield, L., Hopker, J. G., Jobson, S., Friel, D. & Zabala, M. (2017). *Knowledge is power: issues of measuring training and performance in cycling.* J. Sports Sci. 35(14):1426–1434.
- **[Rapaport 2011]** Rapaport, D. C. (2011). *Evaluating cumulative ascent: mountain biking meets Mandelbrot.* Int. J. Mod. Phys. C 22(3):209–217.
- **[Sánchez et al. 2024]** Sánchez, R. et al. (2024). *Assessing the impact of DEM resolution on elevation gain estimations in trail running.* ICECET 2024.
- **[Shirabe 2008]** Shirabe, T. (2008). *Minimum work paths in elevated networks.* Networks 52(2):88–97.
- **[Smith & Winkler 2006]** Smith, J. E. & Winkler, R. L. (2006). *The optimizer's curse: skepticism and postdecision surprise in decision analysis.* Management Science 52(3):311–322.
- **[Tobler 1993]** Tobler, W. (1993). *Three presentations on geographical analysis and modeling: non-isotropic geographic modeling; speculations on the geometry of geography; global spatial analysis.* NCGIA Technical Report 93-1, University of California, Santa Barbara.
