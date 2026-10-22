# slack-mcp

Минимальный **read-only** [MCP](https://modelcontextprotocol.io/) сервер для Slack.

Работает **от твоего аккаунта через сессию браузера** — без бота, без Slack-приложения и без одобрения админов. Авторизация автоматическая: команда `slack-readonly-login` открывает окно браузера, ты логинишься руками, а дальше web-токен и cookie `d` вытаскиваются и сохраняются сами. Агент может читать историю, треды и искать сообщения **только в явно разрешённых каналах**. Отправки, правок и удаления нет.

Стек: Python 3.10+, [httpx](https://www.python-httpx.org/), официальный MCP Python SDK.

## Зачем так

- не нужно создавать Slack App и просить админа его одобрить;
- доступ ровно такой же, как у тебя в браузере (включая `search.messages`, который боту недоступен);
- fail-closed allowlist (`SLACK_ALLOWED_CHANNELS` обязателен);
- только чтение, маленький код, который можно просмотреть целиком.

## Tools

| Tool | Описание |
|------|----------|
| `whoami` | Чей аккаунт и workspace у сессии |
| `list_allowed_channels` | Каналы из allowlist, в которых ты состоишь |
| `get_channel` | Метаданные канала (id или `#name`) |
| `get_history` | История канала (до 100, newest first, пагинация по cursor) |
| `get_thread` | Тред (родитель + ответы) по `thread_ts` |
| `search_messages` | Поиск; результаты фильтруются по allowlist |
| `get_user` | Инфо о пользователе по id |

## Требования

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- Аккаунт Slack (ты залогинишься в открывшемся браузере)

## Быстрый старт

```bash
git clone https://github.com/SHTIKOV/slack-mcp.git
cd slack-mcp
uv sync --extra dev --extra browser
uv run playwright install chromium
cp .env.example .env
```

Укажи каналы в `.env`:

```env
SLACK_ALLOWED_CHANNELS=C01234567,#general,#dev-team
```

## Авторизация (автоматическая)

```bash
uv run slack-readonly-login
```

Откроется окно браузера на `app.slack.com`. Залогинься (если ещё не залогинен) —
команда дождётся сессии, сама достанет токен и cookie `d` и сохранит их в
`~/.local/state/slack-readonly-mcp/credentials.json` (права `600`). Профиль
браузера тоже сохраняется, так что в следующий раз пароль вводить не нужно.

- Если валидная сессия уже есть — команда ничего не открывает и просто говорит
  «already authorized». Принудительно переавторизоваться: `--force`.
- Когда сессия протухнет (например, ты вышел из Slack), снова запусти
  `slack-readonly-login`.

По умолчанию берётся собственный Chromium от Playwright (системный Chromium из
snap не может писать профиль в `~/.local`). Чтобы использовать свой браузер,
задай `SLACK_CHROMIUM_PATH`.

Ручная альтернатива (если не хочешь браузер): вписать `SLACK_XOXC_TOKEN` и
`SLACK_XOXD_COOKIE` в `.env` самому — env перекрывает сохранённый файл.

Проверка и запуск:

```bash
uv run slack-readonly-whoami
uv run pytest -q
uv run slack-readonly-mcp
```

## Подключение к Claude Code

Секреты лежат в `.env` проекта, в конфиг MCP их класть не нужно:

```bash
claude mcp add slack-readonly -- uv --directory /absolute/path/to/slack-mcp run slack-readonly-mcp
```

## Подключение к Cursor

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "slack-readonly": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/slack-mcp",
        "run",
        "slack-readonly-mcp"
      ]
    }
  }
}
```

Дальше можно просить: «покажи последние сообщения в #dev-team» / «найди в #general обсуждение релиза».

## Allowlist

`SLACK_ALLOWED_CHANNELS` — обязательный список через запятую:

- id канала: `C01234567` (а также `G...`/`D...`)
- имя: `#general` или `general`

Пустое значение → сервер не стартует. Запрос к каналу вне списка → `access_denied`. Результаты поиска из неразрешённых каналов отбрасываются.

Как узнать id: добавь `#name` в allowlist и вызови `list_allowed_channels` — в ответе будет `id`.

## Безопасность

- Токен + cookie `d` = **полный доступ к твоему аккаунту**. Они лежат в `~/.local/state/slack-readonly-mcp/credentials.json` (права `600`), не коммить `.env`.
- Если выйти из Slack в этом браузере, сессия инвалидируется — достань значения заново.
- Это неофициальный способ (как у веб-клиента). Slack его не документирует; на платных тарифах админ видит сессии в access logs. Оцени, допустимо ли это по правилам твоего workspace.
- Отправка/изменение сообщений не реализованы намеренно.

## Структура

```
src/slack_readonly_mcp/
  allowlist.py     # парсинг и проверка каналов (fail-closed)
  browserlogin.py  # CLI авторизации через браузер (Playwright)
  client.py        # async-клиент Slack web API (xoxc token + d cookie)
  credentials.py   # сохранение/чтение кредов в ~/.local/state
  format.py        # сериализация сообщений/каналов/пользователей
  login.py         # CLI проверки сессии (whoami)
  server.py        # MCP tools (stdio)
  service.py       # read-only операции + allowlist-гард
tests/             # unit-тесты с моками (без сети)
```

## Лицензия

MIT.
