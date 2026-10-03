-- Retire only the three school-fears variants that assume church demolition.
-- Preserve their texts, revisions and conditions as historical source rows.
BEGIN IMMEDIATE;
CREATE TEMP TABLE faith_update_guard (ok INTEGER CHECK (ok = 1));
INSERT INTO faith_update_guard
SELECT CASE WHEN COUNT(*) = 3 THEN 1 ELSE 0 END FROM line
WHERE rev = 1 AND approved_rev IS NULL AND deprecated IN (0, 1)
AND (
    (key = 'dialogue.school_fears.teacher.full_lesson_no_tower'
     AND condition_ref = 'church_absent')
 OR (key = 'dialogue.school_fears.witch.retelling_no_tower'
     AND condition_ref = 'school_fears.secret=retelling; church_absent')
 OR (key = 'scene.school_fears.count_cloud.shape_no_tower'
     AND condition_ref = 'church_absent')
);
UPDATE line SET deprecated = 1 WHERE key IN (
    'dialogue.school_fears.teacher.full_lesson_no_tower',
    'dialogue.school_fears.witch.retelling_no_tower',
    'scene.school_fears.count_cloud.shape_no_tower'
);
DROP TABLE faith_update_guard;
COMMIT;
