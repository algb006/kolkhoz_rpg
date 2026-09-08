-- Сюжетная база RPG-слоя: голоса, авторская структура сцен и реплики.
--
-- Механика сцены (запуск, повтор, пропуск, эпоха) остаётся в
-- ../db/design.db.scene. Здесь scene_key — только внешняя ссылка, которую
-- проверяет tools/story.py check.

PRAGMA foreign_keys = ON;

CREATE TABLE character (
    key           TEXT PRIMARY KEY
                       CHECK (key GLOB '[a-z][a-z0-9_]*'
                              AND key NOT GLOB '*[^a-z0-9_]*'),
    kind          TEXT NOT NULL CHECK (kind IN (
                      'fixed_person',       -- один и тот же человек во всех партиях
                      'role_voice',         -- голос сменяемой должности
                      'procedural_voice')), -- рамка для случайного жителя
    title         TEXT NOT NULL,            -- редакционное имя
    display_name  TEXT,                     -- имя в мире; NULL у сменяемой роли
    gender        TEXT NOT NULL CHECK (gender IN ('male', 'female', 'variable')),
    age_profile   TEXT NOT NULL,            -- возраст или честно записанная неизвестность
    social_status TEXT NOT NULL,
    address_rule  TEXT NOT NULL,            -- ты/вы, имя-отчество, допустимая дистанция
    voice         TEXT NOT NULL,            -- краткий паспорт голоса
    source_ref    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'draft'
                       CHECK (status IN ('draft', 'review', 'approved', 'retired')),
    note          TEXT,
    sort          INTEGER NOT NULL DEFAULT 0,
    CHECK (kind <> 'fixed_person' OR
           (display_name IS NOT NULL AND gender <> 'variable'))
);

CREATE TABLE arc (
    key         TEXT PRIMARY KEY
                     CHECK (key GLOB '[a-z][a-z0-9_]*'
                            AND key NOT GLOB '*[^a-z0-9_]*'),
    title       TEXT NOT NULL,
    era_from    TEXT CHECK (era_from IS NULL OR era_from IN ('era_1', 'era_2', 'era_3')),
    era_to      TEXT CHECK (era_to IS NULL OR era_to IN ('era_1', 'era_2', 'era_3')),
    role_focus  TEXT NOT NULL,              -- идейный / гуманист / хозяин / смешанная
    summary     TEXT NOT NULL,
    source_ref  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft', 'review', 'approved', 'retired')),
    note        TEXT,
    sort        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE story_branch (
    key             TEXT PRIMARY KEY
                         CHECK (key GLOB '[a-z][a-z0-9_]*'
                                AND key NOT GLOB '*[^a-z0-9_]*'),
    arc_key         TEXT NOT NULL REFERENCES arc(key),
    parent_key      TEXT REFERENCES story_branch(key),
    title           TEXT NOT NULL,
    entry_quest_key TEXT,                   -- внешний ключ из design.db.quest
    condition_ref   TEXT,                   -- уже существующие факты/условия, не новая логика
    optional        INTEGER NOT NULL DEFAULT 0 CHECK (optional IN (0, 1)),
    summary         TEXT NOT NULL,
    source_ref      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft'
                         CHECK (status IN ('draft', 'review', 'approved', 'retired')),
    note            TEXT,
    sort            INTEGER NOT NULL DEFAULT 0,
    CHECK (parent_key IS NULL OR parent_key <> key)
);

-- Авторская сторона строки design.scene. Никаких полей запуска здесь нет.
CREATE TABLE scene_script (
    scene_key        TEXT PRIMARY KEY
                          CHECK (scene_key GLOB 'scene.[a-z0-9_.]*'
                                 AND scene_key NOT GLOB '*[^a-z0-9_.]*'),
    arc_key          TEXT REFERENCES arc(key),
    story_branch_key TEXT REFERENCES story_branch(key),
    source_ref       TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'draft'
                          CHECK (status IN ('draft', 'review', 'approved', 'retired')),
    note             TEXT,
    sort             INTEGER NOT NULL DEFAULT 0
);

-- Роль в одной сцене. Случайный житель сначала выбирается из партии, и только
-- затем его точный пол/возраст/статус определяют допустимый вариант реплики.
CREATE TABLE cast_slot (
    scene_key       TEXT NOT NULL REFERENCES scene_script(scene_key) ON DELETE CASCADE,
    key             TEXT NOT NULL
                         CHECK (key GLOB '[a-z][a-z0-9_]*'
                                AND key NOT GLOB '*[^a-z0-9_]*'),
    title           TEXT NOT NULL,
    binding_kind    TEXT NOT NULL CHECK (binding_kind IN (
                        'chairman', 'fixed_character', 'role_holder',
                        'procedural_resident', 'group')),
    character_key   TEXT REFERENCES character(key),
    role_ref        TEXT,
    gender_binding  TEXT NOT NULL CHECK (gender_binding IN (
                        'fixed_male', 'fixed_female', 'runtime_resident',
                        'chairman_avatar', 'mixed_group')),
    age_binding     TEXT NOT NULL,
    social_status   TEXT NOT NULL,
    relation_note   TEXT NOT NULL,
    address_rule    TEXT NOT NULL,
    count_min       INTEGER NOT NULL DEFAULT 1 CHECK (count_min >= 1),
    count_max       INTEGER NOT NULL DEFAULT 1 CHECK (count_max >= count_min),
    note            TEXT,
    sort            INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scene_key, key),
    CHECK ((binding_kind = 'fixed_character') = (character_key IS NOT NULL)),
    CHECK (binding_kind <> 'group' OR count_max > 1)
);

