"""Spectre subcircuit parser."""

from __future__ import annotations

import re
from pathlib import Path

from spice_to_ibis.models.spice import PinRole, SpiceSubcircuit

# Matches: subckt <name> (<ports...>)  or  subckt <name> (port1 port2 ...)
_SUBCKT_RE = re.compile(r"^\s*subckt\s+(\w+)\s+\(([^)]*)\)", re.IGNORECASE)
_ENDS_RE = re.compile(r"^\s*ends\s+(\w+)", re.IGNORECASE)
_PARAM_RE = re.compile(r"^\s*parameters\s+(.*)", re.IGNORECASE)
_INCLUDE_RE = re.compile(r'^\s*include\s+"([^"]+)"', re.IGNORECASE)


class SpiceParser:
    """Parser for Spectre .scs subcircuit files."""

    def parse(
        self,
        filepath: str | Path,
        pin_map: dict[str, PinRole] | None = None,
    ) -> SpiceSubcircuit:
        """Parse a Spectre .scs file and return a SpiceSubcircuit.

        Args:
            filepath: Path to the .scs file.
            pin_map: Optional mapping of port names to PinRole values.

        Returns:
            Parsed SpiceSubcircuit instance.
        """
        filepath = Path(filepath)
        raw_lines = filepath.read_text().splitlines()
        return self._parse_lines(raw_lines, pin_map)

    def _parse_lines(
        self,
        lines: list[str],
        pin_map: dict[str, PinRole] | None = None,
    ) -> SpiceSubcircuit:
        sub = SpiceSubcircuit()
        sub.raw_lines = lines

        includes: list[str] = []
        in_subckt = False

        for line in lines:
            stripped = line.strip()

            # Skip comments and blank lines for parsing (but keep in raw)
            if not stripped or stripped.startswith("//"):
                # Check for include even in comment-free lines
                pass

            # Include statements (can appear outside subckt)
            inc_match = _INCLUDE_RE.match(stripped)
            if inc_match:
                includes.append(inc_match.group(1))
                continue

            # Subcircuit start
            subckt_match = _SUBCKT_RE.match(stripped)
            if subckt_match:
                sub.name = subckt_match.group(1)
                port_str = subckt_match.group(2).strip()
                sub.ports = port_str.split()
                in_subckt = True
                continue

            # Parameters line (inside subckt)
            if in_subckt:
                param_match = _PARAM_RE.match(stripped)
                if param_match:
                    param_str = param_match.group(1)
                    sub.parameters = self._parse_params(param_str)
                    continue

            # End of subcircuit
            ends_match = _ENDS_RE.match(stripped)
            if ends_match:
                in_subckt = False
                continue

        sub.include_paths = includes
        if pin_map is not None:
            sub.pin_map = pin_map

        return sub

    @staticmethod
    def _parse_params(param_str: str) -> dict[str, str]:
        """Parse a Spectre parameters line into key=value pairs."""
        params: dict[str, str] = {}
        for token in param_str.split():
            if "=" in token:
                key, _, val = token.partition("=")
                params[key.strip()] = val.strip()
        return params


# NgSPICE regexes
_NG_SUBCKT_RE = re.compile(r"^\s*\.subckt\s+(\w+)\s+(.*)", re.IGNORECASE)
_NG_ENDS_RE = re.compile(r"^\s*\.ends\s*(\w*)", re.IGNORECASE)
_NG_PARAM_RE = re.compile(r"^\s*\.param\s+(.*)", re.IGNORECASE)
_NG_INCLUDE_RE = re.compile(r'^\s*\.include\s+"([^"]+)"', re.IGNORECASE)


class NgspiceParser:
    """Parser for NgSPICE .cir subcircuit files."""

    def parse(
        self,
        filepath: str | Path,
        pin_map: dict[str, PinRole] | None = None,
    ) -> SpiceSubcircuit:
        """Parse an NgSPICE .cir file and return a SpiceSubcircuit."""
        filepath = Path(filepath)
        raw_lines = filepath.read_text().splitlines()
        return self._parse_lines(raw_lines, pin_map)

    def _parse_lines(
        self,
        lines: list[str],
        pin_map: dict[str, PinRole] | None = None,
    ) -> SpiceSubcircuit:
        sub = SpiceSubcircuit()
        sub.raw_lines = lines

        includes: list[str] = []
        in_subckt = False

        for line in lines:
            stripped = line.strip()

            # Skip comments and blank lines
            if not stripped or stripped.startswith("*"):
                continue

            # Include statements (can appear outside subckt)
            inc_match = _NG_INCLUDE_RE.match(stripped)
            if inc_match:
                includes.append(inc_match.group(1))
                continue

            # Subcircuit start: .subckt name port1 port2 ... [param=val ...]
            subckt_match = _NG_SUBCKT_RE.match(stripped)
            if subckt_match:
                sub.name = subckt_match.group(1)
                rest = subckt_match.group(2).strip()
                ports: list[str] = []
                params: dict[str, str] = {}
                for token in rest.split():
                    if "=" in token:
                        key, _, val = token.partition("=")
                        params[key.strip()] = val.strip()
                    else:
                        ports.append(token)
                sub.ports = ports
                sub.parameters = params
                in_subckt = True
                continue

            # .param lines inside subckt
            if in_subckt:
                param_match = _NG_PARAM_RE.match(stripped)
                if param_match:
                    param_str = param_match.group(1)
                    for token in param_str.split():
                        if "=" in token:
                            key, _, val = token.partition("=")
                            sub.parameters[key.strip()] = val.strip()
                    continue

            # End of subcircuit
            ends_match = _NG_ENDS_RE.match(stripped)
            if ends_match:
                in_subckt = False
                continue

        sub.include_paths = includes
        if pin_map is not None:
            sub.pin_map = pin_map

        return sub


def get_parser(simulator: str = "spectre") -> SpiceParser | NgspiceParser:
    """Factory to get the parser for a simulator.

    Args:
        simulator: "spectre" or "ngspice".

    Returns:
        Parser instance.
    """
    if simulator == "spectre":
        return SpiceParser()
    if simulator == "ngspice":
        return NgspiceParser()
    raise ValueError(f"Unknown simulator: {simulator!r}")
