#!/bin/sh
set -e

# Создаём структуру /apps и симлинки на примонтированный проект
rm -rf /apps/_core /apps/services /apps/backups 2>/dev/null || true
ln -sf /projects/apps-service-opus/_core /apps/_core
ln -sf /projects/apps-service-opus/services /apps/services
ln -sf /projects/apps-service-opus/backups /apps/backups
ln -sf /projects/apps-service-opus/.ops-config.yml /apps/.ops-config.yml
ln -sf /projects/apps-service-opus/.ops-config.local.yml /apps/.ops-config.local.yml 2>/dev/null || true
ln -sf /projects/apps-service-opus/install.sh /apps/install.sh
ln -sf /projects/apps-service-opus/restart_core.sh /apps/restart_core.sh

echo "Symlinks ready. Docker from host socket."
tail -f /dev/null