CREATE TABLE choice_group (
    scene_key     TEXT NOT NULL REFERENCES scene_script(scene_key) ON DELETE CASCADE,
    key           TEXT NOT NULL
                       CHECK (key GLOB '[a-z][a-z0-9_]*'
                              AND key NOT GLOB '*[^a-z0-9_]*'),
    title         TEXT NOT NULL,
    condition_ref TEXT,
    note          TEXT,
    sort          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scene_key, key)
);

-- Одна переводимая строка. Альтернативы пола или аватара имеют общий
-- variant_key, но разные ключи строк и условия. Варианты выбора имеют
-- kind='choice' и принадлежат choice_group.
CREATE TABLE line (
    key                 TEXT PRIMARY KEY
                             CHECK (key GLOB '[a-z][a-z0-9_.]*'
                                    AND key NOT GLOB '*[^a-z0-9_.]*'),
    scene_key           TEXT NOT NULL REFERENCES scene_script(scene_key) ON DELETE CASCADE,
    namespace           TEXT NOT NULL CHECK (namespace IN (
                            'quest', 'event', 'dialogue', 'scene')),
    kind                TEXT NOT NULL CHECK (kind IN (
                            'dialogue', 'choice', 'narration', 'document',
                            'journal', 'caption', 'backdrop')),
    speaker_slot        TEXT,
    addressee_slot      TEXT,
    relationship       TEXT,
    choice_group_key    TEXT,
    variant_key         TEXT,
    grammatical_gender TEXT NOT NULL DEFAULT 'neutral'
                              CHECK (grammatical_gender IN ('neutral', 'male', 'female')),
    condition_ref       TEXT,
    previous_key        TEXT REFERENCES line(key),
    text                TEXT NOT NULL CHECK (length(trim(text)) > 0),
    context             TEXT NOT NULL,
    meaning             TEXT NOT NULL,
    intent              TEXT NOT NULL,
    keep                TEXT NOT NULL,
    source_ref          TEXT NOT NULL,
    rev                 INTEGER NOT NULL DEFAULT 1 CHECK (rev >= 1),
    approved_rev        INTEGER CHECK (approved_rev IS NULL OR
                                       (approved_rev >= 1 AND approved_rev <= rev)),
    deprecated          INTEGER NOT NULL DEFAULT 0 CHECK (deprecated IN (0, 1)),
    sort                INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (scene_key, speaker_slot)
        REFERENCES cast_slot(scene_key, key),
    FOREIGN KEY (scene_key, addressee_slot)
        REFERENCES cast_slot(scene_key, key),
    FOREIGN KEY (scene_key, choice_group_key)
        REFERENCES choice_group(scene_key, key),
    CHECK ((kind = 'choice') = (choice_group_key IS NOT NULL)),
    CHECK (kind NOT IN ('dialogue', 'choice') OR speaker_slot IS NOT NULL),
    CHECK (speaker_slot IS NOT NULL OR addressee_slot IS NULL),
    CHECK (variant_key IS NULL OR length(trim(variant_key)) > 0),
    CHECK (substr(key, 1, length(namespace) + 1) = namespace || '.')
);

CREATE INDEX line_scene_sort ON line (scene_key, sort, key);
CREATE INDEX line_choice ON line (scene_key, choice_group_key, sort);
CREATE INDEX line_variant ON line (scene_key, variant_key, grammatical_gender);

