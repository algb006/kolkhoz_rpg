# Пролог: сравнение архивной v1 и принятой v2

**v2 принята человеком 26 сентября 2026 года** и хранится в
`voice/accepted/prologue/`; v1 сохранена для отката в
`voice/superseded/prologue-v1/`. В обеих версиях
одинаковые 64 строки утверждённого текста `rev=2`, те же восемь голосов; v2
меняет только манеру исполнения через `speech_metadata.style`. Слушать пары
при одинаковой громкости: это исходные WAV без финального мастеринга.

| Аватар | Архивная v1 `t8` | Принятая v2 `t8` | Проверить |
|---|---|---|---|
| Деревенский | [v1](/home/alex/kolkhoz/rpg/voice/superseded/prologue-v1/scene.start.prologue.villager.t8.wav) | [v2](/home/alex/kolkhoz/rpg/voice/accepted/prologue/scene.start.prologue.villager.t8.wav) | Основательность без комического говора |
| Рабочий | [v1](/home/alex/kolkhoz/rpg/voice/superseded/prologue-v1/scene.start.prologue.worker.t8.wav) | [v2](/home/alex/kolkhoz/rpg/voice/accepted/prologue/scene.start.prologue.worker.t8.wav) | Фабричный живой ритм, не диктор |
| Студент | [v1](/home/alex/kolkhoz/rpg/voice/superseded/prologue-v1/scene.start.prologue.student.t8.wav) | [v2](/home/alex/kolkhoz/rpg/voice/accepted/prologue/scene.start.prologue.student.t8.wav) | Книжность 1920-х без детскости |
| Снятый председатель | [v1](/home/alex/kolkhoz/rpg/voice/superseded/prologue-v1/scene.start.prologue.ex_chairman.t8.wav) | [v2](/home/alex/kolkhoz/rpg/voice/accepted/prologue/scene.start.prologue.ex_chairman.t8.wav) | Сухая осторожность, не старость |
| Выдвиженец | [v1](/home/alex/kolkhoz/rpg/voice/superseded/prologue-v1/scene.start.prologue.promoted.t8.wav) | [v2](/home/alex/kolkhoz/rpg/voice/accepted/prologue/scene.start.prologue.promoted.t8.wav) | Гладкая аппаратная манера без карикатуры |
| Вояка | [v1](/home/alex/kolkhoz/rpg/voice/superseded/prologue-v1/scene.start.prologue.old_fighter.t8.wav) | [v2](/home/alex/kolkhoz/rpg/voice/accepted/prologue/scene.start.prologue.old_fighter.t8.wav) | Жёсткие короткие такты, не приказ вслух |
| Делец | [v1](/home/alex/kolkhoz/rpg/voice/superseded/prologue-v1/scene.start.prologue.dealer.t8.wav) | [v2](/home/alex/kolkhoz/rpg/voice/accepted/prologue/scene.start.prologue.dealer.t8.wav) | Лёгкий одесский оттенок, не пародия |
| Временная | [v1](/home/alex/kolkhoz/rpg/voice/superseded/prologue-v1/scene.start.prologue.acting.t8.wav) | [v2](/home/alex/kolkhoz/rpg/voice/accepted/prologue/scene.start.prologue.acting.t8.wav) | Деловая собранность без холодности |

Дополнительная пара для раннего впечатления о Дельце:
[архивная v1 `t1`](/home/alex/kolkhoz/rpg/voice/superseded/prologue-v1/scene.start.prologue.dealer.t1.wav) /
[принятая v2 `t1`](/home/alex/kolkhoz/rpg/voice/accepted/prologue/scene.start.prologue.dealer.t1.wav).

Все восемь реплик каждого аватара находятся рядом с приведённой `t8` в своих
папках; имя меняется только в конце, от `t1` до `t8`. Квитанции v2 лежат рядом
с WAV и содержат точный текст, голос, стилевую подсказку, хеш, длительность и
расход. [Технический отчёт](/data/kolkhoz/voice/prologue/v2/technical-report.json)
проверяет файлы, но не произношение и не актёрскую игру.

Сырые файлы: 54/64 прошли технический порог. Восьми нужен контроль true peak,
двум — подрезка хвостовой тишины (обе превышают порог лишь на 0,01 с). Это не
повод перегонять актёрские дубли: звуковой проход приведёт уровень и границы
файлов к игровому стандарту. До этого v2 не отправлять в UE.

Отдельное ограничение сцены: `t8` начинается в **4:22**, главная музыкальная
тема раскрывается в **4:30**, окно — 8 секунд. Три дубля v2 сейчас не
помещаются: Делец 9,04 с, Снятый председатель 10,48 с, Вояка 8,56 с.
Архивная v1 помещалась целиком. **26 сентября человек разрешил наложение
принятых v2 на начало темы.** Все 64 исходника остаются, короткие пробы
отклонены; музыку, темп речи и текст не меняем. Замер —
[аудит звуковой группы](../../sound/effects/speech_prologue_v1/t8_timing_audit_2026-09-26.md).
