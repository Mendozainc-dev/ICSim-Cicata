from datetime import datetime
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

try:
    import can
except ImportError:
    can = None  # type: ignore

try:
    from rich.console import Console
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

from lang import translator

console = Console(width=100)
title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)
status_style = Style(color="cyan", bold=True)
success_style = Style(color="green", bold=True)

DEFAULT_IC_DESCRIPTIONS: Dict[int, Dict[str, Any]] = {
    0x244: {"description": "Velocímetro del tablero", "min_payload_len": 5, "expected_range": "0-260 km/h"},
    0x188: {"description": "Señales de giro (intermitentes)", "min_payload_len": 1, "expected_range": "0x00, 0x01, 0x02"},
    0x19B: {"description": "Seguros de puertas (4 puertas)", "min_payload_len": 3, "expected_range": "0x00 - 0x0F"},
    0x080: {"description": "Telemetría de motor / ECU", "min_payload_len": 2, "expected_range": "estándar"},
    0x110: {"description": "Sensor de transmisión / marcha", "min_payload_len": 2, "expected_range": "estándar"},
    0x133: {"description": "Estado de frenos y ABS", "min_payload_len": 2, "expected_range": "estándar"},
}


class CanCapture:
    """Fase 2: Captura pasiva de tramas benignas y mapeo de IDs de la red vehicular."""

    def __init__(self, interface: str = "vcan0", log_dir: Optional[Path] = None):
        self.interface = interface
        self.log_dir = log_dir or (Path(__file__).resolve().parent.parent / "logs")
        self.mapping_file = self.log_dir / "can_mapping.json"
        self.captured_frames: List[Any] = []
        self.grouped_stats: Dict[int, Dict[str, Any]] = {}

    def capture(
        self,
        duration: float = 5.0,
        max_packets: int = 0,
        bus: Optional[Any] = None,
        output_file: Optional[Path] = None,
    ) -> List[Any]:
        """Captura tramas de la interfaz SocketCAN durante un tiempo o límite de paquetes."""
        self.captured_frames.clear()
        start_time = time.monotonic()
        external_bus = bus is not None

        active_bus = bus
        if active_bus is None:
            if can is None:
                raise RuntimeError("python-can no está instalado")
            active_bus = can.Bus(channel=self.interface, interface="socketcan")

        out_path = output_file
        if out_path is None:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
            out_path = self.log_dir / f"capture-{timestamp_str}.log"

        out_handle = None
        try:
            out_handle = open(out_path, "w", encoding="utf-8")
            while True:
                elapsed = time.monotonic() - start_time
                if duration > 0 and elapsed >= duration:
                    break

                # Tiempo de espera corto para no bloquear la salida
                frame = active_bus.recv(timeout=0.2)
                if frame is not None:
                    self.captured_frames.append(frame)
                    # Formato candump estándar compatible con can.LogReader
                    ts = getattr(frame, "timestamp", None) or time.time()
                    data_hex = frame.data.hex().upper() if hasattr(frame, "data") else ""
                    log_line = f"({ts:.6f}) {self.interface} {frame.arbitration_id:03X}#{data_hex}\n"
                    out_handle.write(log_line)

                    if max_packets > 0 and len(self.captured_frames) >= max_packets:
                        break
        finally:
            if out_handle:
                out_handle.close()
            if not external_bus and active_bus:
                try:
                    active_bus.shutdown()
                except Exception:
                    pass

        self.group_by_id(duration=time.monotonic() - start_time)
        return self.captured_frames

    def group_by_id(self, duration: float = 1.0) -> Dict[int, Dict[str, Any]]:
        """Agrupa las tramas capturadas por Arbitration ID y calcula su frecuencia."""
        grouped: Dict[int, Dict[str, Any]] = {}
        dur = max(0.001, duration)

        existing_mapping = self.load_mapping()

        for frame in self.captured_frames:
            cid = frame.arbitration_id
            if cid not in grouped:
                desc = existing_mapping.get(str(cid), {}).get("description")
                if not desc:
                    desc = DEFAULT_IC_DESCRIPTIONS.get(cid, {}).get("description", "No identificado")

                grouped[cid] = {
                    "can_id": cid,
                    "hex_id": f"0x{cid:03X}",
                    "count": 0,
                    "frequency": 0.0,
                    "description": desc,
                    "sample_data": frame.data.hex(" ").upper() if hasattr(frame, "data") else "",
                    "dlc": frame.dlc if hasattr(frame, "dlc") else len(getattr(frame, "data", b"")),
                }
            grouped[cid]["count"] += 1

        for cid, stats in grouped.items():
            stats["frequency"] = round(stats["count"] / dur, 2)

        self.grouped_stats = grouped
        return grouped

    def save_mapping(self, mapping: Optional[Dict[str, Any]] = None, filepath: Optional[Path] = None) -> Path:
        """Guarda el diccionario de mapeo ID -> descripción y especificaciones en JSON."""
        target_path = filepath or self.mapping_file
        target_path.parent.mkdir(parents=True, exist_ok=True)

        data_to_save: Dict[str, Any] = {}
        # Cargar mapeo previo si existe
        if target_path.exists():
            try:
                data_to_save = json.loads(target_path.read_text(encoding="utf-8"))
            except Exception:
                data_to_save = {}

        source = mapping if mapping is not None else self.grouped_stats
        for key, val in source.items():
            str_key = str(key)
            if isinstance(val, dict):
                data_to_save[str_key] = {
                    "hex_id": val.get("hex_id", f"0x{int(key):03X}" if str(key).isdigit() else str_key),
                    "description": val.get("description", "Componente automotriz"),
                    "frequency": val.get("frequency", 0.0),
                    "expected_range": val.get("expected_range", "0-255"),
                }
            elif isinstance(val, str):
                data_to_save[str_key] = {
                    "hex_id": f"0x{int(key):03X}" if str(key).isdigit() else str_key,
                    "description": val,
                    "frequency": 0.0,
                    "expected_range": "0-255",
                }

        target_path.write_text(json.dumps(data_to_save, indent=2, ensure_ascii=False), encoding="utf-8")
        return target_path

    def load_mapping(self, filepath: Optional[Path] = None) -> Dict[str, Any]:
        """Carga el mapeo ID -> descripción desde JSON."""
        target_path = filepath or self.mapping_file
        if not target_path.exists():
            # Retornar mapeo por defecto de ICSim
            return {
                str(k): {"hex_id": f"0x{k:03X}", "description": v["description"], "expected_range": v["expected_range"]}
                for k, v in DEFAULT_IC_DESCRIPTIONS.items()
            }
        try:
            return json.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def run_interactive(self) -> None:
        """Flujo guiado por consola con rich para capturar tráfico y mapear IDs."""
        console.print(f"\n{translator.t('capture.title')}", style=title_style)
        console.print(f"{translator.t('capture.duration_prompt')} ", style=title_style, end="")

        try:
            dur_str = input().strip()
            duration = float(dur_str) if dur_str else 5.0
        except (ValueError, EOFError, KeyboardInterrupt):
            duration = 5.0

        msg_start = translator.t("capture.starting").format(interface=self.interface)
        console.print(f"\n[INFO] {msg_start}", style=status_style)

        try:
            self.capture(duration=duration)
        except Exception as exc:
            console.print(f"[ERROR] Error al capturar tramas: {exc}", style=error_style)
            return

        total = len(self.captured_frames)
        rate = total / duration if duration > 0 else 0
        msg_complete = translator.t("capture.complete").format(total=total, seconds=duration, rate=rate)
        console.print(f"\n[OK] {msg_complete}\n", style=success_style)

        if not self.grouped_stats:
            console.print("[AVISO] No se detectaron tramas activas en el bus.", style=status_style)
            return

        # Renderizar tabla con rich
        table = Table(title=translator.t("capture.table_title"), border_style="cyan")
        table.add_column(translator.t("capture.col_id"), justify="center", style="bold yellow")
        table.add_column(translator.t("capture.col_count"), justify="right", style="white")
        table.add_column(translator.t("capture.col_freq"), justify="right", style="cyan")
        table.add_column(translator.t("capture.col_desc"), justify="left", style="green")
        table.add_column(translator.t("capture.col_payload"), justify="left", style="white")

        for cid, stats in sorted(self.grouped_stats.items()):
            table.add_row(
                stats["hex_id"],
                str(stats["count"]),
                f"{stats['frequency']} Hz",
                stats["description"],
                stats["sample_data"],
            )

        console.print(table, justify="center")

        # Permitir al usuario anotar/modificar funciones de IDs
        while True:
            console.print(f"\n{translator.t('capture.edit_prompt')} ", style=title_style, end="")
            try:
                edit_id_str = input().strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not edit_id_str:
                break

            try:
                target_can_id = int(edit_id_str, 0)
            except ValueError:
                console.print("[ERROR] Formato de ID inválido. Usa hex (ej. 0x244) o decimal (ej. 580).", style=error_style)
                continue

            prompt_desc = translator.t("capture.desc_input").format(id=f"0x{target_can_id:03X}")
            console.print(f"{prompt_desc} ", style=title_style, end="")
            try:
                user_desc = input().strip()
            except (EOFError, KeyboardInterrupt):
                break

            if user_desc:
                if target_can_id in self.grouped_stats:
                    self.grouped_stats[target_can_id]["description"] = user_desc
                else:
                    self.grouped_stats[target_can_id] = {
                        "can_id": target_can_id,
                        "hex_id": f"0x{target_can_id:03X}",
                        "count": 0,
                        "frequency": 0.0,
                        "description": user_desc,
                        "sample_data": "-",
                        "dlc": 8,
                    }
                console.print(f"[OK] ID 0x{target_can_id:03X} mapeado a '{user_desc}'.", style=success_style)

        saved_path = self.save_mapping()
        msg_saved = translator.t("capture.saved").format(path=saved_path)
        console.print(f"\n[OK] {msg_saved}", style=success_style)
