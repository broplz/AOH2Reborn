# ADR-0001 · AI-команда: роли, конвейер задач, проверка без игры

Oct 28, 2026 · @broplz

## Статус

Proposed — комплект собран по образцу BROzen BROwser (ADR-0012 там) и прогнан на этом репо:
`check.sh`, `test.sh`, `kvcheck.py`, `vanilla_diff.py`, хуки. После первого реального цикла на
задачах фазы 0–1 статус меняется на Accepted.

- Область: `.claude/` (agents, hooks, skills, settings), `CLAUDE.md`, `scripts/agents/`, `tools/`,
  `tests/`, `tasks/`, `docs/reports/`, `.github/workflows/ci.yml`.
- Основание: конвейер BB (ADR-0012, 28.10.2026) и опыт RotS, перенесённый с тремя отличиями,
  которые диктует Dota: нет сборки, игра не запускается с Mac, KV — второй язык проекта.
- Воплощает решения владельца: main сливает только человек; работа ведётся в Claude Code локально;
  карту переписываем инкрементально, по аудиту (ADR-0002).

## Контекст и проблема

Код карты не трогали с июня 2023: 36 тыс. строк Lua, 52 тыс. строк KV, тикет-система боссов,
которую сам автор просил заменить, и Dota, которая с тех пор прошла 7.34–7.41f. Аудит нашёл
~40 багов, 62 дефекта KV, 4 удалённых ванильных имени и ~5.4 тыс. предупреждений luacheck
(675 — обращения к неопределённым переменным). Один владелец задаёт вектор; всю рутину должны
делать агенты «пока задача не сделана или не появился блокер».

Чем Dota отличается от BB для конвейера:

1. **Сборки нет.** Lua не компилируется, KV читается движком на старте карты. Зато есть дешёвые
   статические проверки: luacheck с полным списком API движка, stylua, валидатор KV, сверка имён с
   текущим билдом Valve. Цикл проверки — секунды, а не 40 минут.
2. **Игру здесь не запустить.** Workshop Tools — Windows-only; у агентов нет Dota. Всё, что видно
   только в игре, — `[human]`-пункт DoD, который закрывает владелец плейтестом. Логику, которая
   не зависит от движка (очередь кастов, парсеры, математика), агенты проверяют юнит-тестами на
   заглушке API (`tests/dota_stub.lua`).
3. **KV — не конфиг, а половина кода.** 154 datadriven-способности, 552 оверрайда в формате,
   которого у Valve больше нет. Проверки KV — отдельный линт с «храповиком» (baseline известных
   дефектов, падает только на новых).

## Требования

- R1. Человек принимает только ключевые решения: ADR, порядок бэклога, одобрение изменений в ядре
  (gamemode/round/spawner, modifier_boss, generic.lua, магазин, список героев), плейтест на гейте
  фазы, `feat → main`.
- R2. Минимум токенов: короткие свежие сессии, sonnet на код и QA, opus на ревью/декомпозицию/ядро,
  ноль токенов на детерминированное (merge, lint, kvcheck, отчёт).
- R3. Контекст не переполняется: KV-файлы по 20 тыс. строк никогда не читаются целиком; лимиты
  ходов и бюджета; Handoff вместо обрыва.
- R4. Режим «до готовности или блокера»: `run_task.py`/`run_queue.py` ведут задачу до `done`,
  останавливаясь только на решении человека.
- R5. Конвенции ADR-0002 нельзя нарушить незаметно: хуки + `aoh_lint.py` + `kvcheck.py`, не промпты.

## Решение 1 — роли и модели

| Роль | Модель | Делает | Не делает |
|---|---|---|---|
| teamlead | opus / high, память | ADR + бэклог → файлы задач; разблокировка (split / re-spec / escalate) | код, merge |
| developer | sonnet / medium | способности, предметы, модификаторы, KV-записи, локализация, Panorama-исходники | ядро, миграции KV на много записей |
| developer-hard | opus / high | aohgamemode/round/spawner, modifier_boss и очередь кастов, generic.lua, lib/, миграции KV, безопасность событий | — |
| reviewer | opus / high, память | вердикт по DoD, ADR-0002 и capped diff; `aoh_lint.py` | код, check.sh |
| qa | sonnet / medium | `check.sh`, `test.sh`, DoD буквально, тест на логику без теста, PASS/FAIL с repro; список `[human]` для владельца | правка кода |
| architect | fable / high, интерактивно | ADR в репо, с источниками по текущему билду Dota | конвейер |

