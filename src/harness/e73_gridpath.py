#!/usr/bin/env python3
"""Entry 73 — paper 3's discrete-routing ladder: the matched ridden path.

Pre-registered in MODEL_COMPARISON_JOURNAL.md Entry 73 BEFORE the full run.

The discrete router's cost is evaluated on the path a router would actually
charge for the ride the rider actually rode: each ride's GPS line is QUANTIZED
onto a grid (the terrain raster's own lattice) as a connected sequence of
moves from an n-direction move set — the Python mirror of Simujaules'
`buildMoves` (classic 8 first in classic order, Farey/mediant octant ladder at
levels {16:1, 32:2, 64:3, 128:4}, long moves profile-integrated at
subN = 2·max(|dr|,|dc|) sub-steps).  No Dijkstra, no routing, no detour
confound: what varies is the DISCRETIZATION, one factor at a time.

Four axes, pure one-factor ladders around a base config:
  1. base model    — v2Edge (deployed; `r1d_v2_edge`) scored beside the
                     route-level forms F1–F4, F5f and the Entry-72 valley
                     patch, all computed on the SAME discrete path profile.
                     Models are COLUMNS, not arms.
  2. terrain chain — paper 2's elevation sources; the chain also sets the
                     lattice: own barometer (n = 1 only), IGC-SP 5 m
                     (raw / σ10 / σ30 along-path), IGC at a 30 m lattice,
                     FABDEM 30 m.
  3. directions    — n = 1 (the ride's own polyline at lattice pitch, the
                     Entry-72 profile) then 4, 8, 16, 32, 64, 128.
  4. semantic      — the Entry-26 OSM bridge/tunnel straight deck applied to
                     the base path (offline-only; spans matched on the TRUE
                     track and mapped to the path by projected chainage).

TWO POPULATIONS (registration decision, Danilo): the IGC pop — D3–D5 rides
inside the IGC-SP raster (igc_ok) — carries every arm; the FABDEM pop —
D3–D6, FABDEM being global — carries the fab30 ladder.  Each arm is compared
within its population only.

Physics: paper 1's A-chain per-ride constants (m̂/Ĉrr/ĈdA from
e52_aggregates.csv, ρ/k_eff frozen, wind 0, G = 9.7864) — e72's protocol
verbatim.  Every fitted constant is read from its producing CSV
(e52_split.csv, e63_split.E63_TAUN2p0.csv), never a literal.

Scores per config: signed Δ% vs measured energy for every model column, plus
Δ% of v2Edge vs the ROUTE-LEVEL ESTIMATE (F4-published on the same chain's
n = 1 profile) — the discretisation cost isolated from the terrain cost.

The quantizer (resolves paper 3 §2.3's map-matching TODO): a deterministic
greedy chainage follower.  Fast path: each step scores every move k by the
squared distance from its endpoint to the polyline point one move-length
ahead (P(s_cur + L_k)); the winner is verified by exact local projection
(chainage must advance ≥ 0.05·L_k, endpoint lateral ≤ one cell diagonal).
On rejection the step falls back to exhaustive projection of every move
(max chainage advance; ties → min lateral → min move index); if no move is
feasible (a switchback tighter than the lattice) the follower JUMPS one
pitch along the track (njump counted; an arm with njump > 0.5% of nodes is
dropped for that ride).  n = 1 bypasses the follower entirely.

Run:  /Users/danlessa/conda/bin/python src/harness/e73_gridpath.py
      E73_SMOKE=1 …    (15 rides/group; .SMOKE/_smoke suffixes; no asserts)
      E73_GATES=1 …    (synthetic gates only — no data, no rasters, ~seconds)
      E73_ONLY=igc5s10_n8,fab30_n128 …   (restrict configs while iterating)
Output: data/results/e73_gridpath[.SMOKE].csv, console scoreboard,
        research/article/figs/fig-p3-dirs[.SMOKE].svg + fig-p3-chain[.SMOKE].svg.
Caches: data/results/cache/dem/e73_{grid}_n{n}[_smoke].{bin,meta.json}.

MODULE IS IMPORT-SAFE — the driver lives in main().
"""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
import time
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from bicycling_energy_model import (approx_components, build_profile,  # noqa: E402
                                    deadband, empirical_kj, eps_geom,
                                    extract_regime_powers, flat_eq_speed,
                                    haversine, is_finite, load_pts,
                                    overall_mean_power, resample_profile)
from bicycling_energy_model.engines import G  # noqa: E402
from bicycling_energy_model.jsfmt import js_str, to_fixed  # noqa: E402

from igc_resolution_test import (geo_track_from_fit, grid_positions,  # noqa: E402
                                 lon_lat_at)
from perride_invert import CLIMB_THR, DESC_THR, KEFF, RESULTS, RHO  # noqa: E402
from regime_compare import r1d_v2_edge  # noqa: E402
from skc_compare import boot_ci_strat, med_of, ride_files, sign_p  # noqa: E402
# e41 is import-safe and holds the DEM instrument this harness extends: the
# raster paths, the QA thresholds, valid_fill, the FABDEM tile machinery and
# the offline portal-coverage test.  Importing it also loads its anchor-mass
# recovery (a few seconds) — accepted, it keeps exactly one copy of each.
from e41_dem_route import (ELEV_HI, ELEV_LO, FABDEM_VRT, GAP_FRAC_MAX,  # noqa: E402
                           GAP_MIN, IGC_BBOX, IGC_WIDE, VALID_MIN, ZWIFT,
                           e26_module, ensure_fabdem, fabdem_tile,
                           portal_tiles_cached, read_buf, regrid, span_metres,
                           valid_fill)

DATA = os.path.join(REPO, "data", "inputs", "activities")
SCRATCH = os.path.join(RESULTS, "cache", "dem")
os.makedirs(SCRATCH, exist_ok=True)
FIGS = os.path.join(REPO, "research", "article", "figs")

SMOKE = bool(os.environ.get("E73_SMOKE"))
SMOKE_N = 15
GATES_ONLY = bool(os.environ.get("E73_GATES"))
ONLY = {t.strip() for t in os.environ.get("E73_ONLY", "").split(",") if t.strip()}
SUFF = ".SMOKE" if SMOKE else ""
CSUFF = "_smoke" if SMOKE else ""

ENGINE_DX = 5.0                 # the polyline arc grid every ride is traced on
PITCH30 = 30.0
NDIRS = (1, 4, 8, 16, 32, 64, 128)
BASE_N = 8
F5F_FLOOR = 2.0                 # the registered F5f arm (e63_split.E63_TAUN2p0)
TAU_PUB = None                  # F3's published deadband — read from e52_split.csv
# deployed metre-per-degree factors (simujaules app.js loadDemFromArrayBuffer)
M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON = 111320.0
# quantizer constants (pre-registered)
ADV_MIN = 0.05                  # chainage must advance >= ADV_MIN * move length
JUMP_FRAC_MAX = 0.005           # drop the arm when njump exceeds this share
STEP_CAP_FACTOR = 6             # hard termination: steps <= factor * S / pitch
PARITY_TOL = 0.02               # pp — e41's convention (reference CSVs print 4 dp)

GROUPS = ("D3", "D4", "D5", "D6-user_1", "D6-user_2", "D6-user_3", "D6-user_5")
CORPUS_OF = {"D3": "ppaz", "D4": "jaam", "D5": "danlessa"}

# chain -> (grid key, sigma m).  own5/own30 are the barometric controls.
CHAINS = {"igc5": ("igc5", 0.0), "igc5s10": ("igc5", 10.0),
          "igc5s30": ("igc5", 30.0), "igc30": ("igc30", 0.0),
          "fab30": ("fab30", 0.0), "fab30s30": ("fab30", 30.0)}
GRID_RASTER = {"igc5": IGC_WIDE, "igc30": IGC_WIDE, "fab30": FABDEM_VRT}
GRID_PITCH = {"igc5": 5.0, "igc30": 30.0, "fab30": None}   # fab: native arcsec

# config list per population: (chain, n, portal?).  Models are columns.
# The three igc5-grid chains and both fab30-grid chains carry FULL n-ladders
# (same cached paths — the σ variants are scoring-only), so the eF-family
# vs n tables exist raw and map-treated on both DTMs.
IGC_CONFIGS = ([("own5", 1, False), ("own30", 1, False)]
               + [("igc5s10", n, False) for n in NDIRS]
               + [("igc5", n, False) for n in NDIRS]
               + [("igc5s30", n, False) for n in NDIRS]
               + [("igc30", 1, False), ("fab30", 1, False),
                  ("igc30", BASE_N, False), ("fab30", BASE_N, False),
                  ("igc5s10", BASE_N, True),
                  # H4's registered stacking arm: the deck on the σ30-treated
                  # base — at route grain the two repairs subtract twice
                  ("igc5s30", BASE_N, True)])
FAB_CONFIGS = ([("own30", 1, False)]
               + [("fab30", n, False) for n in NDIRS]
               + [("fab30s30", n, False) for n in NDIRS])

E73_SPANS = os.path.join(SCRATCH, "e73_portal_spans.json")
E41_SPANS = os.path.join(SCRATCH, "e41_portal_spans.json")
CACHE_VERSION = 3       # v2: n = 1 positions from the raw geo track;
                        # v3: full-precision sample coordinates (both parity fixes)


def cfg_name(chain: str, n: int, portal: bool) -> str:
    return f"{chain}_n{n}" + ("p" if portal else "")


# ===================================================================== moves
def build_moves(n: int) -> list[tuple[int, int]]:
    """Simujaules buildMoves' vector list, verbatim geometry (energy-worker.js
    line 389): 4 = von Neumann; >= 8 = classic 8 first in classic order, then
    the Farey/mediant octant ladder expanded to 4 sign x swap images, deduped
    in insertion order."""
    if n == 4:
        return [(-1, 0), (0, -1), (0, 1), (1, 0)]
    vecs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    level = {16: 1, 32: 2, 64: 3, 128: 4}.get(n, 0)
    if level > 0:
        oct_ = [(1, 0), (1, 1)]
        for _ in range(level):
            nxt = []
            for i in range(len(oct_) - 1):
                nxt.append(oct_[i])
                nxt.append((oct_[i][0] + oct_[i + 1][0], oct_[i][1] + oct_[i + 1][1]))
            nxt.append(oct_[-1])
            oct_ = nxt
        seen = set(vecs)
        for a, b in oct_:
            for dr, dc in ((a, b), (b, a)):
                for sr in (1, -1):
                    for sc in (1, -1):
                        v = (dr * sr or 0, dc * sc or 0)
                        if v not in seen:
                            seen.add(v)
                            vecs.append(v)
    return vecs


def move_table(n: int, dxm: float, dym: float) -> list[tuple]:
    """(dr, dc, dE, dN, length m, subN) per move on a lattice with metric cell
    size (dxm east, dym north).  Unit distances use the exact legacy
    expressions; long distances hypot(dr*dy, dc*dx) — the worker's."""
    diag = math.hypot(dxm, dym)
    out = []
    for dr, dc in build_moves(n):
        if dr == 0:
            dist = dxm * abs(dc)
        elif dc == 0:
            dist = dym * abs(dr)
        elif abs(dr) == 1 and abs(dc) == 1:
            dist = diag
        else:
            dist = math.hypot(dr * dym, dc * dxm)
        m = max(abs(dr), abs(dc))
        out.append((dr, dc, dc * dxm, -dr * dym, dist, 2 * m if m > 1 else 1))
    return out


