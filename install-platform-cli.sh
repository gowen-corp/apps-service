#!/bin/bash
# Скрипт для установки Platform CLI после основной установки

set -e

echo "📦 Установка Platform CLI"
echo "========================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Проверка конфигурации Ops Manager
CONFIG_CANDIDATES=(
    "$SCRIPT_DIR/.ops-config.yml"
    "$HOME/.config/ops-manager/config.yml"
)

CONFIG_FILE=""
for cfg in "${CONFIG_CANDIDATES[@]}"; do
    [[ -f "$cfg" ]] && { CONFIG_FILE="$cfg"; break; }
done

if [[ -n "$CONFIG_FILE" ]]; then
    # Извлечение PROJECT_ROOT из конфига
    PROJECT_ROOT="$(grep '^project_root:' "$CONFIG_FILE" | cut -d':' -f2- | sed 's/^[[:space:]]*//')"
else
    # Fallback: используем текущую директорию
    PROJECT_ROOT="$SCRIPT_DIR"
fi

CLI_DIR="$PROJECT_ROOT/_core/platform-cli"

# Проверка наличия platform-cli
if [[ ! -d "$CLI_DIR" ]]; then
    echo "❌ Platform CLI не найден в $CLI_DIR"
    exit 1
fi

# Проверка pipx
if ! command -v pipx &> /dev/null; then
    echo "⚠️  pipx не найден. Установка..."
    
    if ! python3 -m pip --version &> /dev/null; then
        echo "❌ pip не найден. Установите Python pip."
        exit 1
    fi
    
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    
    export PATH="$HOME/.local/bin:$PATH"
fi

# Проверка установки
if command -v platform &> /dev/null; then
    echo "ℹ️  Platform CLI уже установлен"
    echo ""
    read -rp "Переустановить? [y/N]: " REINSTALL
    if [[ "$REINSTALL" =~ ^[yY] ]]; then
        pipx uninstall platform-cli
    else
        echo "Использование: platform --help"
        exit 0
    fi
fi

# Установка
echo ""
echo "📦 Установка platform-cli..."
pipx install "$CLI_DIR"

echo ""
echo "✅ Platform CLI установлен!"
echo ""
echo "Использование:"
echo "  platform --help"
echo "  platform list"
echo "  platform new myapp public"
echo "  platform deploy myapp"
