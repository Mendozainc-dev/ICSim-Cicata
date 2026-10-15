from datetime import datetime
from pathlib import Path
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
warning_style = Style(color="yellow", bold=True)

# Umbrales por defecto explícitos (configurables por el usuario)
DEFAULT_MAX_FREQ_HZ = 80.0       # Más de 80 tramas/s para un mismo ID es anómalo
DEFAULT_WINDOW_SECONDS = 1.0     # Ventana de tiempo de evaluación
DEFAULT_MAX_SPEED_KMH = 260.0    # Límite de escala del velocímetro


class VulnerabilityReport:
    """Fase 5: Clasificación técnica de vulnerabilidades contra el catálogo CWE y directrices ISO/SAE 21434."""

    @staticmethod
    def classify(
        run_data: Dict[str, Any],
        mapping: Optional[Dict[str, Any]] = None,
        flood_threshold_rate: float = 120.0,
    ) -> Dict[str, Any]:
        """Clasifica las fallas observadas en una corrida bajo reglas explícitas de CWE-20 o CWE-400."""
        anomalies = run_data.get("anomaly_count", 0)
        rate = run_data.get("rate", 0.0)
        total_sent = run_data.get("total_sent", 0)
        notes = " ".join(run_data.get("anomaly_notes", [])).lower()

        matched_cwes: List[Dict[str, str]] = []

        # Regla 1: CWE-400 (Uncontrolled Resource Consumption)
        # Se activa si hubo anomalías en condiciones de alta tasa de inyección (flood/inundación)
        if anomalies > 0 and (rate >= flood_threshold_rate or total_sent >= 5000):
            matched_cwes.append({
                "cwe_id": "CWE-400",
                "title": translator.t("ids.cwe400_title"),
                "description": translator.t("ids.cwe400_desc"),
                "evidence": f"Tasa de inyección: {rate:.1f} tramas/s, volumen total: {total_sent} tramas.",
                "mitigation": (
                    "ISO/SAE 21434 Sección 9: Implementar limitación de tasa (Rate Limiting) "
                    "en el Gateway automotriz y filtrado de colas en el controlador CAN."
                ),
            })

        # Regla 2: CWE-20 (Improper Input Validation)
        # Se activa si hubo anomalías asociadas a datos fuera de rango o descalibración física
        data_keywords = ["aguja", "descalibr", "rango", "payload", "puerta", "luz", "valor", "corrup"]
        has_data_anomaly = any(kw in notes for kw in data_keywords) or (anomalies > 0 and rate < flood_threshold_rate)

        if anomalies > 0 and has_data_anomaly:
            matched_cwes.append({
                "cwe_id": "CWE-20",
                "title": translator.t("ids.cwe20_title"),
                "description": translator.t("ids.cwe20_desc"),
                "evidence": "Anomalías reportadas por valores fuera de especificación en el tablero simulado.",
                "mitigation": (
                    "ISO/SAE 21434 Sección 10: Validación estricta de rangos (Range Checking) "
                    "en la capa de aplicación de la ECU receptora antes de actualizar indicadores."
                ),
            })

        if not matched_cwes:
            matched_cwes.append({
                "cwe_id": "Sin clasificar",
                "title": translator.t("ids.unclassified"),
                "description": "No se registraron anomalías suficientes para confirmar debilidades de seguridad.",
                "evidence": f"Anomalías marcadas: {anomalies}.",
                "mitigation": "Mantener monitoreo pasivo de telemetría.",
            })

        return {
            "run_filename": run_data.get("filename", "desconocido"),
            "classifications": matched_cwes,
            "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        }


class RuleBasedIds:
    """Fase 5: Sistema de Detección de Intrusos (IDS) basado en reglas explícitas según ISO/SAE 21434."""

    def __init__(
        self,
        max_freq_hz: float = DEFAULT_MAX_FREQ_HZ,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        authorized_ids: Optional[List[int]] = None,
        max_speed_kmh: float = DEFAULT_MAX_SPEED_KMH,
        log_dir: Optional[Path] = None,
    ):
        self.max_freq_hz = max_freq_hz
        self.window_seconds = window_seconds
        # IDs conocidos por defecto en ICSim si no se especifica mapeo
        self.authorized_ids = authorized_ids if authorized_ids is not None else [0x080, 0x110, 0x188, 0x244, 0x133, 0x19B]
        self.max_speed_kmh = max_speed_kmh
        self.log_dir = log_dir or (Path(__file__).resolve().parent.parent / "logs")

    def evaluate_frames(
        self,
        frames: List[Any],
        duration: float = 1.0,
    ) -> Dict[str, Any]:
        """Evalúa una lista de tramas recibidas contra las 3 reglas del IDS automotriz."""
        dur = max(0.001, duration)
        total_frames = len(frames)
        counts_by_id: Dict[int, int] = {}
        alerts: List[Dict[str, Any]] = []

        # Conteo por ID para la regla 1
        for frame in frames:
            cid = frame.arbitration_id
            counts_by_id[cid] = counts_by_id.get(cid, 0) + 1

            # Regla 2: Carga útil fuera de rango esperado
            # En ICSim, ID 0x244 velocímetro bytes 3 y 4: ((b3 << 8) + b4) / 100 km/h
            if cid == 0x244 and hasattr(frame, "data") and len(frame.data) >= 5:
                speed = ((frame.data[3] << 8) + frame.data[4]) / 100.0
                if speed > self.max_speed_kmh or speed < 0:
                    alerts.append({
                        "rule": "Regla 2: Carga útil fuera de rango",
                        "can_id": f"0x{cid:03X}",
                        "severity": "ALTA",
                        "detail": f"Velocidad calculada ({speed:.1f} km/h) excede el máximo permitido ({self.max_speed_kmh} km/h).",
                    })

            # Regla 3: ID no autorizado (Whitelisting)
            if cid not in self.authorized_ids:
                alerts.append({
                    "rule": "Regla 3: ID no autorizado en la red",
                    "can_id": f"0x{cid:03X}",
                    "severity": "CRÍTICA",
                    "detail": f"Arbitration ID 0x{cid:03X} no pertenece a la lista blanca de la red vehicular.",
                })

        # Regla 1: Frecuencia anómala (Tasa de tramas superior al umbral en la ventana de tiempo)
        for cid, count in counts_by_id.items():
            freq = count / dur
            if freq > self.max_freq_hz:
                alerts.append({
                    "rule": "Regla 1: Frecuencia anómala (Posible Inundación / DoS)",
                    "can_id": f"0x{cid:03X}",
                    "severity": "ALTA",
                    "detail": f"Frecuencia observada {freq:.1f} Hz supera el umbral configurado de {self.max_freq_hz} Hz.",
                })

        # Agrupar estadísticas de alertas
        rule1_count = sum(1 for a in alerts if "Regla 1" in a["rule"])
        rule2_count = sum(1 for a in alerts if "Regla 2" in a["rule"])
        rule3_count = sum(1 for a in alerts if "Regla 3" in a["rule"])

        return {
            "total_frames": total_frames,
            "duration": dur,
            "alerts": alerts,
            "alerts_count": len(alerts),
            "rule1_count": rule1_count,
            "rule2_count": rule2_count,
            "rule3_count": rule3_count,
            "thresholds": {
                "max_freq_hz": self.max_freq_hz,
                "window_seconds": self.window_seconds,
                "max_speed_kmh": self.max_speed_kmh,
                "authorized_ids": [f"0x{i:03X}" for i in self.authorized_ids],
            },
        }

    def save_evaluation_report(self, result: Dict[str, Any], filepath: Optional[Path] = None) -> Path:
        """Guarda el informe formal de evaluación del IDS en logs/ids_evaluation_*.txt."""
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        target_path = filepath or (self.log_dir / f"ids_evaluation_{timestamp_str}.txt")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        lines = [
            "REPORTE DE EVALUACIÓN DE IDS AUTOMOTRIZ (ISO/SAE 21434)",
            "=" * 56,
            f"Fecha de evaluación: {datetime.now().isoformat(timespec='seconds')}",
            f"Total de tramas evaluadas: {result['total_frames']}",
            f"Duración analizada: {result['duration']:.2f} s",
            "",
            "PARÁMETROS Y UMBRALES CONFIGURADOS",
            f"  - Umbral de frecuencia máxima: {result['thresholds']['max_freq_hz']} Hz",
            f"  - Límite de velocidad permitida: {result['thresholds']['max_speed_kmh']} km/h",
            f"  - IDs autorizados (Lista blanca): {', '.join(result['thresholds']['authorized_ids'])}",
            "",
            "RESUMEN DE ALERTAS DE INTRUSIÓN",
            f"  Total alertas detectadas: {result['alerts_count']}",
            f"  - Regla 1 (Frecuencia anómala / Flood): {result['rule1_count']}",
            f"  - Regla 2 (Carga útil fuera de rango): {result['rule2_count']}",
            f"  - Regla 3 (ID no reconocido en red): {result['rule3_count']}",
            "",
            "DETALLE DE ALERTAS DETECTADAS:",
        ]

        if not result["alerts"]:
            lines.append("  Ninguna alerta detectada. El tráfico se ajusta a las reglas de normalidad.")
        else:
            for idx, alert in enumerate(result["alerts"][:50], 1):
                lines.append(f"  [{idx:02d}] {alert['severity']} | {alert['rule']} | ID: {alert['can_id']}")
                lines.append(f"       Detalle: {alert['detail']}")

        lines.extend([
            "",
            "RECOMENDACIONES DE MITIGACIÓN (ISO/SAE 21434)",
            "1. Despliegue de Gateway con filtrado por lista blanca a nivel de capa de enlace.",
            "2. Limitación de tasa de paquetes (Rate Limiting) para mitigar vectores de inundación DoS.",
            "3. Verificación de integridad y validación de tipos y rangos de datos en ECUs destino.",
            "",
        ])

        target_path.write_text("\n".join(lines), encoding="utf-8")
        return target_path

    def display_results(self, result: Dict[str, Any]) -> None:
        """Muestra los resultados del IDS en consola formateados con rich."""
        table = Table(title=translator.t("ids.eval_title"), border_style="red")
        table.add_column("Regla de Detección", style="bold white")
        table.add_column("Alertas Disparadas", justify="right", style="bold yellow")
        table.add_column("Criterio Configurado", style="cyan")

        table.add_row(
            "Regla 1: Frecuencia Anómala (Flood / DoS)",
            str(result["rule1_count"]),
            f"> {self.max_freq_hz} Hz en {self.window_seconds}s",
        )
        table.add_row(
            "Regla 2: Carga Útil Fuera de Rango",
            str(result["rule2_count"]),
            f"Velocidad > {self.max_speed_kmh} km/h o formato corrupto",
        )
        table.add_row(
            "Regla 3: ID no Autorizado (Whitelisting)",
            str(result["rule3_count"]),
            "Arbitration ID ajeno a la lista blanca",
        )

        console.print(table, justify="center")
        total_msg = translator.t("ids.alerts_total").format(count=result["alerts_count"])
        console.print(f"\n[bold]{total_msg}[/bold]\n", style=warning_style if result["alerts_count"] else success_style)
