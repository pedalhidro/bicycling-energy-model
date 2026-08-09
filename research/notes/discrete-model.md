# The discrete model family — how F1–F5, v2Edge and the valley patch are computed on a quantized path

This note is the algorithmic companion to Entry 73 (`src/harness/e73_gridpath.py`)
and paper 3 §2–3: what exactly gets computed when the model family is evaluated
on a **discrete routing path** instead of the ride's own profile. The physics
*derivations* live elsewhere — `original_notes.md` for the closed form and its
(α, β, ε), `epsilon-origin.md` for how the F1–F5 ladder falls out of the
canonical dynamics. Here the models are treated as **algorithms over a path
profile**: inputs, loops, outputs.

The single design rule: **every model consumes the same path profile and the
same per-ride physics**, so any difference between two model columns is the
model, and any difference between two configs of one model is the
discretisation. Constants are never literals — each is read at runtime from the
CSV of the harness that fitted it (values quoted below are the published ones
as of Entry 73).

## 0. The input: a path profile

A configuration (chain × directions n × portals) turns one ride into a path
profile — two parallel arrays:

- `x[i]` — cumulative **path** chainage in metres. For n = 1 this is the
  polyline's own arc length; for n > 1 it is the sum of lattice-move lengths,
  so it carries the metrication inflation (`len_ratio` ≈ 1.27 at n = 4,
  ≈ 1.05 at n = 8 on a 5 m lattice). Long moves (max(|Δr|, |Δc|) > 1)
  contribute `subN = 2·max(|Δr|,|Δc|)` sub-segments of length L/subN each —
  the profile-integration rule the deployed engine uses (`energy-worker.js
  longEdgeCost`); costing a long move from its endpoint Δh alone flattens the
  relief it crosses and flips the error sign (Simujaules research note §5.3).
- `h[i]` — elevation at each path point: bilinear raster samples for DEM
  chains (after `valid_fill`'s validity band + linear gap fill), the ride's
  barometer for the `own` chains. σ-chains apply the mask-normalized 1-D
  Gaussian **along the path** (`gauss1d_x`, trapezoidal measure — a ramp
  stays a ramp on the non-uniform sub-point spacing). The portal arm then
  replaces heights inside each OSM span with a straight deck between the
  profile's own values at the span-boundary chainages (`apply_deck_x`).

Every segment quantity below is `dx = x[i] − x[i−1]`, `dh = h[i] − h[i−1]`,
`slope = dh/dx`.

## 1. Shared per-ride quantities

From the paper-1 A-chain cache (`e52_aggregates.csv`): the per-ride inverted
physics `m̂, Ĉrr, ĈdA`; frozen `ρ = 1.13`, `k_eff = 0.98`, wind 0,
`G = 9.7864`. From the ride's own power stream: regime powers (`P_flat`,
`P_climb`) and the flat-equilibrium speed `v_f = flatEqSpeed(P_flat)`.

Derived coefficients (J/m unless noted):

```
β      = m·G / k_eff                    # gravity cost per metre climbed
aRoll  = m·G·Crr / k_eff                # rolling cost per metre
aAero  = ½·ρ·CdA·v_f² / k_eff           # flat-speed aero cost per metre
α      = aRoll + aAero
```

