"""Abstract base class for simulation deck generators."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

from spice_to_ibis.models.corners import Corner
from spice_to_ibis.models.spice import SpiceSubcircuit
from spice_to_ibis.syntax import SimSyntax, SpectreSyntax


@dataclass
class SimDeck:
    """A generated simulation deck ready to be written to disk."""

    name: str
    deck_type: str  # "pulldown", "pullup", "clamp", "rising", "falling"
    corner: Corner
    content: str
    expected_measurements: list[str] = field(default_factory=list)


class DeckGenerator(abc.ABC):
    """Base class for deck generators."""

    deck_type: str = ""

    def __init__(self, syntax: SimSyntax | None = None):
        self.syntax = syntax or SpectreSyntax()

    @abc.abstractmethod
    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        """Generate a simulation deck for the given subcircuit and corner."""

    def _header(self, corner: Corner) -> str:
        """Common header with simulator preamble."""
        return self.syntax.header(self.deck_type, corner.label, corner.suffix)

    def _global_options(self) -> str:
        return self.syntax.global_options()

    def _include_block(self, subcircuit: SpiceSubcircuit) -> str:
        lines = []
        for inc in subcircuit.include_paths:
            lines.append(self.syntax.include(inc))
        return "\n".join(lines) + "\n" if lines else ""

    def _supply_sources(self, subcircuit: SpiceSubcircuit, corner: Corner) -> str:
        """Generate VDD and VSS voltage sources."""
        vdd_pin = self._find_pin(subcircuit, "vdd")
        vss_pin = self._find_pin(subcircuit, "vss")
        lines = [
            self.syntax.voltage_source("v_vdd", vdd_pin, "0", corner.voltage),
            self.syntax.voltage_source("v_vss", vss_pin, "0", 0),
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _find_pin(subcircuit: SpiceSubcircuit, role: str) -> str:
        """Find port name for a given role, falling back to role name."""
        from spice_to_ibis.models.spice import PinRole

        role_enum = PinRole(role)
        for port, pin_role in subcircuit.pin_map.items():
            if pin_role == role_enum:
                return port
        # Fallback: check if role name exists in ports
        if role in subcircuit.ports:
            return role
        return role
