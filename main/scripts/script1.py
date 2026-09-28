#!/usr/bin/env python3

import argparse
import csv
from datetime import datetime
import math
from pathlib import Path
import random
import signal
import sys
import time
from typing import Any

import can
from rich.console import Console
from rich.style import Style


console = Console(width=100)
tittle = Style(color="white", bold=True)
error = Style(color="red", blink=True, bold=True)
status = Style(color="cyan", bold=True)

ICSIM_CAN_IDS = [
    0x080,
    0x110,
    0x188,
    0x244,
    0x133,
]
ICSIM_SHARED_IDS = {
    0x188: "señales de giro",
    0x244: "velocidad del tablero",
}
MAX_CAN_ID = 0x7FF
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


class RandomCANFuzzer:
    def __init__(
        self,
        interface: str = "vcan0",
        delay: float = 0.01,
        target_ids: list[int] | None = None,
        seed: int | None = None,
        mode: str = "random",
        corpus: list[can.Message] | None = None,
        output_path: str | None = None,
        log_dir: str | Path = LOG_DIR,
    ):
        if not math.isfinite(delay) or delay < 0:
            raise ValueError("El delay debe ser un número finito no negativo")
        if mode not in {"random", "mutate"}:
            raise ValueError("El modo debe ser 'random' o 'mutate'")

        self.interface = interface
        self.delay = delay
        corpus_frames = corpus or []
        if target_ids is None and mode == "mutate":
            default_ids = [frame.arbitration_id for frame in corpus_frames]
        else:
            default_ids = ICSIM_CAN_IDS if target_ids is None else target_ids
        self.target_ids = list(dict.fromkeys(default_ids))
        if not self.target_ids:
            raise ValueError("Debe seleccionarse al menos un ID CAN")
        if any(can_id < 0 or can_id > MAX_CAN_ID for can_id in self.target_ids):
            raise ValueError(f"Los IDs CAN estándar deben estar entre 0 y {MAX_CAN_ID:#05x}")
        self.seed = seed
        self.random = random.Random(seed)
        self.mode = mode
        self.corpus = [
            frame for frame in corpus_frames
            if frame.arbitration_id in self.target_ids
            and not frame.is_extended_id
            and not frame.is_error_frame
            and not frame.is_remote_frame
            and not frame.is_fd
            and 1 <= len(frame.data) <= 8
        ]
        if mode == "mutate" and not self.corpus:
            raise ValueError("El modo mutate necesita una captura con tramas CAN clásicas de los IDs seleccionados")
        self.output_path = output_path
        self.log_dir = Path(log_dir)
        self.bus: Any = None
        self.running = False
        self.total_sent = 0
        self.start_time = 0.0
        self.sent_by_id = {can_id: 0 for can_id in self.target_ids}
        self.last_frame: can.Message | None = None
        self.last_error: str | None = None
        self.stop_reason = "Ejecución no iniciada"
        self.run_started_at: datetime | None = None
        self.packet_limit = 0
        self.duration_limit: float | None = None

    def connect(self) -> None:
        try:
            self.bus = can.Bus(channel=self.interface, interface="socketcan")
            console.print(f"\n[FUZZER] Conectado a la interfaz {self.interface}\n", style=tittle)
        except OSError as exception:
            self.last_error = str(exception)
            console.print(f"\n[ERROR] No se pudo conectar a {self.interface}: {exception}\n", style=error)
            sys.exit(1)
        except can.CanError as exception:
            self.last_error = str(exception)
            console.print(f"\n[ERROR] Error de CAN al conectar con {self.interface}: {exception}\n", style=error)
            sys.exit(1)

    def generate_random_frame(self) -> can.Message:
        can_id = self.random.choice(self.target_ids)
        dlc = self.random.randint(1, 8)
        payload = bytes(self.random.randint(0, 255) for _ in range(dlc))

        return can.Message(
            arbitration_id=can_id,
            data=payload,
            is_extended_id=False,
        )

    def generate_mutated_frame(self) -> can.Message:
        original = self.random.choice(self.corpus)
        payload = bytearray(original.data)
        index = self.random.randrange(len(payload))
        replacement = self.random.randrange(255)
        if replacement >= payload[index]:
            replacement += 1
        payload[index] = replacement

        return can.Message(
            arbitration_id=original.arbitration_id,
            data=bytes(payload),
            is_extended_id=False,
        )

    def start_fuzzing(self, max_packets: int = 0, duration: float | None = None) -> None:
        if max_packets < 0:
            raise ValueError("El límite de tramas no puede ser negativo")
        if duration is not None and (not math.isfinite(duration) or duration < 0):
            raise ValueError("La duración debe ser un número finito no negativo")

        self.running = True
        self.total_sent = 0
        self.start_time = time.monotonic()
        self.run_started_at = datetime.now().astimezone()
        self.sent_by_id = {can_id: 0 for can_id in self.target_ids}
        self.last_frame = None
        self.last_error = None
        self.stop_reason = "Ejecución interrumpida antes de terminar"
        self.packet_limit = max_packets
        self.duration_limit = duration

        console.print("[FUZZER] Iniciando fuzzing CAN", style=tittle)
        console.print(
            f"[FUZZER] Interfaz: {self.interface} | Modo: {self.mode} | "
            f"Delay: {self.delay}s | Límite: {max_packets or 'sin límite'} | "
            f"Duración: {duration if duration is not None else 'sin límite'}s | Semilla: {self.seed}",
            style=tittle,
        )
        console.print("[FUZZER] IDs objetivo: " + ", ".join(f"0x{can_id:03X}" for can_id in self.target_ids))
        if self.mode == "mutate":
            console.print(f"[FUZZER] Tramas disponibles en la captura: {len(self.corpus)}")
        shared_ids = [
            f"0x{can_id:03X} ({name})"
            for can_id, name in ICSIM_SHARED_IDS.items()
            if can_id in self.target_ids
        ]
        if shared_ids:
            console.print(
                f"[AVISO] IDs que comparten con ICSim: {', '.join(shared_ids)}. "
                "Las tramas aleatorias pueden alterar esos indicadores.",
                style=error,
            )
        console.print("[FUZZER] Presiona Ctrl+C para detener\n", style=tittle)

        output_file = None
        try:
            if not self.bus:
                self.connect()

            writer = None
            if self.output_path:
                output_file = open(self.output_path, "w", newline="", encoding="utf-8")
                writer = csv.writer(output_file)
                writer.writerow(["elapsed_s", "mode", "seed", "can_id", "dlc", "data_hex"])

            while self.running:
                elapsed = time.monotonic() - self.start_time
                if duration is not None and elapsed >= duration:
                    self.stop_reason = f"Límite de duración alcanzado ({duration:g} s)"
                    break

                frame = self.generate_mutated_frame() if self.mode == "mutate" else self.generate_random_frame()
                self.bus.send(frame)
                self.total_sent += 1
                self.last_frame = frame
                self.sent_by_id[frame.arbitration_id] = self.sent_by_id.get(frame.arbitration_id, 0) + 1
                elapsed = time.monotonic() - self.start_time
                if writer:
                    writer.writerow([
                        f"{elapsed:.6f}", self.mode, self.seed,
                        f"0x{frame.arbitration_id:03X}", frame.dlc, frame.data.hex(),
                    ])

                if self.total_sent % 50 == 0:
                    self.show_status(frame)

                if max_packets > 0 and self.total_sent >= max_packets:
                    self.stop_reason = f"Límite de tramas alcanzado ({max_packets})"
                    break

                if self.delay:
                    time.sleep(self.delay)

        except KeyboardInterrupt:
            self.stop_reason = "Interrumpido por el usuario (Ctrl+C)"
            console.print("\n[FUZZER] Detenido por el usuario", style=tittle)
        except can.CanError as exception:
            self.stop_reason = "Error de comunicación CAN"
            self.last_error = str(exception)
            console.print(f"\n[ERROR] No se pudo enviar la trama CAN: {exception}", style=error)
        except SystemExit:
            self.stop_reason = "Fallo al iniciar la conexión CAN"
            raise
        except OSError as exception:
            self.stop_reason = "Error al escribir el CSV u otro archivo"
            self.last_error = str(exception)
            console.print(f"\n[ERROR] {exception}", style=error)
        except Exception as exception:
            self.stop_reason = "Error inesperado"
            self.last_error = f"{type(exception).__name__}: {exception}"
            raise
        finally:
            if output_file:
                output_file.close()
            self.stop()
            self.write_run_report()

    def show_status(self, frame: can.Message) -> None:
        elapsed = time.monotonic() - self.start_time
        rate = self.total_sent / elapsed if elapsed > 0 else 0
        payload = frame.data.hex(" ").upper()
        can_id = f"0x{frame.arbitration_id:08X}" if frame.is_extended_id else f"0x{frame.arbitration_id:03X}"
        id_counts = " | ".join(
            f"0x{can_id:03X}: {count}"
            for can_id, count in sorted(self.sent_by_id.items())
        )

        console.print(
            f"[STATUS] Enviadas: {self.total_sent} | "
            f"Tiempo: {elapsed:.1f}s | Tasa: {rate:.2f} tramas/s"
        )
        console.print(
            f"[TRAMA] ID: {can_id} | DLC: {frame.dlc} | "
            f"Formato: {'extendido' if frame.is_extended_id else 'estándar'} | "
            f"Datos: {payload}"
        )
        console.print(
            f"[POR ID] {id_counts}",
            style=status,
        )

    def stop(self) -> None:
        self.running = False
        if self.bus:
            self.bus.shutdown()
            self.bus = None

        elapsed = time.monotonic() - self.start_time if self.start_time else 0
        console.print(f"\n[FUZZER] Finalizado. Tramas enviadas: {self.total_sent} | Tiempo: {elapsed:.2f}s\n", style=tittle)

    def write_run_report(self) -> Path | None:
        if self.run_started_at is None:
            return None

        finished_at = datetime.now().astimezone()
        elapsed = time.monotonic() - self.start_time
        filename = f"fuzz-{self.run_started_at.strftime('%Y%m%d-%H%M%S-%f')}.txt"
        report_path = self.log_dir / filename

        if self.last_error:
            conclusion = (
                f"La ejecución se detuvo con un error después de enviar {self.total_sent} tramas. "
                "Este registro no confirma por sí solo una vulnerabilidad ni su impacto."
            )
        elif self.total_sent:
            conclusion = (
                f"Se enviaron {self.total_sent} tramas y la ejecución terminó por: {self.stop_reason}. "
                "El envío no confirma por sí solo que el objetivo haya fallado o tenga una vulnerabilidad."
            )
        else:
            conclusion = (
                "No se enviaron tramas; no hay resultado de fuzzing que evaluar. "
                "Revisa la interfaz CAN y los parámetros de la ejecución."
            )

        lines = [
            "REPORTE DE EJECUCIÓN - FUZZER CAN",
            "=" * 38,
            f"Inicio: {self.run_started_at.isoformat(timespec='seconds')}",
            f"Fin: {finished_at.isoformat(timespec='seconds')}",
            f"Interfaz: {self.interface}",
            f"Modo: {self.mode}",
            f"IDs objetivo: {', '.join(f'0x{can_id:03X}' for can_id in self.target_ids)}",
            f"Delay configurado: {self.delay} s",
            f"Límite de tramas: {self.packet_limit or 'sin límite'}",
            f"Límite de duración: {self.duration_limit if self.duration_limit is not None else 'sin límite'} s",
            f"Semilla: {self.seed if self.seed is not None else 'no especificada'}",
            f"Tramas en corpus: {len(self.corpus) if self.mode == 'mutate' else 'no aplica'}",
            f"CSV de salida: {self.output_path or 'no solicitado'}",
            "",
            "RESULTADO",
            f"Estado: {self.stop_reason}",
            f"Tramas enviadas: {self.total_sent}",
            f"Duración real: {elapsed:.3f} s",
            f"Tasa media: {self.total_sent / elapsed if elapsed > 0 else 0:.2f} tramas/s",
            "Tramas por ID:",
        ]
        lines.extend(
            f"  0x{can_id:03X}: {count}"
            for can_id, count in sorted(self.sent_by_id.items())
        )
        if self.last_frame:
            lines.extend([
                f"Última trama: ID 0x{self.last_frame.arbitration_id:03X}, "
                f"DLC {self.last_frame.dlc}, datos {self.last_frame.data.hex(' ').upper()}",
            ])
        if self.last_error:
            lines.append(f"Error: {self.last_error}")
        lines.extend(["", "CONCLUSIÓN", conclusion, ""])

        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            report_path.write_text("\n".join(lines), encoding="utf-8")
        except OSError as exception:
            console.print(f"[ERROR] No se pudo guardar el reporte {report_path}: {exception}", style=error)
            return None

        console.print(f"[FUZZER] Reporte guardado en: {report_path}", style=tittle)
        return report_path

    def run(self, max_packets: int = 0, duration: float | None = None) -> None:
        self.start_fuzzing(max_packets=max_packets, duration=duration)


