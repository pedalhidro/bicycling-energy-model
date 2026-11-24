#!/usr/bin/env python3
"""Entry 77 — does a stop term earn a place in the edge cost?

REGISTERED 2026-11-24, before any run on ride data. 77 is the next free entry
number as this is written; the entry fixes it when it lands.

THE CRITICISM. A per-edge cost is additive and stateless, so it cannot carry
the kinetic energy a rider throws away at every stop and rebuilds from the
legs. The law has no such term. One full stop from the flat reference speed
costs (1/2) m v_f^2 / k_eff: 0.8 kJ for 75 kg at 17 km/h, the price of 74 m of
flat road.

WHERE THE STOPS GO TODAY. Entry 35 found them inside the flat rate: with the
drag area inverted at the ride's own measured flat speed, a stop-go ride
returns a "total-loss coefficient", not an aerodynamic one (D2's reads 0.62).
So under P0, where the constants are read off the scored ride, the ride's stops
are already paid for. Under the planning arm (Entry 76) the constants are the
RIDER's medians, which carry the rider's TYPICAL stop density. What a planner
then misses is the stops a route has in excess of what that rider usually
meets.

THE TERM. Count each ride's stops from its own speed record (below), and add

    E_stop = kappa * (N - nbar * x) * (1/2) m v_f^2 / k_eff

to F3, with N the ride's stop count, x its length, nbar the rider's median
stops per km over their TRAINING rides, m and v_f the planner's own (the arm
cache's), and kappa one fitted number. kappa = 1 means each excess stop costs
one full stop from v_f. The count comes from the ride, so this is an oracle for
what a router could know from junctions: if the true count does not help, a
count read off the graph will not either.

A STOP is an event on flat ground (grade over the last 50 m inside the flat
band the chain uses): having been above 4 m/s, the rider falls below 2 m/s, or
the recording pauses for more than 10 s. Flat ground only, on purpose: on a
descent gravity pays for the re-acceleration, and slowing into a climb is
momentum carried uphill (Entry 63's toll), not a stop.

THE RULES. Fold CV as in Entry 52: the same split, the same 20 folds, F3
fitted in-fold by the chain's own fit(), then (eps, kappa) refitted in-fold at
that fold's tau. The criterion is the chain's own parsimony rule: a form with
one more parameter is adopted only if it beats the simpler one by more than
one fold SE of the simpler one's CV.

  EARNED       on the planning cache (`pace`), the term lowers F3's fold CV
               over all rides by more than one fold SE.
  NOT EARNED   otherwise. A count of stops, priced at one reference stop each,
               has then not shown that it belongs in the router.
  CHECK        kappa, fitted on the whole training half, lies between 0.5 and
               2. Outside that band the count carries signal but not as one
               reference stop each, and the entry says which way.
  CONTROL      on the published cache (P0), the ABSOLUTE count
               kappa * N * (1/2) m v_f^2 / k_eff buys nothing: it does not lower
               the fold CV over all rides by more than one SE. If it does, the
               stops are not fully inside the flat rate at P0 and Entry 35's
               reading is incomplete.
  EXPECTATION  for the record: the term is earned on the urban rides with
               kappa above 1 (riders cruise faster between stops than their
               flat average), and the control holds.

The held-out half is scored ONCE for each of the two registered cells, with
the constants fitted on the whole training half. Diagnostics are fold CV only
and have no rule: the paired fold-by-fold difference with its own SE (more
sensitive than the rule: a term can be real and still too small to earn a
parameter); the same figures on the "urban" rides, the top third by stops per
km with the cut taken on the training half; the kinetic head each stop
actually destroyed, in excess of the rider's usual per km (an upper bound on
what a count could do); the absolute count on the planning cache; the excess
count on the published cache; and a stricter definition of a stop (above
3 m/s, then below 0.5 m/s).

WHY ALL RIDES AND NOT THE URBAN ONES. The term is an excess over the rider's
own usual density, so it speaks wherever a ride differs from that rider's
habit, in either direction: a rider of quiet roads crossing a city, or a city
rider on an open road. The top third by absolute density is mostly the habitual
rides of riders who always stop a lot, which is where the excess is small. A
positive control on simulated riders showed this before any real run: with a
stop cost planted, the term improved the fit over all rides and not on the
"urban" third. The urban figures are reported, and carry no rule.

CONTROLS, run on simulated riders before this was registered (seven riders,
168 rides from the repo's own forward simulation, each rider with a usual stop
density and each ride its own; the whole chain run on them, then this file):

  stops planted, quiet days   the rule fires: -2.55 SE, kappa 0.60, and the P0
                              control holds (+0.16 SE, kappa 0.00)
  the same stops dealt to     the rule does not fire: +0.69 SE, kappa -0.18
  the wrong rides
  stops planted, days as      -0.57 SE on 140 training rides: real, and too
  noisy as a real rider's     small to earn a parameter at that size

Two cautions the controls taught. The absolute count on the planning cache can
"gain" with the stops shuffled (-1.65 SE): it carries the rider's identity, so
it is a diagnostic there and never the rule. And the simulated riders' stops
cost more than a real rider's are likely to; the controls show the test can
see an effect and can refuse one, not how large the real one is.

NOT COVERED. Whether a graph can predict the count (junctions, signals); stops
on climbs and descents; and the routes, which are the riders' own.

Reads:   the published A-chain cache and Entry 76's `pace` cache
         (e52_aggregates.csv, e52_aggregates.p1pace.csv), and their
         e52_split CSVs for the drift check.
Writes:  data/results/e77_stops.csv  (per-ride stop features, one walk)
         data/results/e77_split.csv  (the table)
Run:     python3 src/harness/e77_stops.py     (E77_SMOKE=1 for a subset on the
         smoke caches; E77_REBUILD=1 to walk the corpora again). Run it with no
         arm flag set: it reads the arm's cache by name.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

SMOKE = bool(os.environ.get("E77_SMOKE"))
if SMOKE:                      # align e52's suffix logic before importing it
    os.environ["E52_SMOKE"] = "1"

from bicycling_energy_model.jsfmt import to_fixed  # noqa: E402

import e52_split as S  # noqa: E402
from e52_build import AERO, C_PUB, FALLBACK, GROUPS, TAU_GRID, e_form  # noqa: E402
from e44_scurve import corpus_rides  # noqa: E402
from perride_invert import CLIMB_THR, DESC_THR, KEFF, RESULTS  # noqa: E402
from skc_compare import boot_ci_strat, med_of, sign_p  # noqa: E402

V_HI, V_LO = 4.0, 2.0                  # m/s: armed above, a stop below
V_HI_STRICT, V_LO_STRICT = 3.0, 0.5    # the strict definition (diagnostic)
GAP_S = 10.0                           # a recording pause this long is a stop
PRE_S = 20.0                           # window for the speed held before a stop
RUN_M = 50.0                           # the grade is taken over this run
KAPPA_BOUNDS = (-2.0, 6.0)
KAPPA_BAND = (0.5, 2.0)                # the registered CHECK
SEED77 = 57                            # the held-out paired CI (56 is Entry 76's)
SUFF = ".SMOKE" if SMOKE else ""
STOPS_CSV = os.path.join(RESULTS, "e77_stops" + SUFF + ".csv")
# (label, the cache's arm suffix, the registered regressor on that cache)
CACHES = (("pace", ".p1pace", "exc"), ("P0", "", "abs"))
REGRESSORS = ("exc", "abs", "ke", "exc_full")


def cache_suffix(arm: str) -> str:
    """The suffix e52_build gives a cache: aero, fallback, arm, smoke."""
    return (("" if AERO == "reg" else "." + AERO)
            + ("" if FALLBACK == "rider" else "." + FALLBACK) + arm + SUFF)


# ------------------------------------------------------------ stage 1: stops

def stop_features(pts) -> dict:
    """Stops of one ride, from its speed record (the docstring's definition).
    `n_stop` and `n_full` count events; `ke_head` sums, over the n_stop events,
    the kinetic head destroyed, (v_before^2 - v_after^2)/2 in J/kg, with
    v_before the fastest the rider was in the PRE_S seconds before."""
    out = {"n_stop": 0, "n_full": 0, "ke_head": 0.0}
    armed = armed_strict = False
    win: deque = deque()               # (clock s, speed) over the last PRE_S
    clock = 0.0
    j = 0                              # the point RUN_M behind the current one
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        v = b.get("v")
        if v is None:
            continue
        dt = b.get("dt") or 0.0
        raw = (b["t"] - a["t"]) if (b.get("t") is not None
                                    and a.get("t") is not None) else dt
        paused = raw is not None and raw > GAP_S
        clock += dt
        while j < i - 1 and pts[j + 1]["x"] <= b["x"] - RUN_M:
            j += 1
        run = b["x"] - pts[j]["x"]
        grade = (b["alt"] - pts[j]["alt"]) / run if run > 0 else 0.0
        flat = DESC_THR < grade < CLIMB_THR
        if armed and (v <= V_LO or paused):
            if flat:
                v_pre = max((w for _, w in win), default=v)
                v_end = 0.0 if paused else v
                out["n_stop"] += 1
                out["ke_head"] += 0.5 * max(0.0, v_pre * v_pre - v_end * v_end)
            armed = False
        if armed_strict and (v <= V_LO_STRICT or paused):
            if flat:
                out["n_full"] += 1
            armed_strict = False
        if v >= V_HI:
            armed = True
        if v >= V_HI_STRICT:
            armed_strict = True
        win.append((clock, v))
        while win and win[0][0] < clock - PRE_S:
            win.popleft()
    return out


def build_stops(cache_rows) -> None:
    """Walk the corpora once. Labels replicate e52_build's counter, so the join
    with the caches is by construction (Entry 63's toll walk does the same)."""
    want = {r["ride"] for r in cache_rows}
    out_rows = []
    seen: dict[str, int] = {}
    for group, pts, _mass in corpus_rides():
        if group not in GROUPS:
            continue
        i = seen.get(group, 0)
        seen[group] = i + 1
        label = f"{group}#{i}"
        if label not in want:
            continue
        try:
            f = stop_features(pts)
        except Exception:
            continue
        out_rows.append({"group": group, "ride": label, **f})
    with open(STOPS_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["group", "ride", "n_stop", "n_full", "ke_head"])
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"  wrote {os.path.basename(STOPS_CSV)} ({len(out_rows)} rides)")


def load_stops() -> dict:
    with open(STOPS_CSV, encoding="utf-8") as fh:
        return {r["ride"]: {k: float(r[k]) for k in ("n_stop", "n_full", "ke_head")}
                for r in csv.DictReader(fh)}


# ------------------------------------------------ stage 2: the term's algebra

def attach(rows, stops) -> int:
    """Stop features onto cache rows. A ride the walk missed gets none and is
    counted aloud: its regressors are zero, so it is scored as plain F3 and the
    population stays the chain's."""
    missing = 0
    for r in rows:
        s = stops.get(r["ride"])
        r["has_stops"] = s is not None
        for k in ("n_stop", "n_full", "ke_head"):
            r[k] = s[k] if s else 0.0
        missing += 0 if s else 1
    return missing


def add_regressors(rows, train) -> dict:
    """The four regressors, in kJ at kappa = 1, from the cache's own mass and
    v_f (the planner's under `pace`, the ride's under P0). Rider densities are
    medians over TRAINING rides only. Returns them for the record."""
    dens = {}
    for g in GROUPS:
        sub = [r for r in train if r["group"] == g and r["has_stops"] and r["x_m"] > 0]
        dens[g] = {k: (med_of([r[k] / (r["x_m"] / 1000.0) for r in sub]) if sub else 0.0)
                   for k in ("n_stop", "n_full", "ke_head")}
    for r in rows:
        if not r["has_stops"]:
            r.update({"R_" + k: 0.0 for k in REGRESSORS})
            continue
        x_km = r["x_m"] / 1000.0
        vf = r["vf_kmh"] / 3.6
        unit = 0.5 * r["m_hat"] * vf * vf / KEFF / 1000.0      # one stop, kJ
        d = dens[r["group"]]
        r["R_abs"] = r["n_stop"] * unit
        r["R_exc"] = (r["n_stop"] - d["n_stop"] * x_km) * unit
        r["R_exc_full"] = (r["n_full"] - d["n_full"] * x_km) * unit
        r["R_ke"] = r["m_hat"] * (r["ke_head"] - d["ke_head"] * x_km) / KEFF / 1000.0
    return dens


def e_stop(r, eps, kappa, ti, key) -> float:
    return e_form(r, "F3", eps, C_PUB, ti) + kappa * r["R_" + key]


def loss_stop(rows, eps, kappa, ti, key) -> float:
    """The chain's loss with the term added. The population is the chain's
    fixed one for F3 at this tau, never filtered by the parameters: a ride the
    term drives non-positive scores infinity instead of vanishing."""
    tot, n = 0.0, 0
    for r in rows:
        if not S._usable(r, "F3", C_PUB, ti):
            continue
        e = e_stop(r, eps, kappa, ti, key)
        if not e > 0:
            return float("inf")
        tot += abs(math.log(e / r["emp"]))
        n += 1
    return tot / n if n else float("inf")


def fit_stop(rows, ti, key, eps0) -> tuple[float, float]:
    """(eps, kappa) at one tau, by alternating the chain's grid-then-refine
    search over each. Starts at (eps0, 0), F3's own optimum, and keeps the
    current point whenever a grid does not beat it, so the fitted loss is never
    above F3's on the same rides."""
    sub = [(e_form(r, "F3", 0.0, C_PUB, ti),
            e_form(r, "F3", 1.0, C_PUB, ti) - e_form(r, "F3", 0.0, C_PUB, ti),
            r["R_" + key], r["emp"])
           for r in rows if S._usable(r, "F3", C_PUB, ti)]
    if not sub:
        return eps0, 0.0

    def loss(e: float, k: float) -> float:
        tot = 0.0
        for a, b, rr, emp in sub:
            v = a + e * b + k * rr
            if not v > 0:
                return float("inf")
            tot += abs(math.log(v / emp))
        return tot / len(sub)

    def refine(f, lo, hi, cur):
        best = cur
        for _ in range(5):
            step = (hi - lo) / 100
            best = min([lo + i * step for i in range(101)] + [best], key=f)
            lo, hi = best - step, best + step
        return best

    eps, kap = eps0, 0.0
    for _ in range(3):
        kap = refine(lambda k: loss(eps, k), *KAPPA_BOUNDS, kap)
        eps = refine(lambda e: loss(e, kap), *S.EPS_BOUNDS, eps)
    return eps, kap


def mean_se(v: list[float]) -> tuple[float, float]:
    n = len(v)
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1)) if n > 1 else 0.0
    return m, sd / math.sqrt(n)


