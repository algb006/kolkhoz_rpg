---
name: rpg-string-delivery
description: Prepare and verify Kolkhoz RPG string TSVs for boss, including bilingual copy, English backlog batches, source revisions, and post-import reconciliation.
---

# RPG string delivery

Run from the RPG repository. Use [AGENTS.md](../../../AGENTS.md) for ownership,
source approval, glossary review and mail rules. The shared catalog is
`file:../db/strings.db?mode=ro`; the RPG source database is `db/story.db`.

1. Read the current keys from `string_source`, including origin, kind, revision,
   limit and Russian copy. Join `string.approved_rev` when source approval matters.
   Read the English row with its text, status and `src_rev`. Confirm the exact
   namespace and relative key with the caller. For backlog counts, query the
   live English rows directly. The `missing_translation` view filters to active
   locales and can report zero while English is planned.
2. Resolve terminology in `../db/strings/export/term_translation.md` and the
   accepted English of the relevant control or object. Use the real trigger
   and payload to check any quantities, conditions or implied outcomes.
3. Deliver `namespace<TAB>key<TAB>rev<TAB>text` per locale. For new keys, use
   proposed rev 1. For a changed RU source, report the expected next revision
   in both files and ask boss to apply and confirm the RU revision first.
   English-only translations use the existing RU revision. For an RPG-origin
   source edit, update the source in `db/story.db`, follow the
   [story DB save/check/export/render procedure](../../../db/README.md), and
   hand off the English for use after the shared RPG sync.
4. Compare key sets, placeholder names and occurrences, plural forms and
   registered display lengths. Include bindings or actual value examples if a
   template could render incorrectly. New keys need registration before an EN
   import can succeed.
5. For a batch of existing keys, run the [import preview](../../../tools/preview-english-import.py)
   from the RPG root:

   ```bash
   python3 -B tools/preview-english-import.py path/to/batch.tsv
   ```

   It reuses the shared importer on an in-memory snapshot and verifies each
   resulting EN text and `src_rev`. Draft import preserves accepted EN rows
   even when the Russian revision has moved. Route reviewed replacements
   through boss's reviewed import path.
6. Send the TSVs or inline rows in the requested parcel. Record target source
   revisions and any unresolved binding. After approval or import, reconcile
   exact wording and status against the live read-only catalog.
