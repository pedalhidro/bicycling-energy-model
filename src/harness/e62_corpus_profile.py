#!/usr/bin/env python3
"""Entry 62 — descriptive/diagnostic profile of D3-D6, and the pairplot.

Registered in MODEL_COMPARISON_JOURNAL.md (Entry 62). Every corpus statistic
the papers report so far is an ERROR statistic: med |D%|, a bias, an eps. What
the corpora ARE -- how long the rides are, how much of the time is moving, how
hard they are ridden -- has never been written down, so a reader cannot tell
whether D6's higher eps comes with a different KIND of riding, and neither
could we.

This computes six per-ride aggregates over the SAME population paper 1 fits
(e44_scurve.corpus_rides, i.e. the D3-D6 selection, D1/D2 excluded as
re-processings of D5), reports 10/50/90 percentiles per corpus, and renders a
seaborn-style pairplot with the corpus as hue.

THE AGGREGATES, defined once here (registration; do not tune):

  km        distance, x[-1] - x[0], km
  hplus     elevation gain, sum of positive dh on the ENGINE_DX-resampled,
            tau=2 m deadbanded profile (what the forms themselves see)
  gasc      mean ascent grade, hplus / (climbing horizontal distance), %
  kj        pedal work done, sum(P*dt) over the whole ride (empirical_kj)
  t_mov     moving time, sum of dt over MOVING samples, hours
  movfrac   t_mov / t_rec, where t_rec = sum of ALL dt
  pow_mov   mean power over moving samples that carry power, dt-weighted,
            ZEROS INCLUDED (coasting is part of how hard a ride is ridden)
  v_mov     mean speed over moving samples, dt-weighted, km/h
  hr_mov    mean heart rate over moving samples that carry hr, dt-weighted, bpm

MOVING is v >= VSTOP = 0.5 km/h, the same gate Entry 44 registered and the
same one fit.py's regime power uses. It is applied to the SAMPLE, not to a
smoothed speed.

TWO MEASUREMENT CAVEATS, both of which the numbers must be read against:

  1. movfrac is a floor on stopped time, not a measurement of it. dt is the
     pause-clamped weight (>10 s gaps count as 10 s) and a device with
     auto-pause never records the stop at all, so a corpus can look like it
     never stops because its riders' head units hid it. The fraction is
     comparable ACROSS rides only to the extent the devices agree, which is
     exactly what this entry cannot verify.
  2. hr coverage is partial and rider-driven -- some rides carry no strap. The
     hr panel is a SUBSET of the rides in every other panel, so its n is
     reported separately and a ride is given an hr only when >= HR_MIN_COV of
     its samples carry one.

Output: data/results/e62_corpus_profile.csv       (per ride; gitignored)
        research/journal/figs/e62-corpus-pairplot.svg
Run:    python3 src/harness/e62_corpus_profile.py    (E62_SMOKE=1 for a subset)
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

from bicycling_energy_model import (build_profile, deadband, empirical_kj,
                                    resample_profile)
from bicycling_energy_model.jsfmt import to_fixed

from e44_scurve import corpus_rides
from perride_invert import ENGINE_DX, RESULTS

SMOKE = bool(os.environ.get("E62_SMOKE"))

# --- registered protocol constants ---
VSTOP = 0.5 / 3.6          # moving gate, m/s (Entry 44's constant)
# Elevation gain and the mean ascent grade are taken on the SAME profile the
# model runs on -- resampled to ENGINE_DX and deadbanded at the PUBLISHED
# tau = 2 m -- not on the raw GPS trace. Raw h+ is inflated by barometric and
# GPS noise (research/notes/ascent-error-literature.md), so an unsmoothed gain
# would describe the sensor rather than the terrain, and would not be the h+
# any of the fitted forms saw.
TAU_PUB = 2.0
HR_MIN_COV = 0.5           # a ride gets an hr only above this sample coverage
CORPORA = ("D3", "D4", "D5", "D6")

# The series is the RIDER, not the corpus. D3/D4/D5 are one rider each, so the
# only corpus that hides riders inside it is D6 — and pooling its four is
# exactly what would hide a rider effect behind a regional label, which is the
# distinction Entries 60 and 61 spent two entries separating. D6 is therefore
# split into D6a..D6d, one per rider of the deposit:
D6_LABEL = {"D6-user_1": "D6a", "D6-user_2": "D6b",
            "D6-user_3": "D6c", "D6-user_5": "D6d"}
SERIES = ("D3", "D4", "D5", "D6a", "D6b", "D6c", "D6d")
# Seven series need seven separable series, and hue alone does not carry that
# in a dense scatter: the first version gave D6a-D6d a purple ramp so they
# would read as one region, and the four became indistinguishable. So each
# series gets BOTH an Okabe-Ito hue (colourblind-safe, as make_figures.py) and
# its own MARKER SHAPE -- shape survives overplotting and greyscale printing
# where hue does not. E62_HUE=corpus pools D6 back to a single series.
HUE = {"D3": "#0072B2", "D4": "#D55E00", "D5": "#009E73", "D6": "#CC79A7",
       "D6a": "#CC79A7", "D6b": "#56B4E9", "D6c": "#E69F00", "D6d": "#000000"}
SHAPE = {"D3": "circle", "D4": "square", "D5": "up", "D6": "circle",
         "D6a": "diamond", "D6b": "down", "D6c": "circle", "D6d": "square"}
BY_CORPUS = os.environ.get("E62_HUE") == "corpus"
INK, GREY = "#222222", "#9aa0a6"

VARS = (("km", "distância (km)", 0),
        ("t_mov", "tempo em movimento (h)", 1),
        ("movfrac", "fração em movimento", 2),
        ("hplus", "ganho de elevação (m)", 0),
        ("gasc", "inclinação média de subida (%)", 1),
        ("kj", "trabalho na pedalada (kJ)", 0),
        ("pow_mov", "potência média (W, c/ zeros)", 0),
        ("v_mov", "velocidade média (km/h)", 0),
        ("hr_mov", "FC média (bpm)", 0))


def corpus_of(group: str) -> str:
    """D6-user_3 -> D6; D3 -> D3."""
    return group.split("-", 1)[0]


def series_of(group: str) -> str:
    """The plotted series: D6-user_3 -> D6c, unless E62_HUE=corpus pools D6."""
    if BY_CORPUS:
        return corpus_of(group)
    return D6_LABEL.get(group, corpus_of(group))


def series_present(rows: list[dict]) -> tuple:
    """Series in the registered order, keeping only those with rides."""
    have = {r["series"] for r in rows}
    return tuple(s for s in (CORPORA if BY_CORPUS else SERIES) if s in have)


def aggregates(pts) -> dict | None:
    """The six per-ride aggregates. None when the ride cannot support them."""
    if len(pts) < 10:
        return None
    km = (pts[-1]["x"] - pts[0]["x"]) / 1000.0
    if not (km > 0):
        return None
    t_rec = t_mov = 0.0
    pw_s = pw_w = 0.0
    v_s = 0.0
    hr_s = hr_w = 0.0
    n_hr = 0
    for q in pts:
        dt = q.get("dt") or 0.0
        if dt <= 0:
            continue
        t_rec += dt
        v = q.get("v")
        if v is None or v < VSTOP:
            continue
        t_mov += dt
        v_s += v * dt
        p = q.get("power")
        if p is not None:
            pw_s += p * dt
            pw_w += dt
        h = q.get("hr")
        if h is not None and h > 0:
            hr_s += h * dt
            hr_w += dt
            n_hr += 1
    if t_mov <= 0 or t_rec <= 0:
        return None
    n_mov = sum(1 for q in pts if (q.get("v") or 0.0) >= VSTOP)
    hplus = gasc = None
    try:
        prof = resample_profile(
            build_profile([q["x"] for q in pts], [q.get("alt") for q in pts]), ENGINE_DX)
        h = deadband(prof["h"], TAU_PUB)
        x = prof["x"]
        up = upx = 0.0
        for i in range(1, len(h)):
            dh = h[i] - h[i - 1]
            if dh > 0:
                up += dh
                upx += x[i] - x[i - 1]
        hplus = up
        gasc = 100.0 * up / upx if upx > 0 else None
    except Exception:
        pass
    return {
        "km": km,
        # measured pedal work: sum(P*dt) over every sample that carries power,
        # via the package's one copy of it. Not gated on MOVING -- a sample
        # with the wheel stopped and the legs turning is still work done -- and
        # an UNDERESTIMATE wherever power coverage is short of 1 (pow_cov).
        "hplus": hplus,
        "gasc": gasc,
        "kj": empirical_kj(pts),
        "t_mov": t_mov / 3600.0,
        "movfrac": t_mov / t_rec,
        "pow_mov": pw_s / pw_w if pw_w > 0 else None,
        "v_mov": (v_s / t_mov) * 3.6,
        "hr_mov": (hr_s / hr_w if hr_w > 0 else None)
        if n_mov and n_hr / max(1, n_mov) >= HR_MIN_COV else None,
        "hr_cov": n_hr / max(1, n_mov),
        "pow_cov": pw_w / t_mov,
        "n": len(pts),
    }


def pctl(v: list[float], q: float) -> float:
    """Linear-interpolation percentile on the sorted sample (numpy's default,
    stated because a published percentile must name its estimator)."""
    if not v:
        return float("nan")
    s = sorted(v)
    if len(s) == 1:
        return s[0]
    i = q * (len(s) - 1)
    lo = int(math.floor(i))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation, average ranks on ties. Spearman rather than Pearson
    because distance and time are heavy-tailed and one 300 km ride would
    otherwise set the correlation by itself."""
    n = len(xs)
    if n < 3:
        return float("nan")

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float("nan")


