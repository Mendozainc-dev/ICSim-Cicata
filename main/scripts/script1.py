#!/usr/bin/env python3

import os
import sys
import time
import random
import signal
import argparse
from typing import List, Optional
import can

ICSIM_CAN_IDS = [
    0x080,
    0x110,
    0x188,
    0x244,
    0x133,
]


class RandomCANFuzzer:
    def __init__(self, interface: str = 'vcan0', delay: float = 0.01, target_ids: Optional[List[int]] = None):
        self.interface = interface
        self.delay = delay
        self.target_ids = target_ids if target_ids else ICSIM_CAN_IDS
        self.bus: Optional[can.Bus] = None
        self.running = False
        self.total_sent = 0
        self.start_time = 0.0

    def connect(self) -> None:
        try:
            self.bus = can.Bus(channel=self.interface, bustype='socketcan')
        except OSError as e:
            sys.exit(1)

    def generate_random_frame(self) -> can.Message:
        can_id = random.choice(self.target_ids)
        dlc = random.randint(1, 8)
        payload = bytes([random.randint(0, 255) for _ in range(dlc)])

        return can.Message(
            arbitration_id=can_id,
            data=payload,
            is_extended_id=False
        )

    def start_fuzzing(self, max_packets: int = 0) -> None:
        if not self.bus:
            self.connect()

        self.running = True
        self.start_time = time.time()

        try:
            while self.running:
                frame = self.generate_random_frame()
                self.bus.send(frame)
                self.total_sent += 1

                if self.total_sent % 50 == 0:
                    elapsed = time.time() - self.start_time
                    rate = self.total_sent / elapsed if elapsed > 0 else 0
                    print(f"\r[STATUS] Tramas Inyectadas: {self.total_sent} | Tasa: {
                          rate:.2f} pkts/sec | Ultima ID: {hex(frame.arbitration_id)}", end="")

                if max_packets > 0 and self.total_sent >= max_packets:
                    break

                time.sleep(self.delay)

        except KeyboardInterrupt:
            pass
        except can.CanError:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        self.running = False
        if self.bus:
            self.bus.shutdown()


def handle_signal(sig, frame):
    sys.exit(0)


    def run(self, max_packets: int = 0):
        self.connect()
        self.start_fuzzing(max_packets)

    def run(self, max_packets: int = 0):
        self.connect()
        self.start_fuzzing(max_packets)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signal)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interface", default="vcan0")
    parser.add_argument("-d", "--delay", type=float, default=0.005)
    parser.add_argument("-n", "--count", type=int, default=0)

    args = parser.parse_args()

    fuzzer = RandomCANFuzzer(
        interface=args.interface,
        delay=args.delay
    )
    fuzzer.start_fuzzing(max_packets=args.count)
