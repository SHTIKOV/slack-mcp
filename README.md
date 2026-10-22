# slack-mcp

Минимальный **read-only** [MCP](https://modelcontextprotocol.io/) сервер для Slack.

Работает **от твоего аккаунта через сессию браузера** — без бота, без Slack-приложения и без одобрения админов. Переиспользуются те же данные, которыми пользуется веб-клиент Slack: web-токен (из localStorage) и cookie `d`. Агент может читать историю, треды и искать сообщения **только в явно разрешённых каналах**. Отправки, правок и удаления нет.

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
- Аккаунт Slack, залогиненный в браузере, состоящий в нужных каналах

## Быстрый старт

```bash
git clone https://github.com/SHTIKOV/slack-mcp.git
cd slack-mcp
uv sync --extra dev
cp .env.example .env
```

## Как достать токен и cookie

Один раз, в браузере, где ты залогинен в Slack (вкладка `app.slack.com`):

1. **Токен.** DevTools → Console:
   ```js
   JSON.parse(localStorage.localConfig_v2).teams
   ```
   Найди свою команду и скопируй её поле `token` (начинается на `x`-`o`-`x`-`c`).
2. **Cookie.** DevTools → Application → Cookies → `https://app.slack.com` → cookie с именем `d` (значение начинается на `x`-`o`-`x`-`d`). Копируй **как есть** (URL-encoded).

Впиши оба значения и список каналов в `.env`:

```env
SLACK_XOXC_TOKEN=...
SLACK_XOXD_COOKIE=...
SLACK_ALLOWED_CHANNELS=C01234567,#general,#dev-team
```

Проверь, что сессия жива:

```bash
uv run slack-readonly-whoami
```

Тесты и запуск:

```bash
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

- Токен + cookie `d` = **полный доступ к твоему аккаунту**. Храни их как пароль, не коммить `.env`.
- Если выйти из Slack в этом браузере, сессия инвалидируется — достань значения заново.
- Это неофициальный способ (как у веб-клиента). Slack его не документирует; на платных тарифах админ видит сессии в access logs. Оцени, допустимо ли это по правилам твоего workspace.
- Отправка/изменение сообщений не реализованы намеренно.

## Структура

```
src/slack_readonly_mcp/
  allowlist.py   # парсинг и проверка каналов (fail-closed)
  client.py      # async-клиент Slack web API (xoxc token + d cookie)
  format.py      # сериализация сообщений/каналов/пользователей
  login.py       # CLI проверки сессии (whoami)
  server.py      # MCP tools (stdio)
  service.py     # read-only операции + allowlist-гард
tests/           # unit-тесты с моками (без сети)
```

## Лицензия

MIT.