def ols_slope(xs: list[float], ys: list[float]) -> float:
    """a in y = a*x + b, least squares. Reported BESIDE Spearman rho, not
    instead of it: rho is rank-based and outlier-resistant, a is neither, so a
    large |a| against a small rho is one heavy ride pulling the line and the
    pair says that out loud."""
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def fmt_slope(a: float) -> str:
    """Three significant figures across nine variables whose units span
    kJ/km to bpm/(km/h)."""
    if a != a:
        return "\u2014"
    m = abs(a)
    if m >= 1000 or (m < 0.001 and m > 0):
        return f"{a:.1e}"
    return to_fixed(a, 0 if m >= 100 else 1 if m >= 10 else 2 if m >= 1 else 3)


# ------------------------------------------------------------------ the SVG

CELL, PAD, LEFT, TOP = 168, 14, 118, 34
NV = len(VARS)


def marker(c: str, x: float, y: float, r: float = 2.6) -> str:
    """One point of series `c` at (x, y) — shape carries the series as much as
    the hue does, which is what makes seven overlapping clouds readable."""
    sh = SHAPE.get(c, "circle")
    if sh == "square":
        return (f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r:.1f}" '
                f'height="{2 * r:.1f}"/>')
    if sh == "diamond":
        d = r * 1.25
        return (f'<polygon points="{x:.1f},{y - d:.1f} {x + d:.1f},{y:.1f} '
                f'{x:.1f},{y + d:.1f} {x - d:.1f},{y:.1f}"/>')
    if sh in ("up", "down"):
        d = r * 1.35
        if sh == "up":
            return (f'<polygon points="{x:.1f},{y - d:.1f} {x + d:.1f},{y + d * 0.8:.1f} '
                    f'{x - d:.1f},{y + d * 0.8:.1f}"/>')
        return (f'<polygon points="{x:.1f},{y + d:.1f} {x + d:.1f},{y - d * 0.8:.1f} '
                f'{x - d:.1f},{y - d * 0.8:.1f}"/>')
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>'


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hist(vals: list[float], lo: float, hi: float, nb: int = 22) -> list[int]:
    b = [0] * nb
    if hi <= lo:
        return b
    for v in vals:
        i = int((v - lo) / (hi - lo) * nb)
        b[min(max(i, 0), nb - 1)] += 1
    return b


