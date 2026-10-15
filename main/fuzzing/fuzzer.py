import argparse
from datetime import datetime
import math
from pathlib import Path
import random
import signal
import sys
import time
from typing import Any, Dict, List, Optional

try:
    import can
except ImportError:
    class MockCan:
        class Message:
            def __init__(
                self,
                arbitration_id: int = 0,
                data: bytes = b"",
                is_extended_id: bool = False,
                is_error_frame: bool = False,
                is_remote_frame: bool = False,
                is_fd: bool = False,
            ):
                self.arbitration_id = arbitration_id
                self.data = bytes(data)
                self.dlc = len(self.data)
                self.is_extended_id = is_extended_id
                self.is_error_frame = is_error_frame
                self.is_remote_frame = is_remote_frame
                self.is_fd = is_fd

        class CanError(Exception):
            pass

    can = MockCan()  # type: ignore

from rich.console import Console
from rich.style import Style

from .can_message import (
    ICSIM_CAN_IDS,
    ICSIM_SHARED_IDS,
    MAX_CAN_ID,
    load_corpus,
    parse_can_id,
)
from .reporting import FuzzingReporter

console = Console(width=100)
title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)
status_style = Style(color="cyan", bold=True)


class FrameGenerator:
    """Generador especializado de tramas CAN estándar en modos aleatorio y mutación."""

    def __init__(
        self,
        target_ids: List[int],
        mode: str = "random",
        corpus: Optional[List[Any]] = None,
        seed: Optional[int] = None,
    ):
        self.target_ids = list(dict.fromkeys(target_ids))
        self.mode = mode
        self.corpus = corpus or []
        self.seed = seed
        self.random = random.Random(seed)

    def generate_random_frame(self) -> Any:
        if can is None:
            raise RuntimeError("python-can no está instalado")
        can_id = self.random.choice(self.target_ids)
        dlc = self.random.randint(1, 8)
        payload = bytes(self.random.randint(0, 255) for _ in range(dlc))

        return can.Message(
            arbitration_id=can_id,
            data=payload,
            is_extended_id=False,
        )

    def generate_mutated_frame(self) -> Any:
        if can is None:
            raise RuntimeError("python-can no está instalado")
        if not self.corpus:
            raise ValueError("El modo mutate necesita una captura con tramas CAN clásicas de los IDs seleccionados")

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

    def generate_frame(self) -> Any:
        if self.mode == "mutate":
            return self.generate_mutated_frame()
        return self.generate_random_frame()


