# The route-energy law, from the equation of motion

`RouteEnergy.lean` is paper 1's Appendix A checked by machine, in Lean 4 with Mathlib. It shows
that the closed form follows from the equation of motion, and names what has to be assumed on
the way. A second part shows what kinetic energy does to the elevation that has to be paid for:
a kinetic-energy buffer acts on the route exactly as a deadband. A third part takes the question
of paper 3: what the equation of motion says about the cost of a single graph edge, and how the
edge costs the paper deploys relate to it. This page is the same argument in plain mathematics;
the names in `code` are the theorems that check each step.

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

**2. Two riding assumptions.** Cut the route into flat stretches, climbs and descents. Write
$R = C_{rr}\,m g$ for the rolling force, $W = m g$ for the weight and $A$ for the air force at
the reference speed. Assume:

- on a flat stretch the air costs $A$ per metre;
- nobody brakes off the descents.

The ledger of a segment with run $x_i$, rise $u_i$ or drop $d_i$, is then

| segment | ledger |
|---|---|
| flat | $k\,e_i = (R + A)\,x_i + W u_i$ |
| climb | $k\,e_i = R\,x_i + \mathrm{air}_i + W u_i$ |
| descent | $k\,e_i = (R + A)\,x_i - W d_i + \mathrm{waste}_i$ |

where $\mathrm{air}_i$ is the work the air takes on that climb, about which nothing is assumed,
and $\mathrm{waste}_i$ is what the descent loses to air drag above the reference bill and to the
brakes. Each segment may also carry a change in kinetic energy; those changes add up to the
ride's $\Delta KE$.

**3. The refund** (`refund_eq_balance`). Define the refund of a descent as the share of its
potential energy that is not wasted, $\varepsilon_i = 1 - \mathrm{waste}_i/(W d_i)$. With
$\alpha = (R + A)/k$ and $\beta = W/k$ the descent ledger becomes

$$e_i \;=\; \alpha\,x_i - \varepsilon_i\,\beta\,d_i, \qquad\text{equivalently}\qquad \varepsilon_i \;=\; \frac{\alpha\,x_i - e_i}{\beta\,d_i},$$

which is (A5): the flat bill less a refund, in terms a power meter can measure.

**4. The law** (`three_term_law`, `closed_form_of_newton`). Add the segments up:

$$E \;=\; \alpha_r\,x \;+\; \alpha_a\,x_{\mathrm{flat}} \;+\; \frac{W_{\mathrm{air,\,climbs}}}{k} \;+\; \beta\,\big(h_+ - \varepsilon\,h_-\big) \;+\; \frac{\Delta KE}{k}, \qquad \varepsilon \;=\; \frac{\sum_i \varepsilon_i\,d_i}{\sum_i d_i},$$

with $\alpha_r = R/k$, $\alpha_a = A/k$, $x_{\mathrm{flat}}$ the distance off the climbs and
$W_{\mathrm{air,\,climbs}} = \sum_i \mathrm{air}_i$ the work done against the air on the climbs.
The weight in $\varepsilon$ is the drop because that is what makes the total credit come out
right (`meanRefund_mul_drop`).

Paper 1's forms are the two ways of closing the air term. **F2** sets it to zero: "on a climb the
air costs nothing". **F1** charges it at the reference speed, $\alpha_a\,x_{\mathrm{climb}}$. If
climbs are ridden no faster than the reference speed the truth lies between the two
(`law_bracket`). The ceiling can be lowered: holding a speed $v$ up a grade $s$ at power $P$
means $k P / v = R + a v^2 + W s$, so $v \le k P/(R + W s)$ (`steady_climb_speed_le`). That is
the speed the engine's `vc` mode charges the air at, capped at the reference speed. So on steady
climbs ridden no faster than the reference speed

$$\text{F2 (zero)} \;\le\; E \;\le\; \text{vc} \;\le\; \text{F1 (off)},$$