def pairplot(rows: list[dict], path: str) -> None:
    """Hand-emitted SVG scatter matrix, hue = corpus. Lower triangle scatter,
    diagonal per-corpus histograms, upper triangle Spearman rho per corpus.

    No matplotlib/seaborn: the repo is build-step-free, and make_figures.py
    already emits the article figures this way.
    """
    keys = [k for k, _l, _d in VARS]
    # per-variable range on the pooled 1-99 percentile, so one outlier does not
    # flatten every panel; points outside are clamped to the frame edge.
    rng = {}
    for k in keys:
        v = [r[k] for r in rows if r.get(k) is not None]
        lo, hi = pctl(v, 0.01), pctl(v, 0.99)
        if not (hi > lo):
            lo, hi = (min(v) if v else 0.0), (max(v) if v else 1.0) + 1e-9
        # pad the frame, but never past a value the variable can actually
        # take: the unclamped version drew a -139 m tick on elevation gain
        pad = 0.04 * (hi - lo)
        rng[k] = (max(lo - pad, min(v)), min(hi + pad, max(v)))

    W = LEFT + NV * (CELL + PAD) + PAD
    H = TOP + NV * (CELL + PAD) + 92
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="{PAD}" y="22" font-size="15" fill="{INK}">'
         f'Entry 62 — perfil descritivo dos corpora D3–D6 '
         f'(uma ride = um ponto; matiz = ciclista)</text>']

    def px(k, v, x0):
        lo, hi = rng[k]
        f = min(max((v - lo) / (hi - lo), 0.0), 1.0)
        return x0 + f * CELL

    def py(k, v, y0):
        lo, hi = rng[k]
        f = min(max((v - lo) / (hi - lo), 0.0), 1.0)
        return y0 + CELL - f * CELL

    ser = series_present(rows)
    dec = {k: d for k, _l, d in VARS}
    NT = 3                       # ticks per axis (registered: at least three)

    def ticks(k):
        lo, hi = rng[k]
        return [lo + n * (hi - lo) / (NT - 1) for n in range(NT)]

    for i, (ky, laby, _dy) in enumerate(VARS):
        for j, (kx, labx, _dx) in enumerate(VARS):
            x0 = LEFT + j * (CELL + PAD)
            y0 = TOP + i * (CELL + PAD)
            o.append(f'<rect x="{x0}" y="{y0}" width="{CELL}" height="{CELL}" '
                     f'fill="none" stroke="#e3e3e3"/>')
            if i == j:
                lo, hi = rng[kx]
                nb, mx, hs = 22, 1, {}
                for c in ser:
                    hs[c] = hist([r[kx] for r in rows
                                  if r["series"] == c and r.get(kx) is not None], lo, hi, nb)
                    mx = max(mx, max(hs[c]) if hs[c] else 1)
                for c in ser:
                    pts = []
                    for b in range(nb):
                        xa = x0 + b * CELL / nb
                        xb = x0 + (b + 1) * CELL / nb
                        yv = y0 + CELL - (hs[c][b] / mx) * CELL * 0.92
                        pts.append(f"{xa:.1f},{yv:.1f} {xb:.1f},{yv:.1f}")
                    o.append(f'<polyline points="{x0},{y0 + CELL} '
                             + " ".join(pts) + f' {x0 + CELL},{y0 + CELL}" '
                             f'fill="{HUE[c]}" fill-opacity="0.08" '
                             f'stroke="{HUE[c]}" stroke-width="1.4" stroke-opacity="0.9"/>')
            elif i > j:
                for c in ser:
                    d = [(r[kx], r[ky]) for r in rows if r["series"] == c
                         and r.get(kx) is not None and r.get(ky) is not None]
                    if not d:
                        continue
                    cir = "".join(marker(c, px(kx, a, x0), py(ky, b, y0), 2.4)
                                  for a, b in d)
                    o.append(f'<g fill="{HUE[c]}" fill-opacity="0.45">{cir}</g>')
            else:
                o.append(f'<text x="{x0 + CELL / 2}" y="{y0 + 15}" font-size="9.5" '
                         f'text-anchor="middle" fill="{GREY}">'
                         f'\u03c1 (Spearman)  ·  a (MQO: y = a\u00b7x + b)</text>')
                for n, c in enumerate(ser):
                    d = [(r[kx], r[ky]) for r in rows if r["series"] == c
                         and r.get(kx) is not None and r.get(ky) is not None]
                    xs_, ys_ = [a for a, _ in d], [b for _, b in d]
                    rho = spearman(xs_, ys_) if len(d) >= 3 else float("nan")
                    txt = "\u2014" if rho != rho else to_fixed(rho, 2)
                    o.append(f'<text x="{x0 + CELL / 2}" y="{y0 + 34 + n * 17}" '
                             f'font-size="10.5" text-anchor="middle" fill="{HUE[c]}">'
                             f'{c} \u03c1 {txt}  a {fmt_slope(ols_slope(xs_, ys_))}'
                             f'  <tspan font-size="8.5" fill="{GREY}">'
                             f'n={len(d)}</tspan></text>')
            # --- axis ticks: NT per axis, drawn on the outer edge only
            if j == 0:
                ly_, lx_ = y0 + CELL / 2, 24
                o.append(f'<text x="{lx_}" y="{ly_}" font-size="11" '
                         f'text-anchor="middle" fill="{INK}" '
                         f'transform="rotate(-90 {lx_} {ly_})">{_esc(laby)}</text>')
                for tv in ticks(ky):
                    yv = py(ky, tv, y0)
                    o.append(f'<line x1="{LEFT - 4}" y1="{yv:.1f}" x2="{LEFT}" '
                             f'y2="{yv:.1f}" stroke="{GREY}"/>')
                    o.append(f'<text x="{LEFT - 7}" y="{yv + 3.2:.1f}" font-size="9" '
                             f'text-anchor="end" fill="{GREY}">'
                             f'{to_fixed(tv, dec[ky])}</text>')
            if i == NV - 1:
                base = TOP + NV * (CELL + PAD) - PAD
                tvs = ticks(kx)
                for n, tv in enumerate(tvs):
                    xv = px(kx, tv, x0)
                    # end ticks are anchored INWARD: at PAD = 10 px between
                    # panels, a centred first/last label collides with its
                    # neighbour's and the axis reads as one run-on number
                    anc = ("start" if n == 0 else
                           "end" if n == len(tvs) - 1 else "middle")
                    o.append(f'<line x1="{xv:.1f}" y1="{base}" x2="{xv:.1f}" '
                             f'y2="{base + 4}" stroke="{GREY}"/>')
                    o.append(f'<text x="{xv:.1f}" y="{base + 15}" font-size="9" '
                             f'text-anchor="{anc}" fill="{GREY}">'
                             f'{to_fixed(tv, dec[kx])}</text>')
                o.append(f'<text x="{x0 + CELL / 2}" y="{base + 31}" '
                         f'font-size="11" text-anchor="middle" fill="{INK}">'
                         f'{_esc(labx)}</text>')

    ly = TOP + NV * (CELL + PAD) + 52
    for n, c in enumerate(ser):
        cx = LEFT + n * 132
        o.append(f'<g fill="{HUE[c]}">{marker(c, cx, ly - 4, 5)}</g>')
        o.append(f'<text x="{cx + 12}" y="{ly}" font-size="12" fill="{INK}">{c} '
                 f'(n={sum(1 for r in rows if r["series"] == c)})</text>')
    o.append(f'<text x="{PAD}" y="{ly + 22}" font-size="10" fill="{GREY}">'
             f'Eixos cortados nos percentis 1\u201399 agregados; pontos fora v\u00e3o para a borda. '
             f'\u201cEm movimento\u201d = v \u2265 0,5 km/h. Pot\u00eancia inclui zeros. '
             f'FC s\u00f3 nas rides com \u226550% de cobertura. '
             f'D6a\u2013D6d s\u00e3o os quatro ciclistas do dep\u00f3sito D6.</text>')
    o.append("</svg>")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(o))


