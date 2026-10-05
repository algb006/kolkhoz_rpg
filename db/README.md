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

## Мысли вслух и учёт озвучки

Решение человека «Делай», переданное `boss` 27 сентября 2026:
опись находится **в этой базе**, текст — только в `line`, аудио — файлами,
не BLOB. Новые API-вызовы и генерация кабинета этим решением не разрешены.

### Схема

- `line.kind='spoken_thought'`: собственный вид мысли; `thought_avatar` — один
  из восьми аватаров, `thought_place` — `prologue/office/world`,
  `thought_trigger_kind` — `scene/item/event/signal`, `thought_trigger_ref` —
  адрес повода. Это опись уже принятых поводов, не правила их запуска.
- `voice_take`: одна запись на дубль TTS. Ссылка на реплику, `text_rev` и
  SHA256 записанного текста, аватар, голос/речевой паспорт, модель,
  JSON фактических настроек, путь квитанции, время генерации (если известно),
  статус `draft/accepted/superseded` («черновик/принято/заменено»).
- `voice_file`: файловые представления дубля. `accepted_original` и
  `technical_master` — разные WAV со своими путями и SHA256. Мастер ссылается
  на исходник посредством `source_path/source_sha256`, не считается ещё одним
  вызовом TTS. Длительность квитанции — отдельное поле
  `receipt_duration_seconds`, не подмена измерения.
- `voice_measurement`: замер конкретного файла. SHA256, время (либо NULL),
  `duration_seconds`, `lufs`, `peak_dbtp`, статус/ошибка, JSON прибора и
  происхождения. Неизвестное число — NULL, никогда не ноль. Идентификатор
  замера вычисляется из записи и происхождения; повторный импорт идемпотентен,
  в том числе при неизвестной дате. Цель мастера не определяет художественное
  принятие исходника.
- `voice_take_state`: вычисляет `current/stale` сравнением `text_rev` и
  нынешнего `line.rev`. Правка текста автоматически делает прежний дубль
  устаревшим, но не переписывает его историческое принятие.
- `latest_voice_measurement`: выбирает свежий датированный замер файла,
  предпочитая его историческому с неизвестным временем. Сводка «не измерено»
  учитывает состояние этого замера, не маскирует его ошибку прежним успехом.
- `spoken_thought_inventory`: текстовая опись с аватаром, поводом и местом.
  `string_source` сохраняет прежний namespace/ключ и `string_kind=body`;
  собственный вид передаётся в `narrative_kind`.

### Проверка и команды

```sh
python3 tools/voice_ledger.py import-accepted
python3 tools/voice_ledger.py import-measurements /путь/voice-ledger-measurements.json
python3 tools/story.py save
python3 tools/story.py check
python3 tools/story.py export
python3 tools/story.py render
python3 tools/test_voice_ledger.py
```

Импортирует только существующие WAV/JSON; не копирует и не обрабатывает звук.
Внешние пакеты `sound.voice-measurements.v1` читаются по `schema` (или `format`),
с массивом `files`. Суммы WAV, исходника мастера и отчёта происхождения
проверяются перед импортом. Несовпадающая редакция/аватар, неизвестный исходник,
нечисловой замер или другая сумма вызывают отказ с откатом пакета.
Чужие базы и звуковые файлы не изменяются.

`story.py check` печатает каждый повод × восемь аватаров, включая нули:
мыслей всего, озвучено по текущему тексту, по старому (с ключами), ждут,
не измерено. Счёт — по **уникальным репликам**, не по дублям или мастерам.
Если у реплики есть и старый, и новый принятые дубли, она входит в обе
соответствующие колонки; «ждут» — те, у кого нет текущего принятого WAV.
Проверяются отсутствие файлов/квитанций, непривязанные WAV в `voice/accepted`,
изменённые суммы и связи мастера. Строки без файлов здесь — потерянные
зарегистрированные WAV; ещё не озвученные мысли показываются как «ждут».

### Первый импорт — 27 сентября 2026

216 мыслей: пролог 64, кабинет 152. Импортированы 64 принятых дубля из
`voice/accepted/prologue`, 64 исходника и 64 мастера `sound`: всего 128 файлов
и 128 измерений. По текущему тексту озвучено 64, по старому 0, ждут 152.
Потерянных/непривязанных WAV 0. Озвучки кабинета нет и пока не должно быть.

