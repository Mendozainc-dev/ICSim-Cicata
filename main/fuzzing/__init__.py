"""Módulo de fuzzing, análisis, mapeo de red e IDS para bus CAN (Fases 2, 4 y 5)."""

from .analysis import RunAnalyzer
from .can_message import (
    ICSIM_CAN_IDS,
    ICSIM_SHARED_IDS,
    MAX_CAN_ID,
    load_corpus,
    parse_can_id,
)
from .capture import CanCapture
from .fuzzer import FrameGenerator, RandomCANFuzzer
from .ids import RuleBasedIds, VulnerabilityReport
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
    "CanCapture",
    "RunAnalyzer",
    "RuleBasedIds",
    "VulnerabilityReport",
]
