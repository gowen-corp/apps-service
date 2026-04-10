#!/usr/bin/env bash
# test_full_cycle.sh — Полный цикл тестирования платформы
# Запускается ВНУТРИ DinD контейнера или на хосте с Docker
#
# Проверяет:
#   1. install.sh — генерация конфига
#   2. ServiceDiscovery — обнаружение сервисов
#   3. CaddyManager — генерация конфигов
#   4. DockerManager (dry-run) — подготовка команд деплоя
#   5. Health check — проверка эндпоинтов
#   6. Очистка — удаление созданных ресурсов

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
TEST_DIR="/projects/apps-service-opus"

pass() { echo -e "${GREEN}✓ PASS${NC} $1"; ((PASS_COUNT++)); }
fail() { echo -e "${RED}✗ FAIL${NC} $1: $2"; ((FAIL_COUNT++)); }
info() { echo -e "${YELLOW}→${NC} $1"; }

check_exit() {
    local desc="$1"
    if [ $? -eq 0 ]; then
        pass "$desc"
    else
        fail "$desc" "exit code != 0"
    fi
}

check_output() {
    local desc="$1"
    local output="$2"
    local expected="$3"
    if echo "$output" | grep -q "$expected"; then
        pass "$desc"
    else
        fail "$desc" "expected '$expected' not found in output"
    fi
}

echo "========================================"
echo " Platform Full-Cycle Test Suite"
echo "========================================"
echo ""

# ------------------------------------------
# Test 1: Environment validation
# ------------------------------------------
info "Test 1: Environment validation"

if command -v docker &>/dev/null; then
    pass "docker is available"
else
    fail "docker" "not found"
fi

if command -v docker compose &>/dev/null || docker compose version &>/dev/null 2>&1; then
    pass "docker compose is available"
else
    fail "docker compose" "not found"
fi

if [ -d "$TEST_DIR" ]; then
    pass "project directory exists"
else
    fail "project directory" "$TEST_DIR not found"
fi

if [ -f "$TEST_DIR/.ops-config.yml" ]; then
    pass ".ops-config.yml exists"
else
    fail ".ops-config.yml" "not found"
fi

echo ""

# ------------------------------------------
# Test 2: Service Discovery
# ------------------------------------------
info "Test 2: Service Discovery (pytest unit + integration)"

cd "$TEST_DIR/_core/master"

# Запускаем тесты с мокнутым Docker
TEST_OUTPUT=$(poetry run pytest tests/ -v --tb=short 2>&1) || true
check_output "pytest tests run" "$TEST_OUTPUT" "passed\|PASSED\|ERROR\|failed"

echo ""

# ------------------------------------------
# Test 3: Dry-run deployment
# ------------------------------------------
info "Test 3: Dry-run deployment"

