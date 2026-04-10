#!/bin/sh
set -e

# Удаляем пустые директории из Dockerfile и создаём симлинки
rm -rf /apps/_core /apps/services /apps/backups
ln -sf /projects/apps-service-opus/_core /apps/_core
ln -sf /projects/apps-service-opus/services /apps/services
ln -sf /projects/apps-service-opus/backups /apps/backups
ln -sf /projects/apps-service-opus/.ops-config.yml /apps/.ops-config.yml
ln -sf /projects/apps-service-opus/.ops-config.local.yml /apps/.ops-config.local.yml 2>/dev/null || true
ln -sf /projects/apps-service-opus/install.sh /apps/install.sh
ln -sf /projects/apps-service-opus/restart_core.sh /apps/restart_core.sh

# Запускаем Docker-in-Docker
dockerd &

# Ждём пока dockerd станет доступен
for i in $(seq 1 30); do
    docker info > /dev/null 2>&1 && break
    echo "Waiting for dockerd... ($i)"
    sleep 1
done

if ! docker info > /dev/null 2>&1; then
    echo "ERROR: dockerd failed to start"
    exit 1
fi

echo "dockerd is ready"
tail -f /dev/null
