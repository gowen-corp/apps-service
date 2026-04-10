# Шпаргалка: обновление платформы на сервере

## 1. Узнать что сейчас на сервере

```bash
ssh <сервер> "cd /apps && git log --oneline -5"
ssh <сервер> "cd /apps && git status"
```

Первая команда покажет последний коммит, вторая — есть ли локальные изменения.

## 2. Что тестировать где

| Что проверяешь | Где |
|---|---|
| Код работает, тесты проходят | **Локально** — DinD (`infra/test-env/`) |
| Миграции БД, существующие сервисы | **Сервер** — только тут реальные данные |
| Caddy + SSL + DNS | **Сервер** — на локале нет доменов |
| Конфликты с ручными правками админа | **Сервер** — только тут они есть |

**DinD не заменит сервер** — там нет реальных сервисов, данных, ручных правок конфига. DinD — только "код вообще запускается".

## 3. Процесс обновления (безопасный)

### Шаг 1: Подготовка (локально)

```bash
# Убедиться что main свежий
git pull origin main

# Посмотреть что изменилось
git log --oneline origin/main..HEAD  # если есть локальные коммиты
git diff HEAD~3 --stat               # что поменялось за последние коммиты
```

### Шаг 2: Бэкап (на сервере) — ОБЯЗАТЕЛЬНО

```bash
ssh <сервер>

# Остановить master (чтобы не писал в БД во время бэкапа)
cd /apps
docker compose -f _core/master/docker-compose.yml down

# Забэкапить БД
cp _core/master/master.db /tmp/master.db.backup.$(date +%Y%m%d)

# Забэкапить все service.yml сервисов
tar czf /tmp/services-backup.$(date +%Y%m%d).tgz services/

# Забэкапить текущий конфиг Caddy
tar czf /tmp/caddy-backup.$(date +%Y%m%d).tgz _core/caddy/

# Проверить что бэкапы создались
ls -lh /tmp/*.backup.* /tmp/*.tgz
```

### Шаг 3: Pull на сервере

```bash
cd /apps

# Проверить нет ли локальных изменений
git status
git stash  # если есть — сохранить

# Обновить код
git pull origin main

# Посмотреть что обновилось
git log --oneline -5
```

### Шаг 4: Перезапуск core

```bash
cd /apps

# Пересобрать и перезапустить master + caddy
./restart_core.sh --build

# Проверить что запустились
docker ps | grep -E "master|caddy"
docker logs platform-master --tail 20
```

### Шаг 5: Проверка

```bash
# Master UI
curl -s http://localhost:8001/healthz

# Caddy
curl -s http://localhost:80/ -o /dev/null -w "%{http_code}"

# Логи master
docker logs platform-master --tail 50

# Проверить что сервисы на месте
cd /apps && ops list   # или platform list
```

### Шаг 6: Проверка сервисов

```bash
# Пройтись по ключевым сервисам
curl http://<домен-сервиса>/healthz
# или
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Если что-то пошло не так — откат

```bash
cd /apps

# Откатить git
git reset --hard HEAD~1  # или к нужному коммиту

# Восстановить БД
cp /tmp/master.db.backup.YYYYMMDD _core/master/master.db

# Перезапустить
./restart_core.sh
```

## 4. Что может сломаться

| Риск | Почему | Как проверить |
|---|---|---|---|
| Миграции БД | Нет Alembic, `create_all()` | master.log при старте |
| Caddy конфиг | Генерируется заново, могли быть ручные правки | Сравнить `_core/caddy/conf.d/` до/после |
| Docker network | `platform_network` может не существовать после ребута | `docker network ls` |
| Зависимости | Новый pyproject.toml, старые образы | `restart_core.sh --build` пересоберёт |
| Local override | `.ops-config.local.yml` — gitignored, не затронется | `git status` покажет если есть |

## 5. Чеклист перед обновлением

- [ ] Бэкап БД сделан
- [ ] Бэкап сервисов сделан
- [ ] Бэкап Caddy конфига сделан
- [ ] Список сервисов записан (`ops list > /tmp/services-before.txt`)
- [ ] Есть план отката (бэкапы на месте)
- [ ] Есть время на фикс если что-то пойдёт не так
- [ ] Telegram уведомления работают (узнаешь если мастер упадёт)
