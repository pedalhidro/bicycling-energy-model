#!/usr/bin/env python3
"""Entry 76 — the air on the climbs, charged instead of dropped.

THE QUESTION. research/proofs/RouteEnergy.lean proves the closed form without
assuming anything about the air on climbs:

    E = a_r*x + a_a*x_flat + W_air,climbs/k + beta*(h+ - eps*h-) + dKE/k

F2, F3 and F4 are that law with the third term set to zero, and eps is fitted
AFTER it is dropped -- so eps absorbs the omission. This harness puts the term
back, refits, and reports what happens to the cross-validation loss and to eps.

THE TERM. K_v = (1/k) * sum over climb segments of rho*CdA/2 * v^2 * dx, on the
profile the form is evaluated on, with a segment a climb exactly when
`approximate` says so (slope >= 2%). Three speeds, each at the ride's own
climb-regime power and inverted constants (e52_build.climb_air):

    off   v = v_f                                   F1's charge, the ceiling
    vc    v = min(v_f, k*P/(R + W*s))               the engine's 'vc' mode
    ex    v solves v*(R + W*s + b*v^2) = k*P        the exact steady speed

On steady climbs the proof gives 0 <= ex <= vc <= off; the bracket is checked
here on every ride. The term is cached PER TAU: the deadband flattens the first
2*tau of every reversal, F3 already bills those segments at v_f, and a constant
computed on the raw classification would bill them twice. The raw-constant
reading runs as a labelled sensitivity row (`.raw`).

THE ARMS (label, base form, what is added to the base's aero component):

    F3+ex, F3+vc       K_ex(tau), K_vc(tau)      primary; the verdict is F3+ex
    F3+off             K_off(tau)                the ceiling in the F3 family
    F2+ex, F2+vc       K(0)                      the term without the filter
    F4+ex, F4+vc       K(0), outside k_m         the totals-only form
    F3+ex.raw, +vc.raw K(0) at every tau         sensitivity

NO SECOND COPY OF THE ALGEBRA. An arm is its base form evaluated on rows whose
aero component carries the term, so the fitting, the loss, AIC and the test
scoring are e52_split's own functions, called on those rows. The F3 family
alone goes through a precomputed search (`fit3`, `cv3`) because Entry 52's
would take about two hours over five arms. It performs the same floating-point
operations in the same order -- (roll + aero + climb + eps*recov1)/1000, the
same 5 x 201 refinement, the same first-minimum tie rule -- and is HELD to it:
it must reproduce e52_split's F3 cross-validation score, its SE and its
full-train (eps, tau) exactly, and on the two primary arms its full-train fit
must equal e52_split.fit on the transformed rows.

PROTOCOL. Entry 52's A-chain: the seed-48 split, repeated stratified 5-fold x 4
with every parameter refitted in-fold, loss mean |log(Ehat/E)|. The decision is
made on cross-validation. The held-out half has been scored before (paper 1,
section 3.1.4); it is scored here once, after the verdict is fixed -- `_DECIDED`
starts None and `score_arm` refuses to run without it.

A DIAGNOSTIC THE VERDICT DOES NOT READ (`cancellation`). A positive control on
synthetic rides -- a simulated rider who pays the air by construction -- still
had the arm LOSE, because the refund a ride earns and its climb-air share rise
and fall together, so dropping the term narrows the spread one flat eps has to
cover. The run measures that co-movement on the real training half, so that a
"charging hurts" verdict can be read for what it is.

GATES, every one of which aborts the run:
  1  cache drift   the .cair cache holds the canonical rides, in order, and
                   the canonical numbers (text; last-bit differences are
                   counted and reported, anything above 1e-9 relative aborts)
  2  build gates   the climb-air loop against the engine, and the exact
                   speed's root residual (e52_build.verify_climb_air)
  3  the bracket   0 <= K_ex <= K_vc <= K_off, every ride, every tau
  4  F2+off == F1  every ride
  5  chain drift   the F1-F4 rows are byte-identical to e52_split.csv; the fit
                   columns are compared BEFORE the test half is touched

It writes NO canonical file. Outputs carry the e52 arm suffix and `.SMOKE`:
  data/results/e52_aggregates.cair.csv   (built here when missing)
  data/results/e76_split.csv             e52_split.csv's columns; F1-F4 + arms
  data/results/e76_summary.csv           key,value: predictions, verdict, eps

Run:  python3 src/harness/e76_climbair.py
      E76_SMOKE=1    15 rides per rider, every output suffixed .SMOKE
      E76_REBUILD=1  force the corpus walk even when the .cair cache exists
"""

from __future__ import annotations

import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

SMOKE = bool(os.environ.get("E76_SMOKE") or os.environ.get("E52_SMOKE"))
if SMOKE:                       # align e52's suffix logic before importing it
    os.environ["E52_SMOKE"] = "1"
