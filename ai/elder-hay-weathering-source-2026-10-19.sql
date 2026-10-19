-- Own narrative source only. The line_source_changed trigger raises rev 5 -> 6.
-- Run once after checking the expected source; never execute against strings.db.
BEGIN IMMEDIATE;
CREATE TEMP TABLE rpg_elder_hay_guard (ok INTEGER CHECK (ok = 1));
INSERT INTO rpg_elder_hay_guard
SELECT CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END
FROM line
WHERE key = 'scene.elder.warnings.hay_before_snow'
  AND rev = 5
  AND text = 'Трава на корню — не зимний запас. Скосите до снега: сено и в кучах сохранится.';
UPDATE line
SET text = 'Трава на корню — не зимний запас. Скосите до снега, а сено свезите в скирду или под крышу: оставленное на лугу портится.',
    meaning = 'На лугу осталась нескошенная трава за месяц до устойчивого снега; скосить недостаточно: оставленное на лугу сено портится, его надо убрать в скирду или под крышу.',
    keep = 'Сохранить уважительное «вы» и предупреждение о траве до снега; не обещать сохранность сена на лугу и не добавлять новых условий сцены.'
WHERE key = 'scene.elder.warnings.hay_before_snow';
INSERT INTO rpg_elder_hay_guard
SELECT CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END
FROM string_source
WHERE full_key = 'scene.elder.warnings.hay_before_snow'
  AND rev = 6
  AND approved_rev IS NULL
  AND text = 'Трава на корню — не зимний запас. Скосите до снега, а сено свезите в скирду или под крышу: оставленное на лугу портится.';
DROP TABLE rpg_elder_hay_guard;
COMMIT;
