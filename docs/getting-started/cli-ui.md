# CLI и UI

Платформа предоставляет два интерфейса управления: терминальный (`ops`, `platform`) и веб (NiceGUI).

## Ops CLI

Простой bash-враппер, устанавливается через `./install.sh`.

| Команда | Описание |
|---|---|
| `ops list` | Все сервисы со статусом |
| `ops up <svc>` | Запустить (`docker compose up -d`) |
| `ops down <svc>` | Остановить |
| `ops logs <svc>` | Логи в реальном времени |
| `ops logs <svc> -f` | Follow mode |
| `ops ui` | lazydocker для всех сервисов |
| `ops ui <svc>` | lazydocker для одного |
| `ops reload` | Перезагрузить Caddy config |

Сокращение: `ops master` = `ops up master`.

## Platform CLI

Полноценный Python CLI (Typer). Устанавливается через `pipx`:

```bash
cd _core/platform-cli && ./install.sh
```

| Команда | Описание |
|---|---|
| `platform list` | Сервисы со статусом (Rich-таблица) |
| `platform new <name> [public\|internal]` | Создать сервис из шаблона |
| `platform deploy <svc> [--build] [--pull]` | Деплой |
| `platform stop <svc>` | Остановка |
| `platform restart <svc>` | Перезапуск |
| `platform logs <svc> [-f] [-n N]` | Логи |
| `platform status [<svc>]` | Статус + метрики Docker |
| `platform backup <svc>` | Запустить бэкап |
| `platform reload` | Перезагрузить Caddy |
| `platform info` | Общая информация о платформе |

## Веб-интерфейс (NiceGUI)

Master Service запускает UI на порту **8001** (маппинг `8001:8000`):

```
http://localhost:8001
```

### Страницы

| Страница | Что показывает |
|---|---|
| **Главная** | Сводка: кол-во сервисов, статус, типы |
| **Сервисы** | Таблица с кнопками deploy/stop/restart |
| **Логи** | Фильтрация по сервису, времени, поиск |
| **Бэкапы** | История бэкапов, restore |
| **Пользователи** | Управление (при builtin auth) |

### Аутентификация

| Режим | Как войти |
|---|---|
| **Builtin** | Логин/пароль из SQLite (создаётся в UI) |
| **Keycloak** | OAuth2 redirect на Keycloak realm |

## API

FastAPI API доступно на `http://localhost:8000`:

- **Swagger UI** → `/docs`
- **ReDoc** → `/redoc`
- **Базовый путь API** → `/api/`

См. [API Reference](../api.md) для подробностей.
