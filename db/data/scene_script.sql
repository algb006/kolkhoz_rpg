-- scene_script: 1 строк. Файл создаётся tools/story.py save —
-- правится база, не этот дамп. Порядок строк детерминирован.
DELETE FROM "scene_script";
INSERT INTO "scene_script" ("scene_key", "arc_key", "story_branch_key", "source_ref", "status", "note", "sort") VALUES ('scene.police.neighborly', NULL, NULL, 'manual/characters/panteleev.md#по-соседски--бумага-подождёт', 'draft', NULL, 680);
