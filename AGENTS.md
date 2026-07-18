# AGENTS.md — правила для навыков

Этот репозиторий содержит Codex/agent skills. При создании или рефакторинге навыка делай его маленьким, переносимым и удобным для агента: `SKILL.md` должен быстро отвечать на главные вопросы, а детали раскрываются через `references/` только когда они нужны.

## Главный принцип

- `SKILL.md` — короткая карточка и маршрутизатор: что это, как запустить, главные правила, decision tree, куда читать дальше.
- `references/` — подробности: runtime, auth, безопасность, API-поля, workflows, примеры, edge cases.
- `scripts/` — вся детерминированная логика. Не заставляй агента вручную собирать HTTP-запросы, парсить сложные форматы или помнить скрытые правила.
- Не дублируй одно и то же в `SKILL.md` и `references/`: если блок редко нужен, вынеси его в отдельный файл.

Хорошие текущие ориентиры: `confluence/SKILL.md` и `jira/SKILL.md`.

## Структура навыка

Минимальная структура для CLI-backed навыка:

```text
<skill>/
  SKILL.md
  scripts/
    run.py
    cli.py          # или другой CLI entrypoint
  references/
    runtime.md      # запуск, env vars, output, exit codes
    safety.md       # мутации, dry-run, downloads, secrets
    workflows.md    # или workflows-and-examples.md, если имя workflows/ уже занято
    api.md          # поля, фильтры, ресурсные особенности, если нужно
  evals/
    evals.json      # обязательные атомарные evals по всем доступным командам CLI
```

Не создавай все файлы механически. Добавляй только те reference-файлы, которые реально уменьшают `SKILL.md` или фиксируют важные правила.

## Frontmatter `SKILL.md`

Frontmatter — самый дорогой и частый routing-сигнал, поэтому он должен быть коротким.

Рекомендуемый шаблон:

```yaml
---
name: <skill-name>
description: >-
  Use when the user wants to perform operations in <system/domain>.
version: 1.0.0
schema_command: uv run --script scripts/run.py schema get --json
launcher:
  cwd: skill-root
  command: uv run --script scripts/run.py
auth:
  type: api_key | bearer | none
  precedence: [keyring, environment]
  docs: references/runtime.md
settings:
  manifest: config/settings.json
  precedence: [environment, default]
capabilities:
  - resource action group
  - search command for bounded queries
  - auth check and schema introspection
metadata:
  tags: general, vendor, domain
  readonly: "true"
allowed-tools: >-
  Read, Bash(uv run --script scripts/run.py *)
---
```

Требования:

- `name` совпадает с папкой навыка.
- `description` короткий: WHAT + WHEN, без длинного списка всех команд.
- `schema_command` указывает на машинно-читаемую схему (`schema get --json` для новых/refactored навыков; legacy `describe --json` оставляй только если так реализован CLI).
- `launcher.cwd: skill-root` и `launcher.command` обязательны для переносимого запуска.
- `capabilities` — 3–8 коротких строк из реального CLI contract, не маркетинг и не инструкции безопасности.
- `allowed-tools` должен ограничивать Bash конкретным launcher-командным префиксом.
- Для навыка с декларативным `config/settings.json` добавляй `settings.manifest` и реальный precedence. Credential precedence указывай в `auth`, например `precedence: [keyring, environment]`; не дублируй полный список настроек во frontmatter.

## Как писать `capabilities`

`capabilities` должны помогать UI/агенту понять поверхность навыка. Пиши их по командам и ресурсам, а не по внутренней реализации.

Хорошо:

```yaml
capabilities:
  - search command for bounded JQL issue search
  - issue get/history/transition plus comments, attachments, links, pull requests, labels, and field aliases
  - issue create/update/move/clone/assign/comment/link/label mutations
  - project discovery, project field metadata, workflow planning, auth check, and schema introspection
```

Плохо:

```yaml
capabilities:
  - confirmed mutations with dry-run and user approval
  - helpers
  - calls REST API
  - many commands
```