where `zero`, `vc` and `off` are the engine's three climb-air modes. F3 is F2 once the elevation
totals are filtered.

**5. The ceiling** (`coast_ceiling`, `refund_of_coaster`, `refund_le_ceiling`). A rider who pedals
only as much as is needed to hold the reference speed, and not at all once gravity suffices,
spends $e_i = \max(0,\ \alpha x_i - \beta d_i)$ on a descent. That is a refund of

$$\varepsilon_i \;=\; \min\!\Big(1,\ \frac{s_*}{s_i}\Big), \qquad s_* = \frac{\alpha}{\beta}, \quad s_i = \frac{d_i}{x_i},$$

a function of grade alone, (A9). And because legs cannot return energy, $e_i \ge 0$, no rider
collects more than $s_*/s_i$ on a descent at least as steep as $s_*$.

## Kinetic energy and the deadband

**6. Kinetic energy is height** (`Obeys.energyLine`, `Obeys.free_lift`). In the ledger of step 1
the speed appears only as the kinetic head $v^2/2g$, added to the elevation. Collect with it the
head already lost to rolling and to the air, and call the sum the energy line:

$$Y \;=\; h \;+\; \frac{v^2}{2g} \;+\; C_{rr}\,X \;+\; \frac{W_{\mathrm{air}}}{m g}, \qquad k\,\Delta E \;=\; m g\,\Delta Y \;+\; \Delta W_{\mathrm{brake}} .$$

Legs raise the energy line, brakes lower it, and nothing else moves it. On a steady ride $Y$ is
the elevation profile tilted up by the flat-resistance grade $s_*$. One consequence: a climb of
$H$ entered at $v_{\mathrm{in}}$ and left at $v_{\mathrm{out}}$, without braking, costs the legs
what a climb of $H - (v_{\mathrm{in}}^2 - v_{\mathrm{out}}^2)/2g$ would at constant speed.

**7. Leg energy is the ascent of the energy line** (`leg_energy_ge_ascent`,
`leg_energy_eq_ascent`). Legs only add energy and brakes only remove it, so between any cuts of
the route

$$E \;\ge\; \beta \cdot \mathrm{ascent}(Y),$$

with equality for a rider who never brakes and pedals on the same stretch.

**8. The deadband is the least ascent in its band** (`deadband_isLeast`). The filter in
`engines.py` is a backlash: its output stays put while the input is within $\tau$ of it, and
otherwise follows at a distance $\tau$. Among all profiles that start where the recording starts
and stay within $\tau$ of it, the filtered profile is one, and none climbs less.

**9. A kinetic buffer is a deadband** (`leg_energy_ge_deadband`). Write
$u = h + C_{rr}\,X + W_{\mathrm{air}}/(m g)$ for the road as the legs meet it: elevation plus the
head lost to resistance. If the rider's kinetic head stays within $\tau$ of some level, the
energy line stays within $\tau$ of $u$, up to a constant. Steps 7 and 8 then give

$$E \;\ge\; \beta \cdot \big(\mathrm{ascent}(\mathrm{deadband}_\tau(u)) - \text{head start}\big),$$

where the head start is how far above the middle of its band the ride begins, and is zero for a
ride that starts there or slower. By the equality case of step 7, a rider whose energy line
follows the filtered road pays exactly that ascent: the rider who coasts whenever the band
allows, pedals only to hold the lowest speed and brakes only at the highest. (That such a ride
exists is physics, not one of the checked statements.) So with $2\tau$ of kinetic head to
spend, the $\tau$-filtered ascent is the least the legs can pay for.

## The edge cost (paper 3)

Paper 3 needs a cost for one edge of a routing graph: a run $\Delta x$ and a rise $\Delta h$ read
off a map. The steps below derive that cost from the equation of motion, and then place the two
families the paper deploys against it.

**10. The ledger of one edge** (`Obeys.edge`). Apply step 1 between two nodes, and write
$H = h + v^2/2g$ for the total head:

