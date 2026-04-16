# Конфигурация Caddy

Руководство по настройке и управлению Caddy в качестве reverse proxy для платформы.

## Обзор

Caddy используется как reverse proxy для маршрутизации трафика к сервисам платформы. Конфигурация генерируется автоматически на основе манифестов сервисов (`service.yml`).

Платформа использует **автоматические поддомены** (`{service}.apps.urfu.online`) как основной интеграции. При первом HTTPS-запросе Caddy автоматически выпускает SSL-сертификат через Let's Encrypt.

## Переменные окружения

### PLATFORM_DOMAIN

Основной домен платформы задаётся через переменную `PLATFORM_DOMAIN`. По умолчанию используется `localhost` для разработки.

```bash
# Продакшен
echo "PLATFORM_DOMAIN=apps.urfu.online" > .env

# Локальная разработка
echo "PLATFORM_DOMAIN=localhost" > .env
```

Переменная передаётся в контейнер Caddy через `docker-compose.yml`:

```yaml
environment:
  - PLATFORM_DOMAIN=${PLATFORM_DOMAIN:-localhost}
```

### APP_ENV

Для условного включения конфигураций разработки используется `APP_ENV`:

- `prod` (по умолчанию) — продакшен с автоматическим HTTPS
- `dev` — разработка с отключённым авто-HTTPS

```yaml
environment:
  - APP_ENV=${APP_ENV:-prod}
  - PLATFORM_DOMAIN=${PLATFORM_DOMAIN:-localhost}
```

## Конфигурационные файлы

| Файл | Описание |
|------|----------|
| `_core/caddy/Caddyfile` | Глобальные настройки и импорт конфигураций |
| `_core/caddy/conf.d/*.caddy` | Автоматически генерируемые конфиги сервисов |
| `_core/caddy/development.caddy` | Конфигурации для локальной разработки |
| `_core/caddy/templates/` | Jinja2-шаблоны для генерации конфигов |

## Автоматические поддомены

Платформа автоматически назначает сервисам поддомены вида `{service}.{base_domain}`.

### Как это работает

```
1. Деплой сервиса с auto_subdomain: true
2. CaddyManager генерирует {name}.apps.urfu.online.caddy
3. Caddy загружает конфиг через Admin API
4. Первый HTTPS-запрос → ACME challenge
5. Caddy вызывает /api/tls/validate?domain=...
6. Master проверяет: домен зарегистрирован? → 200/403
7. Если 200 → Caddy выпускает сертификат
```

### Модель маршрутизации

```python
class RoutingConfigModel(BaseModel):
    type: str  # auto_subdomain | domain | subfolder | port
    auto_subdomain: bool = True 
    base_domain: str = "apps.urfu.online"
    internal_port: int = 8000
    container_name: str  # Обязательно
```

### Эндпоинт валидации TLS

```python
@router.get("/api/tls/validate")
async def validate_tls_domain(domain: str, discovery: ServiceDiscovery):
    """
    Валидация домена для on_demand_tls.
    Возвращает 200 если домен разрешён, 403 если нет.
    """
    # Проверка формата
    if not domain.endswith(".apps.urfu.online"):
        raise HTTPException(403, "Domain not in allowed zone")

    # Извлечение имени сервиса
    service_name = domain.rsplit(".apps.urfu.online", 1)[0]

    # Проверка регистрации
    if service_name not in discovery.services:
        raise HTTPException(403, "Service not registered")

    return {"status": "ok", "service": service_name}
```

### Caddyfile (on_demand_tls)

```caddy
{
    email admin@urfu.online
    admin 0.0.0.0:2019

    on_demand_tls {
        ask http://master:8000/api/tls/validate
    }
}

# Wildcard-конфигурация для автоподдоменов
*.apps.urfu.online {
    tls { on_demand }

    log {
        output file /var/log/caddy/acme.log {
            roll_size 50mb
            roll_keep 5
        }
    }

    # Маршрутизация через импорт конфигов сервисов
    import /etc/caddy/conf.d/*.caddy
}
```

## Различия между окружениями

| Параметр | Продакшен (`prod`) | Разработка (`dev`) |
|----------|-------------------|-------------------|
| HTTPS | Автоматический SSL | Отключён |
| Редиректы HTTP→HTTPS | Включены | Нет |
| Development routes | Нет | Да (localhost, instructor.*) |

## Управление конфигурацией

### Перезагрузка через API

```bash
curl -X POST http://localhost:2019/load \
  -H "Content-Type: application/json" \
  -d @/path/to/new/Caddyfile
```

### Перезапуск контейнера

```bash
docker compose -f _core/caddy/docker-compose.yml restart caddy
```

### Проверка конфигурации

```bash
docker compose -f _core/caddy/docker-compose.yml exec caddy \
  caddy validate --config /etc/caddy/Caddyfile
```

## Требования к сервисам

- По умолчанию все сервисы получают автоматический поддомен (`{name}.apps.urfu.online`)
- Все сервисы должны иметь `service.yml` с полем `health.endpoint`
- Обязательно указывать `container_name` для правильной маршрутизации
- Внутренние сервисы (`services/internal/`) не проксируются наружу
- Генерация конфигов — через `CaddyManager` в Master Service

### Пример service.yml с автоподдоменом

```yaml
name: my-service
visibility: public

routing:
  - auto_subdomain: true
    base_domain: apps.urfu.online
    internal_port: 8000
    container_name: my-service

health:
  enabled: true
  endpoint: /health
```

## См. также

- [Master Service](master-service.md) — основная документация по сервису
- [Архитектура Caddy](../architecture/caddy.md) — детали интеграции
