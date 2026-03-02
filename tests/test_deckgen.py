"""Tests for deck generation modules."""

from __future__ import annotations

import pytest

from spice_to_ibis.deckgen.base import SimDeck
from spice_to_ibis.deckgen.dc_sweep import (
    ClampDeckGen,
    PulldownDeckGen,
    PullupDeckGen,
)
from spice_to_ibis.deckgen.transient import (
    FallingWaveformDeckGen,
    RisingWaveformDeckGen,
)
from spice_to_ibis.models.corners import Corner
from spice_to_ibis.models.spice import PinRole, SpiceSubcircuit
from spice_to_ibis.syntax import NgspiceSyntax


@pytest.fixture
def subcircuit():
    return SpiceSubcircuit(
        name="buf_io",
        ports=["pad", "vdd", "vss", "din", "en"],
        pin_map={
            "pad": PinRole.PAD,
            "vdd": PinRole.VDD,
            "vss": PinRole.VSS,
            "din": PinRole.INPUT,
            "en": PinRole.ENABLE,
        },
        include_paths=["models/nmos.scs", "models/pmos.scs"],
    )


@pytest.fixture
def typ_corner():
    return Corner("typ", "tt", 1.8, 25.0)


class TestPulldownDeckGen:
    def test_generates_sim_deck(self, subcircuit, typ_corner):
        gen = PulldownDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert isinstance(deck, SimDeck)
        assert deck.deck_type == "pulldown"
        assert deck.corner is typ_corner

    def test_deck_name_includes_corner(self, subcircuit, typ_corner):
        gen = PulldownDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert deck.name == "pulldown_tt_1.8V_25.0C"

    def test_deck_contains_subcircuit_instantiation(self, subcircuit, typ_corner):
        gen = PulldownDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "x_dut (pad vdd vss din en) buf_io" in deck.content

    def test_deck_contains_includes(self, subcircuit, typ_corner):
        gen = PulldownDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert 'include "models/nmos.scs"' in deck.content
        assert 'include "models/pmos.scs"' in deck.content

    def test_din_driven_low(self, subcircuit, typ_corner):
        gen = PulldownDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "v_din (din 0) vsource dc=0" in deck.content

    def test_enable_driven_high(self, subcircuit, typ_corner):
        gen = PulldownDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "v_en (en 0) vsource dc=1.8" in deck.content

    def test_dc_sweep_range(self, subcircuit, typ_corner):
        gen = PulldownDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "start=-1.8" in deck.content
        assert "stop=3.6" in deck.content

    def test_rawfmt_psfascii(self, subcircuit, typ_corner):
        gen = PulldownDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "rawfmt=psfascii" in deck.content


class TestPullupDeckGen:
    def test_generates_pullup(self, subcircuit, typ_corner):
        gen = PullupDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert deck.deck_type == "pullup"
        assert deck.name == "pullup_tt_1.8V_25.0C"

    def test_din_driven_high(self, subcircuit, typ_corner):
        gen = PullupDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "v_din (din 0) vsource dc=1.8" in deck.content

    def test_enable_driven_high(self, subcircuit, typ_corner):
        gen = PullupDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "v_en (en 0) vsource dc=1.8" in deck.content


class TestClampDeckGen:
    def test_generates_clamp(self, subcircuit, typ_corner):
        gen = ClampDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert deck.deck_type == "clamp"
        assert deck.name == "clamp_tt_1.8V_25.0C"

    def test_enable_driven_low(self, subcircuit, typ_corner):
        gen = ClampDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "v_en (en 0) vsource dc=0" in deck.content


class TestRisingWaveformDeckGen:
    def test_generates_rising(self, subcircuit, typ_corner):
        gen = RisingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert deck.deck_type == "rising"
        assert deck.name == "rising_tt_1.8V_25.0C"

    def test_has_fixture_resistor(self, subcircuit, typ_corner):
        gen = RisingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "r_fix (pad v_fix) resistor r=50" in deck.content

    def test_fixture_voltage(self, subcircuit, typ_corner):
        gen = RisingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "v_fix_src (v_fix 0) vsource dc=0.9" in deck.content

    def test_input_pulse_low_to_high(self, subcircuit, typ_corner):
        gen = RisingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "val0=0 val1=1.8" in deck.content

    def test_measurement_statements(self, subcircuit, typ_corner):
        gen = RisingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "t20_rise" in deck.content
        assert "t80_rise" in deck.content

    def test_expected_measurements(self, subcircuit, typ_corner):
        gen = RisingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert deck.expected_measurements == ["t20_rise", "t80_rise"]

    def test_transient_analysis(self, subcircuit, typ_corner):
        gen = RisingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "tran_sim tran stop=" in deck.content

    def test_custom_fixture(self, subcircuit, typ_corner):
        gen = RisingWaveformDeckGen(r_fixture=75.0)
        deck = gen.generate(subcircuit, typ_corner)
        assert "r_fix (pad v_fix) resistor r=75" in deck.content


class TestFallingWaveformDeckGen:
    def test_generates_falling(self, subcircuit, typ_corner):
        gen = FallingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert deck.deck_type == "falling"
        assert deck.name == "falling_tt_1.8V_25.0C"

    def test_input_pulse_high_to_low(self, subcircuit, typ_corner):
        gen = FallingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "val0=1.8 val1=0" in deck.content

    def test_measurement_statements(self, subcircuit, typ_corner):
        gen = FallingWaveformDeckGen()
        deck = gen.generate(subcircuit, typ_corner)
        assert "t80_fall" in deck.content
        assert "t20_fall" in deck.content


