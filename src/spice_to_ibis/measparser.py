"""Parser for Spectre simulation results (.mt0, PSF ASCII, logs)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MeasResult:
    """Parsed measurement results from a single simulation."""

    deck_name: str = ""
    deck_type: str = ""  # "pulldown", "pullup", "clamp", "rising", "falling"
    corner_label: str = ""
    measurements: dict[str, float] = field(default_factory=dict)
    sweep_voltage: list[float] = field(default_factory=list)
    sweep_current: list[float] = field(default_factory=list)
    waveform_time: list[float] = field(default_factory=list)
    waveform_voltage: list[float] = field(default_factory=list)


class MeasParser:
    """Parse Spectre output files into MeasResult objects."""

    def parse_mt0(self, filepath: str | Path) -> dict[str, float]:
        """Parse a Spectre .mt0 file for measurement values.

        The .mt0 format has a VALUE section with "name" value pairs.

        Returns:
            Dictionary of measurement name → float value.
        """
        filepath = Path(filepath)
        text = filepath.read_text()
        return self._parse_mt0_text(text)

    def _parse_mt0_text(self, text: str) -> dict[str, float]:
        measurements: dict[str, float] = {}
        in_value = False

        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "VALUE":
                in_value = True
                continue
            if stripped == "END":
                break
            if in_value:
                match = re.match(r'"([^"]+)"\s+([^\s]+)', stripped)
                if match:
                    name = match.group(1)
                    try:
                        value = float(match.group(2))
                        measurements[name] = value
                    except ValueError:
                        pass
        return measurements

    def parse_psf_ascii(
        self, filepath: str | Path
    ) -> tuple[list[float], list[float]]:
        """Parse a PSF ASCII data file with two-column sweep data.

        Returns:
            Tuple of (x_values, y_values).
        """
        filepath = Path(filepath)
        text = filepath.read_text()
        return self._parse_psf_ascii_text(text)

    def _parse_psf_ascii_text(
        self, text: str
    ) -> tuple[list[float], list[float]]:
        x_vals: list[float] = []
        y_vals: list[float] = []
        in_value = False

        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "VALUE":
                in_value = True
                continue
            if stripped == "END":
                break
            if in_value and stripped:
                parts = stripped.split()
                if len(parts) >= 2:
                    try:
                        x_vals.append(float(parts[0]))
                        y_vals.append(float(parts[1]))
                    except ValueError:
                        pass
        return x_vals, y_vals

    def parse_dc_sweep(
        self, filepath: str | Path, deck_name: str = "", corner_label: str = ""
    ) -> MeasResult:
        """Parse DC sweep results into a MeasResult."""
        voltages, currents = self.parse_psf_ascii(filepath)
        return MeasResult(
            deck_name=deck_name,
            corner_label=corner_label,
            sweep_voltage=voltages,
            sweep_current=currents,
        )

    def parse_transient(
        self,
        waveform_path: str | Path,
        mt0_path: str | Path | None = None,
        deck_name: str = "",
        corner_label: str = "",
    ) -> MeasResult:
        """Parse transient results (waveform + optional .mt0 measurements)."""
        times, voltages = self.parse_psf_ascii(waveform_path)
        measurements: dict[str, float] = {}
        if mt0_path is not None:
            measurements = self.parse_mt0(mt0_path)
        return MeasResult(
            deck_name=deck_name,
            corner_label=corner_label,
            measurements=measurements,
            waveform_time=times,
            waveform_voltage=voltages,
        )
