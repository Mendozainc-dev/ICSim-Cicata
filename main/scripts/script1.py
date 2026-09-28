#!/usr/bin/env python3

import argparse
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


class RandomCANFuzzer:
    def __init__(self, interface: str = "vcan0", delay: float = 0.01, target_ids: list[int] | None = None):
        self.interface = interface
        self.delay = delay
        self.target_ids = target_ids if target_ids else ICSIM_CAN_IDS
        self.bus: Any = None
        self.running = False
        self.total_sent = 0
        self.start_time = 0.0
        self.sent_by_id = {can_id: 0 for can_id in self.target_ids}

    def connect(self) -> None:
        try:
            self.bus = can.Bus(channel=self.interface, interface="socketcan")
            console.print(f"\n[FUZZER] Conectado a la interfaz {self.interface}\n", style=tittle)
        except OSError as exception:
            console.print(f"\n[ERROR] No se pudo conectar a {self.interface}: {exception}\n", style=error)
            sys.exit(1)
        except can.CanError as exception:
            console.print(f"\n[ERROR] Error de CAN al conectar con {self.interface}: {exception}\n", style=error)
            sys.exit(1)

    def generate_random_frame(self) -> can.Message:
        can_id = random.choice(self.target_ids)
        dlc = random.randint(1, 8)
        payload = bytes(random.randint(0, 255) for _ in range(dlc))

        return can.Message(
            arbitration_id=can_id,
            data=payload,
            is_extended_id=False,
        )

    def start_fuzzing(self, max_packets: int = 0) -> None:
        if not self.bus:
            self.connect()

        self.running = True
        self.total_sent = 0
        self.start_time = time.time()
        self.sent_by_id = {can_id: 0 for can_id in self.target_ids}

        console.print("[FUZZER] Iniciando fuzzing CAN", style=tittle)
        console.print(f"[FUZZER] Interfaz: {self.interface} | Delay: {self.delay}s | Límite: {max_packets or 'sin límite'}", style=tittle)
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

        try:
            while self.running:
                frame = self.generate_random_frame()
                self.bus.send(frame)
                self.total_sent += 1
                self.sent_by_id[frame.arbitration_id] = self.sent_by_id.get(frame.arbitration_id, 0) + 1

                if self.total_sent % 50 == 0:
                    self.show_status(frame)

                if max_packets > 0 and self.total_sent >= max_packets:
                    break

                time.sleep(self.delay)

        except KeyboardInterrupt:
            console.print("\n[FUZZER] Detenido por el usuario", style=tittle)
        except can.CanError as exception:
            console.print(f"\n[ERROR] No se pudo enviar la trama CAN: {exception}", style=error)
        finally:
            self.stop()

    def show_status(self, frame: can.Message) -> None:
        elapsed = time.time() - self.start_time
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

        elapsed = time.time() - self.start_time if self.start_time else 0
        console.print(f"\n[FUZZER] Finalizado. Tramas enviadas: {self.total_sent} | Tiempo: {elapsed:.2f}s\n", style=tittle)

    def run(self, max_packets: int = 0) -> None:
        self.start_fuzzing(max_packets=max_packets)


def handle_signal(sig, frame):
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signal)

    parser = argparse.ArgumentParser(description="Fuzzer CAN aleatorio para ICSim usando SocketCAN/vcan")
    parser.add_argument("-i", "--interface", default="vcan0")
    parser.add_argument("-d", "--delay", type=float, default=0.005)
    parser.add_argument("-n", "--count", type=int, default=0)

    args = parser.parse_args()

    fuzzer = RandomCANFuzzer(
        interface=args.interface,
        delay=args.delay,
    )
    fuzzer.run(max_packets=args.count)