# ================================================================= quantizer
def follow(px: list[float], py: list[float], s_grid: float, moves: list[tuple],
           i0: int, j0: int, x0e: float, y0n: float, dxm: float, dym: float,
           s_total: float) -> dict | None:
    """The greedy chainage follower.  Polyline (px, py) in metric coords at
    uniform arc step `s_grid`; lattice node (i, j) has metric position
    (x0e + j*dxm, y0n - i*dym).  Returns node list, per-node projected
    chainage and lateral, path chainage (metrication-inflated), njump — or
    None when the step cap trips."""
    n_poly = len(px)
    d_max = math.hypot(dxm, dym)
    l_max = max(mv[4] for mv in moves)
    l_min = min(mv[4] for mv in moves)

    def P(s: float) -> tuple[float, float]:
        t = s / s_grid
        k = int(t)
        if k >= n_poly - 1:
            return px[n_poly - 1], py[n_poly - 1]
        f = t - k
        return px[k] + (px[k + 1] - px[k]) * f, py[k] + (py[k + 1] - py[k]) * f

    def project(ex: float, ey: float, s_lo: float, s_hi: float) -> tuple[float, float]:
        """Exact point→polyline projection on the window [s_lo, s_hi]."""
        k0 = max(0, int(s_lo / s_grid))
        k1 = min(n_poly - 2, int(s_hi / s_grid) + 1)
        best_d2, best_s = float("inf"), s_lo
        for k in range(k0, k1 + 1):
            ax, ay = px[k], py[k]
            bx, by = px[k + 1], py[k + 1]
            vx, vy = bx - ax, by - ay
            vv = vx * vx + vy * vy
            t = 0.0 if vv <= 0 else max(0.0, min(1.0, ((ex - ax) * vx + (ey - ay) * vy) / vv))
            qx, qy = ax + vx * t, ay + vy * t
            d2 = (ex - qx) ** 2 + (ey - qy) ** 2
            if d2 < best_d2:
                best_d2, best_s = d2, (k + t) * s_grid
        return best_s, math.sqrt(best_d2)

    i, j = i0, j0
    ex = x0e + j * dxm
    ey = y0n - i * dym
    s_cur, lat0 = project(ex, ey, 0.0, min(s_total, 4 * d_max))
    nodes = [(i, j)]
    ss = [s_cur]
    lats = [lat0]
    xs = [0.0]
    njump = 0
    step_cap = int(STEP_CAP_FACTOR * s_total / max(l_min, 1e-9)) + 16
    steps = 0
    end_s = s_total - max(l_max, s_grid)
    while s_cur < end_s:
        steps += 1
        if steps > step_cap:
            return None
        # fast path: chase the polyline point one move-length ahead
        best_k, best_d2 = -1, float("inf")
        for k, (dr, dc, de, dn, L, _sub) in enumerate(moves):
            tx, ty = P(min(s_cur + L, s_total))
            d2 = (ex + de - tx) ** 2 + (ey + dn - ty) ** 2
            if d2 < best_d2:
                best_d2, best_k = d2, k
        dr, dc, de, dn, L, _sub = moves[best_k]
        nx, ny = ex + de, ey + dn
        s_new, lat = project(nx, ny, max(0.0, s_cur - 2 * s_grid),
                             s_cur + L + 4 * d_max)
        if not (lat <= d_max and s_new >= s_cur + ADV_MIN * L):
            # exhaustive fallback: exact projection of every move
            best = None
            for k, (dr2, dc2, de2, dn2, L2, _s2) in enumerate(moves):
                cx, cy = ex + de2, ey + dn2
                s2, lat2 = project(cx, cy, max(0.0, s_cur - 2 * s_grid),
                                   s_cur + L2 + 4 * d_max)
                if lat2 <= d_max and s2 >= s_cur + ADV_MIN * L2:
                    key = (-s2, lat2, k)
                    if best is None or key < best[0]:
                        best = (key, k, s2, lat2)
            if best is None:
                # switchback tighter than the lattice: jump one pitch ahead
                njump += 1
                s_cur = min(s_total, s_cur + s_grid)
                tx, ty = P(s_cur)
                jn = round((y0n - ty) / dym)
                jj = round((tx - x0e) / dxm)
                nx2, ny2 = x0e + jj * dxm, y0n - jn * dym
                d_jump = math.hypot(nx2 - ex, ny2 - ey)
                if (jn, jj) == (i, j) or d_jump <= 0:
                    continue
                i, j = jn, jj
                ex, ey = nx2, ny2
                nodes.append((i, j))
                ss.append(s_cur)
                lats.append(math.hypot(nx2 - tx, ny2 - ty))
                xs.append(xs[-1] + d_jump)
                continue
            _key, best_k, s_new, lat = best
            dr, dc, de, dn, L, _sub = moves[best_k]
            nx, ny = ex + de, ey + dn
        i, j = i + dr, j + dc
        ex, ey = nx, ny
        nodes.append((i, j))
        ss.append(s_new)
        lats.append(lat)
        xs.append(xs[-1] + L)
        s_cur = s_new
    return {"nodes": nodes, "ss": ss, "lats": lats, "xs": xs, "njump": njump}


def path_points(res: dict, moves_by_delta: dict) -> tuple[list, list, list]:
    """Expand a follower result into sample points (fractional lattice coords)
    with long moves sub-divided at subN = 2*max(|dr|,|dc|): (coords, xs, ss).
    Jump segments (deltas not in the move set) stay single segments."""
    nodes, ss, xs = res["nodes"], res["ss"], res["xs"]
    out_c = [nodes[0]]
    out_x = [xs[0]]
    out_s = [ss[0]]
    for t in range(1, len(nodes)):
        r0, c0 = nodes[t - 1]
        r1, c1 = nodes[t]
        sub = moves_by_delta.get((r1 - r0, c1 - c0), 1)
        for q in range(1, sub + 1):
            f = q / sub
            out_c.append((r0 + (r1 - r0) * f, c0 + (c1 - c0) * f))
            out_x.append(xs[t - 1] + (xs[t] - xs[t - 1]) * f)
            out_s.append(ss[t - 1] + (ss[t] - ss[t - 1]) * f)
    return out_c, out_x, out_s


