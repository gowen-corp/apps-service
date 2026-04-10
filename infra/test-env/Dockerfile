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
    py3-virtualenv \
    openssh-client \
    jq \
    yq \
    build-base \
    libffi-dev \
    openssl-dev \
    && rm -rf /var/cache/apk/*

# Создаём структуру production server
RUN mkdir -p /apps/_core /apps/services/public /apps/services/internal /apps/backups

# Копируем только тестовые сервисы
COPY test-services/ /apps/services/

# .ops-config.yml
RUN echo -e "environment: server\nproject_root: /apps\ncore_path: _core\nservices_path: services" > /apps/.ops-config.yml

WORKDIR /apps

# Скрипт полного цикла
COPY test_full_cycle.sh /apps/test_full_cycle.sh
RUN chmod +x /apps/test_full_cycle.sh

# Entrypoint: настраивает симлинки
COPY entrypoint.sh /entrypoint.sh
COPY entrypoint-simple.sh /entrypoint-simple.sh
RUN chmod +x /entrypoint.sh /entrypoint-simple.sh

ENTRYPOINT ["/entrypoint-simple.sh"]
