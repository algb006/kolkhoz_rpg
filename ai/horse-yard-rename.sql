-- Переименование по слову человека 1 октября 2026.
-- Меняются только русский текст и описания; ключи остаются прежними.
-- Однократная миграция существующей story.db, не часть её сборки.
.bail on
BEGIN IMMEDIATE;
CREATE TEMP TABLE horse_yard_rename_guard (n INTEGER CHECK (n = 6));
INSERT INTO horse_yard_rename_guard
SELECT
    (SELECT count(*) FROM line
      WHERE key = 'scene.elder.first_meeting.layout.collective_yard'
        AND text LIKE 'Колхозный двор %')
  + (SELECT count(*) FROM line
      WHERE scene_key = 'scene.development.night_pasture_offer'
        AND context LIKE 'У колхозного двора;%')
  + (SELECT count(*) FROM cast_slot
      WHERE scene_key IN ('scene.development.first_night_pasture',
                          'scene.development.night_pasture_offer')
        AND key = 'groom' AND social_status = 'Конюх колхозного двора.');

UPDATE line
   SET text = replace(text, 'Колхозный двор', 'Конный двор')
 WHERE key = 'scene.elder.first_meeting.layout.collective_yard';
UPDATE line
   SET context = replace(context, 'У колхозного двора', 'У конного двора')
 WHERE scene_key = 'scene.development.night_pasture_offer'
   AND context LIKE 'У колхозного двора;%';
UPDATE cast_slot
   SET social_status = 'Конюх конного двора.'
 WHERE scene_key IN ('scene.development.first_night_pasture',
                     'scene.development.night_pasture_offer')
   AND key = 'groom';

DROP TABLE horse_yard_rename_guard;
COMMIT;
