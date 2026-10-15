#!/usr/bin/env bash
# ==============================================================================
# Script de instalación para Debian, Ubuntu, Kali Linux, Linux Mint, Parrot OS
# Proyecto: ICSim-Cicata (Entorno virtualizado para evaluación de vulnerabilidades)
# ==============================================================================
set -euo pipefail

APP_DIR="$HOME/.Proyecto-fuzz-cicata"
REPO="https://github.com/Mendozainc-dev/ICSim-Cicata.git"
SCRIPT_DIR=""

if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -d "$SCRIPT_DIR/ICSim-master" && -d "$SCRIPT_DIR/main" ]]; then
    APP_DIR="$SCRIPT_DIR"
  fi
fi

if [[ "$APP_DIR" != "${SCRIPT_DIR:-}" ]]; then
  if [[ -d "$APP_DIR/.git" ]]; then
    echo "[INFO] El proyecto ya está presente en $APP_DIR. Actualizando repositorio..."
    find "$APP_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    find "$APP_DIR" -type f -name '*.pyc' -delete 2>/dev/null || true
    git -C "$APP_DIR" pull --ff-only || true
  else
    echo "[INFO] Clonando repositorio en $APP_DIR..."
    git clone "$REPO" "$APP_DIR"
  fi
fi

cd "$APP_DIR"

ICSIM_DIR="$APP_DIR/ICSim-master"
REQUIREMENTS="$APP_DIR/main/requirements.txt"
PYTHON_ENV="$APP_DIR/.venv"

wait_for_apt_lock() {
  local max_wait=40
  local waited=0
  while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1; do
    if [ $waited -eq 0 ]; then
      echo "[AVISO] apt o dpkg está bloqueado por otro proceso del sistema (actualizaciones automáticas en segundo plano)."
      echo "Esperando a que se libere /var/lib/dpkg/lock-frontend..."
    fi
    sleep 3
    waited=$((waited + 3))
    if [ $waited -ge $max_wait ]; then
      echo "[ERROR] El gestor de paquetes sigue bloqueado después de $max_wait segundos."
      echo "Comprueba qué proceso lo está usando con: ps aux | grep -E 'apt|dpkg'"
      echo "Una vez finalizado, vuelve a ejecutar el instalador."
      exit 1
    fi
  done
}

install_system_packages() {
  echo "[1/6] Instalando dependencias del sistema para Debian/Ubuntu/Kali (apt)..."
  if command -v apt-get >/dev/null 2>&1; then
    wait_for_apt_lock
    # Ignorar errores de repositorios externos rotos en apt-get update
    sudo apt-get update -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true || true
    wait_for_apt_lock
    sudo apt-get install -y \
      can-utils \
      curl \
      git \
      python3 \
      python3-pip \
      python3-venv \
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
    echo "[ERROR] No se encontró apt-get. Este script está diseñado para Debian, Ubuntu, Kali o derivados."
    exit 1
  fi
}

setup_vcan() {
  echo "[2/6] Configurando y levantando interfaz SocketCAN virtual (vcan0)..."
  sudo modprobe can 2>/dev/null || true
  sudo modprobe vcan 2>/dev/null || true
  sudo ip link add dev vcan0 type vcan 2>/dev/null || true
  sudo ip link set up vcan0 2>/dev/null || true
  ip link show vcan0 || echo "[AVISO] No se pudo verificar vcan0; se intentará levantar en tiempo de ejecución."
}

compile_icsim() {
  echo "[3/6] Compilando el simulador vehicular ICSim con Meson..."
  if [[ ! -d "$ICSIM_DIR" ]]; then
    echo "[ERROR] No se encontró la carpeta $ICSIM_DIR"
    exit 1
  fi

  # Asegurar que data/sample-can.log exista para que Meson no falle al regenerar
  mkdir -p "$ICSIM_DIR/data"
  if [[ ! -f "$ICSIM_DIR/data/sample-can.log" ]]; then
    echo "(1600000000.000001) vcan0 188#000000" > "$ICSIM_DIR/data/sample-can.log"
    echo "(1600000000.010002) vcan0 244#00000000" >> "$ICSIM_DIR/data/sample-can.log"
    echo "(1600000000.020003) vcan0 19B#000000" >> "$ICSIM_DIR/data/sample-can.log"
  fi

  cd "$ICSIM_DIR"
  if [[ ! -d "builddir" ]]; then
    meson setup builddir
  fi
  meson compile -C builddir
  cd "$APP_DIR"
}

install_python_packages() {
  echo "[4/6] Configurando entorno virtual de Python e instalando requirements.txt..."
  if [[ ! -d "$PYTHON_ENV" ]]; then
    python3 -m venv "$PYTHON_ENV"
  fi
  "$PYTHON_ENV/bin/python" -m pip install --upgrade pip
  "$PYTHON_ENV/bin/python" -m pip install -r "$REQUIREMENTS"
}

verify_installation() {
  echo "[5/6] Verificando compilación e integridad..."
  local icsim_bin="$ICSIM_DIR/builddir/icsim"
  local controls_bin="$ICSIM_DIR/builddir/controls"

  if [[ ! -x "$icsim_bin" ]]; then
    echo "[ERROR] Falló la compilación de ICSim: no existe $icsim_bin"
    exit 1
  fi

  if [[ ! -x "$controls_bin" ]]; then
    echo "[ERROR] Falló la compilación de Controls: no existe $controls_bin"
    exit 1
  fi
  echo "[OK] Binarios de ICSim y Controls verificados correctamente."
}

create_global_command() {
  echo "[6/6] Creando comando global 'iov-fuzz'..."
  cat <<EOF | sudo tee /usr/local/bin/iov-fuzz >/dev/null
#!/usr/bin/env bash
sudo modprobe can 2>/dev/null || true
sudo modprobe vcan 2>/dev/null || true
sudo ip link add dev vcan0 type vcan 2>/dev/null || true
sudo ip link set up vcan0 2>/dev/null || true

cd "$APP_DIR"
"$PYTHON_ENV/bin/python" "$APP_DIR/main/main.py" "\$@"
EOF

  sudo chmod +x /usr/local/bin/iov-fuzz
  echo "[OK] Comando 'iov-fuzz' instalado en /usr/local/bin/iov-fuzz."
}

# Ejecutar etapas
install_system_packages
setup_vcan
compile_icsim
install_python_packages
verify_installation
create_global_command

echo "================================================================="
echo " Instalación completada con éxito. Puedes iniciar la CLI con:"
echo "   iov-fuzz"
echo " o ejecutando directamente:"
echo "   $PYTHON_ENV/bin/python $APP_DIR/main/main.py"
echo "================================================================="

# Iniciar automáticamente si se ejecuta interactivamente en una terminal
if [[ -t 0 ]]; then
  "$PYTHON_ENV/bin/python" "$APP_DIR/main/main.py"
fi
