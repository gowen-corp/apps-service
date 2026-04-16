# AI Context: apps-service-opus

## 1. Архитектура и стек

### Компоненты

- **Master Service** (`_core/master/`): FastAPI + NiceGUI, Python 3.11-3.13
- **Caddy Proxy** (`_core/caddy/`): Reverse proxy с on-demand TLS, Admin API на :2019
- **Docker**: Управление контейнерами через aiodocker/docker SDK
- **Service Discovery**: Сканирование `services/{public,internal}/`

### Порты

| Сервис      | Порт | Назначение                     |
| ----------- | ---- | ------------------------------ |
| Master API  | 8000 | REST API                       |
| Master UI   | 8001 | NiceGUI интерфейс              |
| Caddy HTTP  | 80   | Входящий трафик                |
| Caddy HTTPS | 443  | TLS трафик                     |
| Caddy Admin | 2019 | Caddy API (внутри сети)        |
| Keycloak    | 8080 | Аутентификация (если включена) |

### Flow деплоя

```
1. ServiceDiscovery.scan_all() → читает service.yml + docker-compose.yml
2. CaddyManager.regenerate_all() → Jinja2 шаблоны → conf.d/*.caddy
3. CaddyManager.reload_caddy() → POST :2019/load или SIGUSR1
4. DockerManager.deploy_service() → docker compose up -d
```

## 2. Конвенции и правила

### Структура сервисов

```
services/
├── public/           # Доступны извне (домены/поддомены)
└── internal/         # Только внутри Docker сети
    └── {service}/
        ├── service.yml          # Манифест (обязателен)
        ├── docker-compose.yml   # Контейнеры
        └── service.local.yml    # Локальные override (gitignored)
```

### service.yml схема

```yaml
name: string # Уникальное имя (slug)
display_name: string # Человекочитаемое
version: string
type: docker-compose # docker-compose | docker | static
visibility: public # public | internal
routing: # Список маршрутов
  - type: domain # domain | subfolder | port | auto_subdomain
    domain: example.com # Для type=domain
    base_domain: apps.urfu.online # Для auto_subdomain/subfolder
    path: /service # Для type=subfolder
    port: 8080 # Для type=port
    internal_port: 8000 # Порт контейнера
    container_name: string # Имя контейнера для проксирования
    auto_subdomain: bool # {name}.base_domain
    auto_subdomain_base: apps.urfu.online
health:
  enabled: true
  endpoint: /health # Путь проверки
  interval: 30s
  timeout: 10s
  retries: 3
backup:
  enabled: false
  schedule: "0 2 * * *" # cron-формат
  retention: 7 # Дней хранения
  paths: [] # Пути для бэкапа
  databases: [] # Конфиг БД
tags: []
```

### Именование

- Сервисы: kebab-case (`my-service-name`)
- БД контейнеры: `{service_name}_{db_name}_1`
- Caddy конфиги: `{service_name}.caddy` или `_subfolder_{base_domain}.caddy`
- Бэкапы: `{service_name}_{YYYYMMDD}_{HHMMSS}/`

### Запреты

- НЕ коммитить `service.local.yml` — только в .gitignore
- НЕ редактировать файлы в `conf.d/` руками (генерируются)
- НЕ использовать `..` в путях бэкапа (path traversal check)
- НЕ запускать Docker напрямую — использовать DockerManager

## 3. Карта критических файлов

| Зона                | Ключевые файлы                                | Назначение                                          |
| ------------------- | --------------------------------------------- | --------------------------------------------------- |
| **Config**          | `_core/master/app/config.py`                  | Pydantic-settings, переменные окружения             |
| **Entry**           | `_core/master/app/main.py`                    | FastAPI lifespan, фоновые задачи, UI pages          |
| **Discovery**       | `_core/master/app/services/discovery.py`      | Сканирование сервисов, watchdog, мёрж конфигов      |
| **Caddy**           | `_core/master/app/services/caddy_manager.py`  | Генерация конфигов из Jinja2, Caddy API reload      |
| **Docker**          | `_core/master/app/services/docker_manager.py` | Docker compose управление, stats, logs              |
| **Health**          | `_core/master/app/services/health_checker.py` | HTTP health checks каждые 30 сек                    |
| **Backup**          | `_core/master/app/services/backup_manager.py` | rsync, pg_dump, croniter scheduling, Restic         |
| **Notifier**        | `_core/master/app/services/notifier.py`       | Telegram бот                                        |
| **TLS API**         | `_core/master/app/api/routes/tls.py`          | On-demand TLS валидация                             |
| **API Routes**      | `_core/master/app/api/routes/*.py`            | services, deployments, logs, backups, health, users |
| **UI Pages**        | `_core/master/app/ui/*_page.py`               | NiceGUI страницы: main, services, logs, backups     |
| **Models**          | `_core/master/app/models/*.py`                | SQLAlchemy: service, deployment, backup, user       |
| **Conftest**        | `_core/master/tests/conftest.py`              | Pytest fixtures: моки Docker, discovery             |
| **Pytest**          | `_core/master/pytest.ini`                     | `--asyncio-mode=auto`, coverage                     |
| **Full Cycle Test** | `infra/test-env/test_full_cycle.sh`           | DinD интеграционные тесты                           |
| **Caddyfile**       | `_core/caddy/Caddyfile`                       | On-demand TLS, Admin API, импорты                   |
| **Templates**       | `_core/caddy/templates/*.caddy.j2`            | Jinja2: domain, subfolder, port, auto_subdomain     |
| **Ops Config**      | `.ops-config.yml`                             | Корневые пути, docker_host                          |

