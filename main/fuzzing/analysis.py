import csv
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.style import Style
    from rich.table import Table
except ImportError:
    class Style:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class Console:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

        def print(self, *args, **kwargs):
            end = kwargs.get("end", "\n")
            print(*(str(a) for a in args), end=end)

    class Table:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

        def add_column(self, *args, **kwargs):
            pass

        def add_row(self, *args, **kwargs):
            pass

    class Panel:  # type: ignore
        def __init__(self, content, *args, **kwargs):
            self.content = content

        def __str__(self):
            return str(self.content)

from lang import translator

console = Console(width=100)
title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)
status_style = Style(color="cyan", bold=True)
success_style = Style(color="green", bold=True)


class RunAnalyzer:
    """Fase 4: Análisis de impacto, telemetría de fallos y métricas de resiliencia."""

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or (Path(__file__).resolve().parent.parent / "logs")

    def parse_report_file(self, report_path: Path) -> Dict[str, Any]:
        """Extrae la información estructurada de un reporte de fuzzing existente."""
        if not report_path.exists():
            raise FileNotFoundError(f"No existe el reporte: {report_path}")

        content = report_path.read_text(encoding="utf-8", errors="replace")
        lines = [line.strip() for line in content.splitlines()]

        data: Dict[str, Any] = {
            "path": report_path,
            "filename": report_path.name,
            "total_sent": 0,
            "duration": 0.0,
            "rate": 0.0,
            "status": "Finalizado",
            "start_time": "",
            "end_time": "",
            "mode": "random",
            "sent_by_id": {},
            "raw_content": content,
            "has_metrics": "ANÁLISIS DE IMPACTO Y MÉTRICAS (FASE 4)" in content,
            "anomaly_count": 0,
            "anomaly_rate": 0.0,
            "recovery_latency": 0.0,
            "anomaly_notes": [],
        }

        in_ids_section = False
        in_metrics_section = False

        for line in lines:
            if line.startswith("Inicio:"):
                data["start_time"] = line.replace("Inicio:", "").strip()
            elif line.startswith("Fin:"):
                data["end_time"] = line.replace("Fin:", "").strip()
            elif line.startswith("Modo:"):
                data["mode"] = line.replace("Modo:", "").strip()
            elif line.startswith("Estado:"):
                data["status"] = line.replace("Estado:", "").strip()
            elif line.startswith("Tramas enviadas:"):
                try:
                    data["total_sent"] = int(line.replace("Tramas enviadas:", "").strip())
                except ValueError:
                    data["total_sent"] = 0
            elif line.startswith("Duración real:"):
                match = re.search(r"([\d\.]+)", line)
                if match:
                    data["duration"] = float(match.group(1))
            elif line.startswith("Tasa media:"):
                match = re.search(r"([\d\.]+)", line)
                if match:
                    data["rate"] = float(match.group(1))
            elif line == "Tramas por ID:":
                in_ids_section = True
                continue
            elif in_ids_section and line.startswith("0x"):
                parts = line.split(":")
                if len(parts) == 2:
                    try:
                        cid = int(parts[0].strip(), 16)
                        data["sent_by_id"][cid] = int(parts[1].strip())
                    except ValueError:
                        pass
            elif line == "ANÁLISIS DE IMPACTO Y MÉTRICAS (FASE 4)":
                in_ids_section = False
                in_metrics_section = True
            elif in_metrics_section:
                if line.startswith("Marcadores de anomalías visuales:"):
                    try:
                        data["anomaly_count"] = int(line.split(":")[-1].strip())
                    except ValueError:
                        pass
                elif line.startswith("Tasa de anomalías detectadas:"):
                    match = re.search(r"([\d\.]+)%", line)
                    if match:
                        data["anomaly_rate"] = float(match.group(1))
                elif line.startswith("Latencia de recuperación de la ECU:"):
                    match = re.search(r"([\d\.]+)", line)
                    if match:
                        data["recovery_latency"] = float(match.group(1))
            elif line.startswith("CONCLUSIÓN"):
                in_ids_section = False

        return data

    def compute_metrics(
        self,
        total_sent: int,
        anomaly_count: int,
        recovery_latency: float,
    ) -> Dict[str, Any]:
        """Calcula las métricas de evaluación de la Fase 4 del documento."""
        total = max(0, total_sent)
        anomalies = max(0, anomaly_count)
        latency = max(0.0, float(recovery_latency))

        anomaly_rate = (anomalies / total * 100.0) if total > 0 else 0.0

        return {
            "total_sent": total,
            "anomaly_count": anomalies,
            "anomaly_rate": round(anomaly_rate, 2),
            "recovery_latency": round(latency, 2),
        }

    def append_metrics_to_report(
        self,
        report_path: Path,
        anomaly_count: int,
        recovery_latency: float,
        notes: Optional[List[str]] = None,
    ) -> bool:
        """Agrega la sección de métricas de la Fase 4 al final del reporte .txt sin alterar lo previo."""
        if not report_path.exists():
            return False

        content = report_path.read_text(encoding="utf-8", errors="replace")
        parsed = self.parse_report_file(report_path)
        metrics = self.compute_metrics(
            total_sent=parsed["total_sent"],
            anomaly_count=anomaly_count,
            recovery_latency=recovery_latency,
        )

        section_lines = [
            "",
            "ANÁLISIS DE IMPACTO Y MÉTRICAS (FASE 4)",
            "-" * 38,
            f"Marcadores de anomalías visuales: {metrics['anomaly_count']}",
            f"Tasa de anomalías detectadas: {metrics['anomaly_rate']:.2f}%",
            f"Latencia de recuperación de la ECU: {metrics['recovery_latency']:.2f} s",
        ]

        if metrics["anomaly_count"] == 0:
            section_lines.append("Observaciones: 0 anomalías marcadas por el usuario en esta corrida.")
        else:
            obs = ", ".join(notes) if notes else "Anomalías visuales registradas en los indicadores de tablero."
            section_lines.append(f"Observaciones: {obs}")

        # Si ya contenía una sección previa de Fase 4, reemplazarla; de lo contrario añadirla al final
        if "ANÁLISIS DE IMPACTO Y MÉTRICAS (FASE 4)" in content:
            parts = content.split("ANÁLISIS DE IMPACTO Y MÉTRICAS (FASE 4)")
            base_content = parts[0].rstrip()
            new_content = base_content + "\n" + "\n".join(section_lines) + "\n"
        else:
            new_content = content.rstrip() + "\n" + "\n".join(section_lines) + "\n"

        try:
            report_path.write_text(new_content, encoding="utf-8")
            return True
        except OSError as exc:
            console.print(f"[ERROR] No se pudo actualizar el reporte {report_path}: {exc}", style=error_style)
            return False

    def display_metrics(self, data: Dict[str, Any]) -> None:
        """Renderiza las métricas y el panel de impacto con rich."""
        table = Table(title=translator.t("analysis.metrics_title"), border_style="green")
        table.add_column("Métrica de Evaluación", style="bold white")
        table.add_column("Valor Obtenido", justify="right", style="bold cyan")
        table.add_column("Significado Técnico (Fase 4)", style="white")

        table.add_row(
            "Vectores de Fuzzing Enviados",
            str(data["total_sent"]),
            "Total de tramas inyectadas en la interfaz vcan0",
        )
        table.add_row(
            "Anomalías Físicas/Visuales",
            str(data["anomaly_count"]),
            "Eventos de descalibración, trabado o parpadeo errático observados",
        )
        table.add_row(
            translator.t("analysis.anomaly_rate"),
            f"{data['anomaly_rate']:.2f}%",
            "(Anomalías / Total Vectores) x 100",
        )
        table.add_row(
            translator.t("analysis.recovery_latency"),
            f"{data['recovery_latency']:.2f} s",
            "Tiempo desde el cese del ataque hasta estabilización normal",
        )

        console.print(table, justify="center")
