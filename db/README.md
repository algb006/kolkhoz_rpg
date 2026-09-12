# Сюжетная база RPG

`story.db` хранит авторскую половину сюжета: персонажей, арки, ветви, состав сцен и
реплики. Запуск, повторяемость и возможность пропуска сцены остаются в
`../../db/design.db`; переводимые строки позже синхронизируются в
`../../db/strings.db`.

Двоичный `story.db` в git не лежит. Его воспроизводимая копия —
[`schema.sql`](schema.sql) и `data/*.sql`.

```sh
python3 tools/story.py init
python3 tools/story.py save
python3 tools/story.py check
python3 tools/story.py export
python3 tools/story.py render
```

После изменения базы обязательный порядок: `save` → `check` → `export` → `render`.

## Граница

| Здесь | Не здесь |
|---|---|
| Кто говорит, кому и кем они приходятся | Когда сцена запускается |
| Точная реплика и варианты | Повтор, пропуск и эпоха сцены |
| Пол, возраст и статус говорящего | Ключи квестов, сцен и фактов |
| `meaning`, `intent`, `keep` | Переводы на другие языки |
| Namespace и локальный ключ для синхронизации | Устройство общей базы строк |
| `rev` и `approved_rev` русского источника | Статус готовности перевода |

Случайный житель не получает готовую реплику до выбора человека из партии. Его пол,
возраст и социальный статус сначала фиксируются в `cast_slot`, затем выбирается
нейтральная либо точная мужская/женская форма строки.

## Состояние корпуса

<!-- story:coverage -->
| Сцена | Реплик | Черновиков | Утверждено |
|---|---|---|---|
| `scene.start.prologue` | 64 | 64 | 0 |
| `scene.police.neighborly` | 2 | 2 | 0 |
| `scene.development.night_pasture_offer` | 3 | 3 | 0 |
| `scene.development.first_night_pasture` | 5 | 5 | 0 |
| `scene.development.first_wall_newspaper` | 3 | 3 | 0 |
| `scene.development.second_phone_subscriber` | 5 | 5 | 0 |
| `scene.development.radio_node_test` | 3 | 3 | 0 |
| `scene.development.first_loudspeaker_broadcast` | 2 | 2 | 0 |
| `scene.development.winter_evenings_opening` | 3 | 3 | 0 |
| `scene.development.winter_evenings_result` | 4 | 4 | 0 |
| `scene.development.first_club_tv_viewing` | 4 | 4 | 0 |
<!-- /story -->

## Персонажи

<!-- story:characters -->
| Ключ | Кто | Вид | Пол | Возраст | Статус в мире | Редакция |
|---|---|---|---|---|---|---|
| `egor_panteleev` | Егор Наумыч Пантелеев | fixed_person | male | Немолод; двадцать лет знает жителей поимённо. | Участковый; соседняя по отношению к колхозу власть. | approved |
<!-- /story -->

## Арки

<!-- story:arcs -->
_Арки ещё не перенесены из Markdown._
<!-- /story -->
