# Apps Service Platform

> Единая платформа для развёртывания, управления и мониторинга сервисов на Docker.

<div align="center">

[Документация](https://urfu-online.github.io/apps-service) · [Quick Start](#-quick-start-5-минут) · [Architecture](docs/architecture/) · [Contributing](#-contributing)

</div>

---

## 🧩 Что это

Платформа превращает набор Docker-контейнеров в **управляемую систему**:

| Без платформы | С платформой |
|---|---|
| Ручной `docker compose` для каждого сервиса | Один CLI/UI для всех сервисов |
| Маршруты в голове или разбросаны по конфигам | Автогенерация роутинга из `service.yml` |
| «А работает ли оно?» | Health checks + Telegram-уведомления |
| Бэкапы «когда вспомню» | Расписание + Restic + ротация |
| Добавил сервис — правил Caddy, Nginx, DNS | Положил `service.yml` — он появился в UI |

## 🏗 Архитектура

```
┌─────────────────────────────────────────────┐
│              Caddy (reverse proxy)           │
│         SSL · routing · rate limit           │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│          Master Service (FastAPI)            │
│  ┌──────────┬──────────┬──────────┐         │
│  │ Discovery│  Caddy   │  Docker  │         │
│  │          │ Manager  │ Manager  │         │
│  └──────────┴──────────┴──────────┘         │
│  ┌──────────┬──────────┬──────────┐         │
│  │  Health  │  Backup  │   Logs   │         │
│  │ Checker  │ Manager  │ Manager  │         │
│  └──────────┴──────────┴──────────┘         │
└────────────────────┬────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
 services/       services/      _core/backup/
  public/        internal/       (Restic)
```

**5 компонентов:**

| Компонент | Что делает | Стек |
|---|---|---|
| **Master Service** | Управление, UI, API, оркестрация | Python, FastAPI, NiceGUI |
| **Caddy** | Reverse proxy, SSL, роутинг | Caddy 2 |
| **Docker** | Контейнеризация сервисов | Docker Compose |
| **Platform CLI** | Управление из терминала | Python, Typer |
| **Backup** | Restic-бэкапы по расписанию | Restic, cron |

## 🚀 Quick Start (5 минут)

### 1. Клонировать

```bash
git clone https://github.com/urfu-online/apps-service.git
cd apps-service
```

### 2. Установить

```bash
./install.sh
```

Скрипт спросит тип окружения (`local` / `server`) и установит CLI `ops`.

### 3. Добавить сервис

```bash
# Создать шаблон
platform new my-app public

# Или просто положить service.yml + docker-compose.yml
# в services/public/my-app/
```

### 4. Запустить

```bash
./restart_core.sh --build    # master + caddy
ops up my-app                # ваш сервис
ops list                     # увидеть всё
```

Готово. Сервис доступен через Caddy, отображается в UI, мониторится и бэкапится.

## 📋 Возможности

- 🔍 **Auto-discovery** — сканирует `services/`, читает `service.yml`, обновляет роутинг
- 🌐 **Авто-роутинг** — домен, подпапка или порт — настраивается в манифесте
- 🔄 **Hot reload** — изменил `service.yml` → Caddy перегенерировался сам
- 💾 **Бэкапы** — файлы + БД (PostgreSQL/MySQL), Restic, ротация, Telegram
- 📊 **Мониторинг** — health checks каждые 30s, логи, статус в UI
- 🎛 **Dual auth** — встроенная аутентификация или Keycloak (OAuth2)
- 📱 **Telegram** — уведомления о деплое, сбоях, бэкапах
- 🛠 **CLI + UI** — `ops` для терминала, NiceGUI для браузера

## 📁 Структура репозитория

```
.
├── install.sh              # Главный установщик
├── restart_core.sh         # Перезапуск core-сервисов
├── .ops-config.yml         # Конфиг платформы
├── .ops-config.local.yml   # Локальный override (не коммитится)
│
├── _core/
│   ├── master/             # Master Service (FastAPI + NiceGUI)
│   ├── caddy/              # Caddy reverse proxy
│   ├── backup/             # Restic backup service
│   └── platform-cli/       # Platform CLI (Python/Typer)
│
├── services/               # Сервисы (gitignored)
│   ├── public/             #   публичные
│   └── internal/           #   внутренние
│
├── shared/templates/       # Шаблоны для новых сервисов
├── docs/                   # Документация (MkDocs)
└── infra/test-env/         # DinD тестовое окружение
```

## 📖 Документация

| Для кого | Где |
|---|---|
| **Быстрый старт** | Этот README 👆 |
| **Полная документация** | [docs/](docs/) — MkDocs сайт |
| **API Reference** | `http://localhost:8000/docs` (после запуска) |
| **Примеры сервисов** | [docs/examples/](docs/examples/) |
| **Разработчикам** | [docs/development.md](docs/development.md) |

## 🧪 Тестирование

```bash
# Быстро — интеграционные тесты
cd _core/master
pytest tests/integration/test_full_deploy_cycle.py -v

# Полностью — DinD симуляция сервера
cd infra/test-env
docker compose up -d
docker compose exec test-env ./test_full_cycle.sh
```

## 🤝 Contributing

1. Форк → ветка (`feat/...`, `fix/...`, `chore/...`)
2. Коммиты → пуш → PR в `main`
3. Код-ревью → мерж

См. [docs/development.md](docs/development.md) для деталей.

## 📄 License

Проект разработан командой [UrFu Online](https://github.com/urfu-online).
