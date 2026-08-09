#!/usr/bin/env python3
"""Entry 75 — prominence-τ map treatment: the deadband's amplitude
selectivity as raster preprocessing.

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 75 BEFORE the run.

The deadband is an amplitude filter; the σ-Gaussian is a wavelength filter —
Entry 73's P8 measured the substitution gap at 3.5–4.5 pp. This entry tests
the 2-D amplitude analog: h-extrema (prominence-τ) filtering of the terrain
raster — fill every pit and shave every peak of prominence < τ (and, like
the 1-D backlash, shave τ off the survivors) — which is map preprocessing a
router can deploy exactly like σ, keeping edges O(1).

Design (registered): a stratified 300-ride subset (rider × h₊ tercile,
seed 42) — 150 IGC-pop rides on the igc30 lattice, 150 FABDEM-pop rides on
fab30; 30 m lattices only (the 5 m deployment costs real engineering and is
warranted only if the mechanism wins here). Four chains per ride, all
sampled IDENTICALLY from the ride's own crop (internal consistency): raw,
σ30 (profile-space Gaussian, the Entry-73 convention), prom2, prom6.
n ∈ {1, 16}; policies v2 (ε_geo, the deployed default), eF2, F3 (the
path-deadband bound). Filtering: capped geodesic reconstruction (scipy),
64 iterations (1 cell/step covers every noise-scale feature), residual
gated at the path samples.

Disclosure: on the igc30 grid the crop IS the chain — path heights are
bilinear in the ride's 30 m lattice crop, which double-interpolates
relative to Entry 73's direct point sampling of the 5 m raster; a 30 m
planner reads exactly the crop, and all four arms share it, so within-e75
comparisons are exact while the raw-vs-e73 join gate carries a disclosed
tolerance. On fab30 the lattice is the raster's own, so the join is strict.

Run:  /Users/danlessa/conda/bin/python src/harness/e75_prominence.py
      E75_SMOKE=1 …   (10 rides/pop, .SMOKE suffix, no asserts)
Output: data/results/e75_prominence[.SMOKE].csv + console scoreboard.
Needs numpy + scipy + the conda python.  MODULE IS IMPORT-SAFE.
"""

from __future__ import annotations

import csv
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402

from bicycling_energy_model import approx_components, deadband, is_finite  # noqa: E402
from bicycling_energy_model.jsfmt import to_fixed  # noqa: E402

from e41_dem_route import (ELEV_HI, ELEV_LO, FABDEM_VRT, IGC_WIDE, med_of,  # noqa: E402
                           rng)
from e73_gridpath import (CLIMB_THR, M_PER_DEG_LAT, M_PER_DEG_LON,  # noqa: E402
                          PITCH30, edge_form, follow, gdal_info, gauss1d_x,
                          load_cache_rows, load_forms, move_table,
                          path_points, sample_pts, walk_rides,
                          wgs84_to_31983, prepare_ride)
from perride_invert import RESULTS  # noqa: E402
from regime_compare import r1d_v2_edge  # noqa: E402
from skc_compare import sign_p  # noqa: E402

SMOKE = bool(os.environ.get("E75_SMOKE"))
SUFF = ".SMOKE" if SMOKE else ""
N_PER_POP = 10 if SMOKE else 150
TAUS = (2.0, 6.0)
NDIRS75 = (1, 16)
# The first smoke run refuted the 64-step cap: FABDEM's noise makes the
# reconstruction's flood paths long (G3 residual 5.5 m — the filter was
# materially unconverged there, and its scores were artifacts).  The cap is
# now a backstop far above observed convergence; G3 still verifies.
RECON_CAP = 4096
RECON_EXTRA = 10
MARGIN_CELLS = 72          # filter halo + follower excursion


# ---------------------------------------------------- prominence filtering
def geodesic_recon(marker: np.ndarray, mask: np.ndarray, dilate: bool,
                   cap: int) -> np.ndarray:
    """Capped geodesic reconstruction (Vincent's iterative form).  dilate=True:
    reconstruction by dilation (marker ≤ mask); False: by erosion (≥)."""
    m = marker.copy()
    for _ in range(cap):
        if dilate:
            nxt = np.minimum(ndimage.grey_dilation(m, size=(3, 3)), mask)
        else:
            nxt = np.maximum(ndimage.grey_erosion(m, size=(3, 3)), mask)
        if np.array_equal(nxt, m):
            return nxt
        m = nxt
    return m


