from __future__ import annotations

import enum
from dataclasses import dataclass, field


class PinRole(enum.Enum):
    """Role of a subcircuit port in an I/O buffer."""

    PAD = "pad"
    VDD = "vdd"
    VSS = "vss"
    INPUT = "input"
    ENABLE = "enable"
    OUTPUT = "output"


@dataclass
class SpiceSubcircuit:
    """Parsed Spectre subcircuit definition."""

    name: str = ""
    ports: list[str] = field(default_factory=list)
    pin_map: dict[str, PinRole] = field(default_factory=dict)
    parameters: dict[str, str] = field(default_factory=dict)
    include_paths: list[str] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)
