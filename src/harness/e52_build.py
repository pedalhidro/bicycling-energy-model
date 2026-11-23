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

THE CLIMB-AIR ARM — registered 2026-11-23, before any run; it takes its entry
number when it lands in the journal. F2 charges nothing for the air on a
climb, and F3 and F4 are built on F2. research/proofs shows what that drops:
the work against the air on the climbs is a fourth term of the law, and on a
steady climb ridden no faster than v_f it lies between zero and what the
engine's `vc` mode charges (`law_bracket`, `steady_climb_air_le`). The arm asks
whether charging that term buys anything once eps is refitted.

  E52_CLIMBAIR=vc   climbs pay air at v_c = keff*P_c/(Crr*mg*cos + mg*sin),
                    capped at v_f: the engine's own mode, and the ceiling.
  E52_CLIMBAIR=ss   climbs pay air at the exact steady speed, the root of
                    keff*P_c/v = Crr*mg*cos + mg*sin + (rho/2)*CdA*v^2, capped
                    at v_f. Computed in this file, not in the engine: an arm
                    that loses should not cost the applet a mode.
  unset (`zero`)    the published chain, byte for byte.

Under the arm the cache's f2 and f3 columns ARE the arm's forms (f1 already
pays air at v_f everywhere and is untouched), every file is suffixed with the
arm, and e52_split.py runs the A-chain on it unchanged. Only e52_build.py and
e52_split.py accept the flag: every other harness that reads this cache writes
its own canonical CSV and would publish the arm under the canonical name.

  GATE         per ride, air(zero) <= air(ss) <= air(vc) <= air(off): the
               bracket research/proofs proves, checked against fresh engine
               calls. The build refuses to ship a cache that breaks it.
  CHECK        F2's fitted eps rises under ss, and rises more under vc.
               Today eps is lowered to make up for the missing term; if it
               does not rise, something other than the arm changed. (F2, not
               F3: F3's eps also moves with its refitted tau.)
  DECISION     ss becomes a candidate form only if F3's fold CV falls by more
               than one fold SE against the published chain. Inside one SE,
               or worse, eps absorbs the term, F2's assumption costs nothing
               that can be measured, and the published form stays.
  EXPECTATION  for the record: the check holds, and the CV difference is
               small enough that it may sit inside one SE.

Output: data/results/e52_aggregates.csv
Run:    python3 src/harness/e52_build.py            (E52_SMOKE=1 for a subset)
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
from bicycling_energy_model.engines import G, flat_eq_speed
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


# The climb-air arm (docstring): what F2/F3/F4 charge for the air on climbs.
CLIMBAIR = os.environ.get("E52_CLIMBAIR", "zero")
if CLIMBAIR not in ("zero", "vc", "ss"):
    raise SystemExit(f"E52_CLIMBAIR={CLIMBAIR!r}: expected zero, vc or ss")
if CLIMBAIR != "zero":
    _main = os.path.basename(getattr(sys.modules.get("__main__"), "__file__", "") or "")
    if _main not in ("e52_build.py", "e52_split.py"):
        raise SystemExit("E52_CLIMBAIR is an arm of e52_build.py and e52_split.py "
                         f"alone — unset it before running {_main or 'this harness'}")
# One suffix for every file of the chain, so the builder and the splitter
# cannot disagree about which arm a file belongs to. Empty for the published
# chain.
ARM_SUFFIX = (("" if AERO == "reg" else "." + AERO)
              + ("" if FALLBACK == "rider" else "." + FALLBACK)
              + ("" if CLIMBAIR == "zero" else "." + CLIMBAIR)
              + (".SMOKE" if SMOKE else ""))

RIDER_FB = _rider_fallbacks()
CDA_RANGE = (0.10, 1.00)
CHECK: list[float] = []   # build-time cache-vs-engine deviations
BRACKET: list[float] = []  # ss arm: worst violation of zero <= ss <= vc <= off
SS_RESID = [0.0]           # ss arm: worst relative force-balance residual
CANON_FAIL: list[str] = []   # F_base failures, counted rather than swallowed
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


def steady_climb_speed(slope: float, p: dict, vf: float, p_climb: float) -> float:
    """Speed held up a grade at pedal power `p_climb`, capped at v_f: the root
    of keff*P/v = Crr*mg*cos + mg*sin + (rho/2)*CdA*(v+w)|v+w|. The engine's
    `vc` drops the air from this balance and so reads faster; with P <= 0 it
    reads zero, and so does this."""
    if not p_climb > 0:
        return 0.0
    mg = p["m"] * G
    sec = math.sqrt(1 + slope * slope)
    c = (p["Crr"] * mg + mg * slope) / sec     # rolling + gravity along the road
    a = 0.5 * p["rho"] * p["CdA"]
    w = p["wind"]
    kp = p["keff"] * p_climb

    def spare(v: float) -> float:              # power left over at speed v
        return kp - v * (c + a * (v + w) * abs(v + w))

    if spare(vf) >= 0:
        return vf                              # would outrun v_f: capped, as vc is
    if w == 0 and c > 0:
        # a*v^3 + c*v - kp is convex and increasing for v > 0, and min(kp/c,
        # vf) is at or above its root, so Newton descends onto it monotonically
        v = min(kp / c, vf)
        for _ in range(60):
            step = (a * v * v * v + c * v - kp) / (3 * a * v * v + c)
            v -= step
            if abs(step) <= 1e-14 * v:
                break
    else:
        lo, hi = 0.0, vf                       # spare(0) = kp > 0 > spare(vf)
        for _ in range(200):
            v = 0.5 * (lo + hi)
            if spare(v) > 0:
                lo = v
            else:
                hi = v
        v = 0.5 * (lo + hi)
    SS_RESID[0] = max(SS_RESID[0], abs(spare(v)) / kp)
    return v


def climb_air_ss(prof: dict, p: dict, vf: float, p_climb: float,
                 memo: dict) -> float:
    """Work against the air on the climb segments, J at the pedals, charged at
    the steady climb speed. Same segments, same gate and same per-metre
    convention as approximate()'s `vc` branch, so the two differ in the speed
    alone. `memo` maps a slope to its speed within ONE ride (the constants are
    fixed there); pass a fresh dict per ride."""
    a = 0.5 * p["rho"] * p["CdA"] / p["keff"]
    w = p["wind"]
    xs, hs = prof["x"], prof["h"]
    tot = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        slope = (hs[i] - hs[i - 1]) / dx
        if slope < CLIMB_THR:
            continue
        v = memo.get(slope)
        if v is None:
            v = memo[slope] = steady_climb_speed(slope, p, vf, p_climb)
        tot += a * (v + w) * abs(v + w) * dx
    return tot


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
    # The climb-air arm acts on every form built on F2's gate (mode "zero"):
    # `vc` swaps the engine mode, `ss` adds the steady-speed air to the zero-
    # mode components. F1 (mode "off") is the same under every arm.
    arm_mode = lambda mode: "vc" if (CLIMBAIR == "vc" and mode == "zero") else mode
    ss_air = lambda pr, mode, memo: (climb_air_ss(pr, p, vf, p_climb, memo)
                                     if (CLIMBAIR == "ss" and mode == "zero") else None)
    memo: dict = {}
    for tag, pr, mode in forms:
        a0 = approximate(pr, p, vf, 0.0, opt(arm_mode(mode)))
        a1 = approximate(pr, p, vf, 1.0, opt(arm_mode(mode)))
        # Components, not just the E0/E1 pair: the decomposition invariant
        # roll + aero + climb + recov == E makes these exactly equivalent, and
        # storing them is what lets A.7 perturb a term for EVERY form. Caching
        # only E0/E1 silently gave F1-F3 a zero elasticity, since the
        # perturbation had nothing to act on.
        row[f"{tag}_roll"], row[f"{tag}_aero"] = a0["roll"], a0["aero"]
        air = ss_air(pr, mode, memo)
        if air is not None:
            row[f"{tag}_aero"] += air
        row[f"{tag}_climb"] = a0["climb"]
        row[f"{tag}_recov1"] = a1["recov"]      # recov at eps = 1
        if tag == "f2":
            row["hplus"], row["hminus"] = a0["hplus"], a0["hminus"]
    row["x_m"] = prof["x"][-1] - prof["x"][0]

    # --- non-circular check: the cached two-point interpolation against a FRESH
    # engine call at an eps neither endpoint used, plus F4 against the exact
    # expression perride_invert.py publishes. Compares to the engine, not to
    # e_form, so it can actually fail.
    if len(CHECK) < 300:
        worst = 0.0
        for tag, pr, mode in forms:
            air = ss_air(pr, mode, {})         # recomputed, no shared memo
            for eps in (0.2, 0.37, 0.85):
                want = approximate(pr, p, vf, eps, opt(arm_mode(mode)))["E"]
                if air is not None:
                    want += air
                got = (row[tag + "_roll"] + row[tag + "_aero"]
                       + row[tag + "_climb"] + eps * row[tag + "_recov1"])
                if want:
                    worst = max(worst, abs(got - want) / abs(want))
        air = ss_air(prof, "zero", {})
        for eps in (0.2, 0.37):
            a2 = approximate(prof, p, vf, eps, opt(arm_mode("zero")))
            km = (max(0, 1 - C_PUB * (prof["x"][-1] / 1000) / a2["hplus"])
                  if a2["hplus"] > 0 else 1)
            want = a2["roll"] + a2["aero"] + km * (a2["climb"] + a2["recov"])
            if air is not None:
                want += air
            got = e_form(row, "F4", eps) * 1000
            if want:
                worst = max(worst, abs(got - want) / abs(want))
        CHECK.append(worst)
        if CLIMBAIR == "ss":
            # the bracket of research/proofs, against the engine's own modes
            lo_, hi_, top = (approximate(prof, p, vf, 0.0, opt(m))["aero"]
                             for m in ("zero", "vc", "off"))
            mid = row["f2_aero"]
            BRACKET.append(max(lo_ - mid, mid - hi_, hi_ - top) / max(top, 1.0))

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
    if CLIMBAIR == "ss":
        b = max(0.0, max(BRACKET)) if BRACKET else float("inf")
        b_ok = b <= 1e-9
        r_ok = SS_RESID[0] <= 1e-9
        print(f"  climb-air arm (ss) on {len(BRACKET)} rides: "
              f"air(zero) <= air(ss) <= air(vc) <= air(off), worst violation "
              f"{b:.3e}   {'GATE-OK' if b_ok else 'GATE-FAIL'}")
        print(f"    worst force-balance residual of the steady speed: "
              f"{SS_RESID[0]:.3e}   {'GATE-OK' if r_ok else 'GATE-FAIL'}")
        ok = ok and b_ok and r_ok
    return ok


def main() -> None:
    print("Entry 52 stage 1 — building the aggregate cache for D3-D6")
    if CLIMBAIR != "zero":
        print(f"  CLIMB-AIR ARM: F2/F3/F4 charge climb air ({CLIMBAIR}) — files "
              f"are suffixed, nothing canonical is written")
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

    out = os.path.join(RESULTS, "e52_aggregates" + ARM_SUFFIX + ".csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nwrote {os.path.basename(out)}")
    if not ok:
        raise SystemExit("cache does not reproduce the engine — refusing to ship it")


if __name__ == "__main__":
    main()