os.environ["E52_CLIMBAIR"] = "1"   # ... and select the suffixed cache

from bicycling_energy_model import is_finite  # noqa: E402
from bicycling_energy_model.jsfmt import to_fixed  # noqa: E402

import e52_build as build  # noqa: E402
from e52_build import (ARM, CAIR_COLS, C_PUB, TAU_GRID,  # noqa: E402
                       cache_path)
from e52_split import (EPS_BOUNDS, FORMS, K_FOLDS, N_REPEATS,  # noqa: E402
                       SPLIT_HEADER, aic, cross_validate, eps_optimum, fit,
                       folds, load, score_test, select, split, split_row,
                       twin_exposure)
from perride_invert import RESULTS  # noqa: E402
from skc_compare import med_of  # noqa: E402

if not build.CLIMBAIR:
    # e52_build reads its flag at import. Had something imported it before the
    # line above ran, a rebuild from here would write the CANONICAL cache.
    raise ImportError("e52_build was imported before E52_CLIMBAIR was set — "
                      "import e76_climbair first, or export the flag")

SUFF = ARM + (".SMOKE" if SMOKE else "")
NT = len(TAU_GRID)
KINDS = (("ex", "cax"), ("vc", "cav"), ("off", "cao"))
# (label, base form, cache column kind, raw-classified constant?)
ARMS = (("F3+ex", "F3", "cax", False), ("F3+vc", "F3", "cav", False),
        ("F3+off", "F3", "cao", False),
        ("F2+ex", "F2", "cax", False), ("F2+vc", "F2", "cav", False),
        ("F4+ex", "F4", "cax", False), ("F4+vc", "F4", "cav", False),
        ("F3+ex.raw", "F3", "cax", True), ("F3+vc.raw", "F3", "cav", True))
CHECKED = ("F3+ex", "F3+vc")    # fit3 cross-checked against e52_split.fit
# P1's registered magnitudes for the fitted eps (point, low, high), tau refitted
P1_MAG = {"F3+ex": (0.05, 0.02, 0.10), "F3+vc": (0.07, 0.03, 0.13),
          "F2+ex": (0.07, 0.04, 0.11), "F2+vc": (0.09, 0.06, 0.14)}

_DECIDED: dict | None = None    # set by decide(); score_arm refuses without it


def key_of(label: str) -> str:
    """'F3+ex.raw' -> 'f3_ex_raw', the summary-file spelling."""
    return label.lower().replace("+", "_").replace(".", "_")


# ---------------------------------------------------------- the cache gates

def cache_drift(path: str) -> str:
    """Gate 1. The flagged build recomputes every canonical column by the
    canonical code, so it must hold the canonical population and the canonical
    numbers. Same rides in the same order, or abort; any number that differs
    by more than 1e-9 relative, or abort -- the code or the corpus moved since
    that cache was written, and the arm would be scored on something else.

    Cells that differ only in their last bits are counted and reported, not
    fatal: an interpreter change alone does that (sum() over floats is
    compensated since Python 3.12, and the inversion uses it). The binding
    drift check is gate 5, the F1-F4 rows byte for byte."""
    canon = cache_path(False)
    if not os.path.exists(canon):
        print(f"\n  gate 1  cache drift: {os.path.basename(canon)} is not here "
              f"— SKIPPED, the run is UNANCHORED")
        return "SKIP"
    with open(canon, encoding="utf-8") as fa, open(path, encoding="utf-8") as fb:
        ra, rb = list(csv.reader(fa)), list(csv.reader(fb))
    n = len(ra[0])
    if rb[0][:n] != ra[0]:
        raise SystemExit("gate 1: the .cair header does not start with the "
                         "canonical columns — abort")
    ig, ir = ra[0].index("group"), ra[0].index("ride")
    if [(x[ig], x[ir]) for x in ra] != [(y[ig], y[ir]) for y in rb]:
        raise SystemExit(f"gate 1: the two caches do not hold the same rides in "
                         f"the same order ({len(ra) - 1} vs {len(rb) - 1}) — the "
                         f"corpus or the walk moved; refusing to fit an arm on it")
    bad, worst, where = 0, 0.0, ""
    for x, y in zip(ra[1:], rb[1:]):
        for j, (u, v) in enumerate(zip(x, y[:n])):
            if u == v:
                continue
            bad += 1
            try:
                fu, fv = float(u), float(v)
                rel = (0.0 if (fu != fu and fv != fv)
                       else abs(fu - fv) / max(abs(fu), abs(fv), 1e-300))
            except ValueError:
                rel = float("inf")
            if rel > worst:
                worst, where = rel, f"{x[ir]}.{ra[0][j]}"
    ok = worst <= 1e-9
    print(f"\n  gate 1  cache drift vs {os.path.basename(canon)}: same "
          f"{len(ra) - 1} rides; {bad} of {(len(ra) - 1) * n} canonical cells "
          f"differ as text"
          + (f", worst relative {worst:.2e} at {where}" if bad else "")
          + f"   {'GATE-OK' if ok else 'GATE-FAIL'}"
          + ("   (last bits only — see gate 5)" if ok and bad else ""))
    if not ok:
        raise SystemExit("gate 1: the suffixed cache does not carry the "
                         "canonical numbers — rebuild the canonical chain or "
                         "find what moved; refusing to fit an arm on it")
    return "OK" if not bad else "OK-LASTBITS"


