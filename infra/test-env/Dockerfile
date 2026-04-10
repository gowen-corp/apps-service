# DinD (Docker-in-Docker) тестовое окружение
# Симулирует production server (/apps) в изолированном контейнере
#
# Использование:
#   cd infra/test-env
#   docker compose up -d
#   docker exec -it platform-test-env bash
#   ./test_full_cycle.sh

FROM docker:27-dind

RUN apk add --no-cache \
    bash \
    curl \
    git \
    python3 \
    py3-pip \
    openssh-client \
    jq \
    yq \
    && rm -rf /var/cache/apk/*

# Создаём структуру production server
RUN mkdir -p /apps/_core /apps/services/public /apps/services/internal /apps/backups

# Копируем только тестовые сервисы (они маленькие и всегда доступны)
COPY test-services/ /apps/services/

# .ops-config.yml — серверные настройки (локальный override придёт через mount)
RUN echo -e "environment: server\nproject_root: /apps\ncore_path: _core\nservices_path: services" > /apps/.ops-config.yml

WORKDIR /apps

# Скрипт полного цикла
COPY test_full_cycle.sh /apps/test_full_cycle.sh
RUN chmod +x /apps/test_full_cycle.sh

CMD ["dockerd", "--host=unix:///var/run/docker.sock"]