У первоначальных записанных LUFS/пика неизвестны точное время и версия прибора:
`measured_at_utc=NULL`, неизвестная версия в JSON — NULL. Сохранено происхождение
из отчёта `sound`, путь и SHA256 отчёта, параметры, а также отдельное
`duration_verified_at_utc` для новой проверки длительности. Даты не придуманы.
Это исторический импорт имеющихся измерений, не новый замер громкости.

**Свежая поставка `sound` того же дня:** дополнительно импортированы 128
измерений из `voice-ledger-measurements-fresh.json`, с фактическим
`measured_at_utc` и версиями приборов. Теперь 256 записей измерений:
128 исторических + 128 свежих, но по-прежнему 64 дубля и 128 файлов.
Для актуальных чисел выбирается свежая запись конкретного файла по времени;
запись с NULL временем остаётся только аудиторской историей. Прежние неизвестные
метаданные не переписаны задним числом. Повторный импорт свежего пакета не
увеличивает число строк. Все файлы и редакции остались прежними.

Разметка прежних строк как мыслей меняет только классификацию и опись:
буквальный текст, `rev` и `approved_rev` сохранены. При миграции триггер
классификации временно отключается в транзакции и восстанавливается;
тест подтверждает последующее повышение `rev` при правке текста.
Дампы `schema.sql + data/*.sql` воспроизводят базу; файлы WAV остаются
на принятых местах. Массовое хранение тысяч дублей — отдельное решение.

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
| `scene.start.prologue` | 64 | 0 | 64 |
| `scene.start.office` | 168 | 0 | 168 |
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
| `scene.night_hunt.distiller_report` | 6 | 6 | 0 |
| `scene.night_hunt.distiller_leak_return` | 2 | 2 | 0 |
| `scene.elder.introduction` | 6 | 0 | 6 |
| `scene.elder.first_meeting` | 32 | 32 | 0 |
| `scene.elder.warnings` | 7 | 7 | 0 |
| `scene.elder.affected_resident_question` | 4 | 4 | 0 |
| `scene.elder.own_name` | 3 | 3 | 0 |
| `scene.elder.restore_talk` | 4 | 4 | 0 |
| `scene.elder.last_advice` | 1 | 1 | 0 |
| `scene.district.failure_explanation` | 15 | 15 | 0 |
| `scene.school_fears.teacher_opening` | 9 | 9 | 0 |
| `scene.school_fears.witch_account` | 13 | 13 | 0 |
| `scene.school_fears.source_answer` | 16 | 16 | 0 |
| `scene.school_fears.count_cloud` | 9 | 9 | 0 |
| `scene.school_fears.brave_society` | 14 | 14 | 0 |
| `scene.school_fears.words_without_owner` | 5 | 5 | 0 |
| `scene.development.night_pasture_offer` | 3 | 3 | 0 |
| `scene.school_fears.birds_settle` | 4 | 4 | 0 |
| `scene.development.first_night_pasture` | 5 | 5 | 0 |
| `scene.development.first_wall_newspaper` | 3 | 3 | 0 |
| `scene.development.second_phone_subscriber` | 4 | 4 | 0 |
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
| `scene.count_lodge.offer` | 9 | 7 | 2 |
| `scene.count_lodge.opening` | 3 | 0 | 3 |
| `scene.treasure_box.children_bring_casket` | 10 | 10 | 0 |
<!-- /story -->

## Персонажи

<!-- story:characters -->
| Ключ | Кто | Вид | Пол | Возраст | Статус в мире | Редакция |
|---|---|---|---|---|---|---|
| `praskovya_ilyinichna` | Прасковья Ильинична | fixed_person | female | Взрослая; точный возраст не назначен. | Бухгалтер колхоза. | draft |
| `shibanov` | Шибанов | fixed_person | male | Взрослый; точный возраст не назначен. | Завхоз колхоза. | draft |
| `egor_panteleev` | Егор Наумыч Пантелеев | fixed_person | male | Немолод; двадцать лет знает жителей поимённо. | Участковый; соседняя по отношению к колхозу власть. | approved |
| `elder` | {person_address} | fixed_person | male | Пожилой; точный возраст не назначен. | Бывший староста, ныне рядовой работник колхоза. | review |
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
