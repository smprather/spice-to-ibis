"""Transient deck generators for waveform characterization."""

from __future__ import annotations

from spice_to_ibis.deckgen.base import DeckGenerator, SimDeck
from spice_to_ibis.models.corners import Corner
from spice_to_ibis.models.spice import SpiceSubcircuit


class RisingWaveformDeckGen(DeckGenerator):
    """Generate transient deck for rising waveform.

    Stimulus: din pulse LOW→HIGH, R_fix=50Ω to VDD/2.
    Measures V(pad) vs time + 20%/80% crossing times.
    """

    deck_type = "rising"

    def __init__(
        self,
        r_fixture: float = 50.0,
        t_rise: float = 0.2e-9,
        t_sim: float = 20e-9,
    ):
        self.r_fixture = r_fixture
        self.t_rise = t_rise
        self.t_sim = t_sim

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        pad_pin = self._find_pin(subcircuit, "pad")
        din_pin = self._find_pin(subcircuit, "input")
        en_pin = self._find_pin(subcircuit, "enable")

        v_fixture = vdd / 2
        v_20 = vdd * 0.2
        v_80 = vdd * 0.8

        content = self._header(corner)
        content += self._global_options()
        content += self._include_block(subcircuit)
        content += "\n"

        # Instantiate DUT
        ports = " ".join(subcircuit.ports)
        content += f"x_dut ({ports}) {subcircuit.name}\n\n"

        # Power supplies
        content += self._supply_sources(subcircuit, corner)

        # Enable HIGH
        content += f"v_en ({en_pin} 0) vsource dc={vdd}\n\n"

        # Input pulse LOW→HIGH
        content += (
            f"v_din ({din_pin} 0) vsource type=pulse "
            f"val0=0 val1={vdd} "
            f"delay=1n rise={self.t_rise} fall={self.t_rise} "
            f"width={self.t_sim / 2} period={self.t_sim}\n\n"
        )

        # Load: R_fixture to V_fixture
        content += f"r_fix ({pad_pin} v_fix) resistor r={self.r_fixture}\n"
        content += f"v_fix_src (v_fix 0) vsource dc={v_fixture}\n\n"

        # Transient analysis
        content += f"tran_sim tran stop={self.t_sim}\n\n"

        # Measurement statements
        content += (
            f"meas_t20 tran_sim cross sig=v_pad dir=rise val={v_20} "
            f"name=t20_rise\n"
        )
        content += (
            f"meas_t80 tran_sim cross sig=v_pad dir=rise val={v_80} "
            f"name=t80_rise\n"
        )

        name = f"rising_{corner.suffix}"
        expected = ["t20_rise", "t80_rise"]
        return SimDeck(
            name=name,
            deck_type=self.deck_type,
            corner=corner,
            content=content,
            expected_measurements=expected,
        )


class FallingWaveformDeckGen(DeckGenerator):
    """Generate transient deck for falling waveform.

    Stimulus: din pulse HIGH→LOW, R_fix=50Ω to VDD/2.
    Measures V(pad) vs time + 80%/20% crossing times.
    """

    deck_type = "falling"

    def __init__(
        self,
        r_fixture: float = 50.0,
        t_rise: float = 0.2e-9,
        t_sim: float = 20e-9,
    ):
        self.r_fixture = r_fixture
        self.t_rise = t_rise
        self.t_sim = t_sim

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        pad_pin = self._find_pin(subcircuit, "pad")
        din_pin = self._find_pin(subcircuit, "input")
        en_pin = self._find_pin(subcircuit, "enable")

        v_fixture = vdd / 2
        v_80 = vdd * 0.8
        v_20 = vdd * 0.2

        content = self._header(corner)
        content += self._global_options()
        content += self._include_block(subcircuit)
        content += "\n"

        # Instantiate DUT
        ports = " ".join(subcircuit.ports)
        content += f"x_dut ({ports}) {subcircuit.name}\n\n"

        # Power supplies
        content += self._supply_sources(subcircuit, corner)

        # Enable HIGH
        content += f"v_en ({en_pin} 0) vsource dc={vdd}\n\n"

        # Input pulse HIGH→LOW
        content += (
            f"v_din ({din_pin} 0) vsource type=pulse "
            f"val0={vdd} val1=0 "
            f"delay=1n rise={self.t_rise} fall={self.t_rise} "
            f"width={self.t_sim / 2} period={self.t_sim}\n\n"
        )

        # Load: R_fixture to V_fixture
        content += f"r_fix ({pad_pin} v_fix) resistor r={self.r_fixture}\n"
        content += f"v_fix_src (v_fix 0) vsource dc={v_fixture}\n\n"

        # Transient analysis
        content += f"tran_sim tran stop={self.t_sim}\n\n"

        # Measurement statements
        content += (
            f"meas_t80 tran_sim cross sig=v_pad dir=fall val={v_80} "
            f"name=t80_fall\n"
        )
        content += (
            f"meas_t20 tran_sim cross sig=v_pad dir=fall val={v_20} "
            f"name=t20_fall\n"
        )

        name = f"falling_{corner.suffix}"
        expected = ["t80_fall", "t20_fall"]
        return SimDeck(
            name=name,
            deck_type=self.deck_type,
            corner=corner,
            content=content,
            expected_measurements=expected,
        )
