#!/usr/bin/env bash
set -e

APP_DIR="$HOME/.Proyecto-fuzz-cicata"
REPO="https://github.com/Mendozainc-dev/ICSim-Cicata.git"

if [ -d "$APP_DIR/.git" ]; then
    echo "El proyecto ya fue instalado."
    echo "Actualizando..."
    git -C "$APP_DIR" pull --ff-only
else
    echo "Descargando Proyecto-fuzz-cicata"
    git clone "$REPO" "$APP_DIR"
fi

cd "$APP_DIR"

if [ ! -d ".venv" ]; then
    echo "Creando entorno virtual necesario para la ejecucion del proyecto"
    python3 -m venv .venv

    echo "Instalando dependencias..."
    .venv/bin/pip install -r requirements.txt
fi

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    .venv/Scripts/python main/main.py
else
    .venv/bin/python main/main.py
fi
