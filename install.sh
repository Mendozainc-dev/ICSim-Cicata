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

echo "Descargando ICSim desde ZIP (sin Git ni SSH)"
if [ ! -d "ICSim" ] || [ -z "$(ls -A ICSim 2>/dev/null)" ]; then
    tmp_zip="/tmp/ICSim.zip"
    curl -L "https://github.com/zynamics/ICSim/archive/refs/heads/master.zip" -o "$tmp_zip"
    rm -rf "ICSim"
    mkdir -p "ICSim"
    unzip -q "$tmp_zip" -d "/tmp/ICSim_extract"
    cp -R "/tmp/ICSim_extract/ICSim-master/"* "ICSim/"
    rm -rf "/tmp/ICSim_extract" "$tmp_zip"
fi

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