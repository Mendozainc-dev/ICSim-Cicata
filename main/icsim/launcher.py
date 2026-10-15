import os
from pathlib import Path
import subprocess
import time
from typing import List, Optional

from rich.console import Console
from rich.style import Style

from lang import translator

console = Console(width=100)
title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)
status_style = Style(color="cyan", bold=True)


class ICSimLauncher:
    """Gestiona el ciclo de vida de la interfaz vcan0 y los binarios de ICSim (icsim y controls)."""

    def __init__(self, repo_root: Optional[Path] = None):
        if repo_root is None:
            # main/icsim/launcher.py -> repo_root
            self.repo_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.repo_root = Path(repo_root)

        self.icsim_dir = self.repo_root / "ICSim-master"
        self.build_dir = self.icsim_dir / "builddir"
        self.icsim_bin = self.build_dir / "icsim"
        self.controls_bin = self.build_dir / "controls"
        self.setup_script = self.icsim_dir / "setup_vcan.sh"
        self.managed_processes: List[subprocess.Popen] = []

    def is_compiled(self) -> bool:
        """Verifica si los binarios icsim y controls existen y son ejecutables."""
        return (
            self.icsim_bin.exists()
            and os.access(self.icsim_bin, os.X_OK)
            and self.controls_bin.exists()
            and os.access(self.controls_bin, os.X_OK)
        )

    def compile_icsim(self) -> bool:
        """Compila el simulador ICSim usando Meson y Ninja."""
        if not self.icsim_dir.exists():
            console.print(f"[ERROR] No existe el directorio {self.icsim_dir}", style=error_style)
            return False

        console.print(translator.t("launcher.compiling"), style=status_style)
        try:
            # Si no existe builddir, inicializar con meson setup
            if not self.build_dir.exists():
                setup_res = subprocess.run(
                    ["meson", "setup", "builddir"],
                    cwd=str(self.icsim_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                if setup_res.returncode != 0:
                    console.print(f"[ERROR] Meson setup falló: {setup_res.stderr.strip()}", style=error_style)
                    return False

            # Compilar con meson compile
            compile_res = subprocess.run(
                ["meson", "compile", "-C", "builddir"],
                cwd=str(self.icsim_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if compile_res.returncode == 0 and self.is_compiled():
                console.print(translator.t("launcher.compile_success"), style=title_style)
                return True
            else:
                console.print(
                    f"[ERROR] Meson compile falló: {compile_res.stderr.strip()}",
                    style=error_style,
                )
                return False
        except Exception as exc:
            console.print(f"[ERROR] Excepción durante la compilación: {exc}", style=error_style)
            return False

    def is_vcan_up(self, interface: str = "vcan0") -> bool:
        """Comprueba si la interfaz virtual CAN existe y está activa."""
        try:
            res = subprocess.run(
                ["ip", "link", "show", interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            return res.returncode == 0
        except FileNotFoundError:
            return False

    def setup_vcan(self, interface: str = "vcan0") -> bool:
        """Levanta y configura la interfaz vcan0 usando setup_vcan.sh o comandos ip."""
        if self.is_vcan_up(interface):
            return True

        console.print(translator.t("launcher.vcan_starting"), style=status_style)

        # Si existe el script setup_vcan.sh, se reutiliza
        if self.setup_script.exists():
            res = subprocess.run(
                ["bash", str(self.setup_script)],
                cwd=str(self.icsim_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if res.returncode == 0 and self.is_vcan_up(interface):
                return True

        # Fallback ejecutando comandos directamente con sudo
        commands = [
            ["sudo", "modprobe", "can"],
            ["sudo", "modprobe", "vcan"],
            ["sudo", "ip", "link", "add", "dev", interface, "type", "vcan"],
            ["sudo", "ip", "link", "set", "up", interface],
        ]
        for cmd in commands:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        return self.is_vcan_up(interface)

    def prepare_environment(self, interface: str = "vcan0") -> bool:
        """Verifica y prepara vcan y los binarios antes de ejecutar."""
        # 1. Verificar vcan0
        if not self.setup_vcan(interface):
            console.print(
                f"[AVISO] No se pudo levantar {interface} automáticamente. Asegúrate de tener permisos sudo o vcan habilitado.",
                style=status_style,
            )

        # 2. Verificar binarios de ICSim
        if not self.is_compiled():
            console.print(f"\n{translator.t('launcher.not_compiled')}", style=error_style)
            console.print(f"{translator.t('launcher.compile_prompt')} ", style=title_style, end="")
            try:
                choice = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                return False

            if choice in ("s", "y", "si", "yes"):
                if not self.compile_icsim():
                    return False
            else:
                return False

        return True

    def start_simulators(self, interface: str = "vcan0") -> bool:
        """Lanza icsim y controls como subprocesos no bloqueantes apuntando a la interfaz vcan."""
        if not self.is_compiled():
            return False

        display = os.environ.get("DISPLAY")
        if not display:
            console.print(
                "[AVISO] Variable $DISPLAY no detectada. Los simuladores gráficos ICSim requieren un entorno gráfico X11/Wayland.",
                style=status_style,
            )

        console.print(f"\n{translator.t('launcher.icsim_starting')}", style=title_style)
        try:
            proc_icsim = subprocess.Popen(
                [str(self.icsim_bin), interface],
                cwd=str(self.build_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.managed_processes.append(proc_icsim)

            proc_controls = subprocess.Popen(
                [str(self.controls_bin), interface],
                cwd=str(self.build_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.managed_processes.append(proc_controls)

            time.sleep(0.5)
            console.print(f"{translator.t('launcher.icsim_running')}\n", style=status_style)
            return True
        except Exception as exc:
            console.print(f"[ERROR] No se pudieron iniciar los simuladores ICSim: {exc}", style=error_style)
            return False

    def stop_simulators(self) -> None:
        """Detiene única y limpiamente los procesos iniciados por esta instancia."""
        if not self.managed_processes:
            return

        for proc in self.managed_processes:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1.5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            except Exception:
                pass

        self.managed_processes.clear()
        console.print(f"\n{translator.t('launcher.icsim_stopped')}", style=status_style)