def run_cache(label, arm, registered, stops, table) -> None:
    suffix = cache_suffix(arm)
    rows = S.load(suffix)
    missing = attach(rows, stops)
    train, test = S.split(rows)
    dens = add_regressors(rows, train)
    print(f"\n=== cache {label} (e52_aggregates{suffix}.csv): train {len(train)} · "
          f"test {len(test)}" + (f" · {missing} rides missing from the stop walk "
                                 f"(scored as plain F3)" if missing else ""))

    # the urban cut: top third of stops per km, on the training half
    den = sorted(r["n_stop"] / (r["x_m"] / 1000.0) for r in train
                 if r["has_stops"] and r["x_m"] > 0)
    cut = den[min(len(den) - 1, int(math.ceil(2 * len(den) / 3)))] if den else float("inf")
    urban = lambda r: r["has_stops"] and r["x_m"] > 0 and r["n_stop"] / (r["x_m"] / 1000.0) >= cut
    q = lambda p: den[min(len(den) - 1, int(p * (len(den) - 1)))] if den else float("nan")
    print(f"  stops per km on the training half: median {to_fixed(q(.5), 2)}, "
          f"5th {to_fixed(q(.05), 2)}, 95th {to_fixed(q(.95), 2)}; urban rides are "
          f"those at or above {to_fixed(cut, 2)} per km "
          f"({sum(1 for r in train if urban(r))} of {len(train)} training rides, "
          f"{sum(1 for r in test if urban(r))} of {len(test)} held out)")
    print("  rider median stops per km (training): "
          + "  ".join(f"{g} {to_fixed(dens[g]['n_stop'], 2)}" for g in GROUPS))

    # fold CV: F3 by the chain's own fit, then the term at that fold's tau
    base_all, base_urb = [], []
    stop_all = {k: [] for k in REGRESSORS}
    stop_urb = {k: [] for k in REGRESSORS}
    for rep in range(S.N_REPEATS):
        for tr, va in S.folds(train, S.K_FOLDS, rep):
            e0, _c, ti = S.fit(tr, "F3")
            va_u = [r for r in va if urban(r)]
            base_all.append(S.cv_loss(va, "F3", e0, C_PUB, ti))
            base_urb.append(S.cv_loss(va_u, "F3", e0, C_PUB, ti))
            for k in REGRESSORS:
                e, kap = fit_stop(tr, ti, k, e0)
                stop_all[k].append(loss_stop(va, e, kap, ti, k))
                stop_urb[k].append(loss_stop(va_u, e, kap, ti, k))
    b_all, se_all = mean_se(base_all)
    b_urb, se_urb = mean_se(base_urb)

    # drift check: F3's fold CV here must be the chain's own on this cache
    want = None
    with open(os.path.join(RESULTS, "e52_split" + suffix + ".csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["form"] == "F3":
                want = float(r["cv"])
    ok = want is not None and abs(b_all - want) < 5e-7
    print(f"  drift check: F3 fold CV {b_all:.6f} against the chain's "
          f"{'missing' if want is None else format(want, '.6f')}   "
          f"{'GATE-OK' if ok else 'GATE-FAIL'}")
    if not ok and not SMOKE:
        raise SystemExit("F3's fold CV does not reproduce the chain's on this cache")

    e0, _c, ti = S.fit(train, "F3")
    print(f"\n  fold CV, mean of {len(base_all)} folds (lower is better); "
          f"F3 on the whole training half: eps {to_fixed(e0, 4)}, tau {TAU_GRID[ti]} m")
    print(f"    {'term':<22} {'all rides':>10} {'vs F3 (SE)':>11} {'paired diff ± SE':>20} "
          f"{'urban':>10} {'vs F3 (SE)':>11} {'kappa':>7} {'eps':>7}")
    print(f"    {'F3, no term':<22} {b_all:>10.5f} {'± ' + format(se_all, '.5f'):>11} {'':>20} "
          f"{b_urb:>10.5f} {'± ' + format(se_urb, '.5f'):>11}")
    names = {"exc": "excess count", "abs": "absolute count",
             "ke": "excess kinetic head", "exc_full": "excess, strict stops"}
    fits = {}
    for k in REGRESSORS:
        m_all, _ = mean_se(stop_all[k])
        m_urb, _ = mean_se(stop_urb[k])
        e, kap = fit_stop(train, ti, k, e0)
        fits[k] = (e, kap)
        d_all = (m_all - b_all) / se_all if se_all else float("nan")
        d_urb = (m_urb - b_urb) / se_urb if se_urb else float("nan")
        pd, pse = mean_se([s_ - b_ for s_, b_ in zip(stop_all[k], base_all)])
        tag = "  <- registered" if k == registered else ""
        print(f"    {names[k]:<22} {m_all:>10.5f} {d_all:>+11.2f} "
              f"{format(pd, '+.5f') + ' ± ' + format(pse, '.5f'):>20} {m_urb:>10.5f} "
              f"{d_urb:>+11.2f} {kap:>7.3f} {e:>7.4f}{tag}")
        table.append({"cache": label, "term": k,
                      "role": "registered" if k == registered else "diagnostic",
                      "cv_f3_all": b_all, "se_f3_all": se_all, "cv_term_all": m_all,
                      "paired_diff_all": pd, "paired_se_all": pse,
                      "cv_f3_urban": b_urb, "se_f3_urban": se_urb, "cv_term_urban": m_urb,
                      "delta_all_se": d_all, "delta_urban_se": d_urb,
                      "eps_f3": e0, "tau": TAU_GRID[ti], "eps": e, "kappa": kap,
                      "urban_cut_per_km": cut})

    # the registered cell: the rule, then the held-out half, once
    k = registered
    row = next(t for t in table if t["cache"] == label and t["term"] == k)
    e, kap = fits[k]
    if label == "pace":
        earned = row["delta_all_se"] < -1.0
        in_band = KAPPA_BAND[0] <= kap <= KAPPA_BAND[1]
        print(f"\n  RULE (pace, excess count): fold CV over all rides moves by "
              f"{row['delta_all_se']:+.2f} SE -> {'EARNED' if earned else 'NOT EARNED'}"
              f"   (urban rides, no rule: {row['delta_urban_se']:+.2f} SE)")
        print(f"  CHECK: kappa = {kap:.3f} is "
              f"{'inside' if in_band else 'OUTSIDE'} [{KAPPA_BAND[0]}, {KAPPA_BAND[1]}]")
        row["verdict"] = "EARNED" if earned else "NOT EARNED"
        row["kappa_in_band"] = int(in_band)
    else:
        holds = not row["delta_all_se"] < -1.0
        print(f"\n  CONTROL (P0, absolute count): fold CV over all rides moves by "
              f"{row['delta_all_se']:+.2f} SE -> the control "
              f"{'HOLDS' if holds else 'FAILS: stops are not fully inside the flat rate at P0'}")
        row["verdict"] = "CONTROL HOLDS" if holds else "CONTROL FAILS"

    print(f"\n  held-out half, scored once (n = {len(test)})")
    print(f"    {'estimator':<26} {'med|D%|':>6} {'[95% CI]':<19}  {'signed':>6} [95% CI]")
    f3 = lambda rs: S.pct(rs, "F3", e0, C_PUB, ti)
    tm = lambda rs: [100.0 * (e_stop(r, e, kap, ti, k) - r["emp"]) / r["emp"] for r in rs]
    r3 = S._scored(test, "F3, no term", f3)
    rt = S._scored(test, "F3 + " + names[k], tm)
    a3, at = [abs(v) for v in f3(test)], [abs(v) for v in tm(test)]
    diff = [b - a for a, b in zip(a3, at)]
    by_g = [[d for d, r in zip(diff, test) if r["group"] == g] for g in GROUPS]
    ci = boot_ci_strat([x for x in by_g if x], SEED77)
    better = sum(1 for d in diff if d < 0)
    worse = sum(1 for d in diff if d > 0)
    print(f"    per ride, with the term minus without, in |D%|: median "
          f"{to_fixed(med_of(diff), 2)} pp [{to_fixed(ci[0], 2)}, {to_fixed(ci[1], 2)}]; "
          f"closer with the term on {better} of {better + worse} "
          f"(sign p = {to_fixed(sign_p(better, worse), 4)})")
    ut = [i for i, r in enumerate(test) if urban(r)]
    if ut:
        print(f"    on the {len(ut)} urban held-out rides: "
              f"{to_fixed(med_of([a3[i] for i in ut]), 2)} without the term, "
              f"{to_fixed(med_of([at[i] for i in ut]), 2)} with it")
    row.update({"test_f3_med_abs": r3["med_abs"], "test_term_med_abs": rt["med_abs"],
                "test_f3_med_signed": r3["med_signed"], "test_term_med_signed": rt["med_signed"],
                "test_diff_med": med_of(diff), "test_closer": better, "test_further": worse,
                "test_urban_n": len(ut),
                "test_urban_f3": med_of([a3[i] for i in ut]) if ut else float("nan"),
                "test_urban_term": med_of([at[i] for i in ut]) if ut else float("nan")})


def main() -> None:
    print("Entry 77 — a stop term on F3, on the published cache and Entry 76's "
          "planning cache" + ("   [SMOKE]" if SMOKE else ""))
    base = S.load(cache_suffix(""))
    if os.path.exists(STOPS_CSV) and not os.environ.get("E77_REBUILD"):
        print(f"  reusing {os.path.basename(STOPS_CSV)} (E77_REBUILD=1 to walk again)")
    else:
        build_stops(base)
    stops = load_stops()
    n = sorted(s["n_stop"] for s in stops.values())
    if n:
        print(f"  stops per ride: median {n[len(n) // 2]:.0f}, "
              f"5th {n[int(.05 * (len(n) - 1))]:.0f}, 95th {n[int(.95 * (len(n) - 1))]:.0f} "
              f"({len(n)} rides walked of {len(base)} cached)")

    table: list[dict] = []
    for label, arm, registered in CACHES:
        run_cache(label, arm, registered, stops, table)

    cols = ["cache", "term", "role", "verdict", "kappa_in_band", "urban_cut_per_km",
            "cv_f3_all", "se_f3_all", "cv_term_all", "delta_all_se",
            "paired_diff_all", "paired_se_all",
            "cv_f3_urban", "se_f3_urban", "cv_term_urban", "delta_urban_se",
            "eps_f3", "tau", "eps", "kappa",
            "test_f3_med_abs", "test_term_med_abs", "test_f3_med_signed",
            "test_term_med_signed", "test_diff_med", "test_closer", "test_further",
            "test_urban_n", "test_urban_f3", "test_urban_term"]
    out = os.path.join(RESULTS, "e77_split" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, restval="")
        w.writeheader()
        for t in table:
            w.writerow({c: (("" if not math.isfinite(t[c]) else to_fixed(t[c], 6))
                            if isinstance(t.get(c), float) else t.get(c, ""))
                        for c in cols})
    print(f"\nwrote {os.path.basename(out)}")


if __name__ == "__main__":
    main()
