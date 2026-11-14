# The route-energy law, from the equation of motion

`RouteEnergy.lean` is paper 1's Appendix A checked by machine, in Lean 4 with Mathlib. It shows
that the closed form follows from the equation of motion, and names what has to be assumed on
the way. This page is the same argument in plain mathematics; the names in `code` are the
theorems that check each step.

## The derivation

Everything is a function of distance $s$ along the road. Speed is $v$, horizontal position $X$,
elevation $h$, and $E$ is the energy the legs have delivered, so $dE/ds = P/v$.

**1. The ledger** (`ledger`). The equation of motion is paper 1's eq. (3) with a brake force:

$$m\,v\,\frac{dv}{ds} \;=\; \frac{k\,P}{v} \;-\; C_{rr}\,m g\cos\theta \;-\; F_{\mathrm{air}} \;-\; m g\sin\theta \;-\; F_{\mathrm{brake}} .$$

Move everything to one side. The quantity
$k E - \tfrac12 m v^2 - C_{rr}\,m g\,X - W_{\mathrm{air}} - m g\,h - W_{\mathrm{brake}}$
then has derivative zero, so it is constant along the ride:

$$k\,E \;=\; \Delta KE \;+\; C_{rr}\,m g\,x \;+\; W_{\mathrm{air}} \;+\; m g\,\Delta h \;+\; W_{\mathrm{brake}} .$$

This is (A1). The air force is left arbitrary, so wind and any drag law are covered, and rolling
resistance comes out exact in the horizontal distance $x$ on any grade.

**2. Three riding assumptions.** Cut the route into flat stretches, climbs and descents. Write
$R = C_{rr}\,m g$ for the rolling force, $W = m g$ for the weight and $A$ for the air force at
the reference speed. Assume:

- on a flat stretch the air costs $A$ per metre;
- on a climb the air costs nothing;
- nobody brakes off the descents.

The ledger of a segment with run $x_i$, rise $u_i$ or drop $d_i$, is then

| segment | ledger |
|---|---|
| flat | $k\,e_i = (R + A)\,x_i + W u_i$ |
| climb | $k\,e_i = R\,x_i + W u_i$ |
| descent | $k\,e_i = (R + A)\,x_i - W d_i + \mathrm{waste}_i$ |

where $\mathrm{waste}_i$ is what the descent loses to air drag above the reference bill and to the
brakes. Each segment may also carry a change in kinetic energy; those changes add up to the
ride's $\Delta KE$.

**3. The refund** (`refund_eq_balance`). Define the refund of a descent as the share of its
potential energy that is not wasted, $\varepsilon_i = 1 - \mathrm{waste}_i/(W d_i)$. With
$\alpha = (R + A)/k$ and $\beta = W/k$ the descent ledger becomes

$$e_i \;=\; \alpha\,x_i - \varepsilon_i\,\beta\,d_i, \qquad\text{equivalently}\qquad \varepsilon_i \;=\; \frac{\alpha\,x_i - e_i}{\beta\,d_i},$$

which is (A5): the flat bill less a refund, in terms a power meter can measure.

**4. The law** (`three_term_law`, `closed_form_of_newton`). Add the segments up:

$$E \;=\; \alpha_r\,x \;+\; \alpha_a\,x_{\mathrm{flat}} \;+\; \beta\,\big(h_+ - \varepsilon\,h_-\big) \;+\; \frac{\Delta KE}{k}, \qquad \varepsilon \;=\; \frac{\sum_i \varepsilon_i\,d_i}{\sum_i d_i},$$

with $\alpha_r = R/k$, $\alpha_a = A/k$ and $x_{\mathrm{flat}}$ the distance off the climbs. The
weight is the drop because that is what makes the total credit come out right
(`meanRefund_mul_drop`). With no
segment classed as a climb this is F1; otherwise it is F2, and F3 once the elevation totals are
filtered.

**5. The ceiling** (`coast_ceiling`, `refund_of_coaster`, `refund_le_ceiling`). A rider who pedals
only as much as is needed to hold the reference speed, and not at all once gravity suffices,
spends $e_i = \max(0,\ \alpha x_i - \beta d_i)$ on a descent. That is a refund of

$$\varepsilon_i \;=\; \min\!\Big(1,\ \frac{s_*}{s_i}\Big), \qquad s_* = \frac{\alpha}{\beta}, \quad s_i = \frac{d_i}{x_i},$$

a function of grade alone, (A9). And because legs cannot return energy, $e_i \ge 0$, no rider
collects more than $s_*/s_i$ on a descent at least as steep as $s_*$.

## What this establishes, and what it does not

- Under the three assumptions the law is an identity, with the change in kinetic energy as its
  only remainder. Its error on a real ride is how far that ride departs from the assumptions.
- $\varepsilon$ is the number that closes the descent ledger. The derivation fixes its ceiling,
  not its value.
- The coasting deficit $\varepsilon_0$, the deadband threshold $\tau$ and the noise rate $c$ are
  measurements. Nothing here derives them or bounds them.
- Profiles and powers may have kinks: the statements ask only for continuity and a rate taken
  from the right, so a polyline elevation profile and a power that steps between regimes qualify.

## Checking it

```bash
lake exe cache get
lake build
```

Lean and Mathlib are pinned by `lean-toolchain` and `lake-manifest.json`. The first command
downloads Mathlib's prebuilt files, about 7 GB; the build itself then takes seconds. Nothing else
in the repository depends on this directory.