## 4. Ограничения и подводные камни

### Pytest

- `--asyncio-mode=auto` обязателен — без него async fixtures не работают
- Coverage репорт в `htmlcov/index.html`
- Тесты трёх уровней: unit → integration → full-deploy-cycle (DinD)

### Caddy

- On-demand TLS требует валидацию через `/api/tls/validate`
- Admin API на `0.0.0.0:2019` — без auth внутри Docker сети
- Config reload через POST `/load` или SIGUSR1 fallback
- `conf.d/development.caddy` импортируется только в `APP_ENV=dev`

### Health Checks

- Запускаются каждые 30 секунд из `health_check_loop()`
- Требуют `endpoint` в service.yml — иначе сервис всегда "healthy"
- Нет таймаута на уровне цикла — только в `aiohttp.ClientTimeout`

### Backup

- **Restic загрузка не работает** — скрипты есть, логика вызова в backup_manager.py, но окружение не настроено
- Работает: rsync, pg_dump, mysqldump, локальное хранение
- Retention очистка по `metadata.json` timestamp

### Service Discovery

- Использ watchdog.observers.Observer — возможны утечки при рестартах
- `_deep_merge()` рекурсивный — списки заменяются целиком
- Local override применяется после основного манифеста

### Docker

- DockerManager использует `docker.from_env()` — требует /var/run/docker.sock
- Контейнеры ищутся по label `platform.service={name}`
- `container_name` в routing для прямого проксирования

### Local Override

- `.gitignore` должен содержать `*.local.yml`
- Проверка через `os.path.basename()` — не `endswith()`

### DinD (Docker-in-Docker)

- Требуется для full-deploy-cycle тестов
- Сеть `platform_network` должна существовать
- Тестовый образ: `infra/test-env/Dockerfile`

## 5. Правила для AI

### При изменении кода

1. **Сначала читай**: `service.yml` схему в `discovery.py`
2. **Проверяй conftest.py**: есть ли мок для изменяемого сервиса
3. **Запускай тесты**: `make test` или `pytest --asyncio-mode=auto`
4. **Ruff**: строка 120 символов (E, F, W, I, N, UP, B, C4)

### При добавлении endpoint

1. Добавить route в `app/api/routes/` или существующий модуль
2. Подключить в `main.py` в список `routers`
3. Добавить тест в `tests/unit/test_*_endpoints.py`
4. Обновить Caddy config если нужен публичный доступ

### При изменении Caddy

1. Шаблоны в `_core/caddy/templates/*.j2`
2. Логика генерации в `caddy_manager.py`
3. Перезагрузка через `reload_caddy()` — не редактировать conf.d/ руками
4. Тест: `test_full_cycle.sh` Test 4

### При изменении моделей

1. SQLAlchemy модели в `app/models/`
2. Pydantic схемы для API — [UNVERIFIED] (возможно отсутствуют)
3. Создать миграцию — [UNVERIFIED] (alembic не настроен, см. plan/9-alembic-migrations.md)
4. Обновить fixtures в `conftest.py`

### Что игнорировать

- `platform-cli/` — отдельный изолированный пакет со своим venv
- `docs/plan/` — плановые задачи, не текущая реализация
- `docs/DOCUMENTATION_*.md` — мета-анализ документации
- Legacy в `.legacy/`

### Где искать информацию

- API endpoints: `app/api/routes/*.py`
- Фоновые задачи: `main.py` → `lifespan()` → `*_loop()`
- UI: `app/ui/*_page.py`
- Конфигурация: `app/config.py`, `.ops-config.yml`
- Тесты: `tests/unit/` (unit), `tests/integration/` (int), `infra/test-env/` (DinD)
