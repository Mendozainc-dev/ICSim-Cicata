import sys
from pathlib import Path
from typing import Dict, Callable

from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

# Asegurar que el directorio de main/ esté en el sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import Configuration
from fuzzing.reporting import FuzzingReporter
from lang import translator
from menu.scripts_menu import menu_script
from scripts.commands import commands

console = Console(width=100)

title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)
option_style = Style(color="white", bold=True)
status_style = Style(color="cyan", bold=True)


class MainApplication:
    """Orquestador principal de la CLI del entorno de evaluación de vulnerabilidades vehicular."""

    def __init__(self):
        self.running = True
        self.reporter = FuzzingReporter()

    def show_header(self) -> None:
        """Muestra el banner de bienvenida y la descripción del proyecto."""
        table = Table(title="\n", show_header=True, header_style="bold white", border_style="white")
        table.add_column(translator.t("project.title"), justify="full", style=title_style, no_wrap=False)
        table.add_row(translator.t("project.description"))
        console.print(table, justify="center")

    def show_project_info(self) -> None:
        """Muestra la información técnica detallada del proyecto."""
        commands.clearScreen()
        info = "\n\n".join([
            translator.t("project.description"),
            translator.t("info.goal.description"),
            translator.t("info.environment.description"),
            translator.t("info.components.description"),
            translator.t("info.usage.description"),
            translator.t("info.author.description"),
        ])

        table = Table(title="\n", show_header=True, header_style="bold white", border_style="white")
        table.add_column(translator.t("project.title"), justify="full", style=title_style, no_wrap=False)
        table.add_row(info)
        console.print(table, justify="center")

        console.print("\n" + translator.t("info.back") + "\n", style=title_style, justify="center")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
        commands.clearScreen()

    def show_analysis(self) -> None:
        """Visualizador interactivo de resultados y reportes de vulnerabilidades detectadas."""
        commands.clearScreen()
        while True:
            reports = self.reporter.list_reports()
            console.print("\n" + translator.t("project.analysis") + "\n", style=title_style)

            if not reports:
                console.print(f"[AVISO] {translator.t('analysis.empty')}\n", style=status_style)
                console.print(translator.t("info.back") + "\n", style=title_style, justify="center")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    pass
                commands.clearScreen()
                return

            table = Table(title=translator.t("analysis.reports_title"), border_style="cyan")
            table.add_column(translator.t("analysis.col_id"), justify="center", style="bold yellow")
            table.add_column(translator.t("analysis.col_date"), justify="center", style="white")
            table.add_column(translator.t("analysis.col_file"), justify="left", style="cyan")
            table.add_column(translator.t("analysis.col_packets"), justify="right", style="green")
            table.add_column(translator.t("analysis.col_rate"), justify="right", style="white")
            table.add_column(translator.t("analysis.col_status"), justify="left", style="magenta")

            for idx, rep in enumerate(reports, 1):
                table.add_row(
                    str(idx),
                    rep["date"],
                    rep["filename"],
                    rep["packets"],
                    rep["rate"],
                    rep["status"],
                )

            console.print(table, justify="center")
            console.print("\n" + translator.t("analysis.select") + " ", style=title_style, end="")

            try:
                choice = input().strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not choice:
                break

            if choice.isdigit():
                sel_idx = int(choice) - 1
                if 0 <= sel_idx < len(reports):
                    selected_report = reports[sel_idx]
                    report_path: Path = selected_report["path"]
                    commands.clearScreen()
                    try:
                        content = report_path.read_text(encoding="utf-8", errors="replace")
                        console.print(Panel(content, title=f"[bold cyan]{report_path.name}[/bold cyan]", border_style="green"))
                    except OSError as err:
                        console.print(f"[ERROR] No se pudo leer el archivo: {err}", style=error_style)
                    console.print("\n" + translator.t("info.back") + "\n", style=title_style, justify="center")
                    try:
                        input()
                    except (EOFError, KeyboardInterrupt):
                        pass
                    commands.clearScreen()
                else:
                    console.print("\nNúmero fuera de rango.\n", style=error_style)
            else:
                break

        commands.clearScreen()

    def show_menu(self) -> None:
        """Imprime las opciones principales del menú."""
        console.print("\n" + translator.t("menu.title") + ":", style=title_style, justify="full")
        console.print("\n1 " + translator.t("menu.option_1"), style=option_style)
        console.print("2 " + translator.t("menu.option_2"), style=option_style)
        console.print("3 " + translator.t("menu.option_3"), style=option_style)
        console.print("4 " + translator.t("menu.option_4"), style=option_style)
        console.print("5 " + translator.t("menu.option_5"), style=option_style)
        console.print("6 " + translator.t("menu.option_6") + "\n", style=option_style)

    def run(self) -> None:
        """Bucle principal de la CLI sin recursión."""
        commands.clearScreen()
        actions: Dict[str, Callable[[], None]] = {
            "1": self.show_project_info,
            "2": lambda: (commands.clearScreen(), menu_script()),
            "3": self.show_analysis,
            "4": lambda: (commands.clearScreen(), commands.packageVersions()),
            "5": lambda: (commands.clearScreen(), Configuration().optionsMenu()),
        }

        while self.running:
            self.show_header()
            self.show_menu()

            try:
                option = input().strip()
            except (EOFError, KeyboardInterrupt):
                option = "6"

            if option in actions:
                actions[option]()
            elif option == "6" or option.lower() in ("q", "salir", "exit"):
                commands.clearScreen()
                console.print("\n" + translator.t("project.exit") + "\n", style=title_style, justify="center")
                self.running = False
                break
            else:
                commands.clearScreen()
                console.print(translator.t("menu.invalid") + "\n", style=error_style)


def Main() -> None:
    """Función de entrada principal."""
    app = MainApplication()
    app.run()


if __name__ == "__main__":
    Main()
