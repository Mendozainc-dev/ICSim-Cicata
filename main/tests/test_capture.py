from pathlib import Path
import sys
import tempfile
import unittest

MAIN_DIR = Path(__file__).resolve().parent.parent
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

from fuzzing.capture import CanCapture


class MockCanFrame:
    def __init__(self, arbitration_id: int, data: bytes, timestamp: float = 1600000000.0):
        self.arbitration_id = arbitration_id
        self.data = data
        self.dlc = len(data)
        self.timestamp = timestamp


class MockRecvBus:
    def __init__(self, frames):
        self.frames = list(frames)

    def recv(self, timeout=None):
        if self.frames:
            return self.frames.pop(0)
        return None

    def shutdown(self):
        pass


class CanCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temp_dir.name)
        self.capture_tool = CanCapture(interface="vcan0", log_dir=self.log_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_capture_with_mock_bus(self):
        sample_frames = [
            MockCanFrame(0x244, b"\x00\x00\x00\x13\x88"),
            MockCanFrame(0x188, b"\x01\x00"),
            MockCanFrame(0x244, b"\x00\x00\x00\x00\x00"),
        ]
        bus = MockRecvBus(sample_frames)

        captured = self.capture_tool.capture(duration=0.5, bus=bus)
        self.assertEqual(len(captured), 3)

        grouped = self.capture_tool.grouped_stats
        self.assertIn(0x244, grouped)
        self.assertIn(0x188, grouped)
        self.assertEqual(grouped[0x244]["count"], 2)
        self.assertEqual(grouped[0x188]["count"], 1)

    def test_save_and_load_mapping(self):
        test_mapping = {
            "580": {"hex_id": "0x244", "description": "Velocímetro", "frequency": 10.0, "expected_range": "0-260"},
            "392": {"hex_id": "0x188", "description": "Luces de giro", "frequency": 2.0, "expected_range": "0-2"},
        }

        saved_path = self.capture_tool.save_mapping(test_mapping)
        self.assertTrue(saved_path.exists())

        loaded = self.capture_tool.load_mapping(saved_path)
        self.assertIn("580", loaded)
        self.assertEqual(loaded["580"]["description"], "Velocímetro")
        self.assertEqual(loaded["392"]["description"], "Luces de giro")


if __name__ == "__main__":
    unittest.main()
