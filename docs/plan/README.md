# План работ

| # | Задача | Приоритет | Статус | Детали |
|---|--------|-----------|--------|--------|
| 1 | Баги: `AttributeError` в deployments.py и docker_manager.py | 🔴 Критично | ⬜ | [→](1-deploy-bugs.md) |
| 2 | Мёртвые зависимости: aiodocker, python-multipart | 🟡 Низкий | ⬜ | [→](2-dead-deps.md) |
| 3 | Login endpoint в API | 🔴 Критично | ⬜ | [→](3-login-endpoint.md) |
| 4 | LogManager — заглушка, данные не собираются | 🟠 Средний | ⬜ | [→](4-log-manager.md) |
| 5 | Restic upload — скрипты отсутствуют | 🟠 Средний | ⬜ | [→](5-restic-upload.md) |
| 6 | UI: детальная страница сервиса (редирект) | 🟡 Низкий | ⬜ | [→](6-service-detail-page.md) |
| 7 | UI: backup restore/delete — заглушки | 🟡 Низкий | ⬜ | [→](7-backup-restore-ui.md) |
| 8 | `_deploy_static` и `external` type — не реализованы | ⚪ Отложить | ⬜ | [→](8-static-external-types.md) |
| 9 | Миграции БД (Alembic) | 🟠 Средний | ⬜ | [→](9-alembic-migrations.md) |
| 10 | Loki / Prometheus / Grafana | ⚪ Отложить | ⬜ | [→](10-monitoring-stack.md) |
| 11 | Caddy integration — аудит, тестирование, документация, валидация | 🔴 Критично | ⬜ | [→](11-caddy-integration-audit.md) |
| 11a | Аудит кода Caddy integration | 🔴 Критично | ⬜ | [→ #25](https://github.com/urfu-online/apps-service/issues/25) |
| 11b | Аудит реальных сервисов на сервере | 🟠 Средний | ⬜ | [→ #26](https://github.com/urfu-online/apps-service/issues/26) |
| 11c | Тестирование всех сценариев Caddy routing | 🔴 Критично | ⬜ | [→ #27](https://github.com/urfu-online/apps-service/issues/27) |
| 11d | Валидация конфигурации routing | 🟠 Средний | ⬜ | [→ #28](https://github.com/urfu-online/apps-service/issues/28) |
| 11e | Обновить документацию — container_name | 🟡 Низкий | ⬜ | [→ #29](https://github.com/urfu-online/apps-service/issues/29) |
| 11f | Ограничить legacy-режим проксирования | 🟠 Средний | ⬜ | [→ #30](https://github.com/urfu-online/apps-service/issues/30) |

## Структура

```
docs/plan/
  README.md          ← эта страница: таблица задач + ссылки
  N-название.md      ← описание задачи: проблема, подход, решения
  N-название/        ← материалы: код, логи, результаты, заметки
```

## Как работать

1. Выбрал задачу из таблицы → открыл файл → прочитал описание
2. Создал папку `N-название/` → складываешь туда всё по ходу работы
3. Сделал → пометил статус в таблице ✅
4. Закоммитил код + материалы
