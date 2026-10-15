import sys
from pathlib import Path
from typing import Dict, Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

# Asegurar que el directorio de main/ esté en el sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import Configuration
from fuzzing import (
    CanCapture,
    FuzzingReporter,
    RunAnalyzer,
    RuleBasedIds,
    VulnerabilityReport,
)
from lang import translator
from menu.scripts_menu import menu_script
from scripts.commands import commands

console = Console(width=100)

title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)
option_style = Style(color="white", bold=True)
status_style = Style(color="cyan", bold=True)
success_style = Style(color="green", bold=True)
warning_style = Style(color="yellow", bold=True)


class MainApplication:
    """Orquestador principal de la CLI del entorno de evaluación de vulnerabilidades vehicular (Fases 1 a 5)."""

    def __init__(self):
        self.running = True
        self.reporter = FuzzingReporter()
        self.analyzer = RunAnalyzer()
        self.capture_tool = CanCapture()
        self.ids_tool = RuleBasedIds()

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
        """Visualizador interactivo de reportes y cálculo de métricas de impacto (Fase 4)."""
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

                        # Analizar si ya tiene métricas o permitir agregarlas
                        parsed = self.analyzer.parse_report_file(report_path)
                        if parsed["has_metrics"]:
                            console.print("\n[INFO] Esta corrida ya incluye métricas calculadas:", style=status_style)
                            self.analyzer.display_metrics(parsed)
                        else:
                            console.print(f"\n[bold]{translator.t('analysis.metrics_title')}[/bold]", style=title_style)
                            console.print(f"{translator.t('analysis.anomaly_prompt')} ", style=title_style, end="")
                            anom_input = input().strip()
                            if anom_input:
                                try:
                                    anom_count = int(anom_input)
                                    console.print(f"{translator.t('analysis.recovery_prompt')} ", style=title_style, end="")
                                    rec_input = input().strip()
                                    rec_lat = float(rec_input) if rec_input else 0.0

                                    notes = []
                                    if anom_count > 0:
                                        console.print(f"{translator.t('analysis.anomaly_notes_prompt')} ", style=title_style, end="")
                                        note_str = input().strip()
                                        if note_str:
                                            notes.append(note_str)

                                    self.analyzer.append_metrics_to_report(
                                        report_path=report_path,
                                        anomaly_count=anom_count,
                                        recovery_latency=rec_lat,
                                        notes=notes,
                                    )
                                    updated_parsed = self.analyzer.parse_report_file(report_path)
                                    self.analyzer.display_metrics(updated_parsed)
                                    console.print(f"\n[OK] {translator.t('analysis.metrics_appended')}", style=success_style)
                                except ValueError:
                                    console.print("[ERROR] Valor numérico inválido.", style=error_style)
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

    def show_network_mapping(self) -> None:
        """Ejecuta el módulo de captura pasiva y mapeo de IDs de la Fase 2."""
        commands.clearScreen()
        self.capture_tool.run_interactive()
        console.print("\n" + translator.t("info.back") + "\n", style=title_style, justify="center")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
        commands.clearScreen()

    def show_cwe_and_ids(self) -> None:
        """Fase 5: Clasificación contra CWE-20 / CWE-400 y propuesta de IDS automotriz."""
        commands.clearScreen()
        console.print(f"\n{translator.t('ids.title')}\n", style=title_style)

        reports = self.reporter.list_reports()
        if not reports:
            console.print(f"[AVISO] {translator.t('analysis.empty')}\n", style=status_style)
            console.print(translator.t("info.back") + "\n", style=title_style, justify="center")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass
            commands.clearScreen()
            return

        table = Table(title=translator.t("ids.select_report"), border_style="cyan")
        table.add_column("#", justify="center", style="bold yellow")
        table.add_column("Archivo", justify="left", style="white")
        table.add_column("Tramas", justify="right", style="green")
        table.add_column("Estado", justify="left", style="magenta")

        for idx, rep in enumerate(reports, 1):
            table.add_row(str(idx), rep["filename"], rep["packets"], rep["status"])

        console.print(table, justify="center")
        console.print("\nSeleccione el reporte a evaluar (o presione Enter para volver): ", style=title_style, end="")

        try:
            choice = input().strip()
        except (EOFError, KeyboardInterrupt):
            commands.clearScreen()
            return

        if not choice or not choice.isdigit():
            commands.clearScreen()
            return

        sel_idx = int(choice) - 1
        if not (0 <= sel_idx < len(reports)):
            commands.clearScreen()
            return

        report_path: Path = reports[sel_idx]["path"]
        parsed = self.analyzer.parse_report_file(report_path)

        # 1. Clasificación CWE
        commands.clearScreen()
        cwe_result = VulnerabilityReport.classify(parsed)
        console.print(f"\n[bold]{translator.t('ids.classification_title')}[/bold]\n", style=title_style)

        for item in cwe_result["classifications"]:
            panel_text = (
                f"[bold cyan]ID:[/bold cyan] {item['cwe_id']}\n"
                f"[bold cyan]Definición:[/bold cyan] {item['title']}\n"
                f"[bold cyan]Evidencia observada:[/bold cyan] {item['evidence']}\n\n"
                f"[bold green]Recomendación ISO/SAE 21434:[/bold green]\n{item['mitigation']}"
            )
            console.print(Panel(panel_text, title=item["cwe_id"], border_style="yellow" if item["cwe_id"] != "Sin clasificar" else "white"))

        # 2. Evaluación de reglas IDS automotriz
        console.print(f"\n[bold]{translator.t('ids.eval_title')}[/bold]", style=title_style)
        console.print(translator.t("ids.evaluating") + "\n", style=status_style)

        # Construir tramas representativas a partir del reporte para la evaluación del IDS
        class SyntheticFrame:
            def __init__(self, cid: int, data: bytes):
                self.arbitration_id = cid
                self.data = data
                self.dlc = len(data)

        frames_to_eval = []
        for cid, count in parsed["sent_by_id"].items():
            # Crear muestra de tramas
            sample_payload = b"\x00\x00\x00\x13\x88" if cid == 0x244 else b"\x00\x01\x02\x03"
            for _ in range(min(count, 50)):
                frames_to_eval.append(SyntheticFrame(cid, sample_payload))

        ids_result = self.ids_tool.evaluate_frames(
            frames=frames_to_eval,
            duration=parsed["duration"] if parsed["duration"] > 0 else 1.0,
        )
        self.ids_tool.display_results(ids_result)

        saved_ids_path = self.ids_tool.save_evaluation_report(ids_result)
        msg_saved = translator.t("ids.report_saved").format(path=saved_ids_path)
        console.print(f"[OK] {msg_saved}\n", style=success_style)

        console.print(translator.t("info.back") + "\n", style=title_style, justify="center")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
        commands.clearScreen()

    def show_menu(self) -> None:
        """Imprime las opciones principales del menú."""
        console.print("\n" + translator.t("menu.title") + ":", style=title_style, justify="full")
        console.print("\n1 " + translator.t("menu.option_1"), style=option_style)
        console.print("2 " + translator.t("menu.option_2"), style=option_style)
        console.print("3 " + translator.t("menu.option_3"), style=option_style)
        console.print("4 " + translator.t("menu.option_4"), style=option_style)
        console.print("5 " + translator.t("menu.option_5"), style=option_style)
        console.print("6 " + translator.t("menu.option_6"), style=option_style)
        console.print("7 " + translator.t("menu.option_7"), style=option_style)
        console.print("8 " + translator.t("menu.option_8") + "\n", style=option_style)

    def run(self) -> None:
        """Bucle principal de la CLI sin recursión."""
        commands.clearScreen()
        actions: Dict[str, Callable[[], None]] = {
            "1": self.show_project_info,
            "2": lambda: (commands.clearScreen(), menu_script()),
            "3": self.show_analysis,
            "4": self.show_network_mapping,
            "5": self.show_cwe_and_ids,
            "6": lambda: (commands.clearScreen(), commands.packageVersions()),
            "7": lambda: (commands.clearScreen(), Configuration().optionsMenu()),
        }

        while self.running:
            self.show_header()
            self.show_menu()

            try:
                option = input().strip()
            except (EOFError, KeyboardInterrupt):
                option = "8"

            if option in actions:
                actions[option]()
            elif option == "8" or option.lower() in ("q", "salir", "exit"):
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
