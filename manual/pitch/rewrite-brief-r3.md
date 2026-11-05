# Investor description — round 3: a CRITICAL REWRITE (#1565)

**Read this whole brief, then reread the current `investor-description-ru.md` as a hostile editor before writing a line.**

## The human's verdict on round 2, verbatim (tasks.db #1721, 5 Nov 2026)

> «Эпохи у нас определяются не годами а укладом. 1 эпоха лошади и выживание. Бедное село без излишеств. 2 эпоха транспорт и развитие. Визуально примерно 40 50е годы ссср. 3 эпоха это 60-80 годы ссср. В документе совсем выпала социальная тема, отдых, спорт, демография. Также важно подчеркнуть высокий реализм экономики и игрового мира, он не выглядит игрушечным. Реальные расстояния, большая карта целого региона доступная для строительства и освоения. Реалистичная симуляция, логистика, жизнь жителей. Реалистичные сцены жизни деревни связанные с квестами. Мощная рпг компонента что отличает игру от других этого жанра. Цель сделать длинную увлекательную игру с повторным геймплеем. Сейчас документ большой, но очень тяжелый скучный слог и при большом обьеме текста не вместил и малой части того что надо.»

Earlier rounds, still binding: a LIVE description for a potential investor, in Russian, detailed; no economy figures, no prices, no development dates or durations (#1714, #1717); «попаданец» named early as the genre hook, without hindsight (#1720); third person is the main mode, first person is immersion (#1720); the roadmap at the end, by phases (#1716).

## What is wrong with the current text — fix all of it

1. **The prose is heavy and dull.** Long abstract sentences, officialese («обеспечивает», «предполагает», «в рамках», «осуществляет»), explanations of explanations, hedging («может», «предлагается», «не объявляет»). An investor stops reading on page one. **Rewrite, do not edit.** Keep at most the opening road scene.
2. **Volume without content.** It is long and still misses most of what matters. Every paragraph must carry a concrete picture or a concrete claim about the game. Cut every sentence that only frames, qualifies or repeats.
3. **Missing entirely:** the social side — leisure, holidays, the club, the bathhouse, sport, dances, the beach; demography — families, births, children growing up, ageing, people leaving and arriving, the village growing from a handful of households to a large one.
4. **Under-sold:** the REALISM. The world is not a toy: real distances, a large map of a whole region open to building and settlement, roads that take real time, logistics where carts and later trucks move real loads, an economy that holds together, residents who live full lives. Say it with confidence and with pictures, not adjectives.
5. **Under-sold:** quests as REALISTIC SCENES OF VILLAGE LIFE, born from the state of the farm and the people (a wedding, a fire, a sick child, a fair, a district inspection, a drunk tractor driver, the first electric light).
6. **Under-sold:** the RPG component — origins (eight avatars), the chairman's growth, the idea line, the humanist, the shadow economy, the role endings — as THE thing that sets this game apart in its genre.
7. **The goal must be explicit:** a long, absorbing game you replay — different avatars, different paths, different villages.
8. **Epochs are by WAY OF LIFE, not by years** (the human's correction). Use his words:
   - **Epoch I — horses and survival.** A poor village with nothing extra. Starts in 1931 of the parallel USSR.
   - **Epoch II — transport and development.** Visually roughly the 1940s-50s of the USSR.
   - **Epoch III — the 1960s-80s of the USSR.**
   Remove the «[годы эпохи — уточняется]» placeholders. The epoch opens by the farm's readiness, not by the calendar; its LOOK is of those decades. The game's dates never follow real Soviet history (parallel USSR, setting §10).

## Style

- Short, vivid, concrete. Scenes and verbs. A reader should SEE the village in each section.
- Confident present tense about what the game is. Vision (not yet designed) is marked once per section in a plain word («в замысле»), not hedged in every sentence.
- Headings that sell, not headings that classify.
- Allowed numbers: the start year 1931, the decades of the epochs' look, «Колхоз 2». No other figures.
- Length: as long as the content needs, no padding. A rough guide: every section must earn its place by new content; if two sections say the same thing, merge them.

## Canon to draw on (read; do not invent mechanics)

- Positioning, competitors, setting: `manual/design/core/game-setting.md` (now says third person is the main mode), `epochs.md`, `tone.md` (red lines hold), `start.md` (prologue).
- People and social life: `manual/design/people/` — `leisure.md`, `demography.md`, `life-cycle.md`, `society.md`, `needs.md`, `health.md`, `education.md`, `metrics.md`, `party-komsomol-quests.md`; `manual/design/world/units/social.md`, `catering.md`, `housing.md`.
- World and realism: `manual/design/world/map/terrain.md`, `relief-v2.md`, `manual/design/infrastructure/` (roads, transport, vehicles, mts, electricity, water, construction), `manual/design/economy/` (farming, livestock, resources, timber, labor-payment, household-farming, shadow), `manual/design/order/` (fire, crime, wildlife).
- Live world: `manual/design/presentation/live-signals.md`, `camera-and-visuals.md`, `audio.md`.
- RPG: `manual/design/chairman/avatars.md`, `role-lines.md`, `quests.md`, `road-home.md`, `dialogues.md`, `delegation.md`; your own `rpg/manual/story/` and `rpg/manual/quests/`.
- Roadmap: `manual/process/82-roadmap.md`.

## Process

1. First write a short critique of the current text for yourself (what to cut, what is missing) in `rpg/ai/investor-description-1565-r3-critique.txt`.
2. Then write the new `rpg/manual/pitch/investor-description-ru.md` from scratch.
3. Reread it once more as the investor would: anything boring, abstract or repeated goes.
4. Commit, push, report to boss: the path, a 5-line summary of what changed, and any canon contradiction you met (do not resolve it silently).

— Колхозный Босс, 5 November 2026
