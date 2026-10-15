import argparse
from typing import Dict, List, Optional

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

ICSIM_CAN_IDS: List[int] = [
    0x080,
    0x110,
    0x188,
    0x244,
    0x133,
]

ICSIM_SHARED_IDS: Dict[int, str] = {
    0x188: "señales de giro",
    0x244: "velocidad del tablero",
}

MAX_CAN_ID: int = 0x7FF


def parse_can_id(value: str) -> int:
    """Convierte y valida una cadena decimal o hexadecimal en un ID CAN estándar de 11 bits."""
    try:
        can_id = int(value, 0)
    except ValueError as exception:
        raise argparse.ArgumentTypeError(
            "Usa un ID decimal o hexadecimal, por ejemplo 580 o 0x244"
        ) from exception

    if not 0 <= can_id <= MAX_CAN_ID:
        raise argparse.ArgumentTypeError(f"El ID debe estar entre 0 y {MAX_CAN_ID:#05x}")

    return can_id


def load_corpus(path: str, target_ids: Optional[List[int]]) -> List[any]:
    """Carga tramas CAN clásicas desde un archivo de registro compatible con python-can."""
    if can is None:
        raise RuntimeError("La librería python-can no está instalada.")

    frames = [
        frame
        for frame in can.LogReader(path)
        if (target_ids is None or frame.arbitration_id in target_ids)
        and (not getattr(frame, "is_extended_id", False) or frame.arbitration_id <= MAX_CAN_ID)
        and not getattr(frame, "is_error_frame", False)
        and not getattr(frame, "is_remote_frame", False)
        and not getattr(frame, "is_fd", False)
        and 1 <= len(frame.data) <= 8
    ]

    if not frames:
        raise ValueError("La captura no contiene tramas CAN clásicas válidas de los IDs seleccionados")

    return frames
