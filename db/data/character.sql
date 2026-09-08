-- character: 1 строк. Файл создаётся tools/story.py save —
-- правится база, не этот дамп. Порядок строк детерминирован.
DELETE FROM "character";
INSERT INTO "character" ("key", "kind", "title", "display_name", "gender", "age_profile", "social_status", "address_rule", "voice", "source_ref", "status", "note", "sort") VALUES ('egor_panteleev', 'fixed_person', 'Егор Наумыч Пантелеев', 'Егор Наумыч Пантелеев', 'male', 'Немолод; двадцать лет знает жителей поимённо.', 'Участковый; соседняя по отношению к колхозу власть.', 'С председателем — рабочее «вы»; сближение делает речь суше, а не фамильярнее.', 'Короткая фраза после наблюдения; бумага — конкретный предмет; сначала разговор, затем протокол.', 'manual/characters/panteleev.md', 'approved', NULL, 10);
