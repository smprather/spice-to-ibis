from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Corner:
    """A single PVT (process-voltage-temperature) corner."""

    label: str  # e.g. "typ", "min", "max"
    process: str  # e.g. "tt", "ss", "ff"
    voltage: float  # VDD voltage
    temperature: float  # degrees Celsius

    @property
    def suffix(self) -> str:
        """Short suffix for file naming."""
        return f"{self.process}_{self.voltage}V_{self.temperature}C"


@dataclass
class CornerSet:
    """Typ/min/max corner triplet."""

    typ: Corner = field(
        default_factory=lambda: Corner("typ", "tt", 1.8, 25.0)
    )
    min: Corner = field(
        default_factory=lambda: Corner("min", "ss", 1.62, 125.0)
    )
    max: Corner = field(
        default_factory=lambda: Corner("max", "ff", 1.98, -40.0)
    )

    def __iter__(self):
        yield self.typ
        yield self.min
        yield self.max
