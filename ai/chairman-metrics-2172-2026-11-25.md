# #2172 chairman metrics. Draft string bindings

Source proposals in `econ/manual/proposals/`: `hidden-scales-2163-2026-11-25.md`
§§4–6, `authority-epoch1-2161-2026-11-25.md` §§1.3–3 and
`reputation-refresh-2156-2026-11-25.md` §§3.4–4. The November 25 follow-ups
exclude the reading scene and use the effective resident attitude from #2161.

## District letter

Use `ui.office.characteristic.title` in office mail after the annual plan
verdict. Compose only the official scales revealed by the design. For each,
pair its scale caption and one phrase from steps 1–8, ascending by attainment.
Proposed step suffixes identify text order and do not define cutoffs. The public
caption “Раскрытие хищений” names what the district can assess under the
internal `detective` scale. The letter contains no score, bar or private skill.
Display the year’s selected deed records under `characteristic.deeds.title`.
No voice is required for the letter itself.

The step sentences express development. The deed lines are separate observations
for actual annual records. These copy predicates depend on fields the producers
can supply:

| Deed line(s) | Required evidence |
|---|---|
| `discipline.theft_reviewed` | A documented theft and an actual recorded penalty. |
| `discipline.seeds_stolen` | Seed-grain theft in a storehouse already under the chairman's responsibility. Do not use for pre-acceptance loss or an audit remark alone. |
| `economy.plan_met`, `economy.issue_forecast_met` | The no-rush annual plan verdict or the distribution forecast reconciliation respectively. |
| `economy.food_sent_while_hungry` | The observed over-plan food delivery while households needed rations. |
| `agriculture.rotation_kept`, `agriculture.yield_above_forecast` | Rotation record or measured harvest against that field's forecast. |
| `agriculture.late_winter_sowing` | A missed winter-sowing window attributable to the year's work decisions. Confirm attribution before binding. |
| `technical.repair_in_time` | A repair before failure. Bind when the technical repair producer ships with #1361. |
| `detective.theft_reported` | Needs core #2167. Bind to an audit-book entry produced by `kTheftUncovered` with `reported = 1` in the reporting year. The line applies with or without an identified culprit. |

Repair deferral is out of this package until #1361 can identify the action.
`YearLedger` audit totals and the separate `kFoodStolen` occurrence cannot
establish what the district knew about an individual theft. The one report
line uses the planned per-theft source. The event does not establish that a
report was left uninvestigated.

## Authority and understanding

`personal.authority.band.*` uses the project's shared breaks at 25, 50 and 75.
The labels are village-wide. The optional band-change line takes the localized
`{band}` label.

| Authority range | Key suffix | RU | EN |
|---|---|---|---|
| Below 25 | `distrusted` | Не верят | Distrusted |
| 25 to below 50 | `sizing_up` | Присматриваются | Still sizing you up |
| 50 to below 75 | `guarded_trust` | Доверяют с оглядкой | Trusted with reservations |
| 75 and up | `respected` | Уважают | Respected |

The eight deed feed rows cover #2161's seven loud-deed cases. Fair distribution
has separate lines for raising the rate and opening a reserve so the UI can
name the action actually taken. Both correspond to one source case, with no
double credit implied. Render the qualitative cause alone. The authority bar
shows its label, and feed items show no amounts or signed deltas.

`personal.authority.understanding.budget` takes integer `{remaining}` and
`{total}` for this season. The internal thresholds 50/65/80 determine the
budget and belong in simulation, separate from the displayed bands. Select a
reason line for the confirmed harvest, hay, plan, fire, flood or herd loss. Reason and
remaining leeway are separate facts. “Spent” is for an exhausted season's
allowance. These are reports about live conditions. No allocation rules,
cutoffs or recommendations are encoded in the copy.

## Traffic

The TSV contains one RU/EN line for each of four situations and four effective
attitude bands. Worker is the strongest direct interruption. Cart is urgent
enough to make the obstruction audible. Walker stays brief and the other
contact is a quiet acknowledgement. Use the signal's actual classification
and only where the chairman's presence is involved. Preserve the proposal's
per-contact and existing cooldown limits. Match subtitles to the exact spoken
line and speaker.

| Moment | Wordless alternative to test with the established voice |
|---|---|
| Worker interrupted | A brief exhale as the work breaks off. |
| Cart stopped | A short audible intake by the carter if a reaction is needed. The horse's snort is a separate world sound. |
| Walker passing | A low sigh while stepping around the chairman. |
| Other contact | A quiet throat clear or a silent nod, according to the scene. |

A wordless clip carries no new fact and uses the same resident voice on the
Sounds channel. The silent gesture may be preferable for ordinary contact.
Start from the [resident palette proposal](../manual/voice/character-voices-proposal.md).
The draft rule already specifies 32 slots by age, sex, cohort and timbre, with
a stable selection at creation or birth. The concrete voices and compatibility
contract still need to be settled. No paid recordings are part of this draft.