def prom_filter(h: np.ndarray, tau: float, cap: int = RECON_CAP) -> np.ndarray:
    """h-minima fill then h-maxima shave at prominence τ (the registered
    order: bridge valleys first, mirroring the deck's direction)."""
    if tau <= 0:
        return h.copy()
    filled = geodesic_recon(h + tau, h, dilate=False, cap=cap)
    return geodesic_recon(filled - tau, filled, dilate=True, cap=cap)


# ---------------------------------------------------------------- plumbing
def bilinear(A: np.ndarray, fi: np.ndarray, fj: np.ndarray) -> np.ndarray:
    H, W = A.shape
    i0 = np.clip(np.floor(fi).astype(int), 0, H - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, W - 2)
    ti = np.clip(fi - i0, 0.0, 1.0)
    tj = np.clip(fj - j0, 0.0, 1.0)
    return (A[i0, j0] * (1 - ti) * (1 - tj) + A[i0, j0 + 1] * (1 - ti) * tj
            + A[i0 + 1, j0] * ti * (1 - tj) + A[i0 + 1, j0 + 1] * ti * tj)


def subset_draw(rows: list[dict]) -> dict[str, str]:
    """label -> pop ('igc'|'fab'), stratified rider × own-h₊ tercile, seed 42.
    igc = SP rides on the igc30 lattice; fab = the D6 riders on fab30 (the
    EU half of the FABDEM pop — restricting to D6 avoids double membership;
    disclosed deviation from the registration's 'FABDEM pop' wording)."""
    rand = rng(42)
    out: dict[str, str] = {}
    def flag(r, col):
        try:
            return float(r.get(col) or 0) == 1.0
        except ValueError:
            return False

    for popcol, tag in (("pop_igc", "igc"), ("pop_fab", "fab")):
        cand = [r for r in rows if flag(r, popcol)
                and (r["group"] in ("D3", "D4", "D5")) == (tag == "igc")]
        strata: dict[tuple, list] = {}
        for r in cand:
            try:
                hp = float(r["own30_n1_hplus"])
            except (KeyError, ValueError):
                continue
            strata.setdefault(r["group"], []).append((hp, r["ride"]))
        chosen: list[str] = []
        total = sum(len(v) for v in strata.values())
        for g, v in sorted(strata.items()):
            v.sort()
            k = max(1, round(N_PER_POP * len(v) / total))
            terc = [v[: len(v) // 3], v[len(v) // 3: 2 * len(v) // 3],
                    v[2 * len(v) // 3:]]
            per = [k // 3] * 3
            for i in range(k - sum(per)):
                per[i % 3] += 1
            for t, kt in zip(terc, per):
                pool = list(t)
                for _ in range(min(kt, len(pool))):
                    pick = int(rand() * len(pool))
                    chosen.append(pool.pop(pick)[1])
        for lab in chosen[:N_PER_POP + 5]:
            out[lab] = tag if lab not in out else out[lab]
    return out


def score_chain(xs, hs, p, pw, vf, forms) -> dict:
    prof = {"x": xs, "h": hs}
    v2 = r1d_v2_edge(prof, p, pw, CLIMB_THR)
    ef2, _ = edge_form(prof, p, vf, CLIMB_THR, True, forms["F2"]["eps"], 0.0)
    a = approx_components(prof, p, vf, CLIMB_THR)
    h3 = deadband(hs, forms["F3"]["tau"])
    a3 = approx_components({"x": xs, "h": h3}, p, vf, CLIMB_THR)
    f3 = (a["roll"] + a3["aero"] + a["beta"] * a3["hplus"]
          - forms["F3"]["eps"] * a["beta"] * a3["hminus"]) / 1000
    km = (xs[-1] - xs[0]) / 1000
    cn = ((a["hplus"] - sum(max(0.0, h2 - h1) for h1, h2 in
                            zip(deadband(hs, 2.0), deadband(hs, 2.0)[1:]))) / km
          if km > 0 else float("nan"))
    return {"v2": v2, "ef2": ef2, "f3": f3, "hplus": a["hplus"], "cn": cn}


def main() -> None:
    t0 = time.time()
    print(f"Entry 75 — prominence-τ map treatment{'   [SMOKE]' if SMOKE else ''}")
    forms = load_forms()
    cache_rows = load_cache_rows()
    e73 = list(csv.DictReader(open(os.path.join(RESULTS, "e73_gridpath.csv"))))
    e73_by = {r["ride"]: r for r in e73}
    subset = subset_draw(e73)
    print(f"  subset: {sum(1 for v in subset.values() if v == 'igc')} IGC · "
          f"{sum(1 for v in subset.values() if v == 'fab')} FAB", file=sys.stderr)

    gi_igc = gdal_info(IGC_WIDE)
    gi_fab = gdal_info(FABDEM_VRT)
    x0e = gi_igc["ulx"] + 0.5 * PITCH30
    y0n = gi_igc["uly"] - 0.5 * PITCH30

    rows_out: list[dict] = []
    gate = {"g1_worst": 0.0, "g2_bad": 0, "g3_worst": 0.0, "g4_bad": 0,
            "g5_worst": 0.0, "n": 0}
    n_done = 0
    for group, label, pts, path, sid in walk_rides():
        tag = subset.get(label)
        if tag is None:
            continue
        c = cache_rows.get(label)
        if c is None:
            continue
        r = prepare_ride(group, label, pts, path, sid, c)
        if r is None or "skip" in r:
            continue
        p, pw, vf = r["p"], r["pw"], r["vf"]
        # ---- lattice + metric polyline for this ride's grid ----
        if tag == "igc":
            es, ns = wgs84_to_31983(list(r["g5lon"]), list(r["g5lat"]))
            px, py = es, ns
            dxm = dym = PITCH30
            ox, oy = x0e, y0n
            geoloc = True
        else:
            lat0 = sum(r["g5lat"]) / len(r["g5lat"])
            kx = M_PER_DEG_LON * math.cos(math.radians(lat0))
            ky = M_PER_DEG_LAT
            psz = gi_fab["px"]
            lon0, latt0 = r["g5lon"][0], r["g5lat"][0]
            px = [(v - lon0) * kx for v in r["g5lon"]]
            py = [(v - latt0) * ky for v in r["g5lat"]]
            dxm, dym = psz * kx, psz * ky
            ox = (gi_fab["ulx"] + 0.5 * psz - lon0) * kx
            oy = (gi_fab["uly"] - 0.5 * psz - latt0) * ky
            geoloc = False
        # ---- paths: n = 1 (the g30 track positions, exactly Entry 73's)
        # and n = 16 (the follower) ----
        paths = {}
        d30 = list(r["d30"])
        if geoloc:
            e30, n30 = wgs84_to_31983(list(r["g30lon"]), list(r["g30lat"]))
            fi1 = np.array([(oy - y) / dym for y in n30])
            fj1 = np.array([(x - ox) / dxm for x in e30])
        else:
            psz = gi_fab["px"]
            fi1 = np.array([(gi_fab["uly"] - la) / psz - 0.5
                            for la in r["g30lat"]])
            fj1 = np.array([(lo - gi_fab["ulx"]) / psz - 0.5
                            for lo in r["g30lon"]])
        paths[1] = (fi1, fj1, np.array(d30), np.array(d30))
        moves = move_table(16, dxm, dym)
        i0 = round((oy - py[0]) / dym)
        j0 = round((px[0] - ox) / dxm)
        res = follow(px, py, 5.0, moves, i0, j0, ox, oy, dxm, dym, r["total"])
        if res is None:
            continue
        mbd = {(dr, dc): sub for dr, dc, _e, _n, _l, sub in moves}
        coords, xs16, ss16 = path_points(res, mbd)
        paths[16] = (np.array([q[0] for q in coords]),
                     np.array([q[1] for q in coords]),
                     np.array(xs16), np.array(ss16))
        # ---- the crop, sampled with the SAME sampler as e73 ----
        alli = np.concatenate([paths[n][0] for n in NDIRS75])
        allj = np.concatenate([paths[n][1] for n in NDIRS75])
        ilo = int(np.floor(alli.min())) - MARGIN_CELLS
        ihi = int(np.ceil(alli.max())) + MARGIN_CELLS
        jlo = int(np.floor(allj.min())) - MARGIN_CELLS
        jhi = int(np.ceil(allj.max())) + MARGIN_CELLS
        W, H = jhi - jlo + 1, ihi - ilo + 1
        jj, ii = np.meshgrid(np.arange(jlo, jhi + 1), np.arange(ilo, ihi + 1))
        if geoloc:
            cx = (x0e + jj * PITCH30).ravel()
            cy = (y0n - ii * PITCH30).ravel()
        else:
            psz = gi_fab["px"]
            cx = (gi_fab["ulx"] + (jj + 0.5) * psz).ravel()
            cy = (gi_fab["uly"] - (ii + 0.5) * psz).ravel()
        vals = sample_pts(IGC_WIDE if geoloc else FABDEM_VRT,
                          list(cx), list(cy), geoloc)
        A = np.array(vals, dtype=float).reshape(H, W)
        okA = np.isfinite(A) & (A > ELEV_LO) & (A < ELEV_HI)
        if okA.mean() < 0.95:
            continue
        A[~okA] = np.median(A[okA])
        # ---- chains: raw crop, prom2, prom6 (+ σ30 in profile space) ----
        chains2d = {"raw": A}
        for tau in TAUS:
            chains2d[f"prom{int(tau)}"] = prom_filter(A, tau)
        # gates G2/G3/G4
        if not np.array_equal(prom_filter(A, 0.0), A):
            gate["g2_bad"] += 1
        extra = prom_filter(A, TAUS[1], cap=RECON_CAP + RECON_EXTRA)
        for n in NDIRS75:
            fi, fj = paths[n][0] - ilo, paths[n][1] - jlo
            drift = np.max(np.abs(bilinear(chains2d["prom6"], fi, fj)
                                  - bilinear(extra, fi, fj)))
            gate["g3_worst"] = max(gate["g3_worst"], float(drift))
        row = {"ride": label, "group": group, "pop": tag, "emp": r["emp"],
               "km": r["km"]}
        e73r = e73_by.get(label, {})
        for n in NDIRS75:
            fi, fj = paths[n][0] - ilo, paths[n][1] - jlo
            xs = list(paths[n][2])
            raw_h = None
            raw_hplus = None
            for ch in ("raw", "prom2", "prom6"):
                hs = list(bilinear(chains2d[ch], fi, fj))
                s = score_chain(xs, hs, p, pw, vf, forms)
                if ch == "raw":
                    raw_h = hs
                    raw_hplus = s["hplus"]
                elif s["hplus"] > raw_hplus + 1e-6:
                    gate["g4_bad"] += 1
                for k in ("v2", "ef2", "f3"):
                    row[f"{ch}_n{n}_{k}"] = 100 * (s[k] - r["emp"]) / r["emp"]
                row[f"{ch}_n{n}_hplus"] = s["hplus"]
                if n == 1:
                    row[f"{ch}_cn"] = s["cn"]
            # σ30 comparator, profile space on the raw crop chain
            hs30 = gauss1d_x(xs, raw_h, 30.0)
            s = score_chain(xs, hs30, p, pw, vf, forms)
            for k in ("v2", "ef2", "f3"):
                row[f"s30_n{n}_{k}"] = 100 * (s[k] - r["emp"]) / r["emp"]
            row[f"s30_n{n}_hplus"] = s["hplus"]
            if n == 1:
                row["s30_cn"] = s["cn"]
            # G1/G5: the raw chain against Entry 73's cached columns
            ref_h = e73r.get(f"{'igc30' if tag == 'igc' else 'fab30'}_n{n}_hplus")
            if ref_h not in (None, ""):
                key1 = "g1_igc" if tag == "igc" else "g1_fab"
                gate[key1] = max(gate.get(key1, 0.0),
                                 abs(row[f"raw_n{n}_hplus"] - float(ref_h)))
            ref_v = e73r.get(f"{'igc30' if tag == 'igc' else 'fab30'}_n{n}_v2")
            if ref_v not in (None, "") and n == 16 and tag == "fab":
                gate["g5_worst"] = max(gate["g5_worst"],
                                       abs(row[f"raw_n{n}_v2"] - float(ref_v)))
        rows_out.append(row)
        gate["n"] += 1
        n_done += 1
        if n_done % 20 == 0:
            print(f"  …{n_done} rides ({to_fixed(time.time() - t0, 0)} s)",
                  file=sys.stderr)

    out = os.path.join(RESULTS, "e75_prominence" + SUFF + ".csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        for r_ in rows_out:
            w.writerow(r_)
    print(f"\nwrote {os.path.basename(out)} ({len(rows_out)} rides)")

    # ---- scoreboard ----
    print("\n" + "=" * 84)
    print("ENTRY 75 — prominence-τ map treatment (30 m lattices; subset)")
    print("=" * 84)
    for tag, lbl in (("igc", "IGC 30 m (SP)"), ("fab", "FABDEM 30 m")):
        sub = [r_ for r_ in rows_out if r_["pop"] == tag]
        if not sub:
            continue
        print(f"\n── {lbl} · n = {len(sub)} rides ──")
        print("c(τ=2) per chain, m/km: "
              + " · ".join(f"{ch} {med_of([r_[f'{ch}_cn'] for r_ in sub]):.2f}"
                           for ch in ("raw", "s30", "prom2", "prom6")))
        for n in NDIRS75:
            print(f"  n={n}: med|Δ%| (signed) per chain × policy")
            print("chain".ljust(8) + "".join(m.rjust(18) for m in
                                            ("v2", "eF2", "F3")))
            for ch in ("raw", "s30", "prom2", "prom6"):
                cells = []
                for m in ("v2", "ef2", "f3"):
                    v = [r_[f"{ch}_n{n}_{m}"] for r_ in sub
                         if is_finite(r_.get(f"{ch}_n{n}_{m}", float("nan")))]
                    cells.append(f"{med_of([abs(x) for x in v]):6.2f} "
                                 f"({med_of(v):+6.2f})")
                print(ch.ljust(8) + "".join(c.rjust(18) for c in cells))
        # the registered paired test: prom6 vs σ30 under v2 at n = 16
        st = [r_ for r_ in sub
              if is_finite(r_.get("prom6_n16_v2", float("nan")))
              and is_finite(r_.get("s30_n16_v2", float("nan")))]
        w_ = sum(1 for r_ in st if abs(r_["prom6_n16_v2"]) < abs(r_["s30_n16_v2"]))
        l_ = sum(1 for r_ in st if abs(r_["prom6_n16_v2"]) > abs(r_["s30_n16_v2"]))
        print(f"  P1₇₅ paired (v2, n=16): prom6 closer on {w_}/{w_ + l_} "
              f"(sign p = {to_fixed(sign_p(w_, l_), 4)})")

    print("\nGATES")
    g1f, g1i = gate.get("g1_fab", 0.0), gate.get("g1_igc", 0.0)
    print(f"  [{'PASS' if g1f <= 0.1 else 'FAIL'}] G1 fab raw h₊ vs e73 worst "
          f"|Δ| {g1f:.3f} m (strict — same lattice)")
    print(f"  [----] G1 igc30 raw h₊ vs e73 worst |Δ| {g1i:.2f} m — the crop "
          f"IS e75's chain (30 m lattice, double-interp vs e73's direct 5 m "
          f"sampling; disclosed, within-e75 comparisons unaffected)")
    print(f"  [{'PASS' if gate['g2_bad'] == 0 else 'FAIL'}] G2 τ=0 no-op "
          f"({gate['g2_bad']} violations)")
    print(f"  [{'PASS' if gate['g3_worst'] <= 0.01 else 'FAIL'}] G3 convergence "
          f"residual at path samples {gate['g3_worst']:.4f} m (≤ 0.01)")
    print(f"  [{'PASS' if gate['g4_bad'] == 0 else 'FAIL'}] G4 prom h₊ ≤ raw h₊ "
          f"({gate['g4_bad']} violations)")
    print(f"  [{'PASS' if gate['g5_worst'] <= 0.02 else 'FAIL'}] G5 raw fab30 n=16 "
          f"v2 vs e73 worst |Δ| {gate['g5_worst']:.4f} pp")
    print(f"\ntotal {to_fixed((time.time() - t0) / 60, 1)} min")
    sys.exit(0)


if __name__ == "__main__":
    main()
