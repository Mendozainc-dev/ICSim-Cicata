"""Módulo de fuzzing y análisis de vulnerabilidades para el bus CAN."""

from .can_message import (
    ICSIM_CAN_IDS,
    ICSIM_SHARED_IDS,
    MAX_CAN_ID,
    load_corpus,
    parse_can_id,
)
from .fuzzer import FrameGenerator, RandomCANFuzzer
from .reporting import FuzzingReporter

__all__ = [
    "ICSIM_CAN_IDS",
    "ICSIM_SHARED_IDS",
    "MAX_CAN_ID",
    "load_corpus",
    "parse_can_id",
    "FrameGenerator",
    "RandomCANFuzzer",
    "FuzzingReporter",
]