class TestAllDeckGenerators:
    """Test generating all 5 deck types for one corner."""

    def test_generate_all_decks(self, subcircuit, typ_corner):
        generators = [
            PulldownDeckGen(),
            PullupDeckGen(),
            ClampDeckGen(),
            RisingWaveformDeckGen(),
            FallingWaveformDeckGen(),
        ]
        decks = [g.generate(subcircuit, typ_corner) for g in generators]
        types = {d.deck_type for d in decks}
        assert types == {"pulldown", "pullup", "clamp", "rising", "falling"}

    def test_all_decks_have_content(self, subcircuit, typ_corner):
        generators = [
            PulldownDeckGen(),
            PullupDeckGen(),
            ClampDeckGen(),
            RisingWaveformDeckGen(),
            FallingWaveformDeckGen(),
        ]
        for gen in generators:
            deck = gen.generate(subcircuit, typ_corner)
            assert len(deck.content) > 100
            assert "simulator lang=spectre" in deck.content


class TestNgspiceDeckGen:
    """Test NgSPICE deck generation for all 5 deck types."""

    @pytest.fixture
    def ng_syntax(self):
        return NgspiceSyntax()

    def test_pulldown_ngspice_header(self, subcircuit, typ_corner, ng_syntax):
        gen = PulldownDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert "* Auto-generated pulldown deck" in deck.content
        assert "simulator lang" not in deck.content

    def test_pulldown_ngspice_sources(self, subcircuit, typ_corner, ng_syntax):
        gen = PulldownDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert "V_vdd vdd 0 DC 1.8" in deck.content
        assert "V_vss vss 0 DC 0" in deck.content
        assert "V_din din 0 DC 0" in deck.content
        assert "V_en en 0 DC 1.8" in deck.content

    def test_pulldown_ngspice_instance(self, subcircuit, typ_corner, ng_syntax):
        gen = PulldownDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert "X_dut pad vdd vss din en buf_io" in deck.content

    def test_pulldown_ngspice_dc_sweep(self, subcircuit, typ_corner, ng_syntax):
        gen = PulldownDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert ".dc V_pad -1.8 3.6 0.018" in deck.content

    def test_pulldown_ngspice_control_block(self, subcircuit, typ_corner, ng_syntax):
        gen = PulldownDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert ".control" in deck.content
        assert "run" in deck.content
        assert ".endc" in deck.content
        assert ".end" in deck.content

    def test_pulldown_ngspice_include(self, subcircuit, typ_corner, ng_syntax):
        gen = PulldownDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert '.include "models/nmos.scs"' in deck.content

    def test_pullup_ngspice(self, subcircuit, typ_corner, ng_syntax):
        gen = PullupDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert "V_din din 0 DC 1.8" in deck.content
        assert ".dc V_pad" in deck.content

    def test_clamp_ngspice(self, subcircuit, typ_corner, ng_syntax):
        gen = ClampDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert "V_en en 0 DC 0" in deck.content
        assert ".dc V_pad" in deck.content

    def test_rising_ngspice_pulse(self, subcircuit, typ_corner, ng_syntax):
        gen = RisingWaveformDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert "V_din din 0 PULSE(0 1.8" in deck.content

    def test_rising_ngspice_resistor(self, subcircuit, typ_corner, ng_syntax):
        gen = RisingWaveformDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert "R_fix pad v_fix 50" in deck.content

    def test_rising_ngspice_transient(self, subcircuit, typ_corner, ng_syntax):
        gen = RisingWaveformDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert ".tran" in deck.content

    def test_rising_ngspice_meas(self, subcircuit, typ_corner, ng_syntax):
        gen = RisingWaveformDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert ".meas tran t20_rise WHEN" in deck.content
        assert ".meas tran t80_rise WHEN" in deck.content
        assert "RISE=1" in deck.content

    def test_falling_ngspice_pulse(self, subcircuit, typ_corner, ng_syntax):
        gen = FallingWaveformDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert "V_din din 0 PULSE(1.8 0" in deck.content

    def test_falling_ngspice_meas(self, subcircuit, typ_corner, ng_syntax):
        gen = FallingWaveformDeckGen(syntax=ng_syntax)
        deck = gen.generate(subcircuit, typ_corner)
        assert ".meas tran t80_fall WHEN" in deck.content
        assert ".meas tran t20_fall WHEN" in deck.content
        assert "FALL=1" in deck.content

    def test_all_ngspice_decks(self, subcircuit, typ_corner, ng_syntax):
        generators = [
            PulldownDeckGen(syntax=ng_syntax),
            PullupDeckGen(syntax=ng_syntax),
            ClampDeckGen(syntax=ng_syntax),
            RisingWaveformDeckGen(syntax=ng_syntax),
            FallingWaveformDeckGen(syntax=ng_syntax),
        ]
        for gen in generators:
            deck = gen.generate(subcircuit, typ_corner)
            assert len(deck.content) > 100
            assert ".end" in deck.content
            assert "simulator lang" not in deck.content