# ============================================================ raster sampling
def sample_pts(raster: str, xs: list[float], ys: list[float],
               geoloc: bool) -> list[float]:
    """Batch bilinear sampler (e41's sample_raster pattern).  geoloc=True feeds
    georeferenced coords in the raster's own SRS; False feeds WGS84 lon/lat.
    Coordinates go out at FULL js_str precision — %.8f cost 1.157 m of h₊ on a
    211 km ride (2e-4 m height jitter at every turning point accumulates)."""
    data = "".join(js_str(xs[i]) + " " + js_str(ys[i]) + "\n"
                   for i in range(len(xs))).encode()
    flag = "-geoloc" if geoloc else "-wgs84"
    r = subprocess.run(["gdallocationinfo", "-valonly", flag, "-r", "bilinear",
                        raster], input=data, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if r.stderr:
        pass          # per-point misses print megabytes; NaN already marks them
    lines = r.stdout.decode("utf-8", "replace").split("\n")
    out = [float("nan")] * len(xs)
    for i in range(min(len(xs), len(lines))):
        try:
            out[i] = float(lines[i])
        except ValueError:
            pass
    return out


def gdal_info(raster: str) -> dict:
    r = subprocess.run(["gdalinfo", "-json", raster], stdout=subprocess.PIPE,
                       check=True)
    j = json.loads(r.stdout)
    gt = j["geoTransform"]
    return {"ulx": gt[0], "px": gt[1], "uly": gt[3], "py": gt[5]}


def wgs84_to_31983(lons: list[float], lats: list[float]) -> tuple[list[float], list[float]]:
    """Batch WGS84 -> EPSG:31983 (the IGC raster's SRS) via gdaltransform."""
    data = "".join(f"{lons[i]:.8f} {lats[i]:.8f}\n"
                   for i in range(len(lons))).encode()
    r = subprocess.run(["gdaltransform", "-s_srs", "WGS84", "-t_srs",
                        "EPSG:31983", "-output_xy"], input=data,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    es, ns = [], []
    for line in r.stdout.decode().split("\n"):
        p = line.split()
        if len(p) >= 2:
            es.append(float(p[0]))
            ns.append(float(p[1]))
    if len(es) != len(lons):
        raise SystemExit("gdaltransform returned a short batch")
    return es, ns


# ============================================================ profile helpers
def gauss1d_x(xs: list[float], h: list[float], sigma_m: float,
              trunc: float = 3.0) -> list[float]:
    """Mask-normalized 1-D Gaussian on a NON-UNIFORM grid: kernel evaluated at
    the true x offsets, samples weighted by their trapezoidal measure so a
    ramp stays a ramp on irregular spacing.  On a uniform interior it equals
    e41's gauss1d exactly (the constant measure cancels)."""
    if sigma_m <= 0:
        return list(h)
    n = len(h)
    r = trunc * sigma_m
    mu = [0.0] * n
    for i in range(n):
        lo = xs[i] - (xs[i - 1] if i else xs[0])
        hi = (xs[i + 1] if i < n - 1 else xs[n - 1]) - xs[i]
        mu[i] = (lo + hi) / 2 if n > 1 else 1.0
        if mu[i] <= 0:
            mu[i] = 1e-9
    inv2s2 = 0.5 / (sigma_m * sigma_m)
    out = [0.0] * n
    j_lo = 0
    for i in range(n):
        while xs[j_lo] < xs[i] - r:
            j_lo += 1
        acc = wsum = 0.0
        j = j_lo
        while j < n and xs[j] <= xs[i] + r:
            d = xs[j] - xs[i]
            w = math.exp(-d * d * inv2s2) * mu[j]
            acc += w * h[j]
            wsum += w
            j += 1
        out[i] = acc / wsum
    return out


def apply_deck_x(xs: list[float], h: list[float], ss: list[float],
                 crossings: list[dict]) -> list[float]:
    """Straight-deck correction on a PATH profile: inside each matched span
    (bounds in TRUE-track chainage, mapped through the per-point projected
    chainage ss) heights become a line between the profile's own values at
    the span boundaries.  Endpoint heights read from the ORIGINAL array so
    overlapping spans cannot chain (e41's apply_portal_deck invariant)."""
    if not crossings:
        return list(h)
    n = len(xs)
    out = list(h)

    def h_at_s(s: float) -> tuple[float, float]:
        """(height, path x) of the original profile at true chainage s."""
        lo, hi = 0, n - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if ss[mid] < s:
                lo = mid + 1
            else:
                hi = mid
        i1 = max(1, lo)
        s0, s1 = ss[i1 - 1], ss[i1]
        f = 0.0 if s1 - s0 <= 0 else max(0.0, min(1.0, (s - s0) / (s1 - s0)))
        return (h[i1 - 1] * (1 - f) + h[i1] * f,
                xs[i1 - 1] * (1 - f) + xs[i1] * f)

    for c in crossings:
        xlo, xhi = c["xlo"], c["xhi"]
        if not xhi > xlo:
            continue
        h0, p0 = h_at_s(xlo)
        h1, p1 = h_at_s(xhi)
        if not p1 > p0:
            continue
        for i in range(n):
            if xlo <= ss[i] <= xhi:
                f = max(0.0, min(1.0, (xs[i] - p0) / (p1 - p0)))
                out[i] = h0 + (h1 - h0) * f
    return out


def sum_ascent(h) -> float:
    return sum(max(0.0, h[i] - h[i - 1]) for i in range(1, len(h)))


# =============================================================== fitted priors
def load_forms() -> dict:
    """Published (eps, c, tau) per form from e52_split.csv — never literals."""
    path = os.path.join(RESULTS, "e52_split.csv")
    out = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[r["form"]] = {k: (float(r[k]) if r.get(k) not in (None, "", "inf",
                                                                 "meas")
                                  else None)
                              for k in ("eps", "c", "tau")}
    for f in ("F1", "F2", "F3", "F4"):
        if f not in out:
            raise SystemExit(f"{f} row missing from e52_split.csv")
    return out


def load_f5f_eps() -> float:
    path = os.path.join(RESULTS, "e63_split.E63_TAUN2p0.csv")
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["form"] == "F5f":
                return float(r["eps"])
    raise SystemExit("F5f row missing from e63_split.E63_TAUN2p0.csv")


# ---- the deployable edge family (registration v2, Danilo): eF1/eF2/eF4 ----
# Article 1's recommendation is a FLAT ε, so each eF# carries its route form's
# published flat ε on descents — NOT the deployed grade-local estimator (the
# deployed v2Edge stays as its own reference column, `v2`).  The per-edge
# max(0, ·) clamp is what makes a flat-ε cost Dijkstra-safe, and with
# identical constants it is the ONLY difference between eF# and F#:
#   eF# − F# ≡ the clamped-edge mass (the price of refusing negative edges).
#   eF1: aero UNGATED (F1's trait), ε₁.
#   eF2: aero gated off climbs (F2's trait), ε₂ — "v2Edge-F2"; on a σ-treated
#        map this is paper 3's realisation of F3.
#   eF4: eF2 + the per-edge noise deduction — c metres of phantom climb per
#        km removed from BOTH gravity arms locally (climbs β·max(0, dh−c·dx),
#        descents recover on max(0, |dh|−c·dx)), ε₄, c MEASURED per chain
#        (the chain's own c(τ=2) noise rate — the measured-pin doctrine; the
#        published (ε₄, c) bundle is knowingly broken and disclosed).
# All three are O(1)-local and non-negative: Dijkstra-deployable.


def edge_form(prof: dict, p: dict, vf: float, climb_thr: float,
              gate: bool, eps_flat: float, c_mkm: float) -> tuple[float, float]:
    """One per-edge cost of the flat-ε family.  Returns (E kJ, clamped kJ) —
    `clamped` is the energy the max(0, ·) refused (eF# − F# by identity)."""
    mg = p["m"] * G
    beta = mg / p["keff"]
    w = p["wind"]
    aRoll = mg * p["Crr"] / p["keff"]
    aAero = 0.5 * p["rho"] * p["CdA"] * (vf + w) * abs(vf + w) / p["keff"]
    cd = c_mkm / 1000.0
    xs, hs = prof["x"], prof["h"]
    E = 0.0
    clamped = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        if not dx > 0:
            continue
        if dh >= 0:
            aero = aAero * dx if (not gate or dh < climb_thr * dx) else 0
            e = aRoll * dx + aero + beta * max(0.0, dh - cd * dx)
        else:
            ndh = max(0.0, -dh - cd * dx)
            e = aRoll * dx + aAero * dx - eps_flat * beta * ndh
            if e < 0:
                clamped += -e
                e = 0.0
        E += e
    return E / 1000, clamped / 1000


_E63 = None


def toll_of(prof: dict, p: dict, vf: float, p_climb: float, tau_n: float) -> float:
    """Entry-63 KE valley toll (v_b = ∞) at floor tau_n, metres — e41's
    toll_at, one algebra copy (lazy import, module floor set per call)."""
    global _E63
    if _E63 is None:
        import e63_f5_kebuffer as _m
        _E63 = _m
    _E63.TAU_N = tau_n
    t = _E63.ride_tolls(prof, p["m"], p["Crr"], p["CdA"], vf, p_climb)
    return t[f"toll_vb{_E63.VB_INF_I}"]


# ================================================================ corpus walk
def walk_rides():
    """Replicates e44_scurve.corpus_rides' COUNTER exactly (D6 via ride_files
    + its filters; D3–D5 via the manifest walk skc_invert.iter_brazil does),
    but carries the file path and the manifest id.  Yields
    (group, label '{group}#{i}', pts, path, sid)."""
    seen: dict[str, int] = {}
    for rider, path in ride_files():
        group = "D6-" + rider
        try:
            pts = load_pts(path)
        except Exception:
            continue
        if len(pts) < 10:
            continue
        npow = sum(1 for q in pts if q.get("power") is not None)
        nalt = sum(1 for q in pts if q.get("alt") is not None)
        if npow / len(pts) <= 0.5 or nalt / len(pts) < 0.99 or pts[-1]["x"] / 1000 < 20:
            continue
        i = seen.get(group, 0)
        seen[group] = i + 1
        if group in GROUPS:
            yield group, f"{group}#{i}", pts, path, None
    for corpus, group in (("ppaz", "D3"), ("jaam", "D4"), ("danlessa", "D5")):
        man = json.load(open(os.path.join(DATA, f"strava_{corpus}_manifest.json")))
        cand = [a for a in man if a["sport"] == "ride" and a["powCov"] > 0.5
                and a["km"] >= 20 and a["altCov"] >= 0.99]
        for a in cand:
            meta: dict = {}
            try:
                pts = load_pts(os.path.join(DATA, a["file"]), meta)
            except Exception:
                continue
            if meta.get("manufacturer") == ZWIFT:
                continue
            i = seen.get(group, 0)
            seen[group] = i + 1
            yield group, f"{group}#{i}", pts, os.path.join(DATA, a["file"]), a["id"]


def load_cache_rows() -> dict:
    """The A-chain per-ride physics (e52_aggregates.csv), keyed by label."""
    path = os.path.join(RESULTS, "e52_aggregates.csv")
    out = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                out[r["ride"]] = {"m": float(r["m_hat"]), "Crr": float(r["crr_hat"]),
                                  "CdA": float(r["cda_hat"]), "emp": float(r["emp"])}
            except (KeyError, ValueError):
                continue
    return out


# =============================================================== portal spans
def load_spans() -> dict:
    """e41's true-track span cache (read-only) merged under e73's own."""
    out = {}
    for path in (E41_SPANS, E73_SPANS):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                out.update(json.load(fh))
    return out


def spans_for(ride: dict, spans: dict) -> list[dict] | None:
    """Crossings for one ride: e41's cache when present, else Entry 26's
    detector run OFFLINE (only when every OSM tile is already cached).  New
    detections land in e73's own spans file, never e41's."""
    key = f"{ride['corpus']}|{ride['sid']}"
    if key in spans:
        return spans[key]
    lats, lons = ride["g5lat"], ride["g5lon"]
    if not portal_tiles_cached(list(lats), list(lons)):
        spans[key] = None
        return None
    E = e26_module()
    ways = E.ways_for_bbox(min(lats), max(lats), min(lons), max(lons))
    cr = E.match_crossings(ride["d5"], list(lons), list(lats), ways)
    out = [{"xlo": float(c["xlo"]), "xhi": float(c["xhi"]), "kind": c.get("kind")}
           for c in cr if c["xhi"] > c["xlo"]]
    spans[key] = out
    spans["__dirty__"] = True
    return out


def save_spans(spans: dict) -> None:
    if spans.pop("__dirty__", None):
        keep = {k: v for k, v in spans.items() if not k.startswith("__")}
        with open(E73_SPANS, "w", encoding="utf-8") as fh:
            json.dump(keep, fh, separators=(",", ":"))


# ================================================================== scoring
def score_profile(xs: list[float], hs: list[float], ride: dict,
                  forms: dict, eps5f: float, c_mkm: float | None,
                  c_loro: float | None = None) -> dict:
    """Every model column on one config's path profile.  Energies in kJ.
    `c_mkm` is the chain's pooled measured noise pin (m/km) for eF4;
    `c_loro` the leave-one-rider-out pin for eF4L."""
    p, pw, vf = ride["p"], ride["pw"], ride["vf"]
    prof = {"x": xs, "h": hs}
    a = approx_components(prof, p, vf, CLIMB_THR)
    beta = a["beta"]
    x_km = a["X"] / 1000.0
    # v2Edge — the DEPLOYED per-edge cost (grade-local ε; returns kJ);
    # sub-points make the per-segment sum equal the worker's long-edge
    # integration by construction
    v2 = r1d_v2_edge(prof, p, pw, CLIMB_THR)
    # the flat-ε edge family (article 1's recommendation, per-edge)
    ef1, _cl1 = edge_form(prof, p, vf, CLIMB_THR, False, forms["F1"]["eps"], 0.0)
    ef2, cl2 = edge_form(prof, p, vf, CLIMB_THR, True, forms["F2"]["eps"], 0.0)
    if c_mkm is not None:
        ef4, _cl4 = edge_form(prof, p, vf, CLIMB_THR, True,
                              forms["F4"]["eps"], c_mkm)
    else:
        ef4 = float("nan")
    # eF4L — the LORO pin (registration v4): the ride's pin measured on the
    # OTHER riders of its region; the arm the paper quotes
    if c_loro is not None:
        ef4l, _cl4l = edge_form(prof, p, vf, CLIMB_THR, True,
                                forms["F4"]["eps"], c_loro)
    else:
        ef4l = float("nan")
    # F1/F2 on the raw profile
    grav = beta * a["hplus"]
    aero_flat = 0.5 * p["rho"] * p["CdA"] * (vf + p["wind"]) * abs(vf + p["wind"]) / p["keff"]
    f1 = (a["roll"] + aero_flat * a["X"]
          + grav - forms["F1"]["eps"] * beta * a["hminus"]) / 1000
    f2 = (a["roll"] + a["aero"]
          + grav - forms["F2"]["eps"] * beta * a["hminus"]) / 1000
    # F3 on the published-tau deadband
    h3 = deadband(hs, forms["F3"]["tau"])
    a3 = approx_components({"x": xs, "h": h3}, p, vf, CLIMB_THR)
    f3 = (a["roll"] + a3["aero"] + beta * a3["hplus"]
          - forms["F3"]["eps"] * beta * a3["hminus"]) / 1000
    # F4 with its published (eps, c) — the bundle stays paired
    k4 = (max(0.0, 1 - forms["F4"]["c"] * x_km / a["hplus"])
          if a["hplus"] > 0 else 1.0)
    f4 = (a["roll"] + a["aero"]
          + k4 * (grav - forms["F4"]["eps"] * beta * a["hminus"])) / 1000
    # F5f: floor tau_n = 2, v_b = ∞ toll, eps from the producing CSV
    h5 = deadband(hs, F5F_FLOOR)
    a5 = approx_components({"x": xs, "h": h5}, p, vf, CLIMB_THR)
    t5 = toll_of(prof, p, vf, pw["climb"], F5F_FLOOR)
    f5f = (a["roll"] + a5["aero"] + beta * (a5["hplus"] - t5)
           - eps5f * beta * (a5["hminus"] - t5)) / 1000
    # the Entry-72 valley patch: floor 0, eps_geom of THIS profile
    eg = eps_geom(prof, p, vf)
    eg = eg if is_finite(eg) else 0.2
    t0 = toll_of(prof, p, vf, pw["climb"], 0.0)
    patch = (a["roll"] + a["aero"] + beta * (a["hplus"] - t0)
             - eg * beta * (a["hminus"] - t0)) / 1000
    return {"v2": v2, "ef1": ef1, "ef2": ef2, "ef4": ef4, "ef4L": ef4l,
            "ef2cl": cl2,
            "f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5f": f5f,
            "patch": patch, "hplus": a["hplus"], "x_m": a["X"], "toll": t5,
            "eps_geom": eg}


def ref_f4(xs: list[float], hs: list[float], ride: dict, forms: dict) -> float:
    """The route-level estimate: F4-published on a chain's n = 1 profile, kJ."""
    p, vf = ride["p"], ride["vf"]
    a = approx_components({"x": xs, "h": hs}, p, vf, CLIMB_THR)
    x_km = a["X"] / 1000.0
    k4 = (max(0.0, 1 - forms["F4"]["c"] * x_km / a["hplus"])
          if a["hplus"] > 0 else 1.0)
    return (a["roll"] + a["aero"]
            + k4 * (a["beta"] * a["hplus"]
                    - forms["F4"]["eps"] * a["beta"] * a["hminus"])) / 1000


# =========================================================== synthetic gates
def analytic_ratio(moves: list[tuple], theta: float) -> float:
    """Continuum metrication factor of a move set for a straight line at
    azimuth theta: cost of the best two-direction combination per unit
    advance (all directions unit-cost per metre)."""
    dirs = sorted({math.atan2(dn, de) for _r, _c, de, dn, L, _s in moves})
    ext = dirs + [dirs[0] + 2 * math.pi]
    for a, b in zip(ext, ext[1:]):
        if a - 1e-12 <= theta <= b + 1e-12:
            if b - a < 1e-12:
                return 1.0
            return ((math.sin(b - theta) + math.sin(theta - a))
                    / math.sin(b - a))
    return 1.0


def gate_moves() -> tuple[bool, str]:
    msgs = []
    ok = True
    classic = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for n in (4, 8, 16, 32, 64, 128):
        v = build_moves(n)
        if len(v) != n or len(set(v)) != n:
            ok = False
            msgs.append(f"n={n}: K={len(v)}")
        if n >= 8 and v[:8] != classic:
            ok = False
            msgs.append(f"n={n}: classic-8 prefix broken")
        for dr, dc in v:
            if math.gcd(abs(dr), abs(dc)) != 1:
                ok = False
                msgs.append(f"n={n}: non-coprime {(dr, dc)}")
    v16 = set(build_moves(16))
    knight = {(a * sa, b * sb) for a, b in ((2, 1), (1, 2)) for sa in (1, -1)
              for sc in (1,) for sb in (1, -1)}
    if not knight <= v16:
        ok = False
        msgs.append("n=16 lacks the knight moves")
    mx = max(max(abs(a), abs(b)) for a, b in build_moves(128))
    if mx != 8:
        ok = False
        msgs.append(f"n=128 max coordinate {mx} (expect 8)")
    return ok, "; ".join(msgs) if msgs else "K/prefix/coprime/knight/max-r all hold"


def gate_fan() -> tuple[bool, str]:
    """Straight synthetic tracks over a 0–89° azimuth fan: the follower's
    length ratio must sit within [1, analytic + 0.03] and its fan-max must be
    non-increasing in n."""
    ok = True
    worst = {}
    length = 3000.0
    for n in (4, 8, 16, 32, 64, 128):
        moves = move_table(n, 5.0, 5.0)
        wmax = 0.0
        for deg in range(0, 90, 3):
            th = math.radians(deg)
            npts = int(length / 5) + 1
            px = [5 * k * math.cos(th) for k in range(npts)]
            py = [5 * k * math.sin(th) for k in range(npts)]
            res = follow(px, py, 5.0, moves, 0, 0, 0.0, 0.0, 5.0, 5.0, length)
            if res is None:
                return False, f"n={n} az={deg}: step cap tripped"
            ratio = res["xs"][-1] / max(res["ss"][-1] - res["ss"][0], 1e-9)
            ana = analytic_ratio(moves, math.atan2(math.sin(th), math.cos(th)))
            if ratio > ana + 0.03 or ratio < 1.0 - 1e-9:
                ok = False
            if res["njump"]:
                ok = False
            wmax = max(wmax, ratio)
        worst[n] = wmax
    ns = sorted(worst)
    mono = all(worst[a] >= worst[b] - 1e-6 for a, b in zip(ns, ns[1:]))
    ok = ok and mono
    return ok, ("fan max ratio " + " ".join(f"{n}:{worst[n]:.3f}" for n in ns)
                + ("" if mono else "  NOT monotone"))


def gate_gauss() -> tuple[bool, str]:
    from e41_dem_route import gauss1d
    xs_u = [5.0 * i for i in range(200)]
    h = [100 + 20 * math.sin(i / 7.0) for i in range(200)]
    a = gauss1d(h, 10.0, 5.0)
    b = gauss1d_x(xs_u, h, 10.0)
    interior = max(abs(a[i] - b[i]) for i in range(10, 190))
    const = max(abs(v - 7.0) for v in gauss1d_x(xs_u, [7.0] * 200, 30.0))
    xs_n = [0.0]
    for i in range(1, 200):
        xs_n.append(xs_n[-1] + (2.0 if i % 3 else 7.0))
    ramp = [0.5 * x for x in xs_n]
    gr = gauss1d_x(xs_n, ramp, 10.0)
    # the trapezoidal measure keeps a ramp a ramp to second order on irregular
    # spacing — the residual is discretization, mm-scale at sigma = 10
    ramp_err = max(abs(gr[i] - ramp[i]) for i in range(30, 170))
    ok = interior < 1e-9 and const < 1e-12 and ramp_err < 1e-2
    return ok, (f"uniform-interior Δ {interior:.1e} · const {const:.1e} · "
                f"non-uniform ramp {ramp_err:.1e} m (≤ 1e-2)")


def gate_deck() -> tuple[bool, str]:
    xs = [float(i * 4) for i in range(100)]
    ss = list(xs)
    h = [50 + 10 * math.sin(i / 5.0) for i in range(100)]

    def h_orig(s):
        i = min(98, int(s / 4))
        fr = s / 4 - i
        return h[i] * (1 - fr) + h[i + 1] * fr

    # disjoint spans: each deck line bounded by ITS OWN original endpoint
    # heights (e41's invariant — endpoints read from the ORIGINAL array)
    cr = [{"xlo": 40.0, "xhi": 120.0, "kind": "bridge"},
          {"xlo": 200.0, "xhi": 300.0, "kind": "tunnel"}]
    out = apply_deck_x(xs, h, ss, cr)
    worst = 0.0
    for c in cr:
        lo = min(h_orig(c["xlo"]), h_orig(c["xhi"])) - 1e-9
        hi = max(h_orig(c["xlo"]), h_orig(c["xhi"])) + 1e-9
        for i in range(100):
            if c["xlo"] <= ss[i] <= c["xhi"]:
                worst = max(worst, max(0.0, out[i] - hi), max(0.0, lo - out[i]))
    ok = len(out) == len(h) and worst <= 1e-9
    # overlapping spans must not chain: every decked value stays inside the
    # hull of the FOUR original endpoint heights
    cro = [{"xlo": 40.0, "xhi": 120.0}, {"xlo": 100.0, "xhi": 200.0}]
    outo = apply_deck_x(xs, h, ss, cro)
    ends = [h_orig(40.0), h_orig(120.0), h_orig(100.0), h_orig(200.0)]
    lo, hi = min(ends) - 1e-9, max(ends) + 1e-9
    worst_o = max([max(0.0, outo[i] - hi, lo - outo[i]) for i in range(100)
                   if 40.0 <= ss[i] <= 200.0] + [0.0])
    ok = ok and worst_o <= 1e-9
    zero = apply_deck_x(xs, h, ss, [])
    ok = ok and zero == h
    return ok, (f"own-abutment bound {worst:.1e} m · overlap hull {worst_o:.1e} m "
                f"· no-op exact")


def run_synthetic_gates() -> bool:
    print("\nSYNTHETIC GATES")
    allok = True
    for name, fn in (("move-set mirror", gate_moves), ("azimuth fan", gate_fan),
                     ("gauss1d_x", gate_gauss), ("deck on path", gate_deck)):
        ok, msg = fn()
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} — {msg}")
        allok = allok and ok
    return allok


# ================================================================== pipeline
def prepare_ride(group: str, label: str, pts, path: str, sid,
                 cache_row: dict) -> dict | None:
    """Geometry + QA + physics for one ride.  Drops pts before returning."""
    emp = empirical_kj(pts)
    if not (is_finite(emp) and emp > 0):
        return {"skip": "no-emp"}
    if abs(emp - cache_row["emp"]) > max(0.01, 2e-4 * emp):
        return {"skip": "emp-mismatch"}          # hard join-integrity failure
    phys = build_profile([q["x"] for q in pts], [q["alt"] for q in pts])
    prof5 = resample_profile(phys, ENGINE_DX)
    total = prof5["x"][-1]
    if total < 3000:
        return {"skip": "too-short"}
    try:
        buf = (read_buf(os.path.relpath(path, DATA)) if path.startswith(DATA)
               else open(path, "rb").read())
        geo = geo_track_from_fit(buf)
    except Exception:
        return {"skip": "no-geo"}
    if len(geo) < 2:
        return {"skip": "no-geo"}
    max_gap = gap_len = 0.0
    for i in range(1, len(geo)):
        d = haversine(geo[i - 1], geo[i])
        max_gap = max(max_gap, d)
        if d > GAP_MIN:
            gap_len += geo[i]["x"] - geo[i - 1]["x"]
    gap_frac = gap_len / max(1.0, geo[-1]["x"] - geo[0]["x"])
    base = pts[0]["x"]
    span = (min(geo[-1]["x"], base + total) - max(geo[0]["x"], base)) / total
    if span < 0.99:
        return {"skip": "geo-span"}
    if gap_frac > GAP_FRAC_MAX:
        return {"skip": "gap-frac"}
    d5 = grid_positions(total, ENGINE_DX)
    g5 = lon_lat_at(geo, [d + base for d in d5])
    # the 30 m sample positions come from the ORIGINAL geo track, exactly as
    # e41 builds them — interpolating the 5 m polyline again lands metres off
    # laterally, which a noisy raster converts into phantom ascent (the smoke
    # parity gate measured 139 m of it on one FABDEM ride)
    d30 = grid_positions(total, PITCH30)
    g30 = lon_lat_at(geo, [d + base for d in d30])
    igc_ok = group in ("D3", "D4", "D5")
    if igc_ok:
        for k in range(0, len(g5["lats"]), 25):
            if not (IGC_BBOX["lonMin"] <= g5["lons"][k] <= IGC_BBOX["lonMax"]
                    and IGC_BBOX["latMin"] <= g5["lats"][k] <= IGC_BBOX["latMax"]):
                igc_ok = False
                break
    tiles = {fabdem_tile(g5["lats"][k], g5["lons"][k])
             for k in range(0, len(g5["lats"]), 200)}
    tiles.add(fabdem_tile(g5["lats"][-1], g5["lons"][-1]))
    rp = extract_regime_powers(pts, CLIMB_THR, DESC_THR)
    flat = rp["flat"]["mean"] if rp["flat"]["mean"] is not None else overall_mean_power(pts)
    if not (is_finite(flat) and flat > 0):
        return {"skip": "no-power"}
    p = {"m": cache_row["m"], "Crr": cache_row["Crr"], "CdA": cache_row["CdA"],
         "rho": RHO, "keff": KEFF, "wind": 0.0}
    pw = {"climb": rp["climb"]["mean"] if rp["climb"]["mean"] is not None else flat,
          "flat": flat,
          "descent": rp["descent"]["mean"] if rp["descent"]["mean"] is not None else 0,
          "climbThr": CLIMB_THR, "descThr": DESC_THR}
    # own30 resampled from the FULL-resolution profile, exactly as e72 does —
    # resampling the 5 m grid again lands off-node and breaks per-ride parity
    own30 = resample_profile(phys, PITCH30)
    return {"group": group, "label": label, "sid": sid,
            "corpus": CORPUS_OF.get(group, "skc"), "emp": emp,
            "total": total, "km": total / 1000, "igc_ok": igc_ok,
            "gap_frac": gap_frac, "geo_span": span, "tiles": tiles,
            "d5": array("d", d5), "d30": array("d", d30),
            "g5lon": array("d", g5["lons"]), "g5lat": array("d", g5["lats"]),
            "g30lon": array("d", g30["lons"]), "g30lat": array("d", g30["lats"]),
            "own5": {"x": array("d", prof5["x"]), "h": array("d", prof5["h"])},
            "own30": {"x": array("d", own30["x"]), "h": array("d", own30["h"])},
            "p": p, "pw": pw, "vf": flat_eq_speed(flat, p)}


# --------- path+height caches, one file pair per (grid, n) ---------
def cache_paths(grid: str, n: int) -> tuple[str, str]:
    stem = os.path.join(SCRATCH, f"e73_{grid}_n{n}{CSUFF}")
    return stem + ".bin", stem + ".meta.json"


def cache_key_of(rides: list[dict]) -> str:
    return ";".join(f"{r['corpus']}|{r['label']}|{len(r['d5'])}" for r in rides)


def load_grid_cache(grid: str, n: int, rides: list[dict]) -> dict | None:
    binp, metap = cache_paths(grid, n)
    if not (os.path.exists(binp) and os.path.exists(metap)):
        return None
    with open(metap, encoding="utf-8") as fh:
        meta = json.load(fh)
    if meta.get("version") != CACHE_VERSION or meta.get("key") != cache_key_of(rides):
        print(f"  cache {grid}_n{n}: stale — rebuilding", file=sys.stderr)
        return None
    with open(binp, "rb") as fh:
        meta["buf"] = fh.read()
    return meta


def igc_grid_setup():
    info = gdal_info(IGC_WIDE)
    return {"ulx": info["ulx"], "uly": info["uly"], "px": info["px"],
            "py": info["py"]}


def build_grid_cache(grid: str, n: int, rides: list[dict], ginfo: dict,
                     metric: dict) -> dict:
    """Follower + sampling for every ride on one (grid, n).  Stores per ride:
    xs (path chainage), ss (projected true chainage), hs (raw sampled heights)
    as float64 runs, plus the QA scalars."""
    t0 = time.time()
    binp, metap = cache_paths(grid, n)
    raster = GRID_RASTER[grid]
    entries = []
    chunks = []
    off = 0
    pend_x, pend_y = [], []            # sampling batch across rides
    pend_ref = []                      # (entry index, count)
    # n = 1 paths are the polyline itself — sampled in WGS84 exactly as e41
    # does (the parity anchor); lattice paths on the IGC grids sample in the
    # raster's own SRS (-geoloc), which is where the lattice lives.
    geoloc = grid in ("igc5", "igc30") and n > 1

    def flush():
        nonlocal pend_x, pend_y, pend_ref
        if not pend_x:
            return
        vals = sample_pts(raster, pend_x, pend_y, geoloc)
        pos = 0
        for ei, cnt in pend_ref:
            entries[ei]["_h"] = vals[pos:pos + cnt]
            pos += cnt
        pend_x, pend_y, pend_ref = [], [], []

    for ri, r in enumerate(rides):
        ent = {"label": r["label"], "ok": 0}
        entries.append(ent)
        s_total = r["total"]
        if n == 1:
            # the polyline itself, at the exact positions e41 samples (5 m
            # grids use g5, 30 m grids use g30 — both from the raw geo track)
            pitch_eff = GRID_PITCH[grid] or PITCH30
            if pitch_eff == ENGINE_DX:
                dgrid, glon, glat = r["d5"], r["g5lon"], r["g5lat"]
            else:
                dgrid, glon, glat = r["d30"], r["g30lon"], r["g30lat"]
            xs = list(dgrid)
            ss = list(dgrid)
            lats = [0.0] * len(dgrid)
            njump = 0
            coords_x, coords_y = list(glon), list(glat)
        else:
            if grid in ("igc5", "igc30"):
                en = metric[r["label"]]
                px, py = en["e"], en["n"]
                pitch = GRID_PITCH[grid]
                dxm = dym = pitch
                x0e = ginfo["ulx"] + 0.5 * pitch
                y0n = ginfo["uly"] - 0.5 * pitch
            else:
                lat0 = sum(r["g5lat"]) / len(r["g5lat"])
                kx = M_PER_DEG_LON * math.cos(math.radians(lat0))
                ky = M_PER_DEG_LAT
                psz = ginfo["px"]
                lon0, latt0 = r["g5lon"][0], r["g5lat"][0]
                px = [(v - lon0) * kx for v in r["g5lon"]]
                py = [(v - latt0) * ky for v in r["g5lat"]]
                dxm, dym = psz * kx, psz * ky
                x0e = (ginfo["ulx"] + 0.5 * psz - lon0) * kx
                y0n = (ginfo["uly"] - 0.5 * psz - latt0) * ky
            moves = move_table(n, dxm, dym)
            i0 = round((y0n - py[0]) / dym)
            j0 = round((px[0] - x0e) / dxm)
            res = follow(px, py, ENGINE_DX, moves, i0, j0, x0e, y0n,
                         dxm, dym, s_total)
            if res is None or res["njump"] > JUMP_FRAC_MAX * len(res["nodes"]):
                ent["ok"] = 0
                ent["njump"] = res["njump"] if res else -1
                continue
            mbd = {(dr, dc): sub for dr, dc, _e, _n, _l, sub in moves}
            coords, xs, ss = path_points(res, mbd)
            lats = res["lats"]
            njump = res["njump"]
            if geoloc:
                coords_x = [x0e + c * dxm for _r2, c in coords]
                coords_y = [y0n - r2 * dym for r2, c in coords]
            else:
                psz = ginfo["px"]
                coords_x = [ginfo["ulx"] + (c + 0.5) * psz for _r2, c in coords]
                coords_y = [ginfo["uly"] - (r2 + 0.5) * psz for r2, c in coords]
        ent.update({"ok": 1, "k": len(xs), "off": off, "njump": njump,
                    "len_ratio": (xs[-1] - xs[0]) / max(1e-9, ss[-1] - ss[0]),
                    "lat_p95": (sorted(lats)[int(0.95 * (len(lats) - 1))]
                                if lats else 0.0)})
        ent["_x"], ent["_s"] = xs, ss
        off += len(xs)
        pend_x.extend(coords_x)
        pend_y.extend(coords_y)
        pend_ref.append((ri, len(xs)))
        if len(pend_x) >= 200000:
            flush()
        if (ri + 1) % 100 == 0:
            print(f"    …{grid}_n{n}: {ri + 1}/{len(rides)} "
                  f"({to_fixed(time.time() - t0, 0)} s)", file=sys.stderr)
    flush()
    for ent in entries:
        if ent["ok"]:
            chunks.append(array("d", ent.pop("_x")).tobytes())
            chunks.append(array("d", ent.pop("_s")).tobytes())
            chunks.append(array("d", ent.pop("_h")).tobytes())
    buf = b"".join(chunks)
    with open(binp, "wb") as fh:
        fh.write(buf)
    meta = {"version": CACHE_VERSION, "key": cache_key_of(rides),
            "entries": [{k: v for k, v in e.items() if not k.startswith("_")}
                        for e in entries]}
    with open(metap, "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    print(f"  cache {grid}_n{n}: built in {to_fixed(time.time() - t0, 0)} s "
          f"({off} samples)", file=sys.stderr)
    return {**meta, "buf": buf}


def cache_ride(cache: dict, idx: int) -> dict | None:
    e = cache["entries"][idx]
    if not e.get("ok"):
        return None
    k, off = e["k"], e["off"]
    buf = cache["buf"]
    out = {}
    for name, slot in (("x", 0), ("s", 1), ("h", 2)):
        a = array("d")
        a.frombytes(buf[(off * 3 + slot * k) * 8:(off * 3 + slot * k + k) * 8])
        out[name] = list(a)
    out.update({q: e[q] for q in ("njump", "len_ratio", "lat_p95")})
    return out


# ================================================================== driver
def score_config(row: dict, ride: dict, name: str, xs, ss, hs_raw,
                 sigma: float, crossings, forms: dict, eps5f: float,
                 valid: float, c_mkm: float | None,
                 c_loro: float | None = None) -> None:
    """Fill one config's columns on a ride row from raw sampled heights."""
    if hs_raw is None:
        row[f"{name}_ok"] = 0
        return
    h, frac = valid_fill(list(hs_raw)) if valid is None else (list(hs_raw), valid)
    if h is None:
        row[f"{name}_ok"] = 0
        return
    row[f"{name}_valid"] = frac
    if frac < VALID_MIN:
        row[f"{name}_ok"] = 0
        return
    if sigma > 0:
        h = gauss1d_x(xs, h, sigma)
    if crossings:
        h = apply_deck_x(xs, h, ss, crossings)
    s = score_profile(xs, h, ride, forms, eps5f, c_mkm, c_loro)
    emp = ride["emp"]
    row[f"{name}_ok"] = 1
    row[f"{name}_x"] = s["x_m"]
    row[f"{name}_hplus"] = s["hplus"]
    row[f"{name}_toll"] = s["toll"]
    row[f"{name}_epsg"] = s["eps_geom"]
    row[f"{name}_ef2cl"] = s["ef2cl"]
    for m in ("v2", "ef1", "ef2", "ef4", "ef4L", "f1", "f2", "f3", "f4",
              "f5f", "patch"):
        if is_finite(s[m]):
            row[f"{name}_{m}"] = 100 * (s[m] - emp) / emp
    chain = name.split("_n")[0]
    ref = row.get(f"ref_{chain}")
    if ref and ref > 0:
        row[f"{name}_v2e"] = 100 * (s["v2"] - ref) / ref
        row[f"{name}_ef2e"] = 100 * (s["ef2"] - ref) / ref


def metric_polylines(rides: list[dict]) -> dict:
    """Batch WGS84 -> EPSG:31983 polylines for the IGC lattices, chunked."""
    out = {}
    batch_lon, batch_lat, batch_ref = [], [], []

    def flush():
        nonlocal batch_lon, batch_lat, batch_ref
        if not batch_lon:
            return
        es, ns = wgs84_to_31983(batch_lon, batch_lat)
        pos = 0
        for label, cnt in batch_ref:
            out[label] = {"e": array("d", es[pos:pos + cnt]),
                          "n": array("d", ns[pos:pos + cnt])}
            pos += cnt
        batch_lon, batch_lat, batch_ref = [], [], []

    for r in rides:
        batch_lon.extend(r["g5lon"])
        batch_lat.extend(r["g5lat"])
        batch_ref.append((r["label"], len(r["g5lon"])))
        if len(batch_lon) >= 500000:
            flush()
    flush()
    return out


def f(x, d: int = 2) -> str:
    return "—" if x is None or not is_finite(x) else to_fixed(x, d)


def ci_line(rows: list[dict], key: str, with_ci: bool = True):
    vals = [r[key] for r in rows if is_finite(r.get(key, float("nan")))]
    if not vals:
        return None
    groups = sorted({r["group"] for r in rows})
    by_g_abs = [[abs(r[key]) for r in rows if r["group"] == g
                 and is_finite(r.get(key, float("nan")))] for g in groups]
    by_g_sgn = [[r[key] for r in rows if r["group"] == g
                 and is_finite(r.get(key, float("nan")))] for g in groups]
    by_g_abs = [g for g in by_g_abs if g]
    by_g_sgn = [g for g in by_g_sgn if g]
    ma, ms = med_of([abs(v) for v in vals]), med_of(vals)
    if not with_ci:
        return ma, ms, None, None
    return ma, ms, boot_ci_strat(by_g_abs, 42), boot_ci_strat(by_g_sgn, 43)


def parse_csv_simple(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        head = [h.strip('"') for h in fh.readline().rstrip("\n").split(",")]
        return [dict(zip(head, (x.strip('"') for x in line.rstrip("\n").split(","))))
                for line in fh if line.strip()]


def fnum(s) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return float("nan")


def data_gates(rows: list[dict], pop_igc: list[dict],
               pop_fab: list[dict], cmed: dict) -> bool:
    print("\nDATA GATES")
    allok = [True]

    def say(name: str, ok: bool, extra: str = "") -> None:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
              + (f" — {extra}" if extra else ""))
        if not ok:
            allok[0] = False

    # the measured c pins must agree with e71's published CRATE rows on the
    # arms both harnesses measure (populations differ slightly — tol 0.6 m/km)
    e71p = os.path.join(RESULTS, "e71_dem_pop.csv")
    if os.path.exists(e71p) and cmed:
        crate = {}
        with open(e71p, encoding="utf-8") as fh:
            for q in csv.DictReader(fh):
                if q.get("table") == "CRATE":
                    crate[(q["pool"], q["arm"])] = float(q["c_med"])
        checks = [("own5", "BR", "D3+D4+D5", "own"),
                  ("igc5", "BR", "D3+D4+D5", "igc5"),
                  ("igc5s10", "BR", "D3+D4+D5", "igc5s10"),
                  ("igc5s30", "BR", "D3+D4+D5", "igc5s30"),
                  ("igc30", "BR", "D3+D4+D5", "igc30"),
                  ("fab30", "BR", "D3+D4+D5", "fab30"),
                  ("fab30", "EU", "D6", "fab30")]
        worst, what, npair = 0.0, "", 0
        for chain, reg, pool, arm in checks:
            a = cmed.get((chain, reg))
            b = crate.get((pool, arm))
            if a is None or b is None:
                continue
            npair += 1
            if abs(a - b) > worst:
                worst, what = abs(a - b), f"{chain}/{reg} {a:.2f} vs e71 {b:.2f}"
        say("C PINS agree with e71's CRATE rows (≤ 0.6 m/km)",
            npair > 0 and worst <= 0.6,
            f"{npair} arms, worst |Δ| {worst:.2f} m/km ({what})")

    # parity vs Entry 72 (same physics protocol, same profiles): per ride
    e72p = os.path.join(RESULTS, "e72_edgegrain" + SUFF + ".csv")
    if not os.path.exists(e72p):
        e72p = os.path.join(RESULTS, "e72_edgegrain.csv")
    if os.path.exists(e72p):
        ref = {r["ride"]: r for r in parse_csv_simple(e72p)}
        worst, what, npair = 0.0, "", 0
        for r in rows:
            q = ref.get(r["ride"])
            if q is None:
                continue
            for mine, theirs in (("own5_n1_v2", "v2_d5"), ("own30_n1_v2", "v2_d30"),
                                 ("own30_n1_patch", "patch30")):
                a, b = r.get(mine), fnum(q.get(theirs))
                if not (is_finite(a) and is_finite(b)):
                    continue
                npair += 1
                if abs(a - b) > worst:
                    worst, what = abs(a - b), f"{r['ride']} {mine}"
        say("PARITY vs e72 (own profiles, v2 + patch, per ride)",
            npair > 0 and worst <= PARITY_TOL,
            f"{npair} comparisons, worst |Δ| {worst:.4f} pp ({what})")
    else:
        say("PARITY vs e72", False, "e72_edgegrain.csv absent — run e72 first")

    # parity vs Entry 41's MODE run (protocol-free geometry columns)
    e41p = os.path.join(RESULTS, "e41_dem_route.E41_POPp1_E41_D61.csv")
    if os.path.exists(e41p):
        ref41 = {(r["corpus"], r["ride"]): r for r in parse_csv_simple(e41p)}
        worst, what, npair = 0.0, "", 0
        for r in rows:
            if not r.get("sid"):
                continue
            q = ref41.get((r["corpus"], str(r["sid"])))
            if q is None:
                continue
            for mine, theirs in (("igc5_n1_hplus", "igc5_hplus"),
                                 ("igc30_n1_hplus_rg", "igc30_hplus"),
                                 ("fab30_n1_hplus_rg", "fab30_hplus")):
                a, b = r.get(mine), fnum(q.get(theirs))
                if not (is_finite(a) and is_finite(b)):
                    continue
                npair += 1
                if abs(a - b) > worst:
                    worst, what = abs(a - b), f"{r['ride']} {mine}"
        say("PARITY vs e41 MODE (DEM h₊ at n = 1, per ride, ≤ 0.5 m)",
            npair > 0 and worst <= 0.5,
            f"{npair} comparisons, worst |Δ| {worst:.3f} m ({what})")

    # ladder sanity on the real corpora.  Registration amendment (disclosed,
    # after the smoke run, before the full run): a coarse lattice legitimately
    # CUTS CORNERS of the GPS line, so len_ratio may dip slightly below 1 —
    # the lower bound is 0.97, not 1.  And the h₊(path)/h₊(n=1) band gates
    # only the SMOOTHED IGC chain, where it checks the quantizer's geometry;
    # on fab30 the ratio is a finding (per-pixel noise read by a zigzag
    # path — forced height oscillation), reported, not gated.
    for pop, chain, rowsp, gate_band in (("IGC", "igc5s10", pop_igc, True),
                                         ("FAB", "fab30", pop_fab, False)):
        meds = {}
        for n in NDIRS:
            k = f"{chain}_n{n}_len"
            v = [r[k] for r in rowsp if is_finite(r.get(k, float("nan")))]
            if v:
                meds[n] = med_of(v)
        ns = sorted(meds)
        mono = all(meds[a] >= meds[b] - 1e-6 for a, b in zip(ns[1:], ns[2:]))
        inb = all(0.97 <= meds[n] <= 1.5 for n in ns)
        say(f"{pop} len_ratio(n) monotone non-increasing (n ≥ 4) and in [0.97, 1.5]",
            mono and inb and len(ns) == len(NDIRS),
            " ".join(f"{n}:{meds[n]:.4f}" for n in ns))
        band = {}
        for n in NDIRS:
            kk, k1 = f"{chain}_n{n}_hplus", f"{chain}_n1_hplus"
            v = [r[kk] / r[k1] for r in rowsp
                 if is_finite(r.get(kk, float("nan")))
                 and is_finite(r.get(k1, float("nan"))) and r.get(k1, 0) > 0]
            if v:
                band[n] = med_of(v)
        if gate_band:
            okb = all(0.90 <= band[n] <= 1.15 for n in band)
            say(f"{pop} h₊(path)/h₊(n=1) median within [0.90, 1.15]", okb,
                " ".join(f"{n}:{band[n]:.3f}" for n in sorted(band)))
        else:
            print(f"  [----] {pop} h₊(path)/h₊(n=1) — a FINDING on this chain, "
                  f"not a gate: "
                  + " ".join(f"{n}:{band[n]:.3f}" for n in sorted(band)))
    return allok[0]


def emit_figures(pop_igc: list[dict], pop_fab: list[dict]) -> None:
    os.makedirs(FIGS, exist_ok=True)

    def curve(rows, chain):
        out = {}
        for n in NDIRS:
            k = f"{chain}_n{n}_ef2"
            v = [r[k] for r in rows if is_finite(r.get(k, float("nan")))]
            kv = f"{chain}_n{n}_v2"
            v2 = [r[kv] for r in rows if is_finite(r.get(kv, float("nan")))]
            if v:
                out[n] = (med_of([abs(x) for x in v]), med_of(v),
                          med_of([abs(x) for x in v2]) if v2 else float("nan"))
        return out

    panels = [("IGC-SP 5 m (σ10) · D3–D5", curve(pop_igc, "igc5s10")),
              ("FABDEM 30 m · D3–D6", curve(pop_fab, "fab30"))]
    W, H, ML, MB, MT, MR, GAP = 900, 380, 56, 50, 30, 14, 40
    pw = (W - ML - MR - GAP) / 2
    ally = [v for _t, c in panels for pair in c.values() for v in pair]
    ymax = max(ally + [1.0]) * 1.15
    ymin = min(ally + [0.0]) * 1.15 - 0.2
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'font-family="sans-serif" font-size="12">',
           f'<rect width="{W}" height="{H}" fill="white"/>']
    for pi, (title, cv) in enumerate(panels):
        x_off = ML + pi * (pw + GAP)

        def X(n):
            return x_off + (math.log2(n) if n > 1 else -0.6) / 7.7 * pw + 0.08 * pw

        def Y(v):
            return MT + (ymax - v) / (ymax - ymin) * (H - MT - MB)

        step = max(1, int((ymax - ymin) / 6))
        for v in range(int(math.floor(ymin)), int(ymax) + 1, step):
            svg.append(f'<line x1="{x_off}" y1="{Y(v):.1f}" x2="{x_off + pw:.1f}" '
                       f'y2="{Y(v):.1f}" stroke="#eee"/>')
            if pi == 0:
                svg.append(f'<text x="{x_off - 6}" y="{Y(v) + 4:.1f}" '
                           f'text-anchor="end">{v}</text>')
        svg.append(f'<line x1="{x_off}" y1="{Y(0):.1f}" x2="{x_off + pw:.1f}" '
                   f'y2="{Y(0):.1f}" stroke="#999"/>')
        for n in NDIRS:
            svg.append(f'<text x="{X(n):.1f}" y="{H - MB + 16}" '
                       f'text-anchor="middle">{n}</text>')
        svg.append(f'<text x="{x_off + pw / 2:.0f}" y="{MT - 10}" '
                   f'text-anchor="middle" font-weight="bold">{title}</text>')
        ns = [n for n in NDIRS if n in cv]
        pl_a = " ".join(f"{X(n):.1f},{Y(cv[n][0]):.1f}" for n in ns)
        pl_s = " ".join(f"{X(n):.1f},{Y(cv[n][1]):.1f}" for n in ns)
        pl_v = " ".join(f"{X(n):.1f},{Y(cv[n][2]):.1f}" for n in ns
                        if is_finite(cv[n][2]))
        svg.append(f'<polyline fill="none" stroke="#999" stroke-width="1.4" '
                   f'points="{pl_v}"/>')
        svg.append(f'<polyline fill="none" stroke="#0072B2" stroke-width="2.2" '
                   f'points="{pl_a}"/>')
        svg.append(f'<polyline fill="none" stroke="#D55E00" stroke-width="2.2" '
                   f'stroke-dasharray="6 3" points="{pl_s}"/>')
        for n in ns:
            svg.append(f'<circle cx="{X(n):.1f}" cy="{Y(cv[n][0]):.1f}" r="3.4" '
                       f'fill="#0072B2"/>')
            svg.append(f'<circle cx="{X(n):.1f}" cy="{Y(cv[n][1]):.1f}" r="3.4" '
                       f'fill="#D55E00"/>')
    svg.append(f'<text x="{ML + 8}" y="{MT + 16}" fill="#0072B2">eF2 med |Δ%| vs measured</text>')
    svg.append(f'<text x="{ML + 8}" y="{MT + 32}" fill="#D55E00">eF2 signed bias</text>')
    svg.append(f'<text x="{ML + 8}" y="{MT + 48}" fill="#999">v2Edge (deployed) med |Δ%|</text>')
    svg.append(f'<text x="{W / 2:.0f}" y="{H - 10}" text-anchor="middle">'
               f'directions n (1 = own polyline at lattice pitch; log₂ axis)</text>')
    svg.append('</svg>')
    with open(os.path.join(FIGS, "fig-p3-dirs" + SUFF + ".svg"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(svg))

    # chain ladder dot plot (IGC pop, n = 8 + the n = 1 controls), eF2
    rows_c = [("own5 (n=1)", "own5_n1"), ("igc5 (n=8)", f"igc5_n{BASE_N}"),
              ("igc5s10 (n=8)", f"igc5s10_n{BASE_N}"),
              ("igc5s30 (n=8)", f"igc5s30_n{BASE_N}"),
              ("igc30 (n=8)", f"igc30_n{BASE_N}"),
              ("fab30 (n=8)", f"fab30_n{BASE_N}"),
              ("fab30s30 (n=8)", f"fab30s30_n{BASE_N}"),
              ("igc5s10+portal", f"igc5s10_n{BASE_N}p")]
    meds = []
    for lab, cfg in rows_c:
        v = [r[f"{cfg}_ef2"] for r in pop_igc
             if is_finite(r.get(f"{cfg}_ef2", float("nan")))]
        if v:
            meds.append((lab, med_of([abs(x) for x in v]), med_of(v)))
    W2, H2, ML2, MT2, MB2, MR2 = 620, 40 + 26 * len(meds) + 50, 150, 34, 44, 20
    xmax = max([m[1] for m in meds] + [abs(m[2]) for m in meds] + [1]) * 1.2
    xmin = min([m[2] for m in meds] + [0]) * 1.2 - 0.3

    def X2(v):
        return ML2 + (v - xmin) / (xmax - xmin) * (W2 - ML2 - MR2)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W2} {H2}" '
           f'font-family="sans-serif" font-size="12">',
           f'<rect width="{W2}" height="{H2}" fill="white"/>',
           f'<line x1="{X2(0):.1f}" y1="{MT2}" x2="{X2(0):.1f}" '
           f'y2="{H2 - MB2}" stroke="#999"/>']
    for i, (lab, ma, ms) in enumerate(meds):
        y = MT2 + 14 + 26 * i
        svg.append(f'<text x="{ML2 - 8}" y="{y + 4}" text-anchor="end">{lab}</text>')
        svg.append(f'<line x1="{X2(min(0, ms)):.1f}" y1="{y}" '
                   f'x2="{X2(max(0, ms)):.1f}" y2="{y}" stroke="#f0c9b0"/>')
        svg.append(f'<circle cx="{X2(ma):.1f}" cy="{y}" r="4" fill="#0072B2"/>')
        svg.append(f'<circle cx="{X2(ms):.1f}" cy="{y}" r="4" fill="#D55E00"/>')
    xstep = max(1, round((xmax - xmin) / 8))
    v0 = int(math.floor(xmin / xstep)) * xstep
    for v in range(v0, int(xmax) + 1, xstep):
        svg.append(f'<text x="{X2(v):.1f}" y="{H2 - MB2 + 16}" '
                   f'text-anchor="middle">{v}</text>')
    svg.append(f'<text x="{(ML2 + W2 - MR2) / 2:.0f}" y="{H2 - 8}" '
               f'text-anchor="middle">eF2 Δ% vs measured (blue = med |Δ%|, '
               f'orange = signed) · IGC pop</text>')
    svg.append('</svg>')
    with open(os.path.join(FIGS, "fig-p3-chain" + SUFF + ".svg"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(svg))
    print(f"  wrote fig-p3-dirs{SUFF}.svg + fig-p3-chain{SUFF}.svg")


def write_csv(rows: list[dict]) -> None:
    if not rows:
        print("no rows")
        return
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    name = "e73_gridpath" + SUFF + ".csv"
    with open(os.path.join(RESULTS, name), "w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(
                (f'"{r[k]}"' if isinstance(r[k], str)
                 else ("" if k not in r or r[k] is None or not is_finite(r[k])
                       else to_fixed(r[k], 4)))
                if k in r else "" for k in cols) + "\n")
    print(f"\nwrote {name} ({len(rows)} rides)")


