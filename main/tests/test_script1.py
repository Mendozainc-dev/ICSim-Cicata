import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import can

from main.scripts.script1 import RandomCANFuzzer, parse_can_id


class RecordingBus:
    def __init__(self):
        self.messages = []
        self.closed = False

    def send(self, frame):
        self.messages.append(frame)

    def shutdown(self):
        self.closed = True


class RandomCANFuzzerTests(unittest.TestCase):
    def test_seed_repeats_random_frame_sequence(self):
        first = RandomCANFuzzer(seed=123)
        second = RandomCANFuzzer(seed=123)

        first_frames = [first.generate_random_frame() for _ in range(5)]
        second_frames = [second.generate_random_frame() for _ in range(5)]

        self.assertEqual(
            [(frame.arbitration_id, frame.data) for frame in first_frames],
            [(frame.arbitration_id, frame.data) for frame in second_frames],
        )

    def test_mutation_changes_one_byte_and_preserves_id_and_length(self):
        original = can.Message(arbitration_id=0x244, data=b"\x10\x20\x30")
        fuzzer = RandomCANFuzzer(
            target_ids=[0x244],
            seed=123,
            mode="mutate",
            corpus=[original],
        )

        mutated = fuzzer.generate_mutated_frame()

        self.assertEqual(mutated.arbitration_id, original.arbitration_id)
        self.assertEqual(mutated.dlc, original.dlc)
        self.assertEqual(sum(left != right for left, right in zip(original.data, mutated.data)), 1)

    def test_mutation_without_selected_ids_uses_capture_ids(self):
        original = can.Message(arbitration_id=0x321, data=b"\x10\x20")
        fuzzer = RandomCANFuzzer(mode="mutate", corpus=[original])

        self.assertEqual(fuzzer.target_ids, [0x321])
        self.assertEqual(fuzzer.generate_mutated_frame().arbitration_id, 0x321)

    def test_packet_limit_and_csv_output_without_socketcan(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "frames.csv"
            fuzzer = RandomCANFuzzer(seed=7, delay=0, output_path=str(output_path))
            bus = RecordingBus()
            fuzzer.bus = bus

            with patch("main.scripts.script1.console.print"):
                fuzzer.run(max_packets=3)

            with output_path.open(newline="", encoding="utf-8") as output_file:
                rows = list(csv.DictReader(output_file))

        self.assertEqual(len(bus.messages), 3)
        self.assertTrue(bus.closed)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["seed"], "7")

    def test_parse_can_id_accepts_decimal_and_hex(self):
        self.assertEqual(parse_can_id("580"), 580)
        self.assertEqual(parse_can_id("0x244"), 0x244)


if __name__ == "__main__":
    unittest.main()