#!/bin/bash
# Скрипт установки Platform CLI через pipx

set -e

echo "🚀 Установка Platform CLI"
echo "========================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$SCRIPT_DIR"

echo ""
echo "📍 Platform CLI directory: $CLI_DIR"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION"

# Проверка и установка pip
if ! python3 -m pip --version &> /dev/null; then
    echo "⚠️  pip не найден. Установка..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y python3-pip python3-venv
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3-pip
    else
        echo "❌ Не удалось установить pip. Установите его вручную."
        exit 1
    fi
fi

PIP_VERSION=$(python3 -m pip --version)
echo "✅ $PIP_VERSION"

# Проверка и установка pipx
if ! command -v pipx &> /dev/null; then
    echo "⚠️  pipx не найден. Установка..."
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    
    # Добавление pipx в PATH для текущей сессии
    export PATH="$HOME/.local/bin:$PATH"
    
    if ! command -v pipx &> /dev/null; then
        echo "❌ Не удалось установить pipx. Попробуйте вручную:"
        echo "   python3 -m pip install --user pipx"
        echo "   python3 -m pipx ensurepath"
        exit 1
    fi
fi

PIPX_VERSION=$(pipx --version)
echo "✅ pipx $PIPX_VERSION"

# Установка platform-cli
echo ""
echo "📦 Установка platform-cli..."

if pipx list | grep -q "platform-cli"; then
    echo "ℹ️  platform-cli уже установлен. Обновление..."
    pipx upgrade platform-cli
else
    pipx install "$CLI_DIR"
fi

echo ""
echo "✅ Установка завершена!"
echo ""

# Проверка установки
if command -v platform &> /dev/null; then
    echo "✅ platform CLI доступен"
    echo ""
    echo "Использование:"
    echo "  platform --help"
    echo "  platform list"
    echo "  platform new myapp public"
else
    echo "⚠️  platform не найден в PATH"
    echo ""
    echo "Добавьте ~/.local/bin в PATH:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Для постоянного добавления в ~/.bashrc:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
fi
