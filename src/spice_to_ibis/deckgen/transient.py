"""Transient deck generators for waveform characterization."""

from __future__ import annotations

from spice_to_ibis.deckgen.base import DeckGenerator, SimDeck
from spice_to_ibis.models.corners import Corner
from spice_to_ibis.models.spice import SpiceSubcircuit
from spice_to_ibis.syntax import SimSyntax


class RisingWaveformDeckGen(DeckGenerator):
    """Generate transient deck for rising waveform.

    Stimulus: din pulse LOW->HIGH, R_fix=50Ohm to VDD/2.
    Measures V(pad) vs time + 20%/80% crossing times.

    For differential subcircuits, uses R_diff (2*R_fixture) between pad_p and
    pad_n, and measures differential zero crossing instead of per-pin thresholds.
    """

    deck_type = "rising"

    def __init__(
        self,
        syntax: SimSyntax | None = None,
        r_fixture: float = 50.0,
        t_rise: float = 0.2e-9,
        t_sim: float = 20e-9,
    ):
        super().__init__(syntax)
        self.r_fixture = r_fixture
        self.t_rise = t_rise
        self.t_sim = t_sim

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        diff = self._is_differential(subcircuit)
        if diff:
            pad_p, pad_n = self._diff_pad_pins(subcircuit)
        else:
            pad_p = self._find_pin(subcircuit, "pad")
        din_pin = self._find_pin(subcircuit, "input")
        en_pin = self._find_pin(subcircuit, "enable")

        content = self._header(corner)
        content += self._global_options()
        content += self._include_block(subcircuit)
        content += "\n"

        # Instantiate DUT
        content += (
            self.syntax.subcircuit_instance("x_dut", subcircuit.ports, subcircuit.name)
            + "\n\n"
        )

        # Power supplies
        content += self._supply_sources(subcircuit, corner)

        # Enable HIGH
        content += self.syntax.voltage_source("v_en", en_pin, "0", vdd) + "\n\n"

        # Input pulse LOW->HIGH
        content += (
            self.syntax.pulse_source(
                "v_din",
                din_pin,
                "0",
                val0=0,
                val1=vdd,
                delay="1n",
                rise=self.t_rise,
                fall=self.t_rise,
                width=self.t_sim / 2,
                period=self.t_sim,
            )
            + "\n\n"
        )

        if diff:
            # Differential load: R_diff between pad_p and pad_n
            r_diff = 2 * self.r_fixture
            content += (
                self.syntax.resistor("r_diff", pad_p, pad_n, r_diff) + "\n"
            )
            # Behavioral source to probe differential voltage
            probe = self.syntax.diff_probe(pad_p, pad_n)
            if probe:
                content += probe + "\n"
            content += "\n"
        else:
            # Single-ended load: R_fixture to V_fixture (VDD/2)
            v_fixture = vdd / 2
            content += (
                self.syntax.resistor("r_fix", pad_p, "v_fix", self.r_fixture)
                + "\n"
            )
            content += (
                self.syntax.voltage_source("v_fix_src", "v_fix", "0", v_fixture)
                + "\n\n"
            )

        # Transient analysis
        content += self.syntax.transient(self.t_sim) + "\n\n"

        # Measurement statements
        if diff:
            content += (
                self.syntax.meas_cross_diff(
                    "meas_t_cross", pad_p, pad_n, "rise", 0.0, "t_cross_rise"
                )
                + "\n"
            )
            expected = ["t_cross_rise"]
        else:
            v_20 = vdd * 0.2
            v_80 = vdd * 0.8
            content += (
                self.syntax.meas_cross(
                    "meas_t20", pad_p, "rise", v_20, "t20_rise"
                )
                + "\n"
            )
            content += (
                self.syntax.meas_cross(
                    "meas_t80", pad_p, "rise", v_80, "t80_rise"
                )
                + "\n"
            )
            expected = ["t20_rise", "t80_rise"]

        # Control block and end (non-empty for NgSPICE)
        content += self.syntax.control_block(f"rising_{corner.suffix}")
        content += self.syntax.end_statement()

        name = f"rising_{corner.suffix}"
        return SimDeck(
            name=name,
            deck_type=self.deck_type,
            corner=corner,
            content=content,
            expected_measurements=expected,
        )