class RandomCANFuzzer:
    """Motor de inyección y evaluación de vulnerabilidades por fuzzing en bus CAN."""

    def __init__(
        self,
        interface: str = "vcan0",
        delay: float = 0.01,
        target_ids: Optional[List[int]] = None,
        seed: Optional[int] = None,
        mode: str = "random",
        corpus: Optional[List[Any]] = None,
        output_path: Optional[str] = None,
        log_dir: Optional[Path | str] = None,
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
        self.mode = mode
        self.corpus = [
            frame
            for frame in corpus_frames
            if frame.arbitration_id in self.target_ids
            and (not getattr(frame, "is_extended_id", False) or frame.arbitration_id <= MAX_CAN_ID)
            and not getattr(frame, "is_error_frame", False)
            and not getattr(frame, "is_remote_frame", False)
            and not getattr(frame, "is_fd", False)
            and 1 <= len(frame.data) <= 8
        ]
        if mode == "mutate" and not self.corpus:
            raise ValueError("El modo mutate necesita una captura con tramas CAN clásicas de los IDs seleccionados")

        self.generator = FrameGenerator(
            target_ids=self.target_ids,
            mode=self.mode,
            corpus=self.corpus,
            seed=self.seed,
        )

        resolved_log_dir = Path(log_dir) if log_dir else None
        self.reporter = FuzzingReporter(output_path=output_path, log_dir=resolved_log_dir)
        self.output_path = output_path
        self.log_dir = self.reporter.log_dir

        self.bus: Any = None
        self.running = False
        self.total_sent = 0
        self.start_time = 0.0
        self.sent_by_id: Dict[int, int] = {can_id: 0 for can_id in self.target_ids}
        self.last_frame: Any = None
        self.last_error: Optional[str] = None
        self.stop_reason = "Ejecución no iniciada"
        self.run_started_at: Optional[datetime] = None
        self.packet_limit = 0
        self.duration_limit: Optional[float] = None

    def generate_random_frame(self) -> Any:
        return self.generator.generate_random_frame()

    def generate_mutated_frame(self) -> Any:
        return self.generator.generate_mutated_frame()

    def connect(self) -> None:
        if can is None:
            raise RuntimeError("python-can no está instalado")
        try:
            self.bus = can.Bus(channel=self.interface, interface="socketcan")
            console.print(f"\n[FUZZER] Conectado a la interfaz {self.interface}\n", style=title_style)
        except OSError as exception:
            self.last_error = str(exception)
            console.print(f"\n[ERROR] No se pudo conectar a {self.interface}: {exception}\n", style=error_style)
            sys.exit(1)
        except getattr(can, "CanError", Exception) as exception:
            self.last_error = str(exception)
            console.print(f"\n[ERROR] Error de CAN al conectar con {self.interface}: {exception}\n", style=error_style)
            sys.exit(1)

    def start_fuzzing(self, max_packets: int = 0, duration: Optional[float] = None) -> None:
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

        console.print("[FUZZER] Iniciando fuzzing CAN", style=title_style)
        console.print(
            f"[FUZZER] Interfaz: {self.interface} | Modo: {self.mode} | "
            f"Delay: {self.delay}s | Límite: {max_packets or 'sin límite'} | "
            f"Duración: {duration if duration is not None else 'sin límite'}s | Semilla: {self.seed}",
            style=title_style,
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
                style=error_style,
            )
        console.print("[FUZZER] Presiona Ctrl+C para detener\n", style=title_style)

        try:
            if not self.bus:
                self.connect()

            self.reporter.open_csv()

            while self.running:
                elapsed = time.monotonic() - self.start_time
                if duration is not None and elapsed >= duration:
                    self.stop_reason = f"Límite de duración alcanzado ({duration:g} s)"
                    break

                frame = self.generator.generate_frame()
                self.bus.send(frame)
                self.total_sent += 1
                self.last_frame = frame
                self.sent_by_id[frame.arbitration_id] = self.sent_by_id.get(frame.arbitration_id, 0) + 1

                elapsed = time.monotonic() - self.start_time
                self.reporter.record_frame(
                    elapsed=elapsed,
                    mode=self.mode,
                    seed=self.seed,
                    can_id=frame.arbitration_id,
                    dlc=frame.dlc,
                    data=frame.data,
                )

                if self.total_sent % 50 == 0:
                    self.show_status(frame)

                if max_packets > 0 and self.total_sent >= max_packets:
                    self.stop_reason = f"Límite de tramas alcanzado ({max_packets})"
                    break

                if self.delay:
                    time.sleep(self.delay)

        except KeyboardInterrupt:
            self.stop_reason = "Interrumpido por el usuario (Ctrl+C)"
            console.print("\n[FUZZER] Detenido por el usuario", style=title_style)
        except getattr(can, "CanError", Exception) as exception:
            self.stop_reason = "Error de comunicación CAN"
            self.last_error = str(exception)
            console.print(f"\n[ERROR] No se pudo enviar la trama CAN: {exception}", style=error_style)
        except SystemExit:
            self.stop_reason = "Fallo al iniciar la conexión CAN"
            raise
        except OSError as exception:
            self.stop_reason = "Error al escribir el CSV u otro archivo"
            self.last_error = str(exception)
            console.print(f"\n[ERROR] {exception}", style=error_style)
        except Exception as exception:
            self.stop_reason = "Error inesperado"
            self.last_error = f"{type(exception).__name__}: {exception}"
            raise
        finally:
            self.reporter.close_csv()
            self.stop()
            self.write_run_report()

    def show_status(self, frame: Any) -> None:
        elapsed = time.monotonic() - self.start_time
        rate = self.total_sent / elapsed if elapsed > 0 else 0
        payload = frame.data.hex(" ").upper()
        can_id = (
            f"0x{frame.arbitration_id:08X}"
            if getattr(frame, "is_extended_id", False)
            else f"0x{frame.arbitration_id:03X}"
        )
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
            f"Formato: {'extendido' if getattr(frame, 'is_extended_id', False) else 'estándar'} | "
            f"Datos: {payload}"
        )
        console.print(
            f"[POR ID] {id_counts}",
            style=status_style,
        )

    def stop(self) -> None:
        self.running = False
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception:
                pass
            self.bus = None

        elapsed = time.monotonic() - self.start_time if self.start_time else 0
        console.print(
            f"\n[FUZZER] Finalizado. Tramas enviadas: {self.total_sent} | Tiempo: {elapsed:.2f}s\n",
            style=title_style,
        )

    def write_run_report(self) -> Optional[Path]:
        if self.run_started_at is None:
            return None
        elapsed = time.monotonic() - self.start_time
        finished_at = datetime.now().astimezone()

        return self.reporter.write_run_report(
            run_started_at=self.run_started_at,
            finished_at=finished_at,
            elapsed=elapsed,
            interface=self.interface,
            mode=self.mode,
            target_ids=self.target_ids,
            delay=self.delay,
            packet_limit=self.packet_limit,
            duration_limit=self.duration_limit,
            seed=self.seed,
            corpus_count=len(self.corpus),
            stop_reason=self.stop_reason,
            total_sent=self.total_sent,
            sent_by_id=self.sent_by_id,
            last_frame=self.last_frame,
            last_error=self.last_error,
        )

    def run(self, max_packets: int = 0, duration: Optional[float] = None) -> None:
        self.start_fuzzing(max_packets=max_packets, duration=duration)


def handle_signal(sig: Any, frame: Any) -> None:
    raise KeyboardInterrupt


def cli_main() -> None:
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


if __name__ == "__main__":
    cli_main()
