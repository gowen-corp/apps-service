#!/bin/bash
set -e
trap 'cd /projects/apps-service-opus' EXIT

# Создание тестового сервиса на хосте
cd /projects/apps-service-opus
mkdir -p ./infra/local-test-env/services/public/test/html
echo "<h1>Test Service Working</h1>" > ./infra/local-test-env/services/public/test/html/index.html

cat > ./infra/local-test-env/services/public/test/docker-compose.yml <<'EOF'
services:
  test-web:
    image: nginx:alpine
    volumes:
      - ./html:/usr/share/nginx/html:ro
    networks:
      - platform-net
networks:
  platform-net:
    external: true
EOF

cat > ./infra/local-test-env/services/public/test/caddy.conf <<'EOF'
localhost:80 {
  handle_path /test* {
    reverse_proxy http://test-web:80
  }
}
EOF

# Деплой в ВМ
cd ./infra/local-test-env
vagrant ssh <<'VM_COMMANDS'
# === УСТАНОВКА DOCKER ИЗ ОФИЦИАЛЬНОГО РЕПОЗИТОРИЯ ===
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# === ГАРАНТИРОВАННЫЙ ЗАПУСК DOCKER DAEMON ===
sudo systemctl enable --now docker
# Ждем, пока Docker daemon станет доступен
while ! sudo docker info >/dev/null 2>&1; do
  echo "Waiting for Docker daemon..."
  sleep 2
done

# === СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ И ГРУППЫ ===
sudo groupadd --force platform-admins
sudo useradd -m -s /bin/bash -G platform-admins,docker ignatchenkonv 2>/dev/null || true
sudo usermod -aG docker vagrant

# === СОЗДАНИЕ СТРУКТУРЫ /apps СОГЛАСНО ai_summary.md ===
sudo mkdir -p /apps/{_core/{caddy,master,backup},services/{public,internal},shared/templates,backups}
sudo chown -R ignatchenkonv:platform-admins /apps
sudo chmod 770 /apps

# === НАСТРОЙКА CADDY КАК SYSTEMD-СЕРВИС ===
sudo mkdir -p /apps/_core/caddy/conf.d
cat > /tmp/Caddyfile <<'CADDY'
{
  admin off
  email dev@example.com
}
import /apps/_core/caddy/conf.d/*.conf
CADDY
sudo mv /tmp/Caddyfile /apps/_core/caddy/Caddyfile
sudo chown -R ignatchenkonv:platform-admins /apps/_core/caddy

sudo tee /etc/systemd/system/caddy.service <<'SYSTEMD' >/dev/null
[Unit]
Description=Caddy
Documentation=https://caddyserver.com/docs/
After=network.target docker.service
Requires=docker.service

[Service]
Type=notify
User=ignatchenkonv
Group=platform-admins
ExecStart=/usr/bin/caddy run --config /apps/_core/caddy/Caddyfile --adapter caddyfile
ExecReload=/usr/bin/caddy reload --config /apps/_core/caddy/Caddyfile
TimeoutStopSec=5s
LimitNOFILE=1048576
LimitNPROC=512
PrivateTmp=true
ProtectSystem=full
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
SYSTEMD

sudo systemctl daemon-reload
sudo systemctl enable --now caddy

# === НАСТРОЙКА DOCKER NETWORK ===
sudo docker network create platform-net 2>/dev/null || true

# === КОПИРОВАНИЕ И ЗАПУСК СЕРВИСА ===
sudo -u ignatchenkonv mkdir -p /apps/services/public/test
sudo cp -r /vagrant/services/public/test/* /apps/services/public/test/
sudo chown -R ignatchenkonv:platform-admins /apps/services/public/test

cd /apps/services/public/test
# Убираем version из docker-compose.yml как рекомендует warning
sed -i '/^version:/d' docker-compose.yml
sudo -u ignatchenkonv docker compose up -d

# === КОПИРОВАНИЕ CADDY КОНФИГА ===
sudo cp /apps/services/public/test/caddy.conf /apps/_3/core/caddy/conf.d/test.conf 2>/dev/null || \
sudo cp /apps/services/public/test/caddy.conf /apps/_core/caddy/conf.d/test.conf

sudo systemctl reload caddy
VM_COMMANDS

# Проверка
curl -s http://localhost:8080/test | grep -q "Test Service Working" && echo "SUCCESS" || (echo "FAILED"; exit 1)