Убрано относительно BB: **rebaser** (нет апстрима; синхронизация с патчами Dota — скрипт
`tools/vanilla_snapshot.py` + `vanilla_diff.py` и обычная задача) и **log-triage** (логи
проверок короткие; `triage_log.py` хватает). Как и в BB, нет CEO и ops.

## Решение 2 — задача как единица работы, сессия как расходник

Без изменений относительно BB ADR-0012 §2: `tasks/<id>-<slug>.md` = ветка `task/<id>-<slug>` от
`feat/pN-*`; размеры S/M/L (150/300/500 строк, 5/10/15 файлов); свежая `claude -p --agent <role>`
сессия на каждый прогон; лимиты `--max-turns` и `--max-budget-usd` из `scripts/agents/config.py`
(dev S 25 / M 40 / L 55 ходов — короче, чем в BB, потому что нет ожидания сборки); чекпоинт
на 60 % и 85 % ходов; три сессии без `review` → `blocked: too_big`.

Отличия в полях задачи: `checks: none|lua|kv|all` вместо `build`, `tests:` — паттерны для
`test.sh`, `epic`/`prefix` = фаза (`p0`…`p6`), `needs_approval` обязателен при любом
`[human]`-пункте (это и проверяет `aoh_lint.py`).

Гигиена входа (`guard_read.py`): файл > 200 КБ (каждый `npc_*.txt`) только с `offset/limit ≤ 400`;
бинарные и скомпилированные ассеты (`*_c`, `.vmap`, `.vtex`, `.png`) не читаются вовсе; Grep по
репо — только с `glob`/`type` и `head_limit ≤ 150`; для одной KV-записи —
`python3 tools/kvcheck.py --show <entry>`.

## Решение 3 — конвейер и точки человека

Цикл тот же, что в BB (`run_task.py`): developer → reviewer → qa → merge-скрипт → done, с
`returned`/`blocked` и разовой разблокировкой teamlead. Merge — `merge_task.py`, ноль токенов:
статус, оба вердикта, `reviewed_sha == qa_sha == code head`, `aoh_lint.py`, одобрение.

Точки человека (`tasks/approvals.txt`, строка `<id> approved`):

- любой `[human]`-пункт в DoD (всё, что видно только в игре);
- изменения в ядре: `aohgamemode.lua`, `aohgameround.lua`, `aohspawner.lua`, `dashmanager.lua`,
  `modifier_boss.lua`, `modifier_main_boss.lua`, `generic.lua`, `scripts/shops/`, `scripts/config/`,
  `herolist.txt`, `npc_heroes_custom.txt` (`APPROVAL_RE` в `config.py`);
- гейт фазы: `finish_feature.sh` требует `check.sh all`, `test.sh` и ручной плейтест по чеклисту
  фазы из ADR-0002 перед `feat → main`.

Плейтест владельца должен занимать минуты: developer пишет в `## Result` точные шаги и строку
консоли (`print`), которая доказывает результат; qa переносит их в «For the human».

## Решение 4 — проверки без игры

