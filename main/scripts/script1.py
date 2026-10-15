"""Módulo de compatibilidad para script1.py delegando a main.fuzzing."""

from fuzzing import (
    ICSIM_CAN_IDS,
    ICSIM_SHARED_IDS,
    MAX_CAN_ID,
    FrameGenerator,
    FuzzingReporter,
    RandomCANFuzzer,
    load_corpus,
    parse_can_id,
)
from fuzzing.fuzzer import cli_main, handle_signal

__all__ = [
    "ICSIM_CAN_IDS",
    "ICSIM_SHARED_IDS",
    "MAX_CAN_ID",
    "FrameGenerator",
    "FuzzingReporter",
    "RandomCANFuzzer",
    "load_corpus",
    "parse_can_id",
    "cli_main",
    "handle_signal",
]

if __name__ == "__main__":
    cli_main()