# ------------------------------------------------------------------ driver

def load_rows(path: str) -> list[dict]:
    """Read back a profile CSV. E62_PLOT_ONLY re-renders the figure from it, so
    a layout change costs no re-parse of 2,000 tracks (the e61 raw-dump rule)."""
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            d = {"corpus": r["corpus"], "group": r["group"], "ride": r["ride"],
                 "series": r.get("series") or series_of(r["group"])}
            for k in ("km", "t_mov", "movfrac", "hplus", "gasc", "kj", "pow_mov",
                      "v_mov", "hr_mov",
                      "hr_cov", "pow_cov"):
                d[k] = float(r[k]) if r.get(k) not in (None, "") else None
            out.append(d)
    return out


def main() -> None:
    print("Entry 62 — corpus profile D3–D6" + ("  [E62_SMOKE]" if SMOKE else ""))
    rows: list[dict] = []
    seen: dict[str, int] = {}
    out = os.path.join(RESULTS, "e62_corpus_profile" + (".SMOKE" if SMOKE else "") + ".csv")
    if os.environ.get("E62_PLOT_ONLY"):
        rows = load_rows(out)
        fig = os.path.join(REPO, "research", "journal", "figs",
                           "e62-corpus-pairplot" + (".SMOKE" if SMOKE else "") + ".svg")
        pairplot(rows, fig)
        print(f"  re-rendered {os.path.relpath(fig, REPO)} from {os.path.basename(out)} "
              f"({len(rows)} rides) — no tracks re-parsed")
        return
    for group, pts, _m in corpus_rides():
        c = corpus_of(group)
        if c not in CORPORA:
            continue
        i = seen.get(group, 0)
        seen[group] = i + 1
        if SMOKE and i >= 12:
            continue
        try:
            a = aggregates(pts)
        except Exception:
            a = None
        if a is None:
            continue
        a.update({"group": group, "corpus": c, "series": series_of(group),
                  "ride": f"{group}#{i}"})
        rows.append(a)
        if len(rows) % 100 == 0:
            print(f"  {len(rows)} rides", flush=True)

    cols = ["corpus", "series", "group", "ride", "km", "t_mov", "movfrac",
            "hplus", "gasc", "kj", "pow_mov", "v_mov", "hr_mov",
            "hr_cov", "pow_cov", "n"]
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r.get(k) is None else r.get(k) for k in cols])

    ser = series_present(rows)
    print(f"\n  {len(rows)} rides profiled "
          + "  ".join(f"{c}={sum(1 for r in rows if r['series'] == c)}" for c in ser))
    for key, lab, _d in VARS:
        print(f"\n  {lab}   (p10 / median / p90)")
        for c in tuple(dict.fromkeys(ser + CORPORA)):
            sel = "corpus" if c in CORPORA and c not in ser else "series"
            v = [r[key] for r in rows if r[sel] == c and r.get(key) is not None]
            if not v:
                print(f"    {c:<4} —")
                continue
            print(f"    {c:<4} {to_fixed(pctl(v, 0.10), 2):>8} "
                  f"{to_fixed(pctl(v, 0.50), 2):>8} {to_fixed(pctl(v, 0.90), 2):>8}"
                  f"   n={len(v)}")

    print("\n  coverage (median per series)")
    for c in ser:
        hc = [r["hr_cov"] for r in rows if r["series"] == c]
        pc = [r["pow_cov"] for r in rows if r["series"] == c]
        nh = sum(1 for r in rows if r["series"] == c and r.get("hr_mov") is not None)
        print(f"    {c:<4} hr {to_fixed(pctl(hc, 0.5), 2)}  power {to_fixed(pctl(pc, 0.5), 2)}"
              f"   rides with hr: {nh}")

    fig = os.path.join(REPO, "research", "journal", "figs",
                       "e62-corpus-pairplot" + (".SMOKE" if SMOKE else "") + ".svg")
    pairplot(rows, fig)
    print(f"\nwrote {os.path.basename(out)} and {os.path.relpath(fig, REPO)}")


if __name__ == "__main__":
    main()
