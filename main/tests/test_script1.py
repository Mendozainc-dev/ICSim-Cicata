"""Archivo de compatibilidad para test_script1.py."""
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from test_fuzzer import RandomCANFuzzerTests, RecordingBus

__all__ = ["RandomCANFuzzerTests", "RecordingBus"]

if __name__ == "__main__":
    import unittest
    unittest.main()