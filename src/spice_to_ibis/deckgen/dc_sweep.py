"""DC sweep deck generators for V-I table characterization."""

from __future__ import annotations

from spice_to_ibis.deckgen.base import DeckGenerator, SimDeck
from spice_to_ibis.models.corners import Corner
from spice_to_ibis.models.spice import SpiceSubcircuit
from spice_to_ibis.syntax import SimSyntax


class PulldownDeckGen(DeckGenerator):
    """Generate DC sweep deck for pulldown V-I curve.

    Stimulus: din=LOW (0V), en=HIGH (VDD), sweep V(pad) from -VDD to 2*VDD.
    Measures I(pad) vs V(pad) with output driver pulling low.

    For differential subcircuits, sweeps pad_p and holds pad_n at Vcm (VDD/2).
    """

    deck_type = "pulldown"

    def __init__(self, syntax: SimSyntax | None = None):
        super().__init__(syntax)

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        diff = self._is_differential(subcircuit)
        if diff:
            pad_pin, pad_n = self._diff_pad_pins(subcircuit)
        else:
            pad_pin = self._find_pin(subcircuit, "pad")
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

        # Drive input LOW to activate pulldown, enable HIGH
        content += self.syntax.voltage_source("v_din", din_pin, "0", 0) + "\n"
        content += self.syntax.voltage_source("v_en", en_pin, "0", vdd) + "\n\n"

        # Pad sweep source
        content += self.syntax.voltage_source("v_pad", pad_pin, "0", 0) + "\n"
        if diff:
            content += (
                self.syntax.voltage_source("v_padn", pad_n, "0", vdd / 2) + "\n"
            )
        content += "\n"

        # DC sweep analysis
        content += self.syntax.dc_sweep("v_pad", -vdd, 2 * vdd, vdd / 100) + "\n"

        # Control block and end (non-empty for NgSPICE)
        content += self.syntax.control_block(f"pulldown_{corner.suffix}")
        content += self.syntax.end_statement()

        name = f"pulldown_{corner.suffix}"
        return SimDeck(
            name=name,
            deck_type=self.deck_type,
            corner=corner,
            content=content,
        )


class PullupDeckGen(DeckGenerator):
    """Generate DC sweep deck for pullup V-I curve.

    Stimulus: din=HIGH (VDD), en=HIGH (VDD), sweep V(pad) from -VDD to 2*VDD.
    Measures I(pad) vs V(pad) with output driver pulling high.
    Pullup V-I is referenced to VDD per IBIS spec.

    For differential subcircuits, sweeps pad_p and holds pad_n at Vcm (VDD/2).
    """

    deck_type = "pullup"

    def __init__(self, syntax: SimSyntax | None = None):
        super().__init__(syntax)

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        diff = self._is_differential(subcircuit)
        if diff:
            pad_pin, pad_n = self._diff_pad_pins(subcircuit)
        else:
            pad_pin = self._find_pin(subcircuit, "pad")
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

        # Drive input HIGH to activate pullup, enable HIGH
        content += self.syntax.voltage_source("v_din", din_pin, "0", vdd) + "\n"
        content += self.syntax.voltage_source("v_en", en_pin, "0", vdd) + "\n\n"

        # Pad sweep source
        content += self.syntax.voltage_source("v_pad", pad_pin, "0", 0) + "\n"
        if diff:
            content += (
                self.syntax.voltage_source("v_padn", pad_n, "0", vdd / 2) + "\n"
            )
        content += "\n"

        # DC sweep analysis
        content += self.syntax.dc_sweep("v_pad", -vdd, 2 * vdd, vdd / 100) + "\n"

        # Control block and end (non-empty for NgSPICE)
        content += self.syntax.control_block(f"pullup_{corner.suffix}")
        content += self.syntax.end_statement()

        name = f"pullup_{corner.suffix}"
        return SimDeck(
            name=name,
            deck_type=self.deck_type,
            corner=corner,
            content=content,
        )


class ClampDeckGen(DeckGenerator):
    """Generate DC sweep deck for clamp (tri-state) V-I curve.

    Stimulus: en=LOW (0V, tri-state), sweep V(pad) from -VDD to 2*VDD.
    Measures I(pad) which is then split into GND clamp and POWER clamp.

    For differential subcircuits, sweeps pad_p and holds pad_n at Vcm (VDD/2).
    """

    deck_type = "clamp"

    def __init__(self, syntax: SimSyntax | None = None):
        super().__init__(syntax)

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        diff = self._is_differential(subcircuit)
        if diff:
            pad_pin, pad_n = self._diff_pad_pins(subcircuit)
        else:
            pad_pin = self._find_pin(subcircuit, "pad")
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

        # Input don't-care, enable LOW for tri-state
        content += self.syntax.voltage_source("v_din", din_pin, "0", 0) + "\n"
        content += self.syntax.voltage_source("v_en", en_pin, "0", 0) + "\n\n"

        # Pad sweep source
        content += self.syntax.voltage_source("v_pad", pad_pin, "0", 0) + "\n"
        if diff:
            content += (
                self.syntax.voltage_source("v_padn", pad_n, "0", vdd / 2) + "\n"
            )
        content += "\n"

        # DC sweep analysis
        content += self.syntax.dc_sweep("v_pad", -vdd, 2 * vdd, vdd / 100) + "\n"

        # Control block and end (non-empty for NgSPICE)
        content += self.syntax.control_block(f"clamp_{corner.suffix}")
        content += self.syntax.end_statement()

        name = f"clamp_{corner.suffix}"
        return SimDeck(
            name=name,
            deck_type=self.deck_type,
            corner=corner,
            content=content,
        )
