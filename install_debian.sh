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
  echo "Instalando dependencias del sistema para Debian, Ubuntu, Kali o similares (apt)"

  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y \
      can-utils \
      curl \
      git \
      python3 \
      python3-pip \
      python3-dev \
      libsdl2-dev \
      libsdl2-image-dev \
      gcc \
      make \
      meson \
      ninja-build \
      iproute2 \
      kmod
  else
    echo "Error: No se encontro apt-get. Este script es para Debian, Ubuntu, Kali o sistemas similares."
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
  ip link show vcan0
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

open_simulator_terminal() {
  local title="$1"
  local command="$2"
  local log_file="$APP_DIR/${title// /_}.log"
  local run_command="cd '$ICSIM_DIR/builddir' && $command"

  if [[ -n "${DISPLAY:-}" ]] && command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title "$title" -- bash -lc "$run_command; exec bash" >/dev/null 2>&1 &
  elif [[ -n "${DISPLAY:-}" ]] && command -v konsole >/dev/null 2>&1; then
    konsole --new-tab -p "tabtitle=$title" -e bash -lc "$run_command; exec bash" >/dev/null 2>&1 &
  elif [[ -n "${DISPLAY:-}" ]] && command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal --title "$title" --command "bash -lc \"$run_command; exec bash\"" >/dev/null 2>&1 &
  elif [[ -n "${DISPLAY:-}" ]] && command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -lc "$run_command; exec bash" >/dev/null 2>&1 &
  else
    echo "No se encontro una terminal grafica compatible. Ejecutando $title en segundo plano."
    echo "Log: $log_file"
    (
      cd "$ICSIM_DIR/builddir"
      bash -lc "$command"
    ) >"$log_file" 2>&1 &
  fi
}

start_icsim_simulators() {
  echo "Iniciando simuladores ICSim"
  open_simulator_terminal "ICSim" "./icsim vcan0"
  open_simulator_terminal "ICSim Controls" "./controls vcan0"
  sleep 1
}

install_system_packages
setup_vcan
compile_icsim
install_python_packages
verify_icsim
create_global_command
start_icsim_simulators

clear

python3 "$APP_DIR/main/main.py" </dev/tty