def parse_can_id(value: str) -> int:
    try:
        can_id = int(value, 0)
    except ValueError as exception:
        raise argparse.ArgumentTypeError("Usa un ID decimal o hexadecimal, por ejemplo 580 o 0x244") from exception
    if not 0 <= can_id <= MAX_CAN_ID:
        raise argparse.ArgumentTypeError(f"El ID debe estar entre 0 y {MAX_CAN_ID:#05x}")
    return can_id


def load_corpus(path: str, target_ids: list[int] | None) -> list[can.Message]:
    frames = [
        frame for frame in can.LogReader(path)
        if (target_ids is None or frame.arbitration_id in target_ids)
        and not frame.is_extended_id
        and not frame.is_error_frame
        and not frame.is_remote_frame
        and not frame.is_fd
        and 1 <= len(frame.data) <= 8
    ]
    if not frames:
        raise ValueError("La captura no contiene tramas CAN clásicas válidas de los IDs seleccionados")
    return frames


def handle_signal(sig, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signal)

    parser = argparse.ArgumentParser(description="Fuzzer CAN aleatorio para ICSim usando SocketCAN/vcan")
    parser.add_argument("-i", "--interface", default="vcan0")
    parser.add_argument("-d", "--delay", type=float, default=0.005)
    parser.add_argument("-n", "--count", type=int, default=0)
    parser.add_argument("--duration", type=float, default=30.0, help="Duración máxima en segundos (0 desactiva el límite)")
    parser.add_argument("--seed", type=int, help="Semilla para repetir la misma secuencia aleatoria")
    parser.add_argument("--id", dest="target_ids", action="append", type=parse_can_id, help="ID CAN estándar objetivo; se puede repetir")
    parser.add_argument("--mode", choices=("random", "mutate"), default="random")
    parser.add_argument("--corpus", help="Captura compatible con python-can; obligatoria en modo mutate")
    parser.add_argument("--output", help="Guarda las tramas enviadas en un CSV")

    args = parser.parse_args()
    if any(not math.isfinite(value) or value < 0 for value in (args.delay, args.duration)) or args.count < 0:
        parser.error("delay, count y duration deben ser finitos y no negativos")
    if args.count == 0 and args.duration == 0:
        parser.error("Configura --count o --duration para limitar la prueba")
    if args.mode == "mutate" and not args.corpus:
        parser.error("--corpus es obligatorio con --mode mutate")
    if args.mode == "random" and args.corpus:
        parser.error("--corpus solo se usa con --mode mutate")

    try:
        corpus = load_corpus(args.corpus, args.target_ids) if args.corpus else None
        fuzzer = RandomCANFuzzer(
            interface=args.interface,
            delay=args.delay,
            target_ids=args.target_ids,
            seed=args.seed,
            mode=args.mode,
            corpus=corpus,
            output_path=args.output,
        )
    except (OSError, ValueError) as exception:
        parser.error(str(exception))

    fuzzer.run(max_packets=args.count, duration=args.duration or None)
