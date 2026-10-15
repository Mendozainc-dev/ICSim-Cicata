import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.style import Style

console = Console(width=100)
title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)


class FuzzingReporter:
    """Gestiona la generación de bitácoras CSV y reportes de texto de las pruebas de fuzzing."""

    def __init__(self, output_path: Optional[str] = None, log_dir: Optional[Path] = None):
        self.output_path = output_path
        if log_dir is None:
            self.log_dir = Path(__file__).resolve().parent.parent / "logs"
        else:
            self.log_dir = Path(log_dir)

        self._csv_file = None
        self._csv_writer = None

    def open_csv(self) -> None:
        """Abre el archivo CSV si fue especificado y escribe los encabezados."""
        if not self.output_path:
            return
        try:
            out_path = Path(self.output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._csv_file = open(self.output_path, "w", newline="", encoding="utf-8")
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(
                ["elapsed_s", "mode", "seed", "can_id", "dlc", "data_hex"]
            )
        except OSError as exc:
            console.print(f"[ERROR] No se pudo abrir el archivo CSV {self.output_path}: {exc}", style=error_style)
            self._csv_file = None
            self._csv_writer = None

    def record_frame(
        self,
        elapsed: float,
        mode: str,
        seed: Optional[int],
        can_id: int,
        dlc: int,
        data: bytes,
    ) -> None:
        """Registra una trama CAN enviada en el archivo CSV."""
        if self._csv_writer:
            self._csv_writer.writerow([
                f"{elapsed:.6f}",
                mode,
                seed,
                f"0x{can_id:03X}",
                dlc,
                data.hex(),
            ])

    def close_csv(self) -> None:
        """Cierra el archivo CSV de salida si está abierto."""
        if self._csv_file:
            try:
                self._csv_file.close()
            except OSError:
                pass
            finally:
                self._csv_file = None
                self._csv_writer = None

    def write_run_report(
        self,
        run_started_at: Optional[datetime],
        finished_at: datetime,
        elapsed: float,
        interface: str,
        mode: str,
        target_ids: List[int],
        delay: float,
        packet_limit: int,
        duration_limit: Optional[float],
        seed: Optional[int],
        corpus_count: int,
        stop_reason: str,
        total_sent: int,
        sent_by_id: Dict[int, int],
        last_frame: Any = None,
        last_error: Optional[str] = None,
    ) -> Optional[Path]:
        """Genera y guarda el reporte formal de la ejecución en logs/."""
        if run_started_at is None:
            return None

        filename = f"fuzz-{run_started_at.strftime('%Y%m%d-%H%M%S-%f')}.txt"
        report_path = self.log_dir / filename

        if last_error:
            conclusion = (
                f"La ejecución se detuvo con un error después de enviar {total_sent} tramas. "
                "Este registro no confirma por sí solo una vulnerabilidad ni su impacto."
            )
        elif total_sent:
            conclusion = (
                f"Se enviaron {total_sent} tramas y la ejecución terminó por: {stop_reason}. "
                "El envío no confirma por sí solo que el objetivo haya fallado o tenga una vulnerabilidad."
            )
        else:
            conclusion = (
                "No se enviaron tramas; no hay resultado de fuzzing que evaluar. "
                "Revisa la interfaz CAN y los parámetros de la ejecución."
            )

        rate = total_sent / elapsed if elapsed > 0 else 0

        lines = [
            "REPORTE DE EJECUCIÓN - FUZZER CAN",
            "=" * 38,
            f"Inicio: {run_started_at.isoformat(timespec='seconds')}",
            f"Fin: {finished_at.isoformat(timespec='seconds')}",
            f"Interfaz: {interface}",
            f"Modo: {mode}",
            f"IDs objetivo: {', '.join(f'0x{can_id:03X}' for can_id in target_ids)}",
            f"Delay configurado: {delay} s",
            f"Límite de tramas: {packet_limit or 'sin límite'}",
            f"Límite de duración: {duration_limit if duration_limit is not None else 'sin límite'} s",
            f"Semilla: {seed if seed is not None else 'no especificada'}",
            f"Tramas en corpus: {corpus_count if mode == 'mutate' else 'no aplica'}",
            f"CSV de salida: {self.output_path or 'no solicitado'}",
            "",
            "RESULTADO",
            f"Estado: {stop_reason}",
            f"Tramas enviadas: {total_sent}",
            f"Duración real: {elapsed:.3f} s",
            f"Tasa media: {rate:.2f} tramas/s",
            "Tramas por ID:",
        ]
        lines.extend(
            f"  0x{can_id:03X}: {count}"
            for can_id, count in sorted(sent_by_id.items())
        )
        if last_frame:
            frame_data_hex = last_frame.data.hex(" ").upper() if hasattr(last_frame, "data") else ""
            lines.append(
                f"Última trama: ID 0x{last_frame.arbitration_id:03X}, "
                f"DLC {last_frame.dlc}, datos {frame_data_hex}"
            )
        if last_error:
            lines.append(f"Error: {last_error}")
        lines.extend(["", "CONCLUSIÓN", conclusion, ""])

        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            report_path.write_text("\n".join(lines), encoding="utf-8")
            console.print(f"[FUZZER] Reporte guardado en: {report_path}", style=title_style)
            return report_path
        except OSError as exception:
            console.print(f"[ERROR] No se pudo guardar el reporte {report_path}: {exception}", style=error_style)
            return None

    @staticmethod
    def list_reports(log_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Busca y extrae metadatos resumidos de todos los reportes de fuzzing guardados en logs/."""
        target_dir = log_dir or (Path(__file__).resolve().parent.parent / "logs")
        if not target_dir.exists():
            return []

        reports = []
        for file in sorted(target_dir.glob("fuzz-*.txt"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                content = file.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                metadata: Dict[str, Any] = {
                    "path": file,
                    "filename": file.name,
                    "date": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "packets": "0",
                    "rate": "0 tramas/s",
                    "status": "Finalizado",
                }
                for line in lines:
                    if line.startswith("Inicio:"):
                        metadata["date"] = line.replace("Inicio:", "").strip()
                    elif line.startswith("Tramas enviadas:"):
                        metadata["packets"] = line.replace("Tramas enviadas:", "").strip()
                    elif line.startswith("Tasa media:"):
                        metadata["rate"] = line.replace("Tasa media:", "").strip()
                    elif line.startswith("Estado:"):
                        metadata["status"] = line.replace("Estado:", "").strip()
                reports.append(metadata)
            except Exception:
                continue

        return reports