class FallingWaveformDeckGen(DeckGenerator):
    """Generate transient deck for falling waveform.

    Stimulus: din pulse HIGH->LOW, R_fix=50Ohm to VDD/2.
    Measures V(pad) vs time + 80%/20% crossing times.

    For differential subcircuits, uses R_diff (2*R_fixture) between pad_p and
    pad_n, and measures differential zero crossing instead of per-pin thresholds.
    """

    deck_type = "falling"

    def __init__(
        self,
        syntax: SimSyntax | None = None,
        r_fixture: float = 50.0,
        t_rise: float = 0.2e-9,
        t_sim: float = 20e-9,
    ):
        super().__init__(syntax)
        self.r_fixture = r_fixture
        self.t_rise = t_rise
        self.t_sim = t_sim

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        diff = self._is_differential(subcircuit)
        if diff:
            pad_p, pad_n = self._diff_pad_pins(subcircuit)
        else:
            pad_p = self._find_pin(subcircuit, "pad")
        din_pin = self._find_pin(subcircuit, "input")
        en_pin = self._find_pin(subcircuit, "enable")

        content = self._header(corner)
        content += self._global_options()
        content += self._include_block(subcircuit)
        content += "\n"

        # Instantiate DUT
        content += (
            self.syntax.subcircuit_instance("x_dut", subcircuit.ports, subcircuit.name)
            + "\n\n"
        )

        # Power supplies
        content += self._supply_sources(subcircuit, corner)

        # Enable HIGH
        content += self.syntax.voltage_source("v_en", en_pin, "0", vdd) + "\n\n"

        # Input pulse HIGH->LOW
        content += (
            self.syntax.pulse_source(
                "v_din",
                din_pin,
                "0",
                val0=vdd,
                val1=0,
                delay="1n",
                rise=self.t_rise,
                fall=self.t_rise,
                width=self.t_sim / 2,
                period=self.t_sim,
            )
            + "\n\n"
        )

        if diff:
            # Differential load: R_diff between pad_p and pad_n
            r_diff = 2 * self.r_fixture
            content += (
                self.syntax.resistor("r_diff", pad_p, pad_n, r_diff) + "\n"
            )
            # Behavioral source to probe differential voltage
            probe = self.syntax.diff_probe(pad_p, pad_n)
            if probe:
                content += probe + "\n"
            content += "\n"
        else:
            # Single-ended load: R_fixture to V_fixture (VDD/2)
            v_fixture = vdd / 2
            content += (
                self.syntax.resistor("r_fix", pad_p, "v_fix", self.r_fixture)
                + "\n"
            )
            content += (
                self.syntax.voltage_source("v_fix_src", "v_fix", "0", v_fixture)
                + "\n\n"
            )

        # Transient analysis
        content += self.syntax.transient(self.t_sim) + "\n\n"

        # Measurement statements
        if diff:
            content += (
                self.syntax.meas_cross_diff(
                    "meas_t_cross", pad_p, pad_n, "fall", 0.0, "t_cross_fall"
                )
                + "\n"
            )
            expected = ["t_cross_fall"]
        else:
            v_80 = vdd * 0.8
            v_20 = vdd * 0.2
            content += (
                self.syntax.meas_cross(
                    "meas_t80", pad_p, "fall", v_80, "t80_fall"
                )
                + "\n"
            )
            content += (
                self.syntax.meas_cross(
                    "meas_t20", pad_p, "fall", v_20, "t20_fall"
                )
                + "\n"
            )
            expected = ["t80_fall", "t20_fall"]

        # Control block and end (non-empty for NgSPICE)
        content += self.syntax.control_block(f"falling_{corner.suffix}")
        content += self.syntax.end_statement()

        name = f"falling_{corner.suffix}"
        return SimDeck(
            name=name,
            deck_type=self.deck_type,
            corner=corner,
            content=content,
            expected_measurements=expected,
        )
