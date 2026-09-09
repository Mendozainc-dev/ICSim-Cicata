#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.Proyecto-fuzz-cicata"
REPO="https://github.com/Mendozainc-dev/ICSim-Cicata.git"

if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -d "$SCRIPT_DIR/ICSim-master" ]]; then
    APP_DIR="$SCRIPT_DIR"
  fi
fi

if [[ "$APP_DIR" != "${SCRIPT_DIR:-}" ]]; then
  if [[ -d "$APP_DIR/.git" ]]; then
    echo "El proyecto ya fue instalado"
    echo "Se hara un pull para actualizar el proyecto"
    find "$APP_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    find "$APP_DIR" -type f -name '*.pyc' -delete 2>/dev/null || true
    git -C "$APP_DIR" pull --ff-only
  else
    echo "Descargando Proyecto-fuzz-cicata"
    git clone "$REPO" "$APP_DIR"
  fi
fi

cd "$APP_DIR"

ICSIM_DIR="$APP_DIR/ICSim-master"
REQUIREMENTS="$APP_DIR/main/requirements.txt"

install_system_packages() {
  echo "Instalando dependencias del sistema para Fedora (dnf)"

  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y \
      can-utils \
      python3-pip \
      python3-devel \
      SDL2-devel \
      SDL2_image-devel \
      gcc \
      make \
      meson
  else
    echo "Error: No se encontro dnf. Este script esta configurado exclusivamente para Fedora."
    exit 1
  fi
}

setup_vcan() {
  echo "Cargando y levantando la interfaz SocketCAN virtual (vcan0)"
  sudo modprobe vcan
  sudo ip link add dev vcan0 type vcan 2>/dev/null || true
  sudo ip link set up vcan0
}

compile_icsim() {
  if [[ ! -d "$ICSIM_DIR" ]]; then
    echo "No se encontro el simulador en $ICSIM_DIR"
    exit 1
  fi

  echo "Compilando el simulador ICSim con Meson"
  cd "$ICSIM_DIR"
  rm -rf builddir
  meson setup builddir
  meson compile -C builddir
  cd "$APP_DIR"
}

install_python_packages() {
  echo "Instalando librerias de Python de forma global (python3)"
  if sudo python3 -m pip install --upgrade pip &&
    sudo python3 -m pip install -r "$REQUIREMENTS"; then
    return 0
  fi

  echo "El entorno Python esta protegido; se instalara de forma global con --break-system-packages"
  sudo python3 -m pip install --upgrade pip --break-system-packages
  sudo python3 -m pip install --break-system-packages -r "$REQUIREMENTS"
}

verify_icsim() {
  local icsim_bin="$ICSIM_DIR/builddir/icsim"

  if [[ ! -x "$icsim_bin" ]]; then
    echo "La compilacion de ICSim fallo: no existe $icsim_bin"
    exit 1
  fi

  echo "Verificando la interfaz vcan0"
  ip link show vcan0

  echo "Lanzando ./icsim vcan0 en segundo plano para comprobar la compilacion"
  (
    cd "$ICSIM_DIR/builddir"
    ./icsim vcan0
  ) &
  local icsim_pid=$!
  sleep 2

  if kill -0 "$icsim_pid" 2>/dev/null; then
    echo "ICSim se ejecuto correctamente (PID $icsim_pid)"
    kill "$icsim_pid" 2>/dev/null || true
    wait "$icsim_pid" 2>/dev/null || true
  else
    wait "$icsim_pid" 2>/dev/null || true
    echo "No se pudo mantener ICSim en segundo plano (puede faltar DISPLAY). El binario compilado si existe."
  fi
}

create_global_command() {
  echo "Creando acceso directo global..."

  cat <<EOF | sudo tee /usr/local/bin/iov-fuzz >/dev/null
#!/usr/bin/env bash
sudo modprobe vcan 2>/dev/null || true
sudo ip link add dev vcan0 type vcan 2>/dev/null || true
sudo ip link set up vcan0 2>/dev/null || true

cd "$APP_DIR"
python3 "$APP_DIR/main/main.py" "\$@"
EOF

  sudo chmod +x /usr/local/bin/iov-fuzz
  echo "Comando global 'iov-fuzz' instalado correctamente."
}

install_system_packages
setup_vcan
compile_icsim
install_python_packages
verify_icsim
create_global_command

clear

python3 "$APP_DIR/main/main.py" </dev/tty