def joint(pop: list[dict], ka: str, kb: str, la: str, lb: str) -> None:
    """Paired per-ride comparison of a route form and its edge realisation."""
    st = [r for r in pop if is_finite(r.get(ka, float("nan")))
          and is_finite(r.get(kb, float("nan")))]
    if not st:
        return
    va = [r[ka] for r in st]
    vb = [r[kb] for r in st]
    w = sum(1 for r in st if abs(r[kb]) < abs(r[ka]))
    l_ = sum(1 for r in st if abs(r[kb]) > abs(r[ka]))
    print(f"  {la:<14} {f(med_of([abs(x) for x in va]))} ({f(med_of(va))})"
          f"   {lb:<18} {f(med_of([abs(x) for x in vb]))} ({f(med_of(vb))})"
          f"   edge closer {w}/{w + l_} (p = {to_fixed(sign_p(w, l_), 4)})")


def report(rows: list[dict], pop_igc: list[dict], pop_fab: list[dict],
           forms: dict, eps5f: float, cmed: dict) -> None:
    print("\n" + "=" * 96)
    print("ENTRY 73 — the discrete-routing ladder (matched ridden path; paper 3 §3.2–3.3)")
    print("=" * 96)
    print(f"physics: A-chain per-ride m̂/Ĉrr/ĈdA · ρ {RHO} · k_eff {KEFF} · wind 0 · "
          f"G {G}")
    print(f"forms: F1 ε {forms['F1']['eps']:g} · F2 ε {forms['F2']['eps']:g} · "
          f"F3 (ε {forms['F3']['eps']:g}, τ {forms['F3']['tau']:g}) · "
          f"F4 (ε {forms['F4']['eps']:g}, c {forms['F4']['c']:g}) · "
          f"F5f (ε {eps5f:g}, τ_n {F5F_FLOOR:g}, v_b ∞)   [all read from CSVs]")
    print("edge family: eF1/eF2 flat-ε per-edge (article 1's recommendation) · "
          "eF4 = eF2 + per-edge noise deduction at the chain's MEASURED c pin")
    print("\nC PINS — measured c(τ=2) per chain × region, m/km "
          "(median over the chain's n = 1 profiles):")
    for c, reg in sorted(cmed):
        print(f"  {c:<10} {reg}  {f(cmed[(c, reg)])}")

    for title, pop, chain in (("IGC pop (D3–D5, igc_ok)", pop_igc, "igc5s10"),
                              ("FABDEM pop (D3–D6)", pop_fab, "fab30")):
        if not pop:
            continue
        print(f"\n── {title} · n = {len(pop)} rides "
              f"(complete across every arm of this population) ──")
        print(f"\nDIRS LADDER — chain {chain}, eF2 vs measured "
              f"(v2 = deployed grade-local ε, median only):")
        print("n".rjust(5) + "med|Δ%| [95% CI]".rjust(22) + "signed [95% CI]".rjust(22)
              + "v2".rjust(8) + "len_ratio".rjust(11) + "α·Δx pp".rjust(9)
              + "vs-est Δ%".rjust(11))
        for n in NDIRS:
            cfg = f"{chain}_n{n}"
            got = ci_line(pop, f"{cfg}_ef2")
            if got is None:
                continue
            ma, ms, cia, cis = got
            v2m = med_of([abs(r[f"{cfg}_v2"]) for r in pop
                          if is_finite(r.get(f"{cfg}_v2", float("nan")))])
            lr = med_of([r[f"{cfg}_len"] for r in pop
                         if is_finite(r.get(f"{cfg}_len", float("nan")))])
            adx = med_of([r["alpha_kjm"] * (r[f"{cfg}_x"] - r[f"{chain}_n1_x"])
                          / r["emp"] * 100 for r in pop
                          if is_finite(r.get(f"{cfg}_x", float("nan")))
                          and is_finite(r.get(f"{chain}_n1_x", float("nan")))])
            ve = med_of([r[f"{cfg}_ef2e"] for r in pop
                        if is_finite(r.get(f"{cfg}_ef2e", float("nan")))])
            print(f"{n}".rjust(5)
                  + f"{f(ma)} [{f(cia[0])},{f(cia[1])}]".rjust(22)
                  + f"{f(ms)} [{f(cis[0])},{f(cis[1])}]".rjust(22)
                  + f(v2m).rjust(8)
                  + f(lr, 4).rjust(11) + f(adx).rjust(9) + f(ve).rjust(11))

        print(f"\nMODELS at the base config ({chain}_n{BASE_N}) — Δ% vs measured "
              f"(f5f/patch journal-only, F5 out of paper 3's scope):")
        print("model".ljust(8) + "med|Δ%|".rjust(10) + "signed".rjust(10))
        for m in ("v2", "ef1", "ef2", "ef4", "ef4L", "f1", "f2", "f3", "f4",
                  "f5f", "patch"):
            k = f"{chain}_n{BASE_N}_{m}"
            v = [r[k] for r in pop if is_finite(r.get(k, float("nan")))]
            if v:
                print(m.ljust(8) + f(med_of([abs(x) for x in v])).rjust(10)
                      + f(med_of(v)).rjust(10))

        print(f"\nJOINT — route form vs its edge realisation, per ride "
              f"(med|Δ%| (signed) each):")
        base = f"{chain}_n{BASE_N}"
        joint(pop, f"{base}_f1", f"{base}_ef1", f"F1[{chain}]", "eF1")
        joint(pop, f"{base}_f2", f"{base}_ef2", f"F2[{chain}]", "eF2")
        joint(pop, f"{base}_f4", f"{base}_ef4", f"F4[{chain}]", "eF4(c pin)")
        joint(pop, f"{base}_f4", f"{base}_ef4L", f"F4[{chain}]", "eF4L(LORO)")
        if chain == "igc5s10":
            joint(pop, f"igc5_n{BASE_N}_f3", f"igc5s10_n{BASE_N}_ef2",
                  "F3[igc5 raw]", "eF2[σ10 map]")
            joint(pop, f"igc5_n{BASE_N}_f3", f"igc5s30_n{BASE_N}_ef2",
                  "F3[igc5 raw]", "eF2[σ30 map]")
        else:
            joint(pop, f"fab30_n{BASE_N}_f3", f"fab30s30_n{BASE_N}_ef2",
                  "F3[fab30 raw]", "eF2[σ30 map]")

    # ---- the eF family vs n, per DTM (raw chain; eF2* = the treated map) ----
    def ef_vs_n(pop, title, cols):
        print(f"\nEF FAMILY vs n — {title} — med|Δ%| (signed):")
        print("n".rjust(5) + "".join(lbl.rjust(18) for lbl, _c in cols))
        for n in NDIRS:
            line = f"{n}".rjust(5)
            for _lbl, chain in cols:
                m = {"eF1": "ef1", "eF2": "ef2", "eF4": "ef4",
                     "eF4L": "ef4L"}.get(_lbl, "ef2")
                k = f"{chain}_n{n}_{m}"
                v = [r[k] for r in pop if is_finite(r.get(k, float("nan")))]
                line += (f"{f(med_of([abs(x) for x in v]))} "
                         f"({f(med_of(v))})").rjust(18) if v else "—".rjust(18)
            print(line)

    if pop_igc:
        ef_vs_n(pop_igc, "IGC-SP 5 m (IGC pop)",
                [("eF1", "igc5"), ("eF2", "igc5"), ("eF2*σ10", "igc5s10"),
                 ("eF2*σ30", "igc5s30"), ("eF4", "igc5"), ("eF4L", "igc5")])
    if pop_fab:
        ef_vs_n(pop_fab, "FABDEM 30 m (FABDEM pop)",
                [("eF1", "fab30"), ("eF2", "fab30"),
                 ("eF2*σ30", "fab30s30"), ("eF4", "fab30"),
                 ("eF4L", "fab30")])

    # ---- the ε-side robustness slice: the e52 seed-48 TEST half only (the
    # published ε's were fitted on the train half; registration v4) ----
    try:
        from e52_split import load as _e52_load, split as _e52_split
        _test_ids = {r["ride"] for r in _e52_split(_e52_load())[1]}
        print("\nTEST-HALF SLICE (e52 seed-48 test rides only) — base configs, "
              "med|Δ%| (signed):")
        for lbl_, pop_, base_ in (("IGC", pop_igc, f"igc5s10_n{BASE_N}"),
                                  ("FAB", pop_fab, f"fab30_n{BASE_N}")):
            sub = [r for r in pop_ if r["ride"] in _test_ids]
            cells = []
            for m in ("v2", "ef2", "ef4", "ef4L", "f3"):
                v = [r[f"{base_}_{m}"] for r in sub
                     if is_finite(r.get(f"{base_}_{m}", float("nan")))]
                cells.append(f"{m} {f(med_of([abs(x) for x in v]))} "
                             f"({f(med_of(v))})" if v else f"{m} —")
            print(f"  {lbl_} (n={len(sub)}): " + " · ".join(cells))
    except Exception as exc:
        print(f"  (test-half slice unavailable: {type(exc).__name__})")

    if pop_igc:
        print("\nTERRAIN LADDER (IGC pop, n = 8; n = 1 anchors in brackets) — "
              "v2 · eF2 · eF4 · F3 · F4, med|Δ%| (signed):")
        for chain in ("own5", "igc5", "igc5s10", "igc5s30", "igc30",
                      "fab30", "fab30s30"):
            for n in ((1,) if chain == "own5" else (1, BASE_N)):
                cfg = f"{chain}_n{n}"
                cells = []
                for m in ("v2", "ef2", "ef4", "f3", "f4"):
                    v = [r[f"{cfg}_{m}"] for r in pop_igc
                         if is_finite(r.get(f"{cfg}_{m}", float("nan")))]
                    cells.append(f"{f(med_of([abs(x) for x in v]))} "
                                 f"({f(med_of(v))})" if v else "—")
                tag = f"{chain} n={n}"
                print(("  [" + tag + "]" if n == 1 else "  " + tag).ljust(22)
                      + " · ".join(c.rjust(15) for c in cells))

        base = f"igc5s10_n{BASE_N}"
        pb = [r for r in pop_igc
              if is_finite(r.get(f"{base}_ef2", float("nan")))
              and is_finite(r.get(f"{base}p_ef2", float("nan")))]
        if pb:
            w = sum(1 for r in pb if abs(r[f"{base}p_ef2"]) < abs(r[f"{base}_ef2"]))
            l_ = sum(1 for r in pb if abs(r[f"{base}p_ef2"]) > abs(r[f"{base}_ef2"]))
            touched = [r for r in pb if (r.get("n_spans") or 0) > 0]
            wt = sum(1 for r in touched
                     if abs(r[f"{base}p_ef2"]) < abs(r[f"{base}_ef2"]))
            lt = sum(1 for r in touched
                     if abs(r[f"{base}p_ef2"]) > abs(r[f"{base}_ef2"]))
            print(f"\nPORTALS on the base path — {base}p vs {base} (eF2): closer on "
                  f"{w}/{w + l_} (sign p = {to_fixed(sign_p(w, l_), 4)}); on the "
                  f"{len(touched)} span-touched rides {wt}/{wt + lt} "
                  f"(p = {to_fixed(sign_p(wt, lt), 4)})")
            for m in ("ef2", "f3"):
                raw = [r[f"{base}_{m}"] for r in touched]
                cor = [r[f"{base}p_{m}"] for r in touched]
                if raw:
                    print(f"  {m}: raw {f(med_of([abs(x) for x in raw]))} "
                          f"({f(med_of(raw))}) → deck {f(med_of([abs(x) for x in cor]))} "
                          f"({f(med_of(cor))})   [touched rides]")