def cache_gates(rows) -> None:
    """Gates 3 and 4: the proof's bracket, and F1 recovered from F2."""
    worst_b = worst_f = 0.0
    for r in rows:
        for i in range(NT):
            ex, vc, off = (r[f"f3t{i}_cax"], r[f"f3t{i}_cav"], r[f"f3t{i}_cao"])
            tol = 1e-9 * max(off, 1.0)
            worst_b = max(worst_b, -ex / max(off, 1.0), (ex - vc) / max(off, 1.0),
                          (vc - off) / max(off, 1.0))
            if ex < -tol or ex > vc + tol or vc > off + tol:
                raise SystemExit(f"gate 3: bracket violated on {r['ride']} at "
                                 f"tau {TAU_GRID[i]} — ex {ex}, vc {vc}, off {off}")
        worst_f = max(worst_f, abs(r["f2_aero"] + r["f3t0_cao"] - r["f1_aero"])
                      / max(abs(r["f1_aero"]), 1.0))
    print(f"  gate 3  bracket 0 <= K_ex <= K_vc <= K_off on {len(rows)} rides "
          f"x {NT} tau: worst overshoot {max(worst_b, 0.0):.3e}   GATE-OK")
    ok = worst_f < 1e-9
    print(f"  gate 4  F2 + K_off(0) vs F1, aero component: worst relative "
          f"{worst_f:.3e}   {'GATE-OK' if ok else 'GATE-FAIL'}")
    if not ok:
        raise SystemExit("gate 4: F2 with the v_f charge does not reproduce F1")


# ------------------------------------------------------------ the arm rows

def with_term(rows, base: str, kind: str, raw: bool) -> list[dict]:
    """The rows an arm is fitted on: the base form's aero component plus the
    term. For F3 the term joins every tau's component -- its own tau's, or the
    raw profile's under `raw`. F2 and F4 read f2_aero and get the raw term
    (tau = 0 is a no-op deadband, so f3t0 IS the raw profile). New dicts, the
    cached rows are never mutated."""
    out = []
    for r in rows:
        d = dict(r)
        if base == "F3":
            for i in range(NT):
                d[f"f3t{i}_aero"] = (r[f"f3t{i}_aero"]
                                     + r[f"f3t{0 if raw else i}_{kind}"])
        else:
            d["f2_aero"] = r["f2_aero"] + r[f"f3t0_{kind}"]
        out.append(d)
    return out


# ------------------------------- the F3 family's precomputed search (exact)

def pack3(rows) -> list[list]:
    """Per tau index, each row's (S, B, emp) with S = roll + aero + climb and
    B = recov1 -- or None where e52_split._usable would exclude the ride (a
    predicted energy that goes non-positive somewhere in the eps range; the
    population is fixed once, never per eps)."""
    packs = []
    for ti in range(NT):
        k = f"f3t{ti}"
        col = []
        for r in rows:
            s = r[k + "_roll"] + r[k + "_aero"] + r[k + "_climb"]
            b = r[k + "_recov1"]
            ok = ((s + EPS_BOUNDS[0] * b) / 1000 > 0
                  and (s + EPS_BOUNDS[1] * b) / 1000 > 0)
            col.append((s, b, r["emp"]) if ok else None)
        packs.append(col)
    return packs


def loss3(sub, eps: float) -> float:
    """e52_split.cv_loss on a packed subset: same operations, same order.

    The total is the BUILT-IN sum over a list, as it is there, and not a
    running `+=`: since Python 3.12 sum() compensates float addition, so the
    two differ in the last bits -- enough to move a grid argmin, and enough
    for the identity check in main() to fail, which is how this was found."""
    if not sub:
        return float("inf")
    v = []
    for s, b, emp in sub:
        e = (s + eps * b) / 1000
        v.append(abs(math.log(e / emp)) if e > 0 else float("inf"))
    return sum(v) / len(v)


def eps_opt3(sub) -> float:
    """e52_split.eps_optimum on a packed subset."""
    lo, hi = EPS_BOUNDS
    best = 0.2
    for _ in range(5):
        step = (hi - lo) / 200
        cand = [lo + i * step for i in range(201)]
        best = min(cand, key=lambda e: loss3(sub, e))
        lo, hi = best - step, best + step
    return best


