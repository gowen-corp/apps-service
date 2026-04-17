#!/bin/bash
set -euo pipefail

# Определение абсолютных путей
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Проверка существования .env файла
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Ошибка: файл .env не найден в $ENV_FILE"
    echo "Создайте файл .env на основе .env.example"
    exit 1
fi

# Функция для отображения справки
usage() {
    echo "Использование: $0 [--build]"
    echo "  --build    Пересобрать образы перед запуском"
    echo "  без флагов  Простой рестарт без пересборки"
    exit 1
}

# Переменная для хранения флага --build
BUILD_FLAG=""

# Обработка аргументов командной строки
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_FLAG="--build"
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Неизвестный параметр: $1"
            usage
            ;;
    esac
    shift
done

# Рестарт master-сервисов
echo "Останавливаю master-сервис..."
docker compose --env-file "$ENV_FILE" -f "$PROJECT_ROOT/_core/master/docker-compose.yml" down

echo "Запускаю master-сервис..."
docker compose --env-file "$ENV_FILE" -f "$PROJECT_ROOT/_core/master/docker-compose.yml" up -d $BUILD_FLAG

# Рестарт Caddy
echo "Останавливаю Caddy..."
docker compose --env-file "$ENV_FILE" -f "$PROJECT_ROOT/_core/caddy/docker-compose.yml" down

echo "Запускаю Caddy..."
docker compose --env-file "$ENV_FILE" -f "$PROJECT_ROOT/_core/caddy/docker-compose.yml" up -d $BUILD_FLAG

echo "✅ Обновление завершено."
