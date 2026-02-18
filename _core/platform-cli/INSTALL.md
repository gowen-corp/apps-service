# Platform CLI — Руководство по установке

## Требования

- **Python** 3.11 или выше
- **pip** (менеджер пакетов Python)
- **Docker** и **Docker Compose**
- Доступ к `/var/run/docker.sock`

---

## Способ 1: Установка через pipx (рекомендуется)

### Шаг 1: Установка pipx

```bash
# Установка pipx
python3 -m pip install --user pipx

# Добавление в PATH
python3 -m pipx ensurepath

# Для текущей сессии
export PATH="$HOME/.local/bin:$PATH"
```

### Шаг 2: Установка platform-cli

```bash
pipx install /apps/_core/platform-cli
```

### Шаг 3: Проверка

```bash
platform --help
platform list
```

---

## Способ 2: Автоматическая установка

```bash
cd /apps/_core/platform-cli
./install.sh
```

Скрипт автоматически:
- Проверит наличие Python и pip
- Установит pipx (если отсутствует)
- Установит platform-cli в изолированную среду

---

## Способ 3: Установка через Docker

### Сборка образа

```bash
cd /apps/_core/platform-cli
docker build -t platform-cli .
```

### Запуск

```bash
# Запуск команды
docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /apps:/apps \
    platform-cli list

# Интерактивный режим
docker run --rm -it \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /apps:/apps \
    platform-cli
```

### Алиас для удобства

```bash
alias platform='docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v /apps:/apps platform-cli'
```

---

## Способ 4: Прямая установка через pip

```bash
# Глобальная установка (требует sudo)
sudo pip install /apps/_core/platform-cli

# Установка в домашнюю директорию
pip install --user /apps/_core/platform-cli
```

---

## Проверка установки

```bash
# Проверка версии
platform --version

# Проверка доступных команд
platform --help

# Список сервисов
platform list

# Информация о платформе
platform info
```

---

## Настройка доступа к Docker

Для работы с Docker без sudo:

```bash
# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Применение изменений (требуется перелогиниться)
newgrp docker
```

Проверка:

```bash
docker ps
```

---

## Конфигурация

Platform CLI использует конфигурацию Ops Manager:

```yaml
# ~/.config/ops-manager/config.yml
# или
# /apps/.ops-config.yml

environment: server
project_root: /apps
core_path: _core
services_path: services
```

---

## Устранение неполадок

### "command not found: platform"

```bash
# Проверка PATH
echo $PATH

# Добавление ~/.local/bin в PATH
export PATH="$HOME/.local/bin:$PATH"

# Для постоянного добавления
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### "Permission denied: /var/run/docker.sock"

```bash
# Добавление в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### "Config not found"

```bash
# Проверка наличия конфигурации
ls -la /apps/.ops-config.yml

# Запуск install.sh в корне проекта
cd /apps && ./install.sh
```

---

## Обновление

```bash
# Через pipx
pipx upgrade platform-cli

# Переустановка
pipx reinstall platform-cli

# Из репозитория
cd /apps/_core/platform-cli
git pull
pipx upgrade platform-cli
```

---

## Удаление

```bash
# Через pipx
pipx uninstall platform-cli

# Очистка кэша pipx
pipx uninstall-all
```

---

## Для разработчиков

### Установка в режиме разработки

```bash
# Через pipx
pipx install --editable /apps/_core/platform-cli

# Через pip
pip install -e /apps/_core/platform-cli

# С dev зависимостями
pip install -e "/apps/_core/platform-cli[dev]"
```

### Запуск тестов

```bash
pytest
pytest --cov=platform
```

### Линтинг

```bash
ruff check platform/
black --check platform/
```

---

## Поддержка

При возникновении проблем:

1. Проверьте версию Python: `python3 --version`
2. Проверьте установку pipx: `pipx --version`
3. Проверьте доступ к Docker: `docker ps`
4. Проверьте конфигурацию: `platform info`
