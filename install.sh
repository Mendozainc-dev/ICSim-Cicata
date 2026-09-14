#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.Proyecto-fuzz-cicata"
REPO="https://github.com/Mendozainc-dev/ICSim-Cicata.git"
SCRIPT_DIR=""

if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -d "$SCRIPT_DIR/ICSim-master" ]]; then
    APP_DIR="$SCRIPT_DIR"
  fi
fi

if [[ "$APP_DIR" != "${SCRIPT_DIR:-}" ]]; then
  if [[ -d "$APP_DIR/.git" ]]; then
    echo "El proyecto ya fue instalado"
    echo "Actualizando el proyecto con git pull"
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
VENV_DIR="$APP_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"

install_system_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "Instalando dependencias del sistema para Debian/Ubuntu (apt)"
    sudo apt-get update
    sudo apt-get install -y \
      can-utils \
      curl \
      gcc \
      git \
      iproute2 \
      kmod \
      libsdl2-dev \
      libsdl2-image-dev \
      make \
      meson \
      ninja-build \
      python3 \
      python3-dev \
      python3-pip \
      python3-venv
    return 0
  fi

  if command -v dnf >/dev/null 2>&1; then
    echo "Instalando dependencias del sistema para Fedora (dnf)"
    sudo dnf install -y \
      can-utils \
      curl \
      gcc \
      git \
      iproute \
      kmod \
      make \
      meson \
      ninja-build \
      python3 \
      python3-devel \
      python3-pip \
      SDL2-devel \
      SDL2_image-devel
    return 0
  fi

  echo "Error: no se encontro un gestor compatible. Este instalador soporta apt-get y dnf."
  exit 1
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
  if [[ ! -f "$REQUIREMENTS" ]]; then
    echo "No se encontro el archivo de requerimientos: $REQUIREMENTS"
    exit 1
  fi

  echo "Creando entorno virtual de Python en $VENV_DIR"
  python3 -m venv "$VENV_DIR"

  echo "Instalando librerias de Python en el entorno virtual"
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r "$REQUIREMENTS"
}

verify_icsim() {
  local icsim_bin="$ICSIM_DIR/builddir/icsim"
  local controls_bin="$ICSIM_DIR/builddir/controls"

  if [[ ! -x "$icsim_bin" ]]; then
    echo "La compilacion de ICSim fallo: no existe $icsim_bin"
    exit 1
  fi

  if [[ ! -x "$controls_bin" ]]; then
    echo "La compilacion de Controls fallo: no existe $controls_bin"
    exit 1
  fi

  echo "Verificando la interfaz vcan0"
  ip link show vcan0 >/dev/null

  echo "ICSim y Controls estan compilados correctamente."
}

open_simulator_terminal() {
  local title="$1"
  local command="$2"
  local log_file="$APP_DIR/${title// /_}.log"
  local run_command="cd '$ICSIM_DIR/builddir' && $command"

  if [[ -n "${DISPLAY:-}" ]] && command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title "$title" -- bash -lc "$run_command; exec bash" >/dev/null 2>&1 &
    return 0
  fi

  if [[ -n "${DISPLAY:-}" ]] && command -v konsole >/dev/null 2>&1; then
    konsole --new-tab -p "tabtitle=$title" -e bash -lc "$run_command; exec bash" >/dev/null 2>&1 &
    return 0
  fi

  if [[ -n "${DISPLAY:-}" ]] && command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal --title "$title" --command "bash -lc \"$run_command; exec bash\"" >/dev/null 2>&1 &
    return 0
  fi

  if [[ -n "${DISPLAY:-}" ]] && command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -lc "$run_command; exec bash" >/dev/null 2>&1 &
    return 0
  fi

  echo "No se encontro una terminal grafica compatible para $title. Ejecutando en segundo plano."
  echo "Log: $log_file"
  (
    cd "$ICSIM_DIR/builddir"
    bash -lc "$command"
  ) >"$log_file" 2>&1 &
}

start_icsim_simulators() {
  echo "Iniciando simuladores ICSim"
  open_simulator_terminal "ICSim" "./icsim vcan0"
  open_simulator_terminal "ICSim Controls" "./controls vcan0"
  sleep 1
}

run_main_menu() {
  clear || true

  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "No se encontro el entorno virtual en $PYTHON_BIN"
    echo "Ejecuta primero el instalador completo."
    exit 1
  fi

  if [[ -r /dev/tty ]]; then
    "$PYTHON_BIN" "$APP_DIR/main/main.py" "$@" </dev/tty
  else
    "$PYTHON_BIN" "$APP_DIR/main/main.py" "$@"
  fi
}

create_global_command() {
  echo "Creando acceso directo global..."

  cat <<EOF | sudo tee /usr/local/bin/iov-fuzz >/dev/null
#!/usr/bin/env bash
exec bash "$APP_DIR/install.sh" --run "\$@"
EOF

  sudo chmod +x /usr/local/bin/iov-fuzz
  echo "Comando global 'iov-fuzz' instalado correctamente."
}

if [[ "${1:-}" == "--run" ]]; then
  shift
  setup_vcan
  verify_icsim
  start_icsim_simulators
  run_main_menu "$@"
  exit 0
fi

install_system_packages
setup_vcan
compile_icsim
install_python_packages
verify_icsim
create_global_command
start_icsim_simulators
run_main_menu
