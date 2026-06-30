#!/usr/bin/env bash
# Claude-Gram v2 Launcher
# Fork: claude-gram @ripcats by tg: @justidev

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Определение ОС
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            OS="debian"
        elif [ -f /etc/redhat-release ]; then
            OS="rhel"
        elif [ -f /etc/arch-release ]; then
            OS="arch"
        else
            OS="linux-generic"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
}

detect_os

# Проверка и установка Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${YELLOW}[!] Python 3 не найден. Устанавливаем системные пакеты...${NC}"
    case "$OS" in
        debian)
            sudo apt-get update -y
            sudo apt-get install -y python3 python3-pip python3-venv git curl sudo
            ;;
        rhel)
            sudo dnf install -y python3 python3-pip git curl sudo || sudo yum install -y python3 python3-pip git curl sudo
            ;;
        arch)
            sudo pacman -Sy --noconfirm python-pip git curl sudo
            ;;
        macos)
            if ! command -v brew >/dev/null 2>&1; then
                echo -e "${RED}❌ Homebrew не найден. Установите Homebrew для продолжения.${NC}"
                exit 1
            fi
            brew install python git curl
            ;;
        *)
            echo -e "${RED}❌ Автоматическая установка Python не поддерживается на вашей системе. Пожалуйста, установите python3 и pip3 вручную.${NC}"
            exit 1
            ;;
    esac
fi

# Запуск основного установщика на Python
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$INSTALL_DIR/install.py"
