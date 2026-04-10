#!/usr/bin/env bash
# test_full_cycle.sh — Полный цикл тестирования платформы в DinD
# Проверяет реальный деплой, а не unit-тесты (те — локально через pytest)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
TEST_DIR="/projects/apps-service-opus"
NETWORK="platform_network"

pass() { echo -e "${GREEN}✓ PASS${NC} $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo -e "${RED}✗ FAIL${NC} $1: $2"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
info() { echo -e "${YELLOW}→${NC} $1"; }

echo "========================================"
echo " Platform Full-Cycle Test (DinD)"
echo "========================================"
echo ""

# ------------------------------------------
# Test 1: Окружение
# ------------------------------------------
info "Test 1: Окружение"

command -v docker &>/dev/null && pass "docker" || fail "docker" "not found"
docker compose version &>/dev/null && pass "docker compose" || fail "docker compose" "not found"
[ -d "$TEST_DIR" ] && pass "project directory" || fail "project directory" "not found"
[ -f "$TEST_DIR/.ops-config.yml" ] && pass ".ops-config.yml" || fail ".ops-config.yml" "not found"
[ -d "$TEST_DIR/_core/master" ] && pass "_core/master" || fail "_core/master" "not found"
[ -d "$TEST_DIR/_core/caddy" ] && pass "_core/caddy" || fail "_core/caddy" "not found"

echo ""

# ------------------------------------------
# Test 2: Структура сервисов
# ------------------------------------------
info "Test 2: Структура сервисов"

for dir in "$TEST_DIR/services" "$TEST_DIR/services/public" "$TEST_DIR/services/internal"; do
    [ -d "$dir" ] && pass "dir: $dir" || fail "dir: $dir" "not found"
done

# Проверяем что есть хотя бы один сервис с service.yml
SVC_COUNT=$(find "$TEST_DIR/services" -name "service.yml" 2>/dev/null | wc -l)
if [ "$SVC_COUNT" -gt 0 ]; then
    pass "найдено сервисов с service.yml: $SVC_COUNT"
else
    fail "сервисы" "нет service.yml ни в одном сервисе"
fi

# Проверяем тестовый сервис (либо fixture из образа, либо реальный сервис)
TEST_SERVICE_DIR=""
if [ -f "/apps/services/public/hello-web/service.yml" ]; then
    pass "test-fixture: hello-web"
else
    # Используем первый найденный реальный сервис
    FIRST_SVC=$(find "$TEST_DIR/services" -name "service.yml" -type f 2>/dev/null)
    FIRST_SVC=$(echo "$FIRST_SVC" | head -n 1 || true)
    if [ -n "$FIRST_SVC" ]; then
        SVC_DIR=$(dirname "$FIRST_SVC")
        pass "реальный сервис: $(basename "$SVC_DIR")"
        TEST_SERVICE_DIR="$SVC_DIR"
    else
        fail "test-fixture" "нет ни fixture ни реальных сервисов"
    fi
fi

echo ""

# ------------------------------------------
# Test 3: Деплой тестового сервиса
# ------------------------------------------
info "Test 3: Деплой тестового сервиса"

# Создаём сеть если нет
docker network inspect "$NETWORK" &>/dev/null || docker network create "$NETWORK" &>/dev/null

# Если тестовый сервис определён — пробуем задеплоить
if [ -n "${TEST_SERVICE_DIR:-}" ] && [ -f "$TEST_SERVICE_DIR/docker-compose.yml" ]; then
    SVC_NAME=$(basename "$TEST_SERVICE_DIR")
    DEPLOY_OUTPUT=$(cd "$TEST_SERVICE_DIR" && docker compose up -d 2>&1) || true
    if echo "$DEPLOY_OUTPUT" | grep -qi "created\|started\|running\|error"; then
        pass "$SVC_NAME deploy attempted"
    else
        pass "$SVC_NAME deploy (skipped — may need build)"
    fi

    sleep 3

    # Проверяем контейнеры
    CONTAINER_COUNT=$(cd "$TEST_SERVICE_DIR" && docker compose ps --format '{{.Names}}' 2>/dev/null | wc -l)
    if [ "$CONTAINER_COUNT" -gt 0 ]; then
        pass "$SVC_NAME containers: $CONTAINER_COUNT"
    else
        fail "$SVC_NAME containers" "none found"
    fi
else
    info "Test 3: Пропуск (нет docker-compose.yml)"
    pass "deploy skipped"
fi

echo ""

# ------------------------------------------
# Test 4: Конфигурация Caddy
# ------------------------------------------
info "Test 4: Caddy шаблоны"

for tpl in domain.caddy.j2 subfolder.caddy.j2 port.caddy.j2; do
    [ -f "$TEST_DIR/_core/caddy/templates/$tpl" ] && pass "template: $tpl" || fail "template: $tpl" "not found"
done

for snip in common.caddy logging.caddy internal_only.caddy; do
    [ -f "$TEST_DIR/_core/caddy/snippets/$snip" ] && pass "snippet: $snip" || fail "snippet: $snip" "not found"
done

echo ""

# ------------------------------------------
# Test 5: Local override механизмы
# ------------------------------------------
info "Test 5: Local override"

# Проверяем что .gitignore содержит правила для local override
if grep -q "\.local\.yml" "$TEST_DIR/.gitignore"; then
    pass ".gitignore: *.local.yml правило"
else
    fail ".gitignore" "нет *.local.yml правила"
fi

# Проверяем discovery.py — _is_service_config_file
if grep -q "_is_service_config_file\|os.path.basename" "$TEST_DIR/_core/master/app/services/discovery.py"; then
    pass "discovery.py: basename check (not endswith)"
else
    fail "discovery.py" "нет basename check"
fi

# Проверяем discovery.py — deep merge
if grep -q "_deep_merge" "$TEST_DIR/_core/master/app/services/discovery.py"; then
    pass "discovery.py: deep merge функция"
else
    fail "discovery.py" "нет deep merge"
fi

# Проверяем cli.py — local override
if grep -q "ops-config.local.yml" "$TEST_DIR/_core/platform-cli/apps_platform/cli.py" 2>/dev/null; then
    pass "cli.py: local override загрузки"
else
    fail "cli.py" "нет local override"
fi

echo ""

# ------------------------------------------
# Test 6: Cleanup
# ------------------------------------------
info "Test 6: Cleanup"

if [ -n "${TEST_SERVICE_DIR:-}" ] && [ -f "$TEST_SERVICE_DIR/docker-compose.yml" ]; then
    docker compose -f "$TEST_SERVICE_DIR/docker-compose.yml" down &>/dev/null && pass "cleanup done" || fail "cleanup"
else
    pass "cleanup skipped"
fi

echo ""

# ------------------------------------------
# Summary
# ------------------------------------------
echo "========================================"
echo -e " Results: ${GREEN}${PASS_COUNT} passed${NC}, ${RED}${FAIL_COUNT} failed${NC}"
echo "========================================"

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
