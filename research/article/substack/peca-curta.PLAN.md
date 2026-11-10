<!--
  peca-curta.PLAN.md — SKELETON for one short, shareable piece (pt-BR, ~8 min).

  What this is: beats, word budgets, pictures and a checked numbers sheet. It is
  NOT prose. Per mission-model/08 the text a reader sees is written by humans;
  this file is the machine-produced pre-draft that the writing starts from.

  Relation to the four-part series "A conta dos quilojaules" (this folder, on
  branch substack-series-and-paper-fixes): this piece goes FIRST and stands
  alone. It lifts from the four parts and adds nothing they do not hold, except
  the items marked NEW. The four parts become the follow-ups it links to.

  Provenance rule, as in the series: a number that moves must be updated here
  too. Every number the piece may print is in the sheet at the end, with its
  source and how far it has been checked.
-->

# Short piece — skeleton

## The piece in one paragraph

**Reader:** someone who rides with the collective, or could. Not a reviewer.
**Promise:** by the end they can price a ride on a napkin, know how far to trust
the price, and have two things worth repeating to a friend.
**Length:** about 1,500 words, eight minutes. One equation, shown once. Three pictures.
**Spine:** one hand-worked ride, two surprises, one test, one honest sentence, one map, one thing to try.

Working titles (the first is already yours, from part 1):
- *Uma conta de padaria para a energia de um pedal*
- *Quanto custa um pedal? Uma conta de guardanapo, conferida em 2.039 pedais*
- *Até onde 400 kJ levam*

## Beats

| # | beat | its job | material | lift from | words |
|--:|---|---|---|---|--:|
| 1 | **O chamado** | Open on the collective, not on the method. | Every chamado carries a kJ estimate. The 400 kJ rule, so nobody misses the last train. The effort scale: *de boa* / *OK* / *endorfinado* / *fritasso* / *insano*. The question: how right is that number? | part 1, opening and the scale list | 150 |
| 2 | **A conta no guardanapo** | Let the reader do the sum once. | Three charges: andar, subir, descer. The worked ride: 75 kg, 50 W, 25 km, 200 m up and down → 150 + 98 + 94 − 19 ≈ 320 kJ, *endorfinado*. The equation appears here and nowhere else. | part 1 "Andar, subir, descer"; part 2 "Um exemplo" | 300 |
| 3 | **Surpresa 1: a descida devolve pouco** | First thing to repeat. | The refund is about 29% of what the same height cost to climb. Why so little: steep descents offer more than can be used (air, brakes), and people keep pedalling. It changes with the landscape, 0.24 in São Paulo against 0.37 in the European rides. | part 2 "O reembolso", "Depende de onde se pedala" | 200 |
| 4 | **Surpresa 2: a subida que o mapa inventa** | Second thing to repeat. | Contornar Anhangabaú: the barometer logged 440 m, the 5 m map says 602 m for the same streets. The estimate goes from −1.6% to +8.7%, and smoothing the profile brings it to 0.0%. The general fact behind it: the finer you measure, the more climbing you find (92 / 77 / 56 km for the same 44 rides). | part 3 "Quanto sobe uma subida?"; paper 2 §4 | 250 |
| 5 | **O teste** | Earn the trust, briefly. | 2,039 rides, seven people, power meters. The sealed envelope: 305 rides kept out. Median error 3.2%. A full physics simulation ties: closer on 152 rides, the formula on 153. | part 1 "O envelope lacrado", "O resultado", "Empate com a simulação" | 200 |
| 6 | **O que isso garante, e o que não** | The honest sentence, early enough to be read. | The 3.2% is the account closing when we already know how the person rode. With typical constants instead of each rider's own, the one test so far reads about 8%, on 44 long rides. The proper before-the-ride test is not done yet. Road bikes, rides of 20 km or more, no wind. | part 1 "O que o teste não mostra" | 150 |
| 7 | **Até onde 400 kJ levam** | The picture that travels. | The reach map from Simujaules, from a starting point everyone knows. One caption, one sentence on reading it. | NEW, see Pictures | 100 |
| 8 | **Faça a sua conta** | Something to do tonight. | The Calculadora de Quilojaules and the applet. The happy coincidence: one kJ at the pedals costs the body about one kcal, so 320 kJ is roughly *um pão com manteiga e uma banana*. A closing question, for example: which label was your last ride? | part 2 "Um exemplo" (last paragraph), "Para usar" | 150 |
| — | Créditos | Thanks, authorship, AI declaration, links to the four parts for depth. | | part 1 footer | — |

Optional line for beat 2, NEW and checked: at an easy 17 km/h, climbing one metre costs the same as riding about 70 m on the flat. It is the most repeatable number in the project. It depends on speed (about 50 m at 23 km/h, about 95 m at 10 km/h), so print it with the speed.

## Pictures

1. **The reach map** (lead image, and beat 7). How far 400 kJ gets you from one well-known point. It has to be rendered from Simujaules; none is in this repo. Idea worth trying: colour the bands with the collective's own labels instead of a kJ legend. If the map does not look good, the piece opens on the worked ride instead and loses nothing essential.
2. **The bill on a profile** (beat 2). `figs/fig9-anatomy.svg`, redrawn with Portuguese labels.
3. **Climb against filter width** (beat 4). `figs/fig3-ascent-fractal.svg`, redrawn in Portuguese. Its three numbers (92, 77, 56 km) carry the idea on their own.

## What stays out, and where it lives

| left out | goes to |
|---|---|
| The four versions of the formula, cross-validation, AIC, the filter's 6 m threshold | part 1 |
| Whether the refund belongs to riders or landscapes, the virtual rider, the error budget, the full recipe, wind | part 2 |
| Map sources and their noise rates, FABDEM, bridges and tunnels | part 3 |
| The grid, directions, the per-step cost, the valley toll | part 4 |
| Protocol and bundle names, entry numbers, gates | the papers and the lab journal |

One number per idea. If a second number is needed to explain the first, the idea is too big for this piece.

## Decisions that are yours

1. **Which refund to print.** 0.29 is the pooled value; São Paulo's own is 0.24. Printing "between a quarter and a third" and naming 0.29 once would cover both.
2. **Publish before or after the planner test.** Beat 6 has a slot for the number a reader actually wants: the error when the estimate is made before the ride from a rider's typical constants. If that run is a day's work, do it first. If not, publish with the sentence as written; it is true today.
3. **Anhangabaú is an illustration, not a test.** It is one of your own rides and sits inside the population the constants were fitted on. The piece should say so in half a sentence, as part 3's draft already does.
4. **The kJ ≈ kcal line** rests on a 24% muscle efficiency. It needs a source before it is printed.

## Numbers sheet

Status key: **gated** = asserted by `bootstrap_ci.py` (section in brackets) · **re-run** = gated, but the gate needs `e52_split.py` re-run on the data machine first · **paper** = printed in a paper, not gated · **journal** = lab journal only · **arithmetic** = recomputed here from the package constants · **convention** = the collective's own, not in this repo · **external** = from outside the project.

| number | beat | source | status |
|---|--:|---|---|
| 400 kJ rule; scale 150 / 300 / 500 / 1,000 kJ | 1 | the published Simujaules post; part 1 draft | convention: confirm against the post |
| tyres 6.0 J/m, climb 749 J/m, air 4.9 J/m (75 kg, 50 W) | 2 | paper 1 §4.1.2 | arithmetic: 5.99, 749.0, 4.88 |
| 50 W → 16.6 km/h | 2 | paper 1 §4.1.2 | arithmetic: engine's `flat_eq_speed` gives 16.6 |
| 150 + 98 + 94 − 19 ≈ 320 kJ | 2 | paper 1 §4.1.2 | arithmetic: 149.8 + 97.6 + 93.6 − 18.7 = 322.3 |
| 1 m of climb ≈ 70 m of flat at 17 km/h | 2 | paper 3 §1.1 (69 m at 50 W) | arithmetic: 69; 48 at 23.2 km/h; 96 at 10 km/h |
| refund 0.29 | 3 | `e52_split.csv`; paper 1 Table 2 | gated [3q] as 0.294 |
| 0.24 São Paulo, 0.37 Europe | 3 | `e60_regional.csv`; paper 1 Table 4 | paper: 3t gates the errors, not these two values |
| Anhangabaú: 36.0 km, 440 m, 643 kJ; estimate on its own barometer −1.6% | 4 | paper 2 §4 | paper |
| same ride on the 5 m map: 602 m (+37%), estimate +8.7% | 4 | paper 2 §4 | paper; 602 / 440 = 1.37 checked |
| after smoothing: 449 m, estimate 0.0% | 4 | paper 2 §4 | paper |
| 92 / 77 / 56 km of climb, same 44 rides, by filter width | 4 | `make_figures.py` fig3; part 3 caption | journal: the 44 long rides of the early entries |
| 2,039 rides, seven people | 5 | paper 1 Table 1 | gated [1] |
| 305 held out, 1,734 used | 5 | `e52_summary.csv` | gated [3q] |
| median error 3.2% (3.24 [2.75, 3.50]), bias +0.07% | 5 | `e52_summary.csv` | gated [3q]; brackets re-run |
| simulation 3.2% (3.19) | 5 | `e52_summary.csv` | gated [3q] |
| 153 rides to 152 | 5 | `e52_split.py` console, 2026-09-25 | re-run: the gate now asserts 153 of 305 |
| about 8% with typical constants, 44 rides | 6 | lab journal Entry 31: 8.2 [4.5, 10.8], simulation 8.4 [5.1, 10.9] | journal: it still reads each ride's power, and it used the grade-dependent refund, not 0.29 |
| planner test (before the ride) | 6 | not run | **to produce** |
| 82% of held-out rides have a near-twin | 6, if used | `e52_summary.csv` | gated [3q] |
| 1 kJ at the pedals ≈ 1 kcal | 8 | part 2 draft | external: 0.996 at 24% efficiency, 1.20–0.96 across 20–25%; needs a citation |
| reach map at 400 kJ | 7 | Simujaules | **to produce** |

## Before it goes out

- [ ] Re-run `e52_split.py` and the gate battery, so the envelope numbers above are confirmed by a run rather than by a commit message.
- [ ] Confirm the 400 kJ rule and the scale against the published post.
- [ ] Render the reach map; redraw the two figures in Portuguese.
- [ ] Find a source for the efficiency figure, or drop the kcal line.
- [ ] Read it aloud to someone from the collective who has not followed the research. Cut whatever they did not need.