| Инструмент | Что ловит | Кто запускает |
|---|---|---|
| `.luacheckrc` (генерируется из `@moddota/dota-data` 0.47.2: 3352 имени API, enum'ов, классов) | необъявленные переменные (`ability`, `ParticlzeManager`, `DOTA_UNIT_TARGET_FLAGS_NONE`), новые глобалы, неиспользуемые переменные | `check.sh lua` |
| `stylua` (Lua51, табы, 120) | форматирование; единый стиль для diff'ов | `check.sh lua` |
| `tools/kvcheck.py` + `kvcheck.baseline` | синтаксис KV, дубли записей и ключей, несуществующий `ScriptFile`, `\\` в путях, legacy `AbilitySpecial` (WARN) | `check.sh kv` |
| `tools/vanilla_diff.py` + `vanilla_snapshot.py` | имена, которых нет в текущем билде Dota (BaseClass, оверрайды, таланты-инлайн, новые герои) | `check.sh kv`, после каждого патча Valve |
| `tests/run.lua` + `tests/dota_stub.lua` | юнит-тесты логики без движка; первый — `core/boss_queue.lua` (6 тестов) | `test.sh` |
| `scripts/agents/aoh_lint.py` | конвенции ADR-0002 на добавленных строках diff'а: глобалы, магические числа, `keys.id`, `GetItemInSlot(16)`, `AbilitySpecial` в новом KV, доступ к HUD Valve из Panorama, allowed_paths, размер, `[human]` ⇒ approval | qa, merge |

Область Lua-проверок по умолчанию — файлы, изменённые на ветке относительно `base` (+ `tests/`):
легаси-дерево (5.4 тыс. предупреждений) линтуется по мере того, как задачи его трогают;
`--all-files` — для задачи 0003 (форматирование репо одним коммитом) и ночного CI.

Храповик: `kvcheck.baseline` (55 известных дефектов) и `vanilla_diff.baseline` (4) — задача,
которая чинит дефект, удаляет его строку; новые дефекты падают сразу.

## Последствия

Плюсы: цикл задачи — минуты (проверки ≈ 10–30 с); человек нужен только на плейтесте и ядре;
легаси-код не блокирует конвейер (храповик, scope по diff'у); состояние читается одной командой
(`run_queue.py --list`, `report.py`).

Минусы: ~25 файлов конвейера; `[human]`-гейт делает фазы 2 и 5 зависимыми от доступа к
Windows с Workshop Tools (открытый вопрос); заглушка API в `tests/` будет расти и требовать
честности — метод заглушки, который «всегда возвращает true», обесценивает тест.

## Риски и план проверки

| # | Риск | Как проверяем | Митигация |
|---|---|---|---|
| R1 | Хуки не грузятся в `-p` без trust репо | первый запуск `claude` интерактивно, принять trust | INSTALL, шаг 1 |
| R2 | luacheck/stylua не установлены на маке | `check.sh` выходит с кодом 5 и говорит, что ставить | `brew install luacheck stylua lua@5.1` |
| R3 | Плейтест недоступен (нет Windows) | decisions-needed.md | фазы 0, 1, 3, 4 почти без `[human]`; фазы 2 и 5 ждут |
| R4 | Агент «проходит» `[human]`-пункт на словах | reviewer п.6, `aoh_lint` ⇒ approval | только владелец пишет в approvals.txt |
| R5 | Заглушка не соответствует движку | тест зелёный, в игре падает | каждое расхождение → строка в docs/notes/dota-api.md и правка заглушки |

План: (1) установить комплект, trust, `run_queue.py --list`; (2) `new_feature.sh feat/p0-foundation`,
`run_queue.py --plan` — teamlead пишет 0001–0003; (3) прогнать 0002 (кодировка) и 0003
(stylua) — первый реальный цикл без `[human]`; (4) 0005–0006 — первый цикл с approval; (5) по
`report.py` поправить лимиты; Accepted.

## Как запускать

```
brew install luacheck stylua lua@5.1          # один раз; python3 ≥ 3.10 уже есть
python3 tools/vanilla_snapshot.py             # ванильный KV текущего билда (повторять после патчей)
claude                                        # один раз в репо: trust → хуки работают в -p
scripts/agents/new_feature.sh feat/p0-foundation
scripts/agents/run_queue.py --plan            # teamlead пишет задачи, очередь идёт до пустоты или блокера
scripts/agents/run_task.py 0005 [--once]      # одна задача (или один шаг)
scripts/agents/run_queue.py --list · scripts/agents/report.py
echo "0005 approved" >> tasks/approvals.txt   # после плейтеста, затем rerun
scripts/agents/finish_feature.sh feat/p0-foundation   # feat → main, руками, с плейтестом
claude --agent architect                      # ADR в репо, интерактивно
```

Настройки: `scripts/agents/config.py` (лимиты, бюджеты, APPROVAL_RE), `.claude/agents/*.md`
(модели, effort), `AOH_NOTIFY_CMD` (Telegram), `AOH_CLAUDE_ARGS` (`--model sonnet` для эксперимента),
`AOH_UNLOCK=1` — отключить хуки в своей шелл-сессии.

## Вне scope

Генератор KV (`tools/kvgen.py`, задача 0004); автоматический playtest через dedicated server
(нет API); параллельные агенты/worktrees (конфликты в одном KV-файле неизбежны — очередь
последовательна); Telegram-бот (хук есть, бот отдельно); публикация в Workshop из конвейера
(вопрос аккаунта открыт).

## Ссылки

BROzen BROwser ADR-0012 (`broplz/brozen-browser/docs/adr/0012-ai-team.md`, 28.10.2026) и его
`.claude/`, `scripts/agents/`. Claude Code: subagents, hooks, headless `-p`, `--max-budget-usd`.
luacheck 1.2.0 (lunarmodules), StyLua 2.6.0, `@moddota/dota-data` 0.47.2 (npm),
SteamDatabase/GameTracking-Dota2 (ванильный KV). Аудит карты: ADR-0002 и опубликованный отчёт
«AOH2Reborn — аудит и план модернизации» (28.10.2026).