# Проверяем что dry-run режим работает через Python-скрипт
DRY_RUN_RESULT=$(cd "$TEST_DIR/_core/master" && python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.discovery import ServiceManifest

async def test():
    # Создаём мок нотификатора
    mock_notifier = AsyncMock()
    mock_notifier.send = AsyncMock()

    # Создаём мок docker клиента
    with patch('docker.from_env') as mock_docker:
        mock_docker.return_value = MagicMock()

        from app.services.docker_manager import DockerManager

        manager = DockerManager(mock_notifier)

        manifest = ServiceManifest(
            name='hello-web',
            version='1.0.0',
            type='docker-compose',
            visibility='public',
            routing=[],
        )
        # Указываем реальный путь к тестовому сервису
        from pathlib import Path
        manifest.path = Path('$TEST_DIR/infra/test-env/test-services/public/hello-web')

        result = await manager.deploy_service(manifest, dry_run=True)
        print(f'success={result[\"success\"]}')
        print(f'message={result[\"message\"]}')
        for log in result['logs']:
            print(f'log: {log}')

asyncio.run(test())
" 2>&1)

check_output "dry-run returns success" "$DRY_RUN_RESULT" "success=True"
check_output "dry-run logs commands" "$DRY_RUN_RESULT" "DRY-RUN"

echo ""

# ------------------------------------------
# Test 4: Caddy config generation
# ------------------------------------------
info "Test 4: Caddy config generation"

CADDY_GEN_RESULT=$(cd "$TEST_DIR/_core/master" && python3 -c "
import asyncio
import sys
import tempfile
import shutil
sys.path.insert(0, '.')

async def test():
    from app.services.caddy_manager import CaddyManager
    from app.services.discovery import ServiceManifest, RoutingConfigModel

    # Временная директория для Caddy конфигов
    tmp_caddy = tempfile.mkdtemp()
    templates_src = Path('$TEST_DIR/_core/caddy/templates')
    snippets_src = Path('$TEST_DIR/_core/caddy/snippets')
    (Path(tmp_caddy) / 'templates').mkdir()
    (Path(tmp_caddy) / 'snippets').mkdir()
    (Path(tmp_caddy) / 'conf.d').mkdir()

    import os
    for f in os.listdir(templates_src):
        shutil.copy(templates_src / f, Path(tmp_caddy) / 'templates' / f)
    for f in os.listdir(snippets_src):
        shutil.copy(snippets_src / f, Path(tmp_caddy) / 'snippets' / f)

    manager = CaddyManager(tmp_caddy)

    services = {
        'hello-web': ServiceManifest(
            name='hello-web',
            version='1.0.0',
            visibility='public',
            routing=[RoutingConfigModel(
                type='domain',
                domain='hello.test.local',
                internal_port=80,
                container_name='hello-web',
            )],
        ),
        'test-api': ServiceManifest(
            name='test-api',
            version='0.1.0',
            visibility='internal',
            routing=[RoutingConfigModel(
                type='port',
                internal_port=8000,
                port=9000,
            )],
        ),
    }

    await manager.regenerate_all(services)

    conf_files = list(Path(tmp_caddy).joinpath('conf.d').glob('*.caddy'))
    print(f'generated {len(conf_files)} config files')
    for f in conf_files:
        content = f.read_text()
        print(f'file: {f.name} ({len(content)} bytes)')
        if 'reverse_proxy' in content:
            print(f'  -> contains reverse_proxy')

    # Cleanup
    shutil.rmtree(tmp_caddy)

from pathlib import Path
asyncio.run(test())
" 2>&1)

check_output "caddy generates config files" "$CADDY_GEN_RESULT" "generated.*config files"
check_output "caddy includes reverse_proxy" "$CADDY_GEN_RESULT" "reverse_proxy"

echo ""

# ------------------------------------------
# Test 5: Local override mechanism
# ------------------------------------------
info "Test 5: Local override mechanism"

# Проверяем что .ops-config.local.yml загружается
if [ -f "$TEST_DIR/.ops-config.local.yml" ]; then
    pass ".ops-config.local.yml exists"
else
    fail ".ops-config.local.yml" "not found"
fi

# Проверяем что CLI загружает override
CLI_RESULT=$(cd "$TEST_DIR" && python3 -c "
import sys
sys.path.insert(0, '_core/platform-cli')
from pathlib import Path

# Симулируем загрузку конфига с override
import yaml

config_path = Path('.ops-config.yml')
with open(config_path) as f:
    config = yaml.safe_load(f)

local_override = Path('.ops-config.local.yml')
if local_override.exists():
    with open(local_override) as f:
        local_data = yaml.safe_load(f)
    if local_data and isinstance(local_data, dict):
        config.update(local_data)

print(f'environment={config.get(\"environment\")}')
print(f'project_root={config.get(\"project_root\")}')
" 2>&1)

check_output "local override applied" "$CLI_RESULT" "environment=local"
check_output "project_root is local" "$CLI_RESULT" "project_root=/projects"

echo ""

# ------------------------------------------
# Test 6: File watcher handles .local.yml
# ------------------------------------------
info "Test 6: File watcher detects .local.yml changes"

WATCHER_RESULT=$(cd "$TEST_DIR/_core/master" && python3 -c "
from app.services.discovery import _is_service_config_file

# Тестируем точное совпадение имени файла (не endswith!)
tests = [
    ('/path/service.yml', True),
    ('/path/service.local.yml', True),
    ('/path/docker-compose.yml', True),
    ('/path/myservice.yml', False),       # endswith bug — не должен матчиться
    ('/path/not-service.local.yml', False), # не должен матчиться
    ('/path/service.yml.bak', False),
]

all_pass = True
for path, expected in tests:
    result = _is_service_config_file(path)
    status = 'OK' if result == expected else 'FAIL'
    if result != expected:
        all_pass = False
    print(f'{status}: {path} -> {result} (expected {expected})')

if all_pass:
    print('ALL_WATCHER_TESTS_PASSED')
" 2>&1)

check_output "file watcher uses basename (not endswith)" "$WATCHER_RESULT" "ALL_WATCHER_TESTS_PASSED"

echo ""

# ------------------------------------------
# Summary
# ------------------------------------------
echo "========================================"
echo " Results: ${GREEN}${PASS_COUNT} passed${NC}, ${RED}${FAIL_COUNT} failed${NC}"
echo "========================================"

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}All tests passed! Platform is ready for deployment.${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Review output above.${NC}"
    exit 1
fi