$$k\,e \;=\; R\,\Delta x \;+\; m g\,\Delta H \;+\; \Delta W_{\mathrm{air}} \;+\; \Delta W_{\mathrm{brake}} .$$

Speed enters only through the head at the two nodes. A cost that reads $\Delta h$ off the map is
therefore reading $\Delta H$ correctly only when the rider passes both nodes at the same speed.
Otherwise it is off by $\beta$ times the change in kinetic head, which is the momentum term of
paper 3 §3.4.

**11. The ideal edge cost** (`edge_ge_ideal`, `edge_eq_ideal`, `edge_le_bill`). Suppose the air
and the brakes together take at least the reference bill $A\,\Delta x$, which they do whenever the
edge is ridden no slower than the reference speed. Legs cannot return energy. Then

$$e \;\ge\; \max\big(0,\ \alpha\,\Delta x + \beta\,\Delta H\big),$$

with equality for the rider of step 5, who on each edge either holds the reference bill without
braking or does not pedal. Two companions bound a climb. With $A = 0$ the same statement is a
floor for every rider, $e \ge \max(0,\ \alpha_r\,\Delta x + \beta\,\Delta H)$: rolling and gravity
alone. And an edge on which the air and the brakes take no more than the reference bill costs at
most $\alpha\,\Delta x + \beta\,\Delta H$.

Read against paper 3's E1, with $\varepsilon_0 = 0$:

| arm of E1 | what the equation of motion says about it |
|---|---|
| descent, $\alpha\,\Delta x - \min(1, s_*/s)\,\beta\,d$ | the ideal edge cost (step 5's ceiling) |
| flat band, $\alpha\,\Delta x + \beta\,\Delta h$ | the ideal edge cost |
| gated climb, $\alpha_r\,\Delta x + \beta\,\Delta h$ | the floor, exactly |
| the same climb without the gate | the upper bound, if climbed no faster than the reference speed |

So the climb gate is F2's choice made edge by edge, between the same two bounds as in step 4.

**12. Summing over a path** (`edge_sum_le_energy`, `energy_eq_edge_sum`, `v2_eq_ideal`). For a
ride that passes every node at the same speed, the sum of ideal edge costs is at most the energy
the legs deliver, and equals it for the ideal coaster. This is the sense in which E1 follows from
the equation of motion: at zero deficit and below the gate it is the energy of a definite rider.

**13. The edge sum and the mesh** (`edge_sum_eq_ascent`, `ideal_sum_coarsen`,
`edge_sum_ge_deadband`). The ideal edge cost is $\beta\,\max(0,\ \Delta h + s_*\,\Delta x)$: $\beta$
times the rise of the road tilted by $s_*$. Summed along a path it is

$$\sum_{\mathrm{edges}} \;=\; \beta \cdot \mathrm{ascent}\big(h + s_*\,x\big), \quad\text{sampled at the nodes.}$$

Two things follow. Refining the mesh never lowers the sum: the same route costs at least as much
on a finer mesh. And on every mesh the sum is at least
$\beta \cdot \mathrm{ascent}(\mathrm{deadband}_\tau(h + s_*\,x))$, which by step 9 is the least a
rider with a kinetic buffer pays. The difference between the two is the kinetic term. It is not
a discretisation error that a finer mesh removes, because a finer mesh never lowers the edge sum.
This is what paper 3's Appendix A plans to state as "what vanishes and what does not".

**14. The deployed cost** (`v2Edge`, `v2Edge_descent`, `v2_descent_ge`, `v2_descent_eq`,
`floor_le_v2`). `v2Edge` is defined branch for branch as `r1d_v2_edge` computes it, with the map
scalar $k_s$ on the two gravity arms and not on $s_*$. Three results.

- Its trailing $\max(0, \cdot)$ never acts. For any constants with $0 \le \varepsilon_0 \le 1$
  and $k_s \le 1$ the descent arm is at least $\varepsilon_0\,\alpha\,\Delta x$. Paper 3 reports
  this as measured at the deployed constants; it holds for all of them.
- With $k_s = 1$ the descent arm is the ideal edge cost plus a deficit charge:

  $$e \;=\; \max(0,\ \alpha\,\Delta x - \beta\,d) \;+\; \min(\varepsilon_0\,\beta\,d,\ \alpha\,\Delta x).$$

  | grade of the descent | cost |
  |---|---|
  | up to $s_*$ | $\alpha\,\Delta x - (1 - \varepsilon_0)\,\beta\,d$ |
  | from $s_*$ to $s_*/\varepsilon_0$ | $\varepsilon_0\,\beta\,d$ |
  | beyond $s_*/\varepsilon_0$ | $\alpha\,\Delta x$, the flat bill |

- It never bills less than the floor of step 11, and on a gated climb it bills exactly the floor.

The deficit is then a definite claim about riders: on a descent they spend $\varepsilon_0$ of the
drop's potential energy more than the ideal coaster would, up to the flat bill. That claim is a
measurement. Nothing here derives it.

**15. The flat-$\varepsilon$ family** (`law_sum_eq_route`, `eFEdge_eq_clamped_law`,
`clamp_is_ceiling`, `clamp_mass`). The route law is already additive. Charging each edge
$\alpha\,\Delta x + \beta\,(\Delta h_+ - \varepsilon\,\Delta h_-)$ and summing gives the route law on
the path's own totals. The only thing that stops it being an edge cost is its sign: it is negative
on a descent steeper than $s_*/\varepsilon$. `eF1` and `eF2` floor each edge at zero (`eFEdge` is
defined as `edge_form` computes it), and

$$\max(0,\ \alpha\,\Delta x - \varepsilon\,\beta\,d) \;=\; \alpha\,\Delta x - \min\!\Big(\varepsilon,\ \frac{s_*}{s}\Big)\,\beta\,d .$$

So the floor refunds the flat $\varepsilon$ up to the grade $s_*/\varepsilon$ and the coasting
ceiling beyond it. The clamp is step 5's statement that legs cannot return energy, applied to one
edge. What it adds to a route's cost, `eF# − F#` in paper 3's tables, is the sum of what it
refused.

**16. Potential energy and the search** (`path_potential`, `lawEdge_reduced_ge`, `v2_reduced_ge`,
`v2_path_ge`, `v2_path_ge_rate`, `rolling_bound_fails`). Take $\beta\,\Delta h$ off every edge.
Every path between the same two nodes then changes by the same amount,
$\beta\,(h_{\mathrm{end}} - h_{\mathrm{start}})$, so no shortest path changes. What is left of the
unclamped law is

$$\alpha\,\Delta x \;+\; (1 - \varepsilon)\,\beta\,d \;\ge\; 0 \qquad\text{for } \varepsilon \le 1,$$

the flat bill plus the wasted share of the descent. So the unclamped route law can be searched
with Dijkstra's algorithm after this reweighting. The clamp is a modelling choice, and the search
does not require it. This is the potential that paper 3's Appendix A plans.

For the deployed cost the potential is $k_s\,\beta\,h$, and what is left on each edge is at least
the rolling bill $\alpha_r\,\Delta x$. Two lower bounds on the cost of any path follow:

$$\text{cost} \;\ge\; \alpha_r\,x + k_s\,\beta\,(h_{\mathrm{end}} - h_{\mathrm{start}}), \qquad \text{cost} \;\ge\; \min(\varepsilon_0\,\alpha,\ \alpha_r)\,x .$$

The rolling bill on its own, $\alpha_r\,x$, is not a lower bound. A descent at exactly the grade
$s_*$ costs $\varepsilon_0\,\alpha$ per metre. For a 75 kg rider at 50 W and the shared constants
that is 1.41 J/m against $\alpha_r$ = 5.99 J/m, and the gap stays up to at least 250 W. The
heuristic $\alpha_r \cdot d$ that paper 3 plans for A* (its Appendix B) therefore overestimates and
is not admissible on the deployed costs. The larger of the two bounds above is, with $x$ replaced
by the straight-line distance to the goal. (That a path is no shorter than the straight line is
geometry, and is not among the checked statements.)

**17. The valley toll** (`valley_toll`). A descent of drop $D$ is coasted and a climb of rise $H$
follows. By step 6 the legs pay for the climb less the kinetic head spent on it. That head is at
most $D$, because a coasted descent cannot add more head than it drops, provided the rider leaves
the valley no slower than it came. It is at most the buffer $(v_e^2 - v_c^2)/2g$, with $v_e$ the
fastest the rider is at the bottom and $v_c$ the slowest at the top. And the saving cannot exceed
the climb's own bill, because the legs' energy is not negative. These are the three arms of the
toll $\min(D,\ H,\ \text{buffer})$ in `e63_f5_kebuffer.py`. They are derived as bounds on what a
valley can save. The noise floor $2\tau_n$ that the harness takes off the buffer is a
measurement. The harness then takes the toll off both elevation totals, which credits
$(1 - \varepsilon)\,\beta$ per metre of toll; the bound here credits $\beta$ per metre against the
climb.

## What this establishes, and what it does not

- Under the two assumptions the law is an identity, with the change in kinetic energy and the
  air on the climbs as explicit terms. Its error on a real ride is how far that ride departs
  from the assumptions, plus whatever is done to the air term.
- That air term is not small near the climb gate. For a 75 kg rider at the shared constants,
  holding 100 W up a 2% grade puts 15% of the resisting force in the air, and 3% at a 5% grade;
  climbing at 150 W it is 24% and 5%. F2 drops it, and the fitted $\varepsilon$ makes up the
  difference, which is one more reason $\varepsilon$ is a closure term. The lab journal's runs
  of the `vc` mode put its ceiling at about 4 to 4.6% of a ride's energy (Entries 3 and 17).
- $\varepsilon$ is the number that closes the descent ledger. The derivation fixes its ceiling,
  not its value.
- The coasting deficit $\varepsilon_0$, the deadband threshold $\tau$ and the noise rate $c$ are
  measurements. Nothing here derives them or bounds them.
- Profiles and powers may have kinks: the statements ask only for continuity and a rate taken
  from the right, so a polyline elevation profile and a power that steps between regimes qualify.
- Steps 6–9 run one way. They show that a kinetic buffer produces a deadband; they do not show
  that the deadband fitted to recorded rides is that buffer and nothing else. The lab journal's
  Entries 63–69 measure that question, and find that the kinetic toll alone accounts for about
  half of what the fitted filter does.
- The deadband that kinetic energy produces differs from the fitted one in two ways. It acts on
  $u$, the elevation tilted by the resistance, so only the part of a descent that would otherwise
  be wasted can be carried over. And its threshold is half the swing of $v^2/2g$: 3.7 m for a
  rider whose speed ranges between 12 and 45 km/h.
- For paper 3, the equation of motion gives the ideal edge cost: a lower bound on every edge
  ridden at or above the reference speed, and the exact cost for the ideal coaster. It gives that
  only for a ride that passes the nodes at one speed. Step 13 bounds what that condition costs.
- The deficit $\varepsilon_0$, the 2% climb gate, the map scalar $k_s$ and `eF4`'s noise rate
  $c$ are not derived. They enter steps 14 to 16 as parameters, and those steps are algebra
  about the deployed formulas. Whether the formulas match riders is what paper 3 measures.
- Step 17 runs one way, like steps 6 to 9: it bounds what a valley can save, and does not show
  that riders collect it.

## Checking it

```bash
lake exe cache get
lake build
```

Lean and Mathlib are pinned by `lean-toolchain` and `lake-manifest.json`. The first command
downloads Mathlib's prebuilt files, about 7 GB; the build itself then takes seconds. Nothing else
in the repository depends on this directory.