Правила:

- Если `search` — отдельная top-level команда, укажи ее отдельной capability.
- Если под `issue` есть важные subcommands (`history`, `transition`, `comment`, `attachment`), перечисли их в строке `issue ...`.
- Не пиши в capabilities про confirmation/dry-run — это safety behavior, а не capability.
- Не перечисляй каждую мелкую опцию; для флагов есть schema/help.

## Body `SKILL.md`

Body должен быть лаконичным. Ориентир — 50–100 строк, если навык не требует особого routing.

Обязательные блоки:

1. Заголовок и одна строка назначения.
2. Launcher:
   ```bash
   cd <skill>
   uv run --script scripts/run.py schema get --json
   uv run --script scripts/run.py <resource> [subresource] <action> --help
   ```
3. `Required behavior`: 5–8 важных правил, которые нельзя пропустить.
4. `Decision tree`: какую команду запускать по типу пользовательского запроса.
5. `Read when needed`: ссылки на reference-файлы.

Не держи в `SKILL.md`:

- большие таблицы env vars;
- длинные списки команд;
- десятки copy-paste examples;
- подробные exit codes/output contract;
- полный список field aliases;
- редкие edge cases;
- длинные объяснения форматов вроде Jira wiki или Confluence storage.

Все это должно жить в `references/`.

## Формат CLI-команд

Для новых и refactored CLI-backed навыков предпочитай noun-first дерево команд:

```bash
uv run --script scripts/run.py <resource> [subresource] <action> [args...] --json
```

Правило: сначала существительное/ресурс, потом глагол/действие. Это делает CLI иерархически исследуемым: агент сперва узнает ресурсы (`issue`, `page`, `project`), потом доступные действия (`get`, `list`, `update`, `delete`). Если естественного ресурса нет или команда глобальная, допустим top-level глагол/служебная команда (`search`, `auth check`, `schema get`).

Примеры:

```bash
uv run --script scripts/run.py schema get --json
uv run --script scripts/run.py auth check --json
uv run --script scripts/run.py page search 'text' --limit 10 --json
uv run --script scripts/run.py issue get RBS2-123 --json
uv run --script scripts/run.py issue comment list RBS2-123 --limit 20 --json
```

Требования к CLI:

- Основная грамматика: `resource action`, не `action-resource` и не `action resource`, если можно выразить через ресурс.
- Для вложенных ресурсов используй `resource subresource action`: `issue comment list`, `page attachment download`.
- Top-level глагол допустим только для глобальных операций без явного ресурса: `search`, `schema get`, `auth check`.
- Используй стабильный словарь действий: `get`, `list`, `search`, `create`, `update`, `delete`, `archive`, `restore`, `trigger`, `cancel`, `download`, `upload`, `convert`, `plan`, `check`.
- Не вводи синонимы для одного действия внутри навыка: если выбран `delete`, не смешивай с `remove`; если выбран `list`, не смешивай с `ls`.
- Всегда должна быть schema/introspection команда: `schema get --json` или legacy `describe --json`.
- Для неизвестных флагов агент должен использовать `schema get --json` или `<resource> [subresource] <action> --help`.
- Human-readable help должен давать агенту контекст текущего времени: в top-level, resource и leaf `--help` выводи строку вида `Current time (<IANA timezone>): <ISO-8601> · Unix: <timestamp>`. Используй timezone навыка по умолчанию; вычисляй значение при каждом вызове. Не добавляй динамическое время в `schema get --json`, другие JSON-ответы или рабочий stdout команд. Для тестов инъецируй clock/`now`, а не сравнивай реальное время.
- В non-interactive агентском контексте используй `--json`.
- JSON success идет в stdout; structured errors — в stderr.
- Не смешивай stderr в stdout перед JSON parsing (`2>&1` ломает парсинг).
- Reads должны быть bounded: `--limit`, `--start`, `--fields`, depth/section filters или аналог.
- Mutations должны иметь `--dry-run --json` и `--yes`, если система что-то меняет.