def fit3(packs, idx) -> tuple[float, int]:
    """e52_split.fit for F3 on the rows `idx`: eps optimum at every tau, then
    the tau whose loss is least (first one on a tie, as min() does there)."""
    cands = []
    for ti in range(NT):
        sub = [packs[ti][j] for j in idx if packs[ti][j] is not None]
        e = eps_opt3(sub)
        cands.append((e, ti, loss3(sub, e)))
    e, ti, _ = min(cands, key=lambda q: q[2])
    return e, ti


def cv3(packs, groups) -> dict:
    """e52_split.cross_validate for F3: the same folds (they depend on the
    riders and the row order only), the same in-fold refit, the same mean and
    SE. Keeps the 20 fold scores for the paired diagnostic."""
    stubs = [{"group": g, "j": j} for j, g in enumerate(groups)]
    scores = []
    for rep in range(N_REPEATS):
        for tr, va in folds(stubs, K_FOLDS, rep):
            e, ti = fit3(packs, [s["j"] for s in tr])
            scores.append(loss3([packs[ti][s["j"]] for s in va
                                 if packs[ti][s["j"]] is not None], e))
    n = len(scores)
    mean = sum(scores) / n
    sd = math.sqrt(sum((s - mean) ** 2 for s in scores) / (n - 1)) if n > 1 else 0.0
    return {"cv": mean, "se": sd / math.sqrt(n), "n_scores": n, "scores": scores}


# ------------------------------------------------------------ chain helpers

def canon_split() -> list[str] | None:
    path = os.path.join(RESULTS, "e52_split" + SUFF + ".csv")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines(keepends=True)


def chain_drift_fit(cv, winner: str) -> str:
    """Gate 5, first half -- BEFORE the test half is scored. The columns that
    depend on the training half alone (form, npar, cv, cv_se, aic, eps, c, tau)
    must already equal e52_split.csv's."""
    canon = canon_split()
    name = "e52_split" + SUFF + ".csv"
    if canon is None:
        print(f"\n  gate 5  chain drift: {name} is not here — SKIPPED, the run "
              f"is UNANCHORED")
        return "SKIP"
    dummy = {"med_abs": 0.0, "med_signed": 0.0}
    for f, line in zip(FORMS, canon[1:]):
        mine = split_row(f, f, cv[f], dummy, f == winner).split(",")[:8]
        if mine != line.split(",")[:8]:
            raise SystemExit(f"gate 5: {f}'s fit columns do not reproduce {name}\n"
                             f"    here  {','.join(mine)}\n"
                             f"    there {','.join(line.split(',')[:8])}\n"
                             f"  the chain drifted — the test half stays unscored")
    print(f"\n  gate 5  fit columns of F1-F4 reproduce {name} to the digit   "
          f"GATE-OK   (test columns checked after A.8)")
    return "OK"


def decide(cv, arms, eps_geom_med: float) -> dict:
    """The registered predictions and the verdict, from the training half
    alone. Serialised before the test half is scored: `score_arm` checks."""
    global _DECIDED
    f3, ex, vc, off = cv["F3"], arms["F3+ex"], arms["F3+vc"], arms["F3+off"]
    d: dict = {}
    # P1 — eps rises, in bracket order, tau refitted and tau pinned
    rise = all(arms[lab]["eps"] > cv[base]["eps"]
               for lab, base, _k, _r in ARMS)
    order = f3["eps"] < ex["eps"] < vc["eps"] < off["eps"]
    pinned = f3["eps"] < ex["eps_pin"] < vc["eps_pin"] < off["eps_pin"]
    d["p1_direction"] = "HELD" if (rise and order and pinned) else "REFUTED"
    for lab, (_pt, lo, hi) in P1_MAG.items():
        de = arms[lab]["eps"] - cv[lab[:2]]["eps"]
        d["p1_mag_" + key_of(lab)] = "HELD" if lo <= de <= hi else "REFUTED"
    # P2 — the exact term costs nothing
    d["p2"] = "HELD" if ex["cv"] <= f3["cv"] + f3["se"] else "REFUTED"
    # P3 — the exact speed beats the bound, in both families
    d["p3"] = ("HELD" if (ex["cv"] < vc["cv"]
                          and arms["F2+ex"]["cv"] < arms["F2+vc"]["cv"])
               else "REFUTED")
    # P4 — the absorbed air closes less than half the gap to eps_geom
    gap = eps_geom_med - f3["eps"]
    d["gap"] = gap
    d["closure_ex"] = (ex["eps"] - f3["eps"]) / gap if gap else float("nan")
    d["closure_vc"] = (vc["eps"] - f3["eps"]) / gap if gap else float("nan")
    # (void when the premise fails: a fitted eps that is not below the
    # geometric one leaves no gap to close)
    d["p4"] = ("VOID" if not (is_finite(gap) and gap > 0)
               else "HELD" if d["closure_ex"] < 0.5 else "REFUTED")
    # P5 — tau within one grid step of F3's
    d["p5"] = "HELD" if abs(ex["ti"] - f3["ti"]) <= 1 else "REFUTED"
    # the verdict
    dcv = ex["cv"] - f3["cv"]
    d["dcv_in_se"] = dcv / f3["se"] if f3["se"] else float("nan")
    d["verdict"] = ("CHARGE" if dcv < -f3["se"]
                    else "KEEP-DROPPING" if dcv <= f3["se"]
                    else "KEEP-DROPPING-CHARGING-HURTS")
    _DECIDED = d
    return d


