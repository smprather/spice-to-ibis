"""SPICE file parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SpiceModel:
    """Parsed representation of a SPICE model."""

    name: str = ""
    model_type: str = ""
    parameters: dict[str, float] = field(default_factory=dict)
    raw_lines: list[str] = field(default_factory=list)


class SpiceParser:
    """Parser for SPICE model files."""

    def parse(self, filepath: str | Path) -> SpiceModel:
        """Parse a SPICE file and return a SpiceModel.

        Args:
            filepath: Path to the SPICE model file.

        Returns:
            Parsed SpiceModel instance.
        """
        filepath = Path(filepath)
        raw_lines = filepath.read_text().splitlines()
        return SpiceModel(raw_lines=raw_lines)
