from typing import Optional

from rich.console import Console
from rich.style import Style

from fuzzing import RandomCANFuzzer
from icsim import ICSimLauncher
from lang import translator

console = Console(width=100)
title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)
option_style = Style(color="white", bold=True)


class ScriptsMenu:
    """Menú interactivo para ejecutar pruebas de fuzzing junto con el simulador ICSim."""

    def __init__(self, launcher: Optional[ICSimLauncher] = None):
        self.launcher = launcher or ICSimLauncher()

    def run_fuzzing_with_simulators(self, max_packets: int = 0) -> None:
        """Prepara vcan0, arranca ICSim + Controls, corre el fuzzer y asegura la limpieza al terminar."""
        # 1. Preparar vcan0 y verificar compilación de ICSim
        env_ready = self.launcher.prepare_environment()
        if not env_ready:
            console.print("[AVISO] Continuando solo con el fuzzer de consola...", style=title_style)

        # 2. Iniciar procesos del simulador si está compilado
        simulators_started = False
        if self.launcher.is_compiled():
            simulators_started = self.launcher.start_simulators()

        # 3. Ejecutar el fuzzer en el proceso principal
        try:
            fuzzer = RandomCANFuzzer()
            fuzzer.run(max_packets=max_packets)
        except KeyboardInterrupt:
            console.print("\n[FUZZER] Prueba interrumpida por el usuario.", style=title_style)
        except Exception as exc:
            console.print(f"\n[ERROR] Error durante la ejecución del fuzzer: {exc}", style=error_style)
        finally:
            # 4. Detener únicamente los simuladores lanzados por este flujo
            if simulators_started:
                self.launcher.stop_simulators()

        console.print("\n" + translator.t("info.back") + "\n", style=title_style, justify="center")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass

    def display(self) -> None:
        """Bucle principal del submenú de scripts sin recursión."""
        while True:
            console.print("\n" + translator.t("menu.script_title") + ":", style=title_style, justify="full")
            console.print("\n1 " + translator.t("first.script"), style=option_style)
            console.print("2 " + translator.t("second.script"), style=option_style)
            console.print("3 " + translator.t("third.script"), style=option_style)
            console.print("4 " + translator.t("menu.script_back") + "\n", style=option_style)

            try:
                option = input().strip()
            except (EOFError, KeyboardInterrupt):
                break

            if option == "1":
                self.run_fuzzing_with_simulators(max_packets=0)
            elif option == "2":
                self.run_fuzzing_with_simulators(max_packets=1000)
            elif option == "3":
                self.run_fuzzing_with_simulators(max_packets=10000)
            elif option == "4" or option.lower() in ("q", "salir", "exit", "volver"):
                break
            else:
                console.print("\n" + translator.t("menu.invalid_option") + "\n", style=error_style, justify="full")


def menu_script() -> None:
    """Función de compatibilidad con el código original."""
    menu = ScriptsMenu()
    menu.display()