def score_arm(test_rows, base, a, label) -> dict:
    """A.8 for an arm -- e52_split.score_test on the arm's rows. Refuses to run
    before the verdict exists: the held-out half informs nothing here."""
    if _DECIDED is None:
        raise RuntimeError("A.8 reached before the verdict — gate violation")
    return score_test(test_rows, base, a["eps"], a["c"], label, a["ti"])


def share(rows, col: str) -> tuple[float, float, float]:
    """A term as a percentage of the ride's measured energy: median, 5th, 95th."""
    v = sorted(100.0 * r[col] / 1000.0 / r["emp"] for r in rows)
    q = lambda p: v[min(len(v) - 1, int(p * (len(v) - 1)))]
    return med_of(v), q(.05), q(.95)


def _ranks(v: list[float]) -> list[float]:
    """Average ranks (ties share the mean of their positions)."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    out = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def _iqr(v: list[float]) -> float:
    s = sorted(v)
    q = lambda p: s[min(len(s) - 1, int(p * (len(s) - 1)))]
    return q(.75) - q(.25)


def cancellation(rows, ti: int) -> dict:
    """Does the dropped air cancel part of what one flat eps cannot carry?

    Per ride, the eps that would zero its residual is (S - E_measured)/(beta*h-)
    with the air dropped and (S + K_ex - E_measured)/(beta*h-) with it charged;
    the two differ by k = K_ex/(beta*h-), the term in refund units. If k and
    the charged-air refund rise and fall TOGETHER across rides -- gentle
    terrain earns more refund and is climbed faster, so it pays more air --
    then dropping the term narrows the spread a single eps has to cover, and a
    flat-eps form fits better without a term the rider really pays. Rank
    statistics, because a ride with almost no descent has a wild implied eps.
    A diagnostic: the verdict does not read it."""
    k = f"f3t{ti}"
    e0, e1, kk = [], [], []
    for r in rows:
        s = r[k + "_roll"] + r[k + "_aero"] + r[k + "_climb"]
        b = -r[k + "_recov1"]                    # beta * h-, J
        if not b > 0:
            continue
        e0.append((s - r["emp"] * 1000) / b)
        e1.append((s + r[k + "_cax"] - r["emp"] * 1000) / b)
        kk.append(r[k + "_cax"] / b)
    ra, rb = _ranks(e1), _ranks(kk)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    rho = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / den if den else float("nan")
    return {"n": len(e0), "iqr_dropped": _iqr(e0), "iqr_charged": _iqr(e1),
            "k_med": med_of(kk), "rho": rho}


# -------------------------------------------------------------------- driver

def main() -> None:
    path = cache_path(True)
    print("Entry 76 — the air on the climbs, charged instead of dropped"
          + ("   [SMOKE]" if SMOKE else ""))
    if os.environ.get("E76_REBUILD") or not os.path.exists(path):
        print(f"  building {os.path.basename(path)} — Entry 52's walk plus the "
              f"climb-air columns (gate 2 runs inside it)\n")
        build.main()
        print()
    else:
        print(f"  reusing {os.path.basename(path)} (E76_REBUILD=1 to rewalk; "
              f"gate 2 ran when it was built)")
    rows = load(path)
    if not rows or any(c not in rows[0] for c in CAIR_COLS):
        raise SystemExit(f"{os.path.basename(path)} lacks the climb-air columns "
                         f"— rerun with E76_REBUILD=1")
    print(f"  {len(rows)} rides of D3-D6 under P_f,r")

    g1 = cache_drift(path)
    cache_gates(rows)

    train, test = split(rows)
    print(f"\n  A.1/A.2  train {len(train)} · test {len(test)} — seed 48, the "
          f"SAME split as Entry 52")
    hit, ntest = twin_exposure(train, test)
    print(f"           twin exposure {hit}/{ntest} ({100 * hit / ntest:.0f}%)")

    print("\n  the term as a share of measured energy, train half "
          "(median [5th, 95th] %)")
    for name, col in KINDS:
        m, lo, hi = share(train, f"f3t0_{col}")
        print(f"    K_{name:<3} on the raw profile     {m:>6.2f} [{lo:.2f}, {hi:.2f}]")

    # ---- A.4 / A.5 for F1-F4, through e52_split's own path
    print(f"\n  A.4  repeated stratified {K_FOLDS}-fold x {N_REPEATS}, parameters "
          f"refitted in-fold — F1-F4 through e52_split's own path")
    cv = cross_validate(train)
    w = select(train, cv)
    for f in FORMS:
        print(f"    {f:<10} CV {cv[f]['cv']:.5f} +/- {cv[f]['se']:.5f}   "
              f"eps {cv[f]['eps']:.4f}"
              + (f"   tau {cv[f]['tau']} m" if f == "F3" else "")
              + (f"   c {cv[f]['c']:.2f}" if f == "F4" else ""))
    g5 = chain_drift_fit(cv, w["form"])

    # ---- the precomputed F3 search must BE e52_split's
    groups = [r["group"] for r in train]
    all_idx = list(range(len(train)))
    base3 = cv3(pack3(train), groups)
    e3, t3 = fit3(pack3(train), all_idx)
    same = (base3["cv"] == cv["F3"]["cv"] and base3["se"] == cv["F3"]["se"]
            and e3 == cv["F3"]["eps"] and t3 == cv["F3"]["ti"])
    print(f"  check   precomputed F3 search vs e52_split: CV "
          f"{base3['cv']:.6f}/{cv['F3']['cv']:.6f}, eps "
          f"{e3:.6f}/{cv['F3']['eps']:.6f}, tau index {t3}/{cv['F3']['ti']} "
          f"— {'IDENTICAL   GATE-OK' if same else 'DIFFERENT   GATE-FAIL'}")
    if not same:
        raise SystemExit("the precomputed F3 search is not Entry 52's — abort")

    # ---- the arms
    print("\n  A.4  the arms (same folds, same in-fold refit)")
    arms: dict[str, dict] = {}
    arm_rows: dict[str, tuple] = {}
    for label, base, kind, raw in ARMS:
        tr = with_term(train, base, kind, raw)
        if base == "F3":
            packs = pack3(tr)
            a = cv3(packs, groups)
            a["eps"], a["ti"] = fit3(packs, all_idx)
            a["c"] = C_PUB
            if label in CHECKED and (a["eps"], C_PUB, a["ti"]) != fit(tr, "F3"):
                raise SystemExit(f"{label}: the precomputed fit differs from "
                                 f"e52_split.fit on the same rows — abort")
            a["eps_pin"] = eps_optimum(tr, "F3", C_PUB, cv["F3"]["ti"])
        else:
            a = cross_validate(tr, (base,))[base]
            a["eps"], a["c"], a["ti"] = fit(tr, base)
        a["tau"] = TAU_GRID[a["ti"]]
        a["aic"] = aic(tr, base, a["eps"], a["c"], a["ti"])
        arms[label] = a
        arm_rows[label] = (tr, base, kind, raw)
        b = cv[base]
        print(f"    {label:<10} CV {a['cv']:.5f} +/- {a['se']:.5f}   eps "
              f"{a['eps']:.4f} ({a['eps'] - b['eps']:+.4f})"
              + (f"   tau {a['tau']} m" if base == "F3" else "")
              + (f"   c {a['c']:.2f}" if base == "F4" else "")
              + f"   dCV {a['cv'] - b['cv']:+.5f} = "
                f"{(a['cv'] - b['cv']) / b['se']:+.2f} SE of {base}")

    # ---- diagnostics the verdict does not read
    f3 = cv["F3"]
    print(f"\n  eps with tau PINNED at F3's {f3['tau']} m (the absorption, "
          f"with the filter held still)")
    for label in ("F3+ex", "F3+vc", "F3+off"):
        print(f"    {label:<10} eps {arms[label]['eps_pin']:.4f} "
              f"({arms[label]['eps_pin'] - f3['eps']:+.4f} vs F3's {f3['eps']:.4f})")
    for name, col in KINDS:
        m, lo, hi = share(train, f"f3t{f3['ti']}_{col}")
        print(f"    K_{name:<3} at tau = {f3['tau']} m, % of measured energy "
              f"{m:>6.2f} [{lo:.2f}, {hi:.2f}]")
    print("\n  paired over the 20 folds, arm minus F3 (diagnostic)")
    for label in ("F3+ex", "F3+vc", "F3+off", "F3+ex.raw", "F3+vc.raw"):
        d = [x - y for x, y in zip(arms[label]["scores"], base3["scores"])]
        md = sum(d) / len(d)
        sd = math.sqrt(sum((x - md) ** 2 for x in d) / (len(d) - 1))
        arms[label].update({"fold_dmean": md, "fold_dse": sd / math.sqrt(len(d)),
                            "fold_wins": sum(1 for x in d if x < 0)})
        print(f"    {label:<10} mean {md:+.5f} +/- {sd / math.sqrt(len(d)):.5f}, "
              f"arm better in {arms[label]['fold_wins']}/{len(d)} folds")
    eg = [r["eps_geom"] for r in train if is_finite(r["eps_geom"])]
    eg_med = med_of(eg)
    print(f"\n  eps_geom on the train half: median {eg_med:.4f} over {len(eg)} "
          f"of {len(train)} rides")

    print("\n  does the dropped air cancel the spread of the refund? "
          "(train half, rank statistics)")
    canc = {}
    for tag, ti in (("raw", 0), ("f3tau", f3["ti"])):
        c = cancellation(train, ti)
        canc[tag] = c
        print(f"    tau = {TAU_GRID[ti]:>4} m  n {c['n']}: implied-eps IQR "
              f"{c['iqr_dropped']:.4f} air dropped, {c['iqr_charged']:.4f} air "
              f"charged; K_ex/(beta h-) median {c['k_med']:.4f}; Spearman "
              f"rho(refund, K/(beta h-)) = {c['rho']:+.3f}")

    # ---- the registered predictions and the verdict — training half only
    d = decide(cv, arms, eg_med)
    d["p6"] = ("HELD" if all(c["rho"] > 0 and c["iqr_charged"] > c["iqr_dropped"]
                             for c in canc.values()) else "REFUTED")
    ex, vc = arms["F3+ex"], arms["F3+vc"]
    print("\n  REGISTERED PREDICTIONS (Entry 76), read on cross-validation")
    print(f"    P1  eps rises, in bracket order, tau refitted and pinned"
          f"{'':<13} {d['p1_direction']}")
    for lab, (pt, lo, hi) in P1_MAG.items():
        de = arms[lab]["eps"] - cv[lab[:2]]["eps"]
        print(f"        {lab:<6} d eps {de:+.4f}   registered {pt:+.2f} "
              f"[{lo:+.2f}, {hi:+.2f}]{'':<14} {d['p1_mag_' + key_of(lab)]}")
    print(f"    P2  CV(F3+ex) {ex['cv']:.5f} <= CV(F3) + SE "
          f"{f3['cv'] + f3['se']:.5f}{'':<22} {d['p2']}")
    print(f"    P3  CV(F3+ex) {ex['cv']:.5f} < CV(F3+vc) {vc['cv']:.5f}; "
          f"F2+ex {arms['F2+ex']['cv']:.5f} < F2+vc {arms['F2+vc']['cv']:.5f}"
          f"   {d['p3']}")
    print(f"    P4  F3+ex closes {100 * d['closure_ex']:.0f}% of the gap "
          f"{f3['eps']:.4f} -> {eg_med:.4f} (< 50% registered)"
          f"{'':<5} {d['p4']}")
    print(f"    P5  tau {ex['tau']} m vs F3's {f3['tau']} m (within one grid "
          f"step){'':<18} {d['p5']}")
    print(f"    P6  (addendum) refund and K/(beta h-) rise together, and the "
          f"implied eps spreads wider with the air charged   {d['p6']}")
    print(f"\n  VERDICT (F3+ex against F3, F3's own SE): dCV = "
          f"{ex['cv'] - f3['cv']:+.5f} = {d['dcv_in_se']:+.2f} SE  ->  "
          f"{d['verdict']}")
    aic_note = "agrees" if (ex["aic"] < f3["aic"]) == (ex["cv"] < f3["cv"]) else "disagrees"
    print(f"    AIC, reported not binding: F3 {f3['aic']:.1f}, F3+ex "
          f"{ex['aic']:.1f}, F3+vc {vc['aic']:.1f} — {aic_note} with CV on "
          f"the sign")

    # ---- A.8: the held-out half, once, after the verdict
    print(f"\n  A.8  D_test scored ONCE, after the verdict (n = {len(test)}); "
          f"this half has been scored by earlier entries and decides nothing")
    print(f"    {'estimator':<26} {'med|D%|':>6} {'[95% CI]':<19}  "
          f"{'signed':>6} [95% CI]")
    res = {f: score_test(test, f, cv[f]["eps"], cv[f]["c"], f, cv[f]["ti"])
           for f in FORMS}
    for label, (_tr, base, kind, raw) in arm_rows.items():
        res[label] = score_arm(with_term(test, base, kind, raw), base,
                               arms[label], label)

    # ---- gate 5, second half: the full rows, byte for byte
    mine = [SPLIT_HEADER] + [split_row(f, f, cv[f], res[f], f == w["form"])
                             for f in FORMS]
    canon = canon_split()
    if canon is not None:
        ok = mine == canon[:len(mine)] and len(canon) == len(mine)
        print(f"\n  gate 5  F1-F4 rows vs e52_split{SUFF}.csv: "
              f"{'BYTE-IDENTICAL   GATE-OK' if ok else 'DIFFERENT   GATE-FAIL'}")
        if not ok:
            for a_, b_ in zip(mine, canon):
                if a_ != b_:
                    print(f"    here  {a_.rstrip()}\n    there {b_.rstrip()}")
            raise SystemExit("gate 5: the F1-F4 rows drifted — nothing written")

    out = os.path.join(RESULTS, "e76_split" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8") as fh:
        fh.writelines(mine)
        for label, (_tr, base, _kind, _raw) in arm_rows.items():
            fh.write(split_row(label, base, arms[label], res[label], False))
    summ = os.path.join(RESULTS, "e76_summary" + SUFF + ".csv")
    with open(summ, "w", encoding="utf-8") as fh:
        fh.write("key,value\n")
        fh.write(f"n_rides,{len(rows)}\nn_train,{len(train)}\nn_test,{len(test)}\n")
        fh.write(f"gate_cache_drift,{g1}\ngate_chain_drift,{g5}\n")
        for f in FORMS:
            fh.write(f"{f.lower()}_cv,{cv[f]['cv']:.6f}\n")
            fh.write(f"{f.lower()}_cv_se,{cv[f]['se']:.6f}\n")
            fh.write(f"{f.lower()}_eps,{to_fixed(cv[f]['eps'], 4)}\n")
        fh.write(f"f3_tau,{f3['tau']}\n")
        fh.write(f"eps_geom_train_med,{to_fixed(eg_med, 4)}\n")
        fh.write(f"eps_geom_train_n,{len(eg)}\n")
        for label, (_tr, base, _kind, _raw) in arm_rows.items():
            a, k, b = arms[label], key_of(label), cv[base]
            fh.write(f"{k}_cv,{a['cv']:.6f}\n{k}_cv_se,{a['se']:.6f}\n")
            fh.write(f"{k}_eps,{to_fixed(a['eps'], 4)}\n")
            fh.write(f"{k}_d_eps,{to_fixed(a['eps'] - b['eps'], 4)}\n")
            fh.write(f"{k}_d_cv,{a['cv'] - b['cv']:.6f}\n")
            fh.write(f"{k}_d_cv_in_se,{to_fixed((a['cv'] - b['cv']) / b['se'], 2)}\n")
            fh.write(f"{k}_aic,{a['aic']:.3f}\n")
            if base == "F3":
                fh.write(f"{k}_tau,{a['tau']}\n")
                fh.write(f"{k}_fold_dmean,{a['fold_dmean']:.6f}\n")
                fh.write(f"{k}_fold_dse,{a['fold_dse']:.6f}\n")
                fh.write(f"{k}_fold_wins,{a['fold_wins']}\n")
                if "eps_pin" in a:
                    fh.write(f"{k}_eps_pinned,{to_fixed(a['eps_pin'], 4)}\n")
            if base == "F4":
                fh.write(f"{k}_c,{to_fixed(a['c'], 4)}\n")
            fh.write(f"{k}_test_med_abs,{to_fixed(res[label]['med_abs'], 4)}\n")
            fh.write(f"{k}_test_med_signed,{to_fixed(res[label]['med_signed'], 4)}\n")
        for name, col in KINDS:
            for tag, i in (("raw", 0), ("f3tau", f3["ti"])):
                m, lo, hi = share(train, f"f3t{i}_{col}")
                fh.write(f"share_{name}_{tag}_med,{to_fixed(m, 2)}\n")
                fh.write(f"share_{name}_{tag}_p05,{to_fixed(lo, 2)}\n")
                fh.write(f"share_{name}_{tag}_p95,{to_fixed(hi, 2)}\n")
        for tag, c in canc.items():
            fh.write(f"cancel_{tag}_n,{c['n']}\n")
            fh.write(f"cancel_{tag}_iqr_dropped,{to_fixed(c['iqr_dropped'], 4)}\n")
            fh.write(f"cancel_{tag}_iqr_charged,{to_fixed(c['iqr_charged'], 4)}\n")
            fh.write(f"cancel_{tag}_k_med,{to_fixed(c['k_med'], 4)}\n")
            fh.write(f"cancel_{tag}_rho,{to_fixed(c['rho'], 3)}\n")
        fh.write(f"gap_eps_geom_minus_f3,{to_fixed(d['gap'], 4)}\n")
        fh.write(f"closure_ex,{to_fixed(d['closure_ex'], 4)}\n")
        fh.write(f"closure_vc,{to_fixed(d['closure_vc'], 4)}\n")
        for k in sorted(k for k in d if k.startswith("p")):
            fh.write(f"{k},{d[k]}\n")
        fh.write(f"verdict_d_cv_in_se,{to_fixed(d['dcv_in_se'], 2)}\n")
        fh.write(f"verdict,{d['verdict']}\n")
    print(f"\nwrote {os.path.basename(out)} and {os.path.basename(summ)}"
          + ("   [SMOKE — not a result]" if SMOKE else "")
          + ("   [UNANCHORED: a canonical file was missing, see the gates]"
             if "SKIP" in (g1, g5) else ""))


if __name__ == "__main__":
    main()