CREATE TABLE line_placeholder (
    line_key TEXT NOT NULL REFERENCES line(key) ON DELETE CASCADE,
    name     TEXT NOT NULL
                  CHECK (name GLOB '[a-z][a-z0-9_]*'
                         AND name NOT GLOB '*[^a-z0-9_]*'),
    kind     TEXT NOT NULL CHECK (kind IN (
                 'int', 'real', 'text', 'name', 'date', 'money', 'amount')),
    meaning  TEXT NOT NULL,              -- что именно подставляется в мире
    note     TEXT,
    PRIMARY KEY (line_key, name)
);

-- Любая правка русского источника или переводческого контекста делает ранее
-- утверждённую редакцию черновиком: approved_rev остаётся на старом числе.
CREATE TRIGGER line_source_changed
AFTER UPDATE OF text, context, meaning, intent, keep, kind, speaker_slot,
                addressee_slot, relationship, choice_group_key, variant_key,
                grammatical_gender, condition_ref, previous_key
ON line
WHEN NEW.text IS NOT OLD.text
  OR NEW.context IS NOT OLD.context
  OR NEW.meaning IS NOT OLD.meaning
  OR NEW.intent IS NOT OLD.intent
  OR NEW.keep IS NOT OLD.keep
  OR NEW.kind IS NOT OLD.kind
  OR NEW.speaker_slot IS NOT OLD.speaker_slot
  OR NEW.addressee_slot IS NOT OLD.addressee_slot
  OR NEW.relationship IS NOT OLD.relationship
  OR NEW.choice_group_key IS NOT OLD.choice_group_key
  OR NEW.variant_key IS NOT OLD.variant_key
  OR NEW.grammatical_gender IS NOT OLD.grammatical_gender
  OR NEW.condition_ref IS NOT OLD.condition_ref
  OR NEW.previous_key IS NOT OLD.previous_key
BEGIN
    UPDATE line SET rev = OLD.rev + 1 WHERE key = NEW.key;
END;

CREATE VIEW draft_line AS
SELECT key, scene_key, text, rev, approved_rev
  FROM line
 WHERE deprecated = 0
   AND (approved_rev IS NULL OR approved_rev < rev)
 ORDER BY scene_key, sort, key;

CREATE VIEW scene_coverage AS
SELECT s.scene_key,
       count(l.key) AS lines,
       sum(CASE WHEN l.key IS NOT NULL AND
                     (l.approved_rev IS NULL OR l.approved_rev < l.rev)
                THEN 1 ELSE 0 END) AS drafts,
       sum(CASE WHEN l.key IS NOT NULL AND l.approved_rev = l.rev
                THEN 1 ELSE 0 END) AS approved
  FROM scene_script s
  LEFT JOIN line l ON l.scene_key = s.scene_key AND l.deprecated = 0
 GROUP BY s.scene_key
 ORDER BY s.sort, s.scene_key;

-- Стабильный шов для будущего sync в strings.db. В нём нет перевода и нет
-- механики сцены — только русский источник и всё, что нужно переводчику.
CREATE VIEW string_source AS
SELECT l.namespace,
       substr(l.key, length(l.namespace) + 2) AS source_key,
       l.key AS full_key,
       l.scene_key,
       CASE WHEN l.kind = 'journal' THEN 'log' ELSE 'body' END AS string_kind,
       l.kind AS narrative_kind,
       l.text,
       l.context,
       l.meaning,
       l.intent,
       l.keep,
       l.rev,
       l.approved_rev,
       l.deprecated,
       l.sort
  FROM line l
 ORDER BY l.scene_key, l.sort, l.key;

CREATE VIEW string_placeholder_source AS
SELECT line_key AS source_key, name, kind, meaning, note
  FROM line_placeholder
 ORDER BY line_key, name;

CREATE VIEW line_translation_context AS
SELECT l.key,
       l.scene_key,
       l.kind,
       coalesce(sc.display_name, sp.title) AS speaker,
       coalesce(ac.display_name, ad.title) AS addressee,
       l.relationship,
       l.text,
       p.text AS previous_text,
       (SELECT n.text FROM line n
         WHERE n.previous_key = l.key AND n.deprecated = 0
         ORDER BY n.sort, n.key LIMIT 1) AS next_text,
       l.context,
       l.meaning,
       l.intent,
       l.keep,
       l.rev,
       l.approved_rev
  FROM line l
  LEFT JOIN cast_slot sp ON sp.scene_key = l.scene_key AND sp.key = l.speaker_slot
  LEFT JOIN character sc ON sc.key = sp.character_key
  LEFT JOIN cast_slot ad ON ad.scene_key = l.scene_key AND ad.key = l.addressee_slot
  LEFT JOIN character ac ON ac.key = ad.character_key
  LEFT JOIN line p ON p.key = l.previous_key
 WHERE l.deprecated = 0
 ORDER BY l.scene_key, l.sort, l.key;
