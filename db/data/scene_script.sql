-- scene_script: 2 строк. Файл создаётся tools/story.py save —
-- правится база, не этот дамп. Порядок строк детерминирован.
DELETE FROM "scene_script";
INSERT INTO "scene_script" ("scene_key", "arc_key", "story_branch_key", "source_ref", "status", "note", "sort") VALUES ('scene.police.neighborly', NULL, NULL, 'manual/characters/panteleev.md#по-соседски--бумага-подождёт', 'draft', NULL, 680);
INSERT INTO "scene_script" ("scene_key", "arc_key", "story_branch_key", "source_ref", "status", "note", "sort") VALUES ('scene.start.prologue', NULL, NULL, 'ai/prologue-avatar-thoughts-draft.md', 'draft', '64 внутренние мысли: восемь абсолютных секунд, по варианту для каждого аватара. Живой прогон ещё не выполнен; approved_rev у строк остаётся NULL.', 10);
