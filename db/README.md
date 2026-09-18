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

У строки `kind='choice'` поле `result` может быть `changed`, `unchanged` или `NULL`.
Это авторская метка **решения собеседника**, а не хозяйственной выгоды и не выбора
председателя. `NULL` означает, что разговор не сообщает исход для перка «Поговорить
с людьми»; у остальных видов строк `result` всегда `NULL`. Для сложного варианта
`changed` действует только при успешной попытке; при неуспехе исход `unchanged`
согласно [правилу диалогов §13](../../manual/design/chairman/dialogues.md#13-окно-и-варианты-ответа).

Случайный житель не получает готовую реплику до выбора человека из партии. Его пол,
возраст и социальный статус сначала фиксируются в `cast_slot`, затем выбирается
нейтральная либо точная мужская/женская форма строки.

## Состояние корпуса

<!-- story:coverage -->
| Сцена | Реплик | Черновиков | Утверждено |
|---|---|---|---|
| `scene.start.prologue` | 64 | 64 | 0 |
| `scene.development.roof_over_head` | 2 | 2 | 0 |
| `scene.development.own_office` | 2 | 2 | 0 |
| `scene.development.juicy_feed` | 2 | 2 | 0 |
| `scene.development.winter_crop` | 2 | 2 | 0 |
| `scene.development.teach_children` | 2 | 2 | 0 |
| `scene.development.empty_school` | 2 | 2 | 0 |
| `scene.development.first_lesson` | 1 | 1 | 0 |
| `scene.development.one_basin` | 2 | 2 | 0 |
| `scene.development.first_bath_firing` | 2 | 2 | 0 |
| `scene.development.evening_place` | 3 | 3 | 0 |
| `scene.police.neighborly` | 2 | 2 | 0 |
| `scene.family.before_distribution` | 15 | 15 | 0 |
| `scene.district.failure_explanation` | 15 | 15 | 0 |
| `scene.school_fears.teacher_opening` | 10 | 10 | 0 |
| `scene.school_fears.witch_account` | 14 | 14 | 0 |
| `scene.school_fears.source_answer` | 16 | 16 | 0 |
| `scene.school_fears.count_cloud` | 10 | 10 | 0 |
| `scene.school_fears.brave_society` | 14 | 14 | 0 |
| `scene.school_fears.words_without_owner` | 5 | 5 | 0 |
| `scene.development.night_pasture_offer` | 3 | 3 | 0 |
| `scene.school_fears.birds_settle` | 4 | 4 | 0 |
| `scene.development.first_night_pasture` | 5 | 5 | 0 |
| `scene.development.first_wall_newspaper` | 3 | 3 | 0 |
| `scene.development.second_phone_subscriber` | 5 | 5 | 0 |
| `scene.development.radio_node_test` | 3 | 3 | 0 |
| `scene.development.first_loudspeaker_broadcast` | 2 | 2 | 0 |
| `scene.development.winter_evenings_opening` | 3 | 3 | 0 |
| `scene.development.winter_evenings_result` | 4 | 4 | 0 |
| `scene.development.first_club_tv_viewing` | 4 | 4 | 0 |
| `scene.perk.talk_to_people_open` | 1 | 1 | 0 |
| `scene.perk.talk_to_people_close` | 1 | 1 | 0 |
| `scene.district.plan_warning_first` | 5 | 5 | 0 |
| `scene.district.plan_warning_last` | 5 | 5 | 0 |
| `scene.ending.trial.warning_rumour` | 2 | 2 | 0 |
| `scene.ending.trial.herd_cause` | 5 | 5 | 0 |
| `scene.ending.trial.notice` | 4 | 4 | 0 |
| `scene.ending.trial.commission` | 3 | 3 | 0 |
| `scene.ending.trial.case` | 3 | 3 | 0 |
| `scene.ending.trial.verdict` | 2 | 2 | 0 |
| `scene.ending.trial.farewell` | 4 | 4 | 0 |
| `scene.ending.office.fire` | 2 | 2 | 0 |
| `scene.ending.office.removal` | 2 | 2 | 0 |
| `scene.ending.village.warning_report` | 1 | 1 | 0 |
| `scene.ending.village.warning_rumour` | 1 | 1 | 0 |
| `scene.ending.village.liquidation` | 2 | 2 | 0 |
| `scene.era.first_transition_offer` | 5 | 5 | 0 |
| `scene.era.first_transition_refusal` | 5 | 5 | 0 |
<!-- /story -->

## Персонажи

<!-- story:characters -->
| Ключ | Кто | Вид | Пол | Возраст | Статус в мире | Редакция |
|---|---|---|---|---|---|---|
| `praskovya_ilyinichna` | Прасковья Ильинична | fixed_person | female | Взрослая; точный возраст не назначен. | Бухгалтер колхоза. | draft |
| `shibanov` | Шибанов | fixed_person | male | Взрослый; точный возраст не назначен. | Завхоз колхоза. | draft |
| `egor_panteleev` | Егор Наумыч Пантелеев | fixed_person | male | Немолод; двадцать лет знает жителей поимённо. | Участковый; соседняя по отношению к колхозу власть. | approved |
| `district_korenev` | Игнат Захарович Коренев | fixed_person | male | Старше среднего возраста. | Секретарь райкома. | draft |
| `district_stozharov` | Роман Трофимович Стожаров | fixed_person | male | Старше среднего возраста. | Старший инструктор райкома. | draft |
| `district_karasev` | Геннадий Маркович Карасёв | fixed_person | male | 30–35 лет. | Младший инструктор райкома. | draft |
| `district_zhernova` | Серафима Прокофьевна Жернова | fixed_person | female | Пожилая. | Старшая ревизор финуправления. | draft |
| `district_polushkina` | Зоя Викторовна Полушкина | fixed_person | female | Молодая, недавно после учёбы. | Младшая ревизор финуправления. | draft |
<!-- /story -->

## Арки

<!-- story:arcs -->
_Арки ещё не перенесены из Markdown._
<!-- /story -->