`approx_components(profile)` walks the segments once and returns the shared
aggregates (this is the applet's `approximate` with `climbAeroMode = 'zero'`):

```
X      = Σ dx
h₊     = Σ max(0, dh)
h₋     = Σ max(0, −dh)
roll   = aRoll · X
aero   = Σ (aAero·dx  if slope < climbThr else 0)     # aero gated OFF climbs
```

with `climbThr = 0.02` (2%). All energies below are E/1000 → kJ; every column
in the harness is reported as signed Δ% vs the ride's measured ∫P·dt.

## 2. v2Edge — the deployed per-edge cost (the O(1)-local realisation)

Reference implementation `regime_compare.py::r1d_v2_edge` (returns kJ);
mirrors: applet, Simujaules `energy-worker.js`/Rust. Per segment, in one pass:

```
if dh ≥ 0:                                   # climb or flat
    aero = aAero·dx  if dh < climbThr·dx else 0
    e = aRoll·dx + aero + β·dh
else:                                        # descent — grade-local ε
    s    = |dh| / dx
    ε(s) = clamp01( min(1, (α/β)/s) − ε₀ )   # ε₀ = 0.13, the coasting deficit
    e = aRoll·dx + aAero·dx − ε(s)·β·|dh|
    e = max(0, e)                            # dead clamp (provably unreachable)
E_v2 = Σ e
```

Every term depends only on the segment itself — this is the cost a Dijkstra
edge can carry. No deadband, no route-level clamp: elevation noise hits every
edge with no cancellation, which is why v2Edge's error explodes on unsmoothed
chains and why the deployed app σ-smooths the raster at load.

## 2b. The eF family — flat-ε per-edge realisations (paper 3's model axis)

Article 1's recommendation is a **flat ε**, so paper 3's model axis is the eF
family (Entry 73 registration v2): each paper-1 form realised per-edge with
its own published flat ε, made Dijkstra-safe by the per-edge `max(0, ·)`
clamp. With identical constants, **eF# − F# is exactly the clamped-edge
mass** — the energy a non-negative edge cost must refuse on steep descents —
so the joint per-ride F#/eF# comparison is an exact decomposition of the
localisation cost.

```
per segment:
  climb (dh ≥ 0):  e = aRoll·dx + aero + β·max(0, dh − c·dx)
                   aero = aAero·dx  (eF1: always; eF2/eF4: only if dh < climbThr·dx)
  descent:         ndh' = max(0, |dh| − c·dx)
                   e = max(0, aRoll·dx + aAero·dx − ε#·β·ndh')
```

- **eF1**: aero ungated, ε₁, c = 0 — per-edge F1.
- **eF2**: aero gated off climbs, ε₂, c = 0 — per-edge F2 ("v2Edge-F2");
  on a σ-treated map this is the deployable realisation of **F3**.
- **eF4**: eF2 + the per-edge noise deduction at ε₄ and the chain's
  **measured c pin** — c(τ = 2) per chain × region, the median of
  (h₊ − h₊(τ=2))/km over the chain's own n = 1 profiles (paper 2 eq. L3,
  the measured-pin doctrine; the fitted (ε₄, c) bundle is knowingly broken
  and disclosed, cross-checked against e71's CRATE rows).

The correspondence paper 3 traces (each paper-1 model → a deployable
treatment):

| paper 1 | paper 3 realisation |
|---|---|
| F1 | eF1 · raw map |
| F2 | eF2 · raw map |
| F3 | eF2 · σ-treated map |
| F4 | eF4 (measured c pin) · raw map |
| F5 | **out of scope for paper 3** (journal keeps its columns) |

The deployed v2Edge (grade-local ε, §2) stays as the status-quo reference
column: eF2 vs v2Edge is the flat-vs-geometric ε contest at edge grain,
extending Entry 51/72's flat-beats-dynamic line.

**The ε contest's verdict (Entry 74):** on σ-treated maps the deployed
grade-local ε wins every cell — treated profiles live in the shallow 1–3%
descent band, which only ε_geo credits near its coasting limit — while on
raw chains the ordering inverts and the flat ε₂ wins, because noise
manufactures steep micro-descents a grade-local policy refuses to credit.
Paper 3's default is therefore the deployed cost unchanged, on a
σ30-treated map at n = 16, portals on.

## 3. F1 — the bare closed form

`E₁ = roll + aAero·X + β·h₊ − ε₁·β·h₋`, with the **ungated** aero (flat-speed
drag charged on every metre, climbs included). ε₁ = 0.6830
(`e52_split.csv`). One number per ride from the aggregates — no filtering.

## 4. F2 — climb-gated aero

`E₂ = roll + aero + β·h₊ − ε₂·β·h₋` — identical to F1 except the aero term is
the gated sum (no aero charged on segments at slope ≥ 2%, the quasi-steady
climb-speed approximation). ε₂ = 0.4621.

## 5. F3 — the deadband form (paper 1's selected model)

Apply the backlash filter to the elevation array first:

```
h̃ = deadband(h, τ)      # y follows h only when it escapes the ±τ band:
                        #   h[i] > y+τ → y = h[i]−τ ;  h[i] < y−τ → y = h[i]+τ
```

with the published τ = 6 m, then re-run the component walk on {x, h̃}:

`E₃ = roll + aero(h̃) + β·h₊(h̃) − ε₃·β·h₋(h̃)`, ε₃ = 0.2939. Note `roll` keeps
the raw X (the deadband changes heights, not distance) and the aero gate reads
the *filtered* slopes. The deadband is **not** O(1)-local — h̃[i] depends on
the whole history of the path — so F3 is computable on a known path but cannot
be a Dijkstra edge cost. On noisy chains this term does almost all the work
(FABDEM at n = 8: F3 7.0% vs v2Edge 53.0%).

## 6. F4 — the climb-attenuation form (paper 1's planner recommendation)

No filtering; instead the whole gravity term is attenuated by a route-level
factor built from the ascent-noise rate c (m of phantom climb per km):

```
k  = max(0, 1 − c·(X/1000)/h₊)          (k = 1 when h₊ = 0)
E₄ = roll + aero + k·(β·h₊ − ε₄·β·h₋)
```

(ε₄, c) = (0.4094, 1.1040) — a **bundle**, fitted jointly and never mixed
with a c measured elsewhere (Entry 72's F4-all-measured arm over-corrected to
−3.8% by pairing ε_geom with article 2's c). `k` needs X and h₊ of the whole
path — route-level, not per-edge.

## 7. F5 — the KE-buffer valley toll (F5f as scored here)

The physics: a descent into a climb lets the rider carry kinetic energy
through the valley floor; the recoverable height is capped by the speed the
rider is willing to reach. Algorithm (`e63_f5_kebuffer.ride_tolls`, one copy):

1. Filter the profile with the **noise floor** `h̃ = deadband(h, τ_n)`,
   τ_n = 2 m (the registered F5f arm; per E68–E69 the floor is telemetry —
   pinned per corpus by measured drift — not a tuned constant).
2. Enumerate alternating monotone swings of h̃ (`swing_list`; turn points at
   the last sample moving in the old direction). Every descent-swing followed
   by a climb-swing is a **valley**: depth D, following rise H, grades
   s_d = D/run_d and s_u = H/run_u.
3. Per valley, the buffer height:

   ```
   v_t = √( max(0, m·G·(s_d − Crr)/sec_d) / (½ρ·CdA) )   # coasting terminal
   v_c = k_eff·P_climb / (m·G·(s_u + Crr)/sec_u)          # quasi-steady climb
   v_e = min(v_b, max(v_t, v_f))                          # entry speed; v_b = ∞ here
   buf = max(0, (v_e² − min(v_c, v_e)²) / (2G) − 2τ_n)
   ```

4. The ride's toll `T = Σ min(D, H, buf)` over its valleys — metres of climb
   the KE buffer genuinely pays for.
5. `E₅f = roll + aero(h̃) + β·(h₊(h̃) − T) − ε₅·β·(h₋(h̃) − T)`,
   ε₅ = 0.3632 (`e63_split.E63_TAUN2p0.csv`).

The toll is per-valley — computable on a known path (and, on a graph, at
descent→climb nodes), but not per-edge. The wider family: F5 (v_b fitted),
F5f (v_b frozen at ∞, scored here), F5m (v_b measured per ride), F5p (floor
pinned by measured drift, ε the only fitted parameter — Entry 69). e73
scores F5f at the calibration-chain floor; its loss to F3 on DEM chains at
edge grain is the floor-must-match-the-chain doctrine (E68/E71) showing up
again, not a failure of the mechanism.

## 8. The valley patch (Entry 72's teaser arm)

The toll grafted onto the *unfiltered* closed form, with the geometric ε:

`E_patch = roll + aero + β·(h₊ − T₀) − ε_geom·β·(h₋ − T₀)`,

where T₀ is the toll at floor τ_n = 0, v_b = ∞, and ε_geom is the
geometry-only estimator (drop-weighted coasting limit over 30 m cells minus
ε₀ = 0.13) computed **on the same path profile**. No fitted constants at all —
the fully-measured corner of the family.

## 9. The route-level estimate (the "estimated energy" comparator)

Per chain, the reference every config's v2Edge is also scored against:
**F4 at its published (ε, c) on that chain's n = 1 profile** — paper 1's
planner recommendation applied to the un-quantized polyline. The `_v2e`
column is `100·(E_v2(config) − E_ref)/E_ref`: the discretisation cost with
the terrain-source cost divided out.

## 10. Locality — which model can a router actually carry?

| model | needs | locality |
|---|---|---|
| v2Edge | segment (dx, dh) | **O(1) per edge** — deployable in Dijkstra |
| F1, F2 | path aggregates (X, h₊, h₋, gated aero) | additive per edge — deployable |
| F3 | deadband-filtered heights | path-history — **not** per-edge |
| F4 | k(X, h₊) route clamp | route-level — post-hoc scaling only |
| F5f | valley enumeration + toll | per-valley (graph-node at descent→climb) |
| patch | toll + ε_geom(path) | per-valley + path-level ε |

This column is paper 3's central tension: the accuracy ordering at edge grain
(F3 < F5f < patch < v2Edge on every DEM chain) is the *reverse* of the
deployability ordering.

## Constants and their producing CSVs

| constant | value (published) | read from |
|---|---|---|
| ε₁, ε₂, ε₃ (+τ), ε₄ (+c) | 0.6830 · 0.4621 · 0.2939 (τ=6) · 0.4094 (c=1.1040) | `e52_split.csv` |
| ε₅ (F5f), τ_n | 0.3632 · 2.0 | `e63_split.E63_TAUN2p0.csv` (the arm IS the suffix) |
| ε₀, climbThr | 0.13 · 0.02 | derivation constants (`original_notes.md`) |
| per-ride m̂/Ĉrr/ĈdA, emp | — | `e52_aggregates.csv` |

All ε were fitted at **route grain** on paper 1's population and applied
unchanged at edge grain — deliberately: Entry 73 measures what discretisation
costs the published models, not what refitted models could recover.

## Code pointers

- `src/harness/e73_gridpath.py::score_profile` — every formula above, in the
  order of this note.
- `src/bicycling_energy_model/engines.py` — `approx_components`, `deadband`,
  `eps_geom`, `flat_eq_speed`.
- `src/harness/regime_compare.py::r1d_v2_edge` — v2Edge (kJ), the deployed
  mirror set's Python reference.
- `src/harness/e63_f5_kebuffer.py::ride_tolls` — the toll (one algebra copy;
  callers set the module floor `TAU_N` per call).
