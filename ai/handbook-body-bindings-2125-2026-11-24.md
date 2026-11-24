# Handbook #2125. Existing body sources

Based on the eight-page table and “Устройство книги” in `manual/design/chairman/office.md`.
The page keys below belong to `ui.office`. Use only content that the player has
already seen, at the unlock event specified in the design. Keep the original
locale, selectors and displayed values. The sources below contain no new player copy.

| Page key | Existing source keys | Binding and remaining gaps |
|---|---|---|
| `handbook.page.office` | `scene.office_intro.notebooks.<avatar>`, `scene.office_intro.plan_sketch.<avatar>`, `scene.office_intro.papers.<avatar>` | Pair the matching thoughts with `ui.office.item.notebooks.name`, `ui.office.item.plan_sketch.name` and `ui.office.item.papers.name` as row captions where shown. For window captions use the observed `ui.office.group.<window>` labels, such as `group.works`, `group.map` or `group.journal`. Controls link label and destination are the existing `ui.settings.set.controls` screen. Select from what was seen to fit the page cap. |
| `handbook.page.clerk` | `ui.office.clerk.lead`, `feed.day_order_not_run` with `feed.day_order_not_run.reason.rain`, `feed.day_order_not_run.reason.day_off`, `feed.day_order_not_run.reason.no_work_on_target`, `feed.day_order_not_run.reason.on_post` | Reuse the lead with `{name}` and the feed's observed reason with its rendering context. `no_work_on_target` is the existing wording for no work at the target. `ui.office.works.stop.rain` and `ui.office.works.stop.day_off` are also available when those were the work-row messages shown. |
| `handbook.page.audit` | `feed.audit_remark` after registration | Use the feed entry shown on the first audit remark. Its text has no numeric substitution. The core still carries the shortage in per mille as event data. No registered audit write-off or two-year memory line found. |
| `handbook.page.advance` | No registered player-facing key found for issuing a newcomer advance | `YearLedger::advance` stores the issued amount. `feed.advance_written_off` is the separate debt write-off. Await the issuing ledger string before binding. |
| `handbook.page.raikom` | `feed.summon_letter`, `glossary.reputation` for «на карандаше» / “under scrutiny” | Reuse the summons once shown and the glossary's qualitative rung wording. The summons source is rev 1 and has no English translation in the DB as checked on 24 November. |
| `handbook.page.roads` | Held | The visible trail has no dedicated text. `ui.office.trip.confirm.mud` describes one district trip and is shown on a different trigger. The build menu has surface names and blurbs. No eligible trail or mud-week line found. |
| `handbook.page.thin_ice` | Held | All `scene.accident.ice.warning.{dark,crack,mounted}.<avatar>` keys are deprecated. Boss confirmed on 24 November that the game will hold the page trigger until a shown source exists. |
| `handbook.page.livestock` | `alarm.herd_starving.tip`, `alarm.herd_cold_ahead.tip`, `alarm.herd_freezing.tip`, `alarm.herd_aging.tip`, `alarm.herd_without_stable.tip` | The current database stores these alarm responses as `.tip` keys. Reuse the observed response; when the UI showed a conditional `.advice.*` answer, use that exact displayed answer and its bound values. The hay forecast uses the chosen `alarm.herd_hay_short_ahead.advice.*` line. The opening alarm must never expose unrelated unseen answers. |
| `handbook.page.personal_file` | `avatar.<avatar>.legend`, `avatar.<avatar>.line` and the active `avatar.<avatar>.path.<path>.{open,closed}` rows where present | Read the same values and keys as the selected avatar's live card. The friends text, if shown on that card, comes from the current `ui.office.avatar_friends.<avatar>.personal_file` binding. Check current card revisions, particularly the former chairman's friends description, before reuse. |

For new sources the handoff is the paired #2125 title TSV. `handbook.tab.words`
already exists at rev 1 and appears unchanged in both files for completeness.
