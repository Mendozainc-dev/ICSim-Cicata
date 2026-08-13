#!/usr/bin/env bash
set -e

APP_DIR="$HOME/.Proyecto-fuzz-cicata"
REPO="https://github.com/Mendozainc-dev/ICSim-Cicata.git"

if [ -d "$APP_DIR/.git" ]; then
    echo "El proyecto ya fue instalado"
    echo "Se hara un pull para actualizar el proyecto"
    git -C "$APP_DIR" pull --ff-only
else
    echo "Descargando Proyecto-fuzz-cicata"
    git clone "$REPO" "$APP_DIR"
fi

cd "$APP_DIR"

echo "Inicializando submodulos del proyecto"
git submodule update --init --recursive

if [ ! -d ".venv" ]; then
    echo "Se creara un entorno virtual para el proyecto"
    python3 -m venv .venv
fi

echo "Verificando las dependencias del proyecto (requirements.txt)"
if [ -f ".venv/Scripts/python.exe" ]; then
    .venv/Scripts/python.exe -m pip install -r main/requirements.txt
    PYTHON=".venv/Scripts/python.exe"
else
    .venv/bin/python -m pip install -r main/requirements.txt
    PYTHON=".venv/bin/python"
fi

clear

"$PYTHON" main/main.py < /dev/tty