def main() -> None:
    t0 = time.time()
    if GATES_ONLY:
        sys.exit(0 if run_synthetic_gates() else 1)
    print(f"Entry 73 — the discrete-routing ladder"
          + ("   [SMOKE]" if SMOKE else ""))
    if ONLY:
        print(f"!! NON-AUTHORITATIVE — E73_ONLY={sorted(ONLY)} (completeness "
              f"and gates run on a restricted arm set)")
    syn_ok = run_synthetic_gates()

    forms = load_forms()
    eps5f = load_f5f_eps()
    cache_rows = load_cache_rows()

    # ---- pass A: corpus walk, geometry, physics ----
    print("\npass A — corpus walk + geometry", file=sys.stderr)
    rides: list[dict] = []
    funnel: dict[str, dict[str, int]] = {}
    smoke_seen: dict[str, int] = {}
    for group, label, pts, path, sid in walk_rides():
        if SMOKE:
            if smoke_seen.get(group, 0) >= SMOKE_N:
                continue
            smoke_seen[group] = smoke_seen.get(group, 0) + 1
        fn = funnel.setdefault(group, {})
        fn["candidate"] = fn.get("candidate", 0) + 1
        c = cache_rows.get(label)
        if c is None:
            fn["no-cache"] = fn.get("no-cache", 0) + 1
            continue
        try:
            r = prepare_ride(group, label, pts, path, sid, c)
        except Exception:
            r = {"skip": "unparseable"}
        if r is None or "skip" in r:
            k = (r or {}).get("skip", "unparseable")
            fn[k] = fn.get(k, 0) + 1
            continue
        rides.append(r)
    del cache_rows
    print(f"  {len(rides)} rides prepared ({to_fixed(time.time() - t0, 0)} s)",
          file=sys.stderr)

    pop_igc_r = [r for r in rides if r["group"] in ("D3", "D4", "D5") and r["igc_ok"]]
    pop_fab_r = rides
    tiles = set()
    for r in pop_fab_r:
        tiles |= r["tiles"]
    fab_ok = ensure_fabdem(tiles)

    def wanted(chain, n, portal):
        return not ONLY or cfg_name(chain, n, portal) in ONLY

    igc_cfgs = [(c, n, p) for c, n, p in IGC_CONFIGS if wanted(c, n, p)]
    fab_cfgs = [(c, n, p) for c, n, p in FAB_CONFIGS if wanted(c, n, p)]

    # ---- portal spans (offline) ----
    spans = load_spans()
    need_portal = any(p for _c, _n, p in igc_cfgs)
    crossings_of: dict[str, list | None] = {}
    if need_portal:
        for r in pop_igc_r:
            crossings_of[r["label"]] = spans_for(r, spans)
        save_spans(spans)
        cov = sum(1 for v in crossings_of.values() if v is not None)
        print(f"  portal spans: {cov}/{len(pop_igc_r)} rides covered (offline)",
              file=sys.stderr)

    # ---- grid caches ----
    grids_needed: dict[tuple, list[dict]] = {}
    for c, n, _p in igc_cfgs:
        if c in CHAINS:
            grids_needed.setdefault((CHAINS[c][0], n), pop_igc_r)
    for c, n, _p in fab_cfgs:
        if c in CHAINS:
            grids_needed.setdefault((CHAINS[c][0], n), pop_fab_r)
    # fab grids must span the union population (IGC anchors read them too)
    for (g_, n_), pop in list(grids_needed.items()):
        if g_ == "fab30":
            grids_needed[(g_, n_)] = pop_fab_r

    ginfo = {}
    if any(g_ in ("igc5", "igc30") for g_, _n in grids_needed):
        ginfo["igc"] = igc_grid_setup()
    if any(g_ == "fab30" for g_, _n in grids_needed) and fab_ok:
        ginfo["fab"] = gdal_info(FABDEM_VRT)

    metric = {}
    if any(g_ in ("igc5", "igc30") and n_ > 1 for g_, n_ in grids_needed):
        print("pass B — polylines to EPSG:31983", file=sys.stderr)
        metric = metric_polylines(pop_igc_r)

    # ---- rows skeleton ----
    rows_by = {}
    rows = []
    for r in rides:
        cross = crossings_of.get(r["label"])
        vfk = r["vf"]
        mg = r["p"]["m"] * G
        a_roll = mg * r["p"]["Crr"] / r["p"]["keff"]
        a_aero = 0.5 * r["p"]["rho"] * r["p"]["CdA"] * vfk * vfk / r["p"]["keff"]
        row = {"group": r["group"], "ride": r["label"], "corpus": r["corpus"],
               "sid": str(r["sid"] or ""), "emp": r["emp"], "km": r["km"],
               "igc_ok": int(r["igc_ok"]),
               "portal_ok": int(cross is not None) if need_portal else "",
               "n_spans": len(cross) if cross else 0,
               "span_m": span_metres(cross) if cross else 0.0,
               "alpha_kjm": (a_roll + a_aero) / 1000}
        rows_by[r["label"]] = row
        rows.append(row)

    cfg_all = ([(c, n, p, "igc") for c, n, p in igc_cfgs if c in CHAINS]
               + [(c, n, p, "fab") for c, n, p in fab_cfgs if c in CHAINS])

    def region(r: dict) -> str:
        return "EU" if r["group"].startswith("D6") else "BR"

    # ---- pass C1: the measured noise pins — c(τ=2) per chain × region,
    # from each chain's OWN n = 1 profiles (paper 2's convention, eq. L3).
    # eF4's c is measured geometry, never fitted to energy (the E68/E69
    # measured-pin doctrine); cross-checked against e71's CRATE rows below.
    print("pass C1 — chain noise pins", file=sys.stderr)
    cn: dict[tuple, list] = {}          # (chain, region, group) -> values

    def note_cn(label: str, chain: str, reg: str, xs_, h_) -> None:
        km = (xs_[-1] - xs_[0]) / 1000
        if km <= 0:
            return
        c_ = (sum_ascent(h_) - sum_ascent(deadband(h_, 2.0))) / km
        cn.setdefault((chain, reg, rows_by[label]["group"]), []).append(c_)
        rows_by[label][f"cn_{chain}"] = c_

    for r in rides:
        for chain, prof in (("own5", r["own5"]), ("own30", r["own30"])):
            note_cn(r["label"], chain, region(r), list(prof["x"]), list(prof["h"]))
    for (g_, n_) in sorted(grids_needed, key=lambda t: (t[1], t[0])):
        if n_ != 1 or (g_ == "fab30" and not fab_ok):
            continue
        pop = grids_needed[(g_, n_)]
        gi = ginfo["fab"] if g_ == "fab30" else ginfo["igc"]
        cache = load_grid_cache(g_, 1, pop)
        if cache is None:
            cache = build_grid_cache(g_, 1, pop, gi, metric)
        chains_here = sorted({c for c, _n, _p, _s in cfg_all
                              if CHAINS[c][0] == g_})
        for idx, r in enumerate(pop):
            cr = cache_ride(cache, idx)
            if cr is None:
                continue
            hf, frac = valid_fill(cr["h"])
            if hf is None or frac < VALID_MIN:
                continue
            for c in chains_here:
                sigma = CHAINS[c][1]
                hh = gauss1d_x(cr["x"], hf, sigma) if sigma > 0 else hf
                note_cn(r["label"], c, region(r), cr["x"], hh)
        cache["buf"] = b""
    # pooled pins per (chain, region) — the sensitivity arm — and the LORO
    # pins per (chain, region, group): the OTHER riders' values, ride-weighted
    # (E59's convention), the arm the paper quotes (registration v4)
    CMED: dict[tuple, float] = {}
    LORO: dict[tuple, float] = {}
    for (chain, reg, _g) in list(cn):
        if (chain, reg) not in CMED:
            pool = [v for (c2, r2, _g2), vs in cn.items()
                    if (c2, r2) == (chain, reg) for v in vs]
            CMED[(chain, reg)] = med_of(pool)
    for (chain, reg, grp) in list(cn):
        others = [v for (c2, r2, g2), vs in cn.items()
                  if (c2, r2) == (chain, reg) and g2 != grp for v in vs]
        if others:
            LORO[(chain, reg, grp)] = med_of(others)
    print("  c pins (m/km, τ = 2): "
          + " · ".join(f"{c}/{reg} {CMED[(c, reg)]:.2f}"
                       for c, reg in sorted(CMED)), file=sys.stderr)

    # ---- pass C2: scoring ----
    print("pass C2 — scoring", file=sys.stderr)
    for r in rides:
        row = rows_by[r["label"]]
        for chain, prof in (("own5", r["own5"]), ("own30", r["own30"])):
            if not wanted(chain, 1, False):
                continue
            xs = list(prof["x"])
            hs = list(prof["h"])
            row[f"ref_{chain}"] = ref_f4(xs, hs, r, forms)
            name = f"{chain}_n1"
            row[f"{name}_len"] = 1.0
            row[f"{name}_lat"] = 0.0
            row[f"{name}_njump"] = 0
            score_config(row, r, name, xs, xs, hs, 0.0, None, forms, eps5f,
                         1.0, CMED.get((chain, region(r))),
                         LORO.get((chain, region(r), r["group"])))

    # ---- DEM configs, one (grid, n) cache at a time, n ascending ----
    for (g_, n_) in sorted(grids_needed, key=lambda t: (t[1], t[0])):
        pop = grids_needed[(g_, n_)]
        if g_ == "fab30" and not fab_ok:
            continue
        gi = ginfo["fab"] if g_ == "fab30" else ginfo["igc"]
        cache = load_grid_cache(g_, n_, pop)
        if cache is None:
            cache = build_grid_cache(g_, n_, pop, gi, metric)
        cfgs_here = []
        for c, n, p, _s in cfg_all:
            if CHAINS[c][0] == g_ and n == n_ and (c, n, p) not in cfgs_here:
                cfgs_here.append((c, n, p))
        # every chain on this grid shares the raw heights; sigma varies
        for idx, r in enumerate(pop):
            cr = cache_ride(cache, idx)
            row = rows_by[r["label"]]
            for c, n, portal in cfgs_here:
                name = cfg_name(c, n, portal)
                if cr is None:
                    row[f"{name}_ok"] = 0
                    continue
                sigma = CHAINS[c][1]
                if n_ == 1 and not portal:
                    # chain refs come from the n = 1 profile
                    h_ref, frac = valid_fill(cr["h"])
                    if h_ref is not None and frac >= VALID_MIN:
                        hh = gauss1d_x(cr["x"], h_ref, sigma) if sigma > 0 else h_ref
                        row[f"ref_{c}"] = ref_f4(cr["x"], hh, r, forms)
                        # e41's 30 m arms live REGRIDDED on the ride's 5 m
                        # grid, which clips extrema between nodes (its
                        # synthetic gate aligned exactly and missed it; the
                        # clip is ~1% of h₊ on igc30, ~5% on fab30).  e73
                        # scores the honest 30 m profile; the parity gate
                        # compares under e41's convention via this column.
                        if g_ in ("igc30", "fab30") and c == g_:
                            row[f"{c}_n1_hplus_rg"] = sum_ascent(
                                regrid(cr["x"], h_ref, list(r["d5"])))
                row[f"{name}_len"] = cr["len_ratio"]
                row[f"{name}_lat"] = cr["lat_p95"]
                row[f"{name}_njump"] = cr["njump"]
                cross = crossings_of.get(r["label"]) if portal else None
                if portal and cross is None:
                    row[f"{name}_ok"] = 0
                    continue
                score_config(row, r, name, cr["x"], cr["s"], cr["h"], sigma,
                             cross, forms, eps5f, None,
                             CMED.get((c, region(r))),
                             LORO.get((c, region(r), r["group"])))
        cache["buf"] = b""      # free
        print(f"  scored {g_}_n{n_} ({to_fixed(time.time() - t0, 0)} s)",
              file=sys.stderr)

    # ---- population completeness (the portal arm must not gate the whole
    # population — its OSM coverage is a property of the tile cache, not of
    # the ride; the portal comparison pairs within its own covered subset) ----
    def complete(row, cfgs):
        return all(row.get(f"{cfg_name(c, n, p)}_ok") == 1
                   for c, n, p in cfgs if not p)

    for row in rows:
        r_igc = row["igc_ok"] and row["group"] in ("D3", "D4", "D5")
        row["pop_igc"] = int(bool(r_igc and complete(row, igc_cfgs)))
        row["pop_fab"] = int(complete(row, fab_cfgs))
    pop_igc = [row for row in rows if row["pop_igc"]]
    pop_fab = [row for row in rows if row["pop_fab"]]

    write_csv(rows)
    print("\nCORPUS FUNNEL:")
    for g_ in GROUPS:
        fn = funnel.get(g_) or {}
        kept = sum(1 for r in rides if r["group"] == g_)
        print(f"  {g_:12s} cand={fn.get('candidate', 0):4d} kept={kept:4d} "
              + " ".join(f"{k}={v}" for k, v in sorted(fn.items())
                         if k != "candidate"))
    print(f"\nPOPULATIONS — IGC {len(pop_igc)} · FABDEM {len(pop_fab)} "
          f"(all-arms-complete)")
    print("\nPER-CONFIG DROPOUTS (candidates for the pop with ok = 1):")
    for label_, pop_rows, cfgs in (("IGC", [row for row in rows if row["igc_ok"]
                                            and row["group"] in ("D3", "D4", "D5")],
                                    igc_cfgs),
                                   ("FAB", rows, fab_cfgs)):
        parts = []
        for c, n, p in cfgs:
            nm = cfg_name(c, n, p)
            nok = sum(1 for row in pop_rows if row.get(f"{nm}_ok") == 1)
            if nok < len(pop_rows):
                parts.append(f"{nm}={nok}/{len(pop_rows)}")
        print(f"  {label_}: " + (" ".join(parts) if parts else "no dropouts"))
    report(rows, pop_igc, pop_fab, forms, eps5f, CMED)
    if pop_igc or pop_fab:
        emit_figures(pop_igc, pop_fab)
    gates_ok = data_gates(rows, pop_igc, pop_fab, CMED)
    print(f"\ntotal {to_fixed((time.time() - t0) / 60, 1)} min")
    if SMOKE:
        print("[SMOKE — gates reported, not asserted]")
        sys.exit(0)
    sys.exit(0 if (syn_ok and gates_ok) else 1)


if __name__ == "__main__":
    main()
