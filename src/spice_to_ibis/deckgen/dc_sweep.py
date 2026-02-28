"""DC sweep deck generators for V-I table characterization."""

from __future__ import annotations

from spice_to_ibis.deckgen.base import DeckGenerator, SimDeck
from spice_to_ibis.models.corners import Corner
from spice_to_ibis.models.spice import SpiceSubcircuit


class PulldownDeckGen(DeckGenerator):
    """Generate DC sweep deck for pulldown V-I curve.

    Stimulus: din=LOW (0V), en=HIGH (VDD), sweep V(pad) from -VDD to 2*VDD.
    Measures I(pad) vs V(pad) with output driver pulling low.
    """

    deck_type = "pulldown"

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        pad_pin = self._find_pin(subcircuit, "pad")
        din_pin = self._find_pin(subcircuit, "input")
        en_pin = self._find_pin(subcircuit, "enable")

        content = self._header(corner)
        content += self._global_options()
        content += self._include_block(subcircuit)
        content += "\n"

        # Instantiate DUT
        ports = " ".join(subcircuit.ports)
        content += f"x_dut ({ports}) {subcircuit.name}\n\n"

        # Power supplies
        content += self._supply_sources(subcircuit, corner)

        # Drive input LOW to activate pulldown, enable HIGH
        content += f"v_din ({din_pin} 0) vsource dc=0\n"
        content += f"v_en ({en_pin} 0) vsource dc={vdd}\n\n"

        # Pad sweep source
        content += f"v_pad ({pad_pin} 0) vsource dc=0\n\n"

        # DC sweep analysis
        content += (
            f"dc_sweep dc dev=v_pad param=dc "
            f"start={-vdd} stop={2 * vdd} step={vdd / 100}\n"
        )

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
    """

    deck_type = "pullup"

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        pad_pin = self._find_pin(subcircuit, "pad")
        din_pin = self._find_pin(subcircuit, "input")
        en_pin = self._find_pin(subcircuit, "enable")

        content = self._header(corner)
        content += self._global_options()
        content += self._include_block(subcircuit)
        content += "\n"

        # Instantiate DUT
        ports = " ".join(subcircuit.ports)
        content += f"x_dut ({ports}) {subcircuit.name}\n\n"

        # Power supplies
        content += self._supply_sources(subcircuit, corner)

        # Drive input HIGH to activate pullup, enable HIGH
        content += f"v_din ({din_pin} 0) vsource dc={vdd}\n"
        content += f"v_en ({en_pin} 0) vsource dc={vdd}\n\n"

        # Pad sweep source
        content += f"v_pad ({pad_pin} 0) vsource dc=0\n\n"

        # DC sweep analysis
        content += (
            f"dc_sweep dc dev=v_pad param=dc "
            f"start={-vdd} stop={2 * vdd} step={vdd / 100}\n"
        )

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
    """

    deck_type = "clamp"

    def generate(
        self,
        subcircuit: SpiceSubcircuit,
        corner: Corner,
    ) -> SimDeck:
        vdd = corner.voltage
        pad_pin = self._find_pin(subcircuit, "pad")
        din_pin = self._find_pin(subcircuit, "input")
        en_pin = self._find_pin(subcircuit, "enable")

        content = self._header(corner)
        content += self._global_options()
        content += self._include_block(subcircuit)
        content += "\n"

        # Instantiate DUT
        ports = " ".join(subcircuit.ports)
        content += f"x_dut ({ports}) {subcircuit.name}\n\n"

        # Power supplies
        content += self._supply_sources(subcircuit, corner)

        # Input don't-care, enable LOW for tri-state
        content += f"v_din ({din_pin} 0) vsource dc=0\n"
        content += f"v_en ({en_pin} 0) vsource dc=0\n\n"

        # Pad sweep source
        content += f"v_pad ({pad_pin} 0) vsource dc=0\n\n"

        # DC sweep analysis
        content += (
            f"dc_sweep dc dev=v_pad param=dc "
            f"start={-vdd} stop={2 * vdd} step={vdd / 100}\n"
        )

        name = f"clamp_{corner.suffix}"
        return SimDeck(
            name=name,
            deck_type=self.deck_type,
            corner=corner,
            content=content,
        )
