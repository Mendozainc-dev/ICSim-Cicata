import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Optional

from rich.console import Console
from rich.style import Style

console = Console(width=100)
title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)
status_style = Style(color="cyan", bold=True)


class Commands:
    """Ejecutor seguro de comandos del sistema con rutas absolutas y sin shell=True inseguro."""

    def __init__(self, repo_root: Optional[Path] = None):
        if repo_root is None:
            # main/scripts/commands.py -> repo_root
            self.repo_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.repo_root = Path(repo_root)

        self.main_dir = self.repo_root / "main"
        self.requirements_path = self.main_dir / "requirements.txt"
        self.icsim_dir = self.repo_root / "ICSim-master"
        self.build_dir = self.icsim_dir / "builddir"

    def clearScreen(self) -> None:
        """Limpia la terminal de forma compatible y segura."""
        if shutil.which("clear"):
            subprocess.run(["clear"], check=False)
        elif os.name == "nt":
            subprocess.run(["cls"], shell=True, check=False)
        else:
            print("\033[H\033[2J", end="")

    def packageVersions(self) -> None:
        """Muestra las versiones instaladas de Python, pip, curl y herramientas del entorno."""
        console.print("\n=== VERSIONES DEL ENTORNO ===", style=title_style)

        # 1. Python
        subprocess.run([sys.executable, "--version"], check=False)

        # 2. Pip
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"], check=False)
        except Exception:
            console.print("pip: no disponible en el intérprete actual", style=error_style)

        # 3. Curl
        if shutil.which("curl"):
            subprocess.run(["curl", "--version"], check=False)
        else:
            console.print("curl: no encontrado en el sistema", style=status_style)

        # 4. Herramientas CAN y compilación
        for tool in ("candump", "cansend", "meson", "ninja"):
            if shutil.which(tool):
                console.print(f"{tool}: disponible en el sistema", style=status_style)
            else:
                console.print(f"{tool}: no instalado", style=status_style)
        console.print("=============================\n", style=title_style)

    def installPackages(self) -> bool:
        """Instala las dependencias de Python y compila ICSim de forma robusta."""
        console.print("\n[CONFIG] Instalando librerías de Python desde requirements.txt...", style=status_style)
        if self.requirements_path.exists():
            pip_res = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(self.requirements_path)],
                check=False,
            )
            if pip_res.returncode != 0:
                console.print("[ERROR] Falló la instalación de requirements.txt con pip.", style=error_style)
        else:
            console.print(f"[ERROR] No se encontró {self.requirements_path}", style=error_style)

        # Compilar ICSim si existe
        if self.icsim_dir.exists():
            console.print("[CONFIG] Compilando ICSim con Meson...", style=status_style)
            if not self.build_dir.exists():
                subprocess.run(
                    ["meson", "setup", "builddir"],
                    cwd=str(self.icsim_dir),
                    check=False,
                )
            compile_res = subprocess.run(
                ["meson", "compile", "-C", "builddir"],
                cwd=str(self.icsim_dir),
                check=False,
            )
            if compile_res.returncode == 0:
                console.print("[CONFIG] ICSim compilado exitosamente.", style=title_style)
                return True
            else:
                console.print("[ERROR] Falló la compilación de ICSim.", style=error_style)
                return False
        return True


commands = Commands()