### Exit codes и диагностика ошибок

Используй единые семантические коды выхода из [Agent Surface](https://agentsurface.dev/docs/cli-design/command-structure#exit-codes-with-semantics):

| Code | Значение | Когда использовать |
| --- | --- | --- |
| `0` | Success | Команда завершилась ожидаемо |
| `1` | Failure | Ошибка API, сети, провайдера или внутренняя ошибка |
| `2` | Usage error | Неизвестная команда/опция, пропущенный обязательный аргумент или некорректный ввод |
| `3` | Not found | Запрошенный ресурс не существует |
| `4` | Permission denied | Не хватает прав или не прошла аутентификация |
| `5` | Conflict | Ресурс уже существует или его текущее состояние не допускает операцию |

Код выхода сообщает категорию, но не заменяет описание ошибки:

- При любом ненулевом коде обязательно пиши в stderr краткую и конкретную причину. Сценарий `no output` + ненулевой код недопустим.
- Для usage error называй, что именно неверно: неизвестная команда/опция, имя проблемного флага или аргумента и, когда возможно, ближайший допустимый вариант либо команду `--help`.
- Не проглатывай стандартную диагностику парсера. Launcher и wrappers должны сохранять stderr и исходный exit code.
- В `--json`-режиме возвращай structured error в stderr, например: `{"success":false,"error":{"code":"usage","message":"unrecognized argument: --max-rows","retriable":false,"hint":"Use --limit or run 'log search --help'."}}`.
- Без `--json` выводи в stderr короткое сообщение вида `Usage error: unrecognized argument: --max-rows`, затем при необходимости usage/hint.
- Агент при вызове skill CLI не должен подавлять stderr через `2>/dev/null`: это скрывает причину ошибки и лишает его возможности исправить команду.
- Проверь как минимум negative smoke tests для неизвестной команды и неизвестного флага: оба должны завершаться с code `2` и содержательной диагностикой в stderr.

## Safety и мутации

В `SKILL.md` оставляй только короткое обязательное правило. Подробности — в `references/safety.md`.

Стандартный flow:

1. Запусти мутацию с `--dry-run --json`.
2. Покажи пользователю `target` / `target.path` и важные `changes[]`.
3. Выполни с `--yes --json` только после явного подтверждения.
4. Если есть `*_AUTO_CONFIRM=1`, опиши его только как trusted automation режим.

Запрещено:

- использовать `curl`, `wget`, `httpie` или прямой HTTP, если у навыка есть CLI;
- сохранять токены в папку навыка;
- писать скачанные файлы в неожиданные директории;
- расширять scope мутаций без явного пользовательского запроса.

## Настройки и системное хранилище секретов

При создании или рефакторинге локального CLI-backed навыка, которому нужны настройки или credentials, описывай их в едином версионируемом `config/settings.json`. Для Python-секретов используй `keyring`: macOS Keychain, Windows Credential Locker и совместимый Secret Service/KWallet на Linux. Environment variables оставляй fallback для credentials в CI/headless-средах и override для несекретных настроек.

Не помещай в keyring обычные настройки (`host`, `port`, timeout, output path), если они не являются credentials. Их безопасные defaults храни в `settings.json`, а пользовательские переопределения принимай через environment. Не создавай `settings.local.json` и не записывай пользовательские значения обратно в папку навыка.

### Единый settings manifest

- `config/settings.json` содержит декларацию всех пользовательских runtime-настроек навыка: имена, типы, обязательность, безопасные defaults, описание, источник получения и инструкции.
- Это версионируемый manifest, а не пользовательский config: в нем допустимы общие несекретные defaults, но запрещены локальные override и любые secret values.
- Для каждой настройки сохраняй точное существующее имя environment variable в `name`, чтобы бизнес-код и CI продолжали использовать один contract.
- Для каждого значения обязательно добавляй `description` и `help.source`; в `help.instructions` укажи, где получить значение, как применить его и какой environment variable переопределяет default.
- `help.url` добавляй только при наличии стабильной безопасной страницы получения токена/настройки. Не зашивай нестабильные внутренние URL без необходимости.
- Credential-запись помечай `credential: true`; только такие записи образуют allowlist для keyring setup/status/delete.
- Credential-записи не должны иметь `default`. Их значения существуют только в OS keyring или environment.
- Обычные настройки помечай `credential: false`; они не должны иметь `secret`, `account` или `prompt`.
- Используй один стабильный service в dotted-формате, например `<organization>.<product>.<system>`.
- В качестве account используй точное имя credential-переменной: `OPENSEARCH_USERNAME`, `OPENSEARCH_PASSWORD`, `JIRA_API_TOKEN`.

Порядок разрешения должен быть раздельным:

```text
non-secret setting: environment -> default from settings.json -> missing
credential:         keyring -> environment -> missing
```

Environment переопределяет только несекретный default. Для credentials keyring имеет приоритет; чтобы вернуться к env fallback, пользователь удаляет keyring entry через `auth delete`. Не копируй credential values в `os.environ`.

Пример:

```json
{
  "version": 1,
  "skill": "system-search",
  "keyring_service": "organization.product.system",
  "settings": [
    {
      "name": "SYSTEM_HOST",
      "type": "string",
      "required": true,
      "credential": false,
      "default": "system.dev.example.com",
      "description": "System API endpoint.",
      "help": {
        "source": "The default endpoint is shipped with the skill; request alternatives from the platform administrator.",
        "instructions": [
          "Keep the default for normal development use.",
          "Override it with the SYSTEM_HOST environment variable."
        ]
      }
    },
    {
      "name": "SYSTEM_USERNAME",
      "type": "string",
      "required": true,
      "credential": true,
      "secret": false,
      "account": "SYSTEM_USERNAME",
      "prompt": "System username",
      "description": "Username for the read-only API account.",
      "help": {
        "source": "Request a read-only account from the platform administrator.",
        "instructions": [
          "Use auth setup for local keyring storage.",
          "Use SYSTEM_USERNAME only as the CI/headless environment fallback."
        ]
      }
    },
    {
      "name": "SYSTEM_PASSWORD",
      "type": "string",
      "required": true,
      "credential": true,
      "secret": true,
      "account": "SYSTEM_PASSWORD",
      "prompt": "System password",
      "description": "Password for the read-only API account.",
      "help": {
        "source": "Obtain it through the approved secret-delivery process from the account owner.",
        "instructions": [
          "Use auth setup so terminal input is hidden and the value is stored in the OS keyring.",
          "Never put the value in chat, argv, settings.json, or repository files."
        ]
      }
    }
  ]
}
```

В этом примере `SYSTEM_HOST` имеет общий default и env override. `SYSTEM_USERNAME` и `SYSTEM_PASSWORD` входят в keyring allowlist, но их значения отсутствуют в manifest.

### Минимальный пример реализации

Это ориентир, а не готовый модуль: в реальном навыке добавь строгую валидацию manifest/types, structured errors, doctor, auth status/setup/delete, TTY-проверку и rollback.

```python
import json
import os
from pathlib import Path

import keyring
from keyring.errors import KeyringError


def load_settings_config() -> dict:
    path = Path(__file__).resolve().parents[1] / "config" / "settings.json"
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_runtime_settings(config: dict) -> tuple[dict[str, object], dict[str, str]]:
    values: dict[str, object] = {}
    sources: dict[str, str] = {}

    for item in config["settings"]:
        if item["credential"]:
            continue
        if os.environ.get(item["name"]):
            values[item["name"]] = os.environ[item["name"]]
            sources[item["name"]] = "environment"
        elif "default" in item:
            values[item["name"]] = item["default"]
            sources[item["name"]] = "default"
        elif item["required"]:
            sources[item["name"]] = "missing"

    return values, sources


def resolve_credentials() -> tuple[dict[str, str], dict[str, str]]:
    config = load_settings_config()
    values: dict[str, str] = {}
    sources: dict[str, str] = {}
    missing: list[str] = []

    for item in config["settings"]:
        if not item["credential"]:
            continue
        try:
            value = keyring.get_password(config["keyring_service"], item["account"])
        except KeyringError:
            value = None  # Environment remains the safe compatibility fallback.

        if value:
            source = "keyring"
        elif os.environ.get(item["name"]):
            value = os.environ[item["name"]]
            source = "environment"
        else:
            missing.append(item["name"])
            continue

        values[item["name"]] = value
        sources[item["name"]] = source

    if missing:
        raise RuntimeError("Missing credentials: " + ", ".join(missing))

    return values, sources
```

Существующий бизнес-код можно сохранить: loader возвращает значения по тем же именам `SYSTEM_HOST`, `SYSTEM_PORT` и т. п. Если старый код читает только `os.environ`, launcher может применить исключительно несекретные defaults через `os.environ.setdefault(name, value)`. Credentials передавай явно и никогда не копируй в environment.

Для setup сначала отфильтруй `credential: true`, собери env/prompt values в памяти и выполни bounded auth probe. Только после успешной проверки вызывай `keyring.set_password(keyring_service, account, value)`. Не записывай credential values в environment, stdout, logs или config-файлы.

Для PEP 723 launcher добавь ограниченную major-версию зависимости:

```python
# dependencies = [
#   "keyring>=25,<26",
# ]
```

Не подключай `keyrings.alt` и другие plaintext/file backends как автоматический fallback. Если безопасный OS backend недоступен, верни понятную диагностику и используй environment только при наличии полного набора fallback-переменных.

### Atomic doctor

Для навыка с settings manifest добавляй явную атомарную команду готовности:

```bash
uv run --script scripts/run.py doctor --json
```

`doctor`:

- запускается только явно и никогда автоматически перед реальной командой;
- ничего не записывает, не удаляет и не запрашивает интерактивный ввод;
- валидирует `config/settings.json`, типы/defaults, доступность keyring backend и effective sources;
- показывает для каждой настройки только `configured` и источник `default|environment|keyring|missing`, не значения;
- при missing добавляет безопасные `description`, `help.source`, `help.instructions` и при наличии `help.url` из manifest;
- выполняет один bounded provider/auth probe только после успешного resolution;
- использует semantic exit codes: `2` для incomplete/invalid config, `4` для rejected credentials, `1` для provider/network failure.

Не превращай `doctor` в обязательный preflight: рабочая команда сама должна вернуть конкретную structured error и при необходимости подсказать запустить `doctor`.

### Обязательный CLI lifecycle

Добавь безопасные команды в auth-ресурс и отрази их в schema/help:

```bash
uv run --script scripts/run.py auth status --json
uv run --script scripts/run.py auth setup --dry-run --json
uv run --script scripts/run.py auth setup --yes --json
uv run --script scripts/run.py auth check --json
uv run --script scripts/run.py auth delete --dry-run --json
uv run --script scripts/run.py auth delete --yes --json
```

Если credential variables уже заданы в environment, но пользователь хочет не импортировать их, а ввести новые значения вручную, исключи эти переменные только из environment процесса setup:

```bash
env -u SYSTEM_USERNAME -u SYSTEM_PASSWORD \
  uv run --script scripts/run.py auth setup --yes --json
```

Используй точные имена credential-записей из `settings.json`. `env -u` не меняет текущую shell-сессию: setup не увидит указанные переменные и запросит их через интерактивный TTY; остальные настройки, например `SYSTEM_HOST`, останутся доступными для validation probe. Не используй `unset` без необходимости и не передавай значения секретов прямо в командной строке.

- `auth status` показывает backend, service/account, `configured` и источник `keyring|environment|missing`, но никогда не значения username/password/token.
- `auth setup --dry-run` показывает target, источник ввода и факт перезаписи без prompt, connection и записи.
- `auth setup --yes` может импортировать уже заданные env credentials; отсутствующие значения запрашивает только через интерактивный TTY. Пароль/token вводится через `getpass`.
- Не принимай секрет через CLI-флаг, argv, stdin pipe или JSON payload: это оставляет его в shell history, process list или логах.
- Перед записью проверь credentials безопасным bounded auth probe. При ошибке аутентификации ничего не сохраняй.
- Multi-entry setup/delete реализуй с best-effort rollback, чтобы ошибка второй keyring-операции не оставляла частично измененное состояние.
- `auth delete` удаляет только accounts из config; после удаления снова действует environment fallback.
- OS/agent sandbox может запрещать доступ к Keychain/Credential Locker. Покажи это в `auth status` и попроси user-approved запуск с credential-store access; не ослабляй backend.

В `SKILL.md` оставь короткое first-run правило: `auth status -> setup dry-run -> явное подтверждение -> setup --yes -> auth check`. Подробности, ограничения backend и команды вынеси в `references/runtime.md` и `references/safety.md`.

### Проверка keyring-интеграции

- Unit-тесты используют fake keyring backend и никогда не меняют реальное системное хранилище.
- Проверь: keyring precedence, per-variable env fallback, missing/backend errors без утечки значений, redacted status, no-op dry-run, validation-before-write, обязательный `--yes`, rollback при частичной записи/удалении.
- Проверь settings resolution: environment перекрывает non-secret default, credentials не имеют defaults, типы валидируются, status/doctor не возвращают values, missing guidance берётся из manifest.
- Проверь `doctor`: атомарность, отсутствие мутаций/prompts, default/environment/keyring sources, skip probe при incomplete config и semantic exit codes.
- Добавь атомарные evals для новых `auth` commands. Live setup/delete выполняй только после отдельного подтверждения пользователя.

## Reference-файлы

Типовое разделение:

- `references/runtime.md` — launcher, fallback, env vars, missing secrets, output contract, exit codes, JSON piping.
- `references/safety.md` — confirmation, dry-run, downloads/uploads, secrets, guardrails, destructive actions.
- `references/workflows.md` или `references/workflows-and-examples.md` — практические команды и сценарии.
- `references/api.md` — field aliases, query conventions, resource semantics, rich text, API-specific notes.
- `references/authentication.md` — если auth достаточно большой и его лучше отделить от runtime.

Reference-файл должен иметь понятный заголовок, короткие секции и copy-paste команды только для реально частых workflow.

## Evals

Для каждого нового или refactored CLI-backed навыка создавай `evals/evals.json`. Хороший ориентир по формату и уровню покрытия — `confluence/evals/evals.json`.

Требования:

- В `evals/evals.json` должны быть перечислены evals для всех доступных команд из CLI contract/schema, включая `schema get` / legacy `describe --json` и `auth check`, если команда есть.
- Каждый eval должен быть атомарным: проверяет одну команду или один короткий lifecycle, который нужен только для безопасной проверки команды.
- Prompt должен быть человеческим вопросом/запросом, без готового ответа и без подсказки ожидаемого результата. Технические ожидания (`какую команду запустить`, `какие поля проверить`) держи в `expected_output`.
- Для read/list/search команд задавай bounded сценарии (`--limit`, `--fields`, фильтры, конкретный id/namespace), чтобы eval не требовал unbounded чтения.
- Если eval проверяет мутацию, он должен сам создать тестовый объект и затем удалить/откатить его. Если безопасный rollback невозможен, такой eval не добавляй.
- Если для мутации нужно подтверждение и в навыке есть системный auto-confirm флаг (`*_AUTO_CONFIRM=1` или аналог), prompt должен явно просить использовать этот флаг, чтобы модель задала его в команде и не ждала подтверждения пользователя.
- Мутирующие evals должны использовать уникальные тестовые имена/пути с префиксом `eval-...`, не трогать пользовательские данные и не расширять scope за пределы явно указанного тестового объекта.
- Если навык поддерживает GUARDRAILS/анонимизацию, добавь evals, которые создают или читают тестовые данные с PII и проверяют, что ответ маскирован и не содержит персональных данных. Такие evals тоже должны cleanup-ить созданные объекты.
- Не добавляй evals, которые требуют внешнего состояния без стабильного тестового объекта, ручного подтверждения, необратимой операции или доступа к секретам сверх обычной auth-конфигурации навыка.

## Документация и стиль

- Пиши кратко и конкретно. Убирай вступления, которые не меняют поведение агента.
- Команды и пути должны быть переносимыми: `cd jira`, `cd confluence`, без абсолютных локальных путей.
- Не используй внутренний брендинг или локальные детали, если они не нужны пользователю/агенту.
- Для user-facing ошибок формулировки короткие; raw provider details оставляй в stderr/logs.
- Если правило применимо только к одному навыку, держи его в reference этого навыка, а не в общем `AGENTS.md`.

## Проверка перед завершением

Минимум:

```bash
uv run --script <skill>/scripts/run.py schema get --json
```

Если команда называется иначе, используй значение из `schema_command`.

Дополнительно по ситуации:

- `<command> --help` для измененных команд;
- `python3 -m py_compile` для измененных Python CLI файлов;
- `python3 -m json.tool` для измененных JSON файлов;
- `python3 -m json.tool <skill>/evals/evals.json`, если создавали или меняли evals;
- grep по subtree, если чистили брендинг, язык, абсолютные пути или старые команды.

## Антипаттерны

- Большой `SKILL.md`, который пытается заменить всю документацию.
- Дубли env/output/safety/API details в нескольких файлах.
- `capabilities` как рекламный текст или как список safety-инструкций.
- Команды без schema introspection.
- Небезопасные прямые HTTP-вызовы в обход CLI.
- Unbounded search/list по умолчанию.
- Мутации без dry-run/confirmation boundary.

<!-- br-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_rust](https://github.com/Dicklesworthstone/beads_rust) (`br`/`bd`) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View ready issues (open, unblocked, not deferred)
br ready              # or: bd ready

# List and search
br list --status=open # All open issues
br show <id>          # Full issue details with dependencies
br search "keyword"   # Full-text search

# Create and update
br create --title="..." --description="..." --type=task --priority=2
br update <id> --status=in_progress
br close <id> --reason="Completed"
br close <id1> <id2>  # Close multiple issues at once

# Sync with git
br sync --flush-only  # Export DB to JSONL
br sync --status      # Check sync status
```

### Workflow Pattern

1. **Start**: Run `br ready` to find actionable work
2. **Claim**: Use `br update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `br close <id>`
5. **Sync**: Always run `br sync --flush-only` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `br ready` shows only open, unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers 0-4, not words)
- **Types**: task, bug, feature, epic, chore, docs, question
- **Blocking**: `br dep add <issue> <depends-on>` to add dependencies

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
br sync --flush-only    # Export beads changes to JSONL
git commit -m "..."     # Commit everything
git push                # Push to remote
```

### Best Practices

- Check `br ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `br create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always sync before ending session

<!-- end-br-agent-instructions -->

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

<!-- bv-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View issues (launches TUI - avoid in automated sessions)
bv

# CLI commands for agents (use these instead)
bd ready              # Show issues ready to work (no blockers)
bd list --status=open # All open issues
bd show <id>          # Full issue details with dependencies
bd create --title="..." --type=task --priority=2
bd update <id> --status=in_progress
bd close <id> --reason="Completed"
bd close <id1> <id2>  # Close multiple issues at once
bd sync               # Commit and push changes
```

### Workflow Pattern

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `bd close <id>`
5. **Sync**: Always run `bd sync` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)
- **Types**: task, bug, feature, epic, question, docs
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
bd sync                 # Commit beads changes
git commit -m "..."     # Commit code
bd sync                 # Commit any new beads changes
git push                # Push to remote
```

### Best Practices

- Check `bd ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `bd create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always `bd sync` before ending session

<!-- end-bv-agent-instructions -->
