# Caddy integration — полный аудит, тестирование, документация

## Проблема

Интеграция с Caddy — основная архитектурная механика платформы. От неё зависит маршрутизация всего трафика. Но:

1. Документация противоречит коду (примеры без `container_name`, который обязателен для работы без маппинга портов)
2. Код не анализировался на предмет корректности всех трёх типов роутинга
3. Непонятно что происходит когда `container_name` не указан, но сервис маппит порт наружу
4. Нет защиты от неправильной конфигурации (платформа не валидирует, не предупреждает)
5. Документация про `host.docker.internal` устарела — это legacy, но никто не знает почему

## Цель

Полная уверенность что:
- Caddy integration работает корректно для всех типов роутинга
- Документация точно описывает поведение
- Плохие конфигурации отсекаются или предупреждаются
- Все примеры рабочие

## Подзадачи

### 1. Аудит кода Caddy integration — [#25](https://github.com/urfu-online/apps-service/issues/25)

**Файлы:**
- `_core/caddy/templates/domain.caddy.j2`
- `_core/caddy/templates/subfolder.caddy.j2`
- `_core/caddy/templates/port.caddy.j2`
- `_core/caddy/Caddyfile`
- `_core/master/app/services/caddy_manager.py`
- `_core/master/app/services/discovery.py` (RoutingConfigModel)

**Что проверить:**
- Как именно генерируется `reverse_proxy` для каждого типа routing
- Что происходит когда `container_name` указан / не указан
- Что происходит когда сервис маппит порт / не маппит
- Как `host.docker.internal` разрешается внутри Caddy-контейнера
- Есть ли health check в сгенерированных конфигах
- Правильно ли обрабатываются `strip_prefix`, `base_domain`, `path`
- Нет ли edge cases: `container_name=None`, `internal_port=None`, пустой routing

**Результат:** таблица «входные параметры → сгенерированный Caddy конфиг → что происходит на самом деле»

### 2. Аудит реальных сервисов — [#26](https://github.com/urfu-online/apps-service/issues/26)

**Файлы:**
- `services/public/*/service.yml` — все 4 сервиса
- `services/public/*/docker-compose.yml` — все 4 сервиса

**Что проверить:**
- У каких сервисов есть `container_name` в routing
- Какие сервисы маппят порты наружу (`ports:`)
- Какие сервисы только в `platform_network`
- Есть ли расхождения между `container_name` в service.yml и `container_name` в docker-compose.yml
- Работают ли сейчас сервисы через Caddy или через прямой доступ к порту

**Результат:** таблица реальных сервисов с их конфигурацией и статусом

### 3. Тестирование всех сценариев — [#27](https://github.com/urfu-online/apps-service/issues/27)

**Тест-матрица:**

| container_name | ports маппинг | Тип routing | Ожидание | Реальность |
|---|---|---|---|---|
| ✅ указан | нет | domain | ✅ работает | ? |
| ✅ указан | есть | domain | ✅ работает | ? |
| ❌ нет | нет | domain | ❌ 502 | ? |
| ❌ нет | есть | domain | ⚠️ работает, но legacy | ? |
| ✅ указан | нет | subfolder | ✅ работает | ? |
| ✅ указан | есть | subfolder | ✅ работает | ? |
| ❌ нет | нет | subfolder | ❌ 502 | ? |
| ❌ нет | есть | subfolder | ⚠️ работает, но legacy | ? |
| ✅ указан | нет | port | ✅ работает | ? |
| ❌ нет | нет | port | ❌ 502 | ? |

**Как тестировать:**
- Создать тестовый сервис для каждого сценария
- Задеплоить через `restart_core.sh --build`
- Проверить что Caddy сгенерировал правильный конфиг
- curl'ить через домен/подпапку/порт
- Проверить логи Caddy и master

**Результат:** отчёт что работает, что нет, где расхождения с ожиданиями

### 4. Валидация конфигурации — [#28](https://github.com/urfu-online/apps-service/issues/28)

**Где добавить:**
- `caddy_manager.py` — при генерации конфига
- Или `discovery.py` — при загрузке манифеста

**Что валидировать:**
- `container_name` обязателен (error или warning)
- `container_name` должен совпадать с реальным контейнером в `docker-compose.yml`
- `internal_port` обязателен и > 0
- Предупреждение если `ports:` маппинг есть (legacy)
- Предупреждение если `container_name` не указан

**Результат:** платформа не даёт задеплоить заведомо нерабочую конфигурацию

### 5. Обновление документации — [#29](https://github.com/urfu-online/apps-service/issues/29)

**Файлы для обновления:**
- `docs/user-guide/services.md` — добавить `container_name` во все примеры
- `docs/examples.md` — все 6 примеров с `container_name`
- `docs/getting-started/first-service.md` — пояснение зачем `container_name`
- `README.md` — манифест с `container_name`
- `docs/architecture.md` — уточнить поток данных
- `docs/best-practices.md` — правило: всегда указывать `container_name`

**Что написать:**
- Почему `container_name` обязателен
- Почему внешний маппинг портов — legacy (обход Caddy, конфликты, безопасность)
- Как правильно указать `container_name` в service.yml и docker-compose.yml
- Что будет если забыть (502, логи Caddy)

**Результат:** ни один пример в документации не работает без `container_name`

### 6. Ограничение legacy-режима — [#30](https://github.com/urfu-online/apps-service/issues/30)

**Вопросы для решения:**
- Нужно ли полностью запретить `host.docker.internal` проксирование?
- Или оставить warning + require explicit opt-in?
- Нужен ли `--allow-host-proxy` флаг для миграции старых сервисов?

**Варианты:**
A. **Hard block** — error если нет `container_name`. Ломаем обратную совместимость, но чисто.
B. **Warning + log** — работает но пишет в лог. Не ломаем, но и не чиним.
C. **Explicit opt-in** — `allow_host_proxy: true` в routing. Новые сервисы не смогут по ошибке, старые — явно укажут.

**Результат:** решение + реализация выбранного варианта

## Материалы

- [ ] Таблица аудита кода
- [ ] Таблица реальных сервисов
- [ ] Отчёт тест-матрицы
- [ ] Реализованная валидация
- [ ] Обновлённая документация
- [ ] Реализованное ограничение legacy-режима

## Связанные issues

- [#25](https://github.com/urfu-online/apps-service/issues/25) — 11a: аудит кода
- [#26](https://github.com/urfu-online/apps-service/issues/26) — 11b: аудит сервисов
- [#27](https://github.com/urfu-online/apps-service/issues/27) — 11c: тестирование
- [#28](https://github.com/urfu-online/apps-service/issues/28) — 11d: валидация
- [#29](https://github.com/urfu-online/apps-service/issues/29) — 11e: документация
- [#30](https://github.com/urfu-online/apps-service/issues/30) — 11f: ограничение legacy
