#!/usr/bin/env python3
"""Entry 52, stage 1 — the aggregate cache the A-chain runs on.

Walks D3-D6 ONCE, inverts the per-ride physics (A.3, which by design runs
before the split), and stores enough per ride to evaluate F1-F4 for ANY
(eps, c) by arithmetic alone. That is what makes A.4's repeated k-fold with
per-fold refitting affordable: without it every fold re-parses ~2,000 tracks.

WHY IT IS EXACT, not an approximation. `approximate` is linear in eps -- the
deficit enters only through recov = eps * recov(1) -- so two evaluations pin
the whole family:

    E_i(eps) = E_i(0) + eps * (E_i(1) - E_i(0))        i = 1, 2, 3

F4 carries a second parameter. It is built from F2's components as

    E_4(eps, c) = roll + aero + km(c) * (climb + eps * recov1)
    km(c)       = max(0, 1 - c * x_km / hplus)          published c = 3

which is linear in eps at fixed c and affine in km, so caching the four
components plus (x, hplus) pins that family too. Both facts are verified
against the real engine by `verify()` below rather than assumed.

D1/D2 are absent on purpose: matching on measured kJ puts 87% of D2 and 43%
of D1 inside D5, so they are re-processings of the same rider's rides, not
independent corpora (Entry 52's registration).

Output: data/results/e52_aggregates.csv
Run:    python3 src/harness/e52_build.py            (E52_SMOKE=1 for a subset)

E52_CLIMBAIR=1 (Entry 76) also caches the air work on climb segments -- the
term F2-F4 set to zero -- under three speeds and per tau, and writes
e52_aggregates.cair.csv, never the canonical cache. Every canonical column is
computed by the same code on the same path, so the suffixed cache must carry
the canonical rides and numbers; e76_climbair.py checks that before it fits.
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

from bicycling_energy_model import (approximate, build_profile, canonical,
                                    deadband, empirical_kj,
                                    extract_regime_powers, is_finite,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import G, eps_geom, flat_eq_speed
from bicycling_energy_model.regime import measured_flat_speed
from bicycling_energy_model.jsfmt import to_fixed

from perride_invert import (CLIMB_THR, DESC_THR, ENGINE_DX, KEFF, RESULTS, RHO,
                            TAU_SMOOTH, VMAX, VSTART, find_segments,
                            invert_physics, seg_integrals)
from e44_scurve import corpus_rides

SMOKE = bool(os.environ.get("E52_SMOKE"))
# Entry 55: which aero estimator feeds the physics. "reg" is the DEFAULT since
# Entry 55 -- the regime-consistent CdA, derived at the MEASURED flat speed so
# it closes the v_f gap by construction and needs no qualifying segment; it
# lowers both error and bias and drops the CdA fallback rate from 27% to 3%.
# "seg" is invert_physics's CdA from flat SEGMENTS, what Entries 52/54 used;
# retained as the sensitivity arm because the pair is the evidence for Entry
# 55's tau and F4 observations.
AERO = os.environ.get("E52_AERO", "reg")
# Entry 57: where a per-ride inversion fails, fall back to that RIDER's median
# over their training rides rather than to a global prior -- so every constant
# originates in the rider's own telemetry and no ride has to be dropped.
# "prior" restores the old behaviour as the sensitivity arm.
FALLBACK = os.environ.get("E52_FALLBACK", "rider")
# Entry 76: also cache the air work on climbs, the term F2-F4 set to zero. An
# experimental arm, so it is a flag and a suffixed cache: with the flag unset
# nothing below changes and the canonical file is written exactly as before.
CLIMBAIR = bool(os.environ.get("E52_CLIMBAIR"))
# the sensitivity-arm suffix every e52 output carries (aero, then fallback)
ARM = (("" if AERO == "reg" else "." + AERO)
       + ("" if FALLBACK == "rider" else "." + FALLBACK))


def cache_path(climbair: bool = CLIMBAIR) -> str:
    """Where this build writes: the canonical cache, or its `.cair` sibling."""
    return os.path.join(RESULTS, "e52_aggregates" + ARM
                        + (".cair" if climbair else "")
                        + (".SMOKE" if SMOKE else "") + ".csv")


def _rider_fallbacks() -> dict:
    path = os.path.join(RESULTS, "e52_rider_fallback.csv")
    if FALLBACK != "rider" or not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[r["group"]] = {k: float(r[k]) for k in ("m_hat", "crr_hat", "cda_hat")
                               if r.get(k)}
    return out


RIDER_FB = _rider_fallbacks()
CDA_RANGE = (0.10, 1.00)
CHECK: list[float] = []   # build-time cache-vs-engine deviations
CANON_FAIL: list[str] = []   # F_base failures, counted rather than swallowed
CAIR_CHECK: list[float] = []  # Entry 76: climb-air loop vs engine, one per ride
CAIR_RESID: list[float] = []  # Entry 76: worst root residual of the exact speed
C_PUB = 3.0                      # F4's published climb-fraction constant
# tau grid for F3's deadband. Entry 52's findings showed tau was frozen at the
# historical 2 m -- selected in Entry 5 on data overlapping D3-D6, so fitted
# OUTSIDE the chain on rides now in the test half. Caching a grid lets A.4 refit
# it per fold like every other parameter. tau = 0 is a no-op deadband, so
# F3(tau=0) must reproduce F2 exactly -- an internal check, not an assumption.
# Refined for Entry 56: carries the +/-10% and +/-25% neighbours of the
# plausible optima (2 m under the segment aero, 6 m under the regime one) so a
# loss-inflation figure is exact rather than interpolated across a coarse grid.
TAU_GRID = (0.0, 0.5, 1.0, 1.5, 1.8, 2.0, 2.2, 2.5, 3.0, 4.0, 4.5, 5.4,
            6.0, 6.6, 7.5, 8.0, 12.0)
TAU_PUB_I = TAU_GRID.index(2.0)
GROUPS = ("D3", "D4", "D5", "D6-user_1", "D6-user_2", "D6-user_3", "D6-user_5")
ANCHOR_KEY = {"D3": "ppaz", "D4": "jaam", "D5": "danlessa"}

COLS = (["group", "ride", "date", "emp",
         "m_hat", "m_src", "crr_hat", "crr_src", "cda_hat", "cda_src", "wind_ms"]
        + [f"{t}_{k}" for t in ("f1", "f2")
           for k in ("roll", "aero", "climb", "recov1")]
        + [f"f3t{i}_{k}" for i in range(len(TAU_GRID))
           for k in ("roll", "aero", "climb", "recov1")]
        + ["x_m", "hplus", "hminus", "vf_kmh", "canon_kj"])
# Entry 76's extra columns, appended AFTER the canonical ones so the leading
# fields of a .cair row are the canonical row. Per tau index: the air work on
# that profile's climb segments (J at the pedals, like every other component)
# charged at v_f (`cao`), at the engine's 'vc' speed (`cav`) and at the exact
# steady climbing speed (`cax`). Then the climb-regime power the two speeds
# were solved at, and the geometry-only eps the deployed cost aggregates to.
CAIR_COLS = ([f"f3t{i}_{k}" for i in range(len(TAU_GRID))
              for k in ("cao", "cav", "cax")]
             + ["p_climb", "eps_geom"])


# ------------------------------------------------- Entry 76: the air on climbs

def steady_climb_speed(target: float, fres: float, b: float, w: float,
                       vf: float) -> float:
    """The EXACT steady speed on a climb, capped at v_f: the root of

        v * (fres + b * rel * |rel|) = target,        rel = v + w

    where target = keff * P_climb, fres = Crr*mg*cos + mg*sin and
    b = rho*CdA/2 -- the equation of motion with dv/ds = 0. `approximate`'s
    'vc' mode leaves the air out of the bracket, so it over-states the speed
    (research/proofs/RouteEnergy.lean, `steady_climb_speed_le`); this keeps it.

    Bisection, stdlib only, 60 halvings like engines.flat_eq_speed, on [0, v_f]:
    the closed form never bills a climb above the flat reference speed, so v_f
    is both the cap and the bracket. The root is unique for w >= 0, and wind is
    identically zero on this chain (see one_ride). It lives in the harness on
    purpose: an engine change would have to land in the applet as well."""
    rel = vf + w
    if (fres + b * rel * abs(rel)) * vf <= target:
        return vf                      # the cap binds: power to spare at v_f
    lo, hi = 0.0, vf
    for _ in range(60):
        v = 0.5 * (lo + hi)
        rel = v + w
        if (fres + b * rel * abs(rel)) * v < target:
            lo = v
        else:
            hi = v
    return 0.5 * (lo + hi)


def climb_air(pr, p: dict, vf: float, p_climb: float,
              memo: dict) -> tuple[float, float, float, float]:
    """Air work on the climb segments of `pr`, in J at the pedals, under three
    speeds: (off, vc, exact, worst root residual).

    A segment is a climb exactly when `approximate` says so -- slope >=
    CLIMB_THR on the profile it is handed -- so on a deadbanded profile these
    are the segments F3 itself zeroes the air on, not the raw road's. `off`
    bills them at v_f (F1's charge), `vc` at min(v_f, keff*P/(R + W*s)) as the
    engine's 'vc' mode does, `exact` at steady_climb_speed. The first two are
    re-derived here only so the engine can check this loop (one_ride does);
    the third is the one the engine does not have.

    `memo` maps a slope to its two per-metre charges. It is per RIDE (the
    constants are), created by the caller and keyed on the slope itself --
    never on an id(). A deadband moves a tracked stretch by a constant, so
    its slopes recur bit for bit across the tau grid and are solved once
    (about nine lookups in ten are reuses on a synthetic ride)."""
    mg = p["m"] * G
    w = p["wind"]
    b = 0.5 * p["rho"] * p["CdA"]
    keff = p["keff"]
    target = keff * p_climb
    a_off = b * (vf + w) * abs(vf + w) / keff
    xs, hs = pr["x"], pr["h"]
    off = vc_sum = ex_sum = resid = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        slope = (hs[i] - hs[i - 1]) / dx
        if slope < CLIMB_THR:
            continue
        off += a_off * dx
        got = memo.get(slope)
        if got is None:
            if p_climb > 0:
                sec = math.sqrt(1 + slope * slope)
                fres = p["Crr"] * mg * (1 / sec) + mg * (slope / sec)
                vc = min(vf, target / fres)
                vx = steady_climb_speed(target, fres, b, w, vf)
                rel = vx + w
                r = (abs((fres + b * rel * abs(rel)) * vx - target) / target
                     if vx < vf else 0.0)
            else:                      # the engine's convention: no power, v = 0
                vc = vx = r = 0.0
            got = (b * (vc + w) * abs(vc + w) / keff,
                   b * (vx + w) * abs(vx + w) / keff, r)
            memo[slope] = got
        vc_sum += got[0] * dx
        ex_sum += got[1] * dx
        if got[2] > resid:
            resid = got[2]
    return off, vc_sum, ex_sum, resid


def one_ride(pts, label, group, m_logged) -> dict | None:
    """Everything Entry 52 needs from one ride. Mirrors e47's one_ride setup so
    the two entries share a population by construction.

    WIND IS ZERO for every ride, and that is a property of the iterator rather
    than a choice: corpus_rides() carries no date or file path, because the
    weather fetch would key on centroids derived from third-party riders' home
    addresses. It applies uniformly to all forms, so it cannot bias the A.4
    comparison -- but it does sit inside the absolute error A.8 reports, and the
    paper says so rather than quietly assuming still air.
    """
    emp = empirical_kj(pts)
    if not (is_finite(emp) and emp > 0):
        return None
    phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof = resample_profile(phys, ENGINE_DX)
    if prof["x"][-1] - prof["x"][0] < 3000:
        return None

    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    if not (is_finite(flat) and flat > 0):
        return None
    p_climb = rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat

    wind = 0.0                      # see the docstring: a property of the iterator

    # --- A.3: the per-ride inversion, before the split, as data preparation
    climbs_raw, flats_raw = find_segments(prof)
    wb_climbs = [s for s in (seg_integrals(pts, c, wind) for c in climbs_raw) if s and s["ok"]]
    wb_flats = [s for s in (seg_integrals(pts, f, wind) for f in flats_raw) if s and s["ok"]]
    inv = invert_physics(prof, wb_climbs, wb_flats, ANCHOR_KEY.get(group), m_logged)
    if inv is None:
        return None
    # Entry 57: swap any global prior for this rider's own median. Applied
    # BEFORE the energies are computed, so the substituted constant propagates
    # through v_f and every component rather than being patched on afterwards.
    _fb = RIDER_FB.get(group, {})
    for _v, _s in (("m_hat", "m_src"), ("crr_hat", "crr_src"), ("cda_hat", "cda_src")):
        if inv.get(_s) == "fallback" and _v in _fb:
            inv[_v], inv[_s] = _fb[_v], "rider"

    cda, cda_src = inv["cda_hat"], inv.get("cda_src", "")
    if AERO == "reg":
        # CdA_reg = (keff*P_flat/v_meas - Crr*m*g) / (rho/2 * v_rel^2), the
        # e35_residual arm-B estimator. Falls back to the segment value rather
        # than to the prior, so this arm is never WORSE informed than "seg".
        v_meas = measured_flat_speed(pts)
        if v_meas and v_meas > 2.0 and flat > 20:
            v_rel = v_meas + wind
            den = 0.5 * RHO * v_rel * abs(v_rel)
            if den > 0:
                c = (KEFF * flat / v_meas - inv["crr_hat"] * inv["m_hat"] * G) / den
                if CDA_RANGE[0] <= c <= CDA_RANGE[1]:
                    cda, cda_src = c, "regime"
    p = {"m": inv["m_hat"], "Crr": inv["crr_hat"], "CdA": cda,
         "rho": RHO, "keff": KEFF, "wind": wind, "vmax": VMAX, "vstart": VSTART}
    pw = {"climb": p_climb, "flat": flat,
          "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
          "climbThr": CLIMB_THR, "descThr": DESC_THR}
    vf = flat_eq_speed(flat, p)
    if not (is_finite(vf) and vf > 0):
        return None
    opt = lambda mode: {"climbAeroMode": mode, "climbThr": CLIMB_THR,
                        "descThr": DESC_THR, "climbPower": p_climb}

    row = {"group": group, "ride": label, "date": "", "emp": emp,
           "m_hat": inv["m_hat"], "m_src": inv.get("m_src", ""),
           "crr_hat": inv["crr_hat"], "crr_src": inv.get("crr_src", ""),
           "cda_hat": cda, "cda_src": cda_src,
           "wind_ms": wind, "vf_kmh": vf * 3.6}

    # --- the two-point cache: eps = 0 and eps = 1 pin every form
    forms = [("f1", prof, "off"), ("f2", prof, "zero")]
    for i, tau in enumerate(TAU_GRID):
        forms.append((f"f3t{i}",
                      {"x": prof["x"], "h": deadband(prof["h"], tau)}, "zero"))
    for tag, pr, mode in forms:
        a0 = approximate(pr, p, vf, 0.0, opt(mode))
        a1 = approximate(pr, p, vf, 1.0, opt(mode))
        # Components, not just the E0/E1 pair: the decomposition invariant
        # roll + aero + climb + recov == E makes these exactly equivalent, and
        # storing them is what lets A.7 perturb a term for EVERY form. Caching
        # only E0/E1 silently gave F1-F3 a zero elasticity, since the
        # perturbation had nothing to act on.
        row[f"{tag}_roll"], row[f"{tag}_aero"] = a0["roll"], a0["aero"]
        row[f"{tag}_climb"] = a0["climb"]
        row[f"{tag}_recov1"] = a1["recov"]      # recov at eps = 1
        if tag == "f2":
            row["hplus"], row["hminus"] = a0["hplus"], a0["hminus"]
    row["x_m"] = prof["x"][-1] - prof["x"][0]

    # --- Entry 76: the air on the climbs, the term the `zero` forms drop.
    # Per tau, because the deadband moves which segments count as climbs. The
    # loop is checked against the engine on EVERY ride and every tau: its 'vc'
    # sum against approximate('vc') minus the cached 'zero' aero, and its v_f
    # sum on the raw profile against F1's aero minus F2's.
    if CLIMBAIR:
        try:
            memo: dict = {}
            worst = resid = 0.0
            for tag, pr, _mode in forms[2:]:        # the f3t{i} profiles
                off, vc, ex, res_i = climb_air(pr, p, vf, p_climb, memo)
                row[tag + "_cao"], row[tag + "_cav"], row[tag + "_cax"] = off, vc, ex
                a_vc = approximate(pr, p, vf, 0.0, opt("vc"))["aero"]
                worst = max(worst, abs(vc - (a_vc - row[tag + "_aero"]))
                            / max(abs(a_vc), 1.0))
                resid = max(resid, res_i)
            worst = max(worst,
                        abs(row["f3t0_cao"] - (row["f1_aero"] - row["f2_aero"]))
                        / max(abs(row["f1_aero"]), 1.0))
            CAIR_CHECK.append(worst)
            CAIR_RESID.append(resid)
            row["p_climb"] = p_climb
            eg = eps_geom(prof, p, vf)
            row["eps_geom"] = eg if is_finite(eg) else float("nan")
        except Exception as exc:
            # main() swallows a ride's Exception and drops the ride. A failure
            # HERE must not do that: it would shrink the arm's population below
            # the canonical one without a word. SystemExit passes through.
            raise SystemExit(f"climb-air block failed on {label}: {exc!r}")

    # --- non-circular check: the cached two-point interpolation against a FRESH
    # engine call at an eps neither endpoint used, plus F4 against the exact
    # expression perride_invert.py publishes. Compares to the engine, not to
    # e_form, so it can actually fail.
    if len(CHECK) < 300:
        worst = 0.0
        for tag, pr, mode in forms:
            for eps in (0.2, 0.37, 0.85):
                want = approximate(pr, p, vf, eps, opt(mode))["E"]
                got = (row[tag + "_roll"] + row[tag + "_aero"]
                       + row[tag + "_climb"] + eps * row[tag + "_recov1"])
                if want:
                    worst = max(worst, abs(got - want) / abs(want))
        for eps in (0.2, 0.37):
            a2 = approximate(prof, p, vf, eps, opt("zero"))
            km = (max(0, 1 - C_PUB * (prof["x"][-1] / 1000) / a2["hplus"])
                  if a2["hplus"] > 0 else 1)
            want = a2["roll"] + a2["aero"] + km * (a2["climb"] + a2["recov"])
            got = e_form(row, "F4", eps) * 1000
            if want:
                worst = max(worst, abs(got - want) / abs(want))
        CHECK.append(worst)

    # F_base, the comparator. A bare `except` here silently produced nan on all
    # 2,039 rides and left P3 unanswerable, so the failure is counted and
    # surfaced instead of swallowed.
    try:
        row["canon_kj"] = canonical(prof, pw, p)["legE"] / 1000
    except Exception as exc:
        CANON_FAIL.append(repr(exc))
        row["canon_kj"] = float("nan")
    return row


# --------------------------------------------------------------- form algebra
# The single definition of F1-F4 in terms of the cache. Everything downstream
# (CV, selection, sensitivity, test) calls THESE, so a form cannot drift
# between stages.

def e_form(r: dict, form: str, eps: float, c: float = C_PUB,
           ti: int = TAU_PUB_I) -> float:
    """Energy in kJ for one ride under one form at (eps, c, tau-index)."""
    if form in ("F1", "F2", "F3"):
        k = {"F1": "f1", "F2": "f2", "F3": f"f3t{ti}"}[form]
        return (r[k + "_roll"] + r[k + "_aero"] + r[k + "_climb"]
                + eps * r[k + "_recov1"]) / 1000
    if form == "F4":
        km = 1.0 - c * (r["x_m"] / 1000.0) / r["hplus"] if r["hplus"] > 0 else 1.0
        km = km if km > 0 else 0.0
        return (r["f2_roll"] + r["f2_aero"]
                + km * (r["f2_climb"] + eps * r["f2_recov1"])) / 1000
    raise ValueError(form)


FORMS = ("F1", "F2", "F3", "F4")
NPAR = {"F1": 1, "F2": 1, "F3": 2, "F4": 2}   # eps; F3 adds tau, F4 adds c


def verify() -> bool:
    """Report the build-time engine comparison. Non-circular: every deviation in
    CHECK came from comparing the cache against a fresh approximate() call."""
    if not CHECK:
        print("\n  cache-vs-engine: NO RIDES CHECKED — gate cannot pass")
        return False
    worst = max(CHECK)
    ok = worst < 1e-9
    print(f"\n  cache-vs-engine on {len(CHECK)} rides "
          f"(two-point interpolation + F4 algebra vs fresh engine calls)")
    print(f"    worst relative deviation: {worst:.3e}   "
          f"{'GATE-OK' if ok else 'GATE-FAIL'}")
    return ok


def verify_climb_air() -> bool:
    """Entry 76's build-time gates. The loop that produced the climb-air
    columns is compared with the engine on every ride (its 'vc' and v_f sums
    are quantities `approximate` computes independently), and every exact
    speed it solved is put back into the equation it is the root of."""
    if not CAIR_CHECK:
        print("\n  climb-air: NO RIDES CHECKED — gate cannot pass")
        return False
    worst, resid = max(CAIR_CHECK), max(CAIR_RESID)
    ok1, ok2 = worst < 1e-9, resid < 1e-9
    print(f"\n  climb-air loop vs engine on {len(CAIR_CHECK)} rides x "
          f"{len(TAU_GRID)} tau ('vc' sum vs approximate('vc'); v_f sum vs F1 - F2)")
    print(f"    worst relative deviation: {worst:.3e}   "
          f"{'GATE-OK' if ok1 else 'GATE-FAIL'}")
    print(f"    exact steady speed, worst root residual |v(R + Ws + bv^2) - kP|/kP: "
          f"{resid:.3e}   {'GATE-OK' if ok2 else 'GATE-FAIL'}")
    return ok1 and ok2


def main() -> None:
    print("Entry 52 stage 1 — building the aggregate cache for D3-D6"
          + ("   [E52_CLIMBAIR: + the air on climbs, Entry 76]" if CLIMBAIR else ""))
    rows: list[dict] = []
    seen: dict[str, int] = {}
    for group, pts, mass in corpus_rides():
        if group not in GROUPS:          # drops D1/D2: they are inside D5
            continue
        i = seen.get(group, 0)
        seen[group] = i + 1
        if SMOKE and i >= 15:
            continue
        try:
            r = one_ride(pts, f"{group}#{i}", group, mass)
        except Exception:
            r = None
        if r:
            rows.append(r)
    for g in GROUPS:
        n = sum(1 for r in rows if r["group"] == g)
        print(f"  {g:<12} kept {n:>5} of {seen.get(g, 0)}")
    print(f"\n  {len(rows)} rides cached of {sum(seen.values())} seen")

    ok = verify()
    if CANON_FAIL:
        from collections import Counter
        print(f"\n  F_base (canonical) failed on {len(CANON_FAIL)} rides:")
        for msg, n in Counter(CANON_FAIL).most_common(3):
            print(f"    {n:>5}x  {msg[:96]}")

    if CLIMBAIR:
        ok = verify_climb_air() and ok

    out = cache_path()
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS + (CAIR_COLS if CLIMBAIR else []),
                           extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nwrote {os.path.basename(out)}")
    if not ok:
        raise SystemExit("cache does not reproduce the engine — refusing to ship it")


if __name__ == "__main__":
    main()
