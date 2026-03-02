"""Tests for simulator syntax adapters."""

from __future__ import annotations

import pytest

from spice_to_ibis.syntax import (
    NgspiceSyntax,
    SimSyntax,
    SpectreSyntax,
    get_syntax,
)


class TestSpectreSyntax:
    def test_comment(self):
        s = SpectreSyntax()
        assert s.comment("hello") == "// hello"

    def test_header(self):
        s = SpectreSyntax()
        h = s.header("pulldown", "typ", "tt_1.8V_25.0C")
        assert "// Auto-generated pulldown deck" in h
        assert "// Corner: typ (tt_1.8V_25.0C)" in h
        assert "simulator lang=spectre" in h

    def test_global_options(self):
        s = SpectreSyntax()
        assert s.global_options() == "simulatorOptions options rawfmt=psfascii\n"

    def test_include(self):
        s = SpectreSyntax()
        assert s.include("models/nmos.scs") == 'include "models/nmos.scs"'

    def test_voltage_source(self):
        s = SpectreSyntax()
        result = s.voltage_source("v_vdd", "vdd", "0", 1.8)
        assert result == "v_vdd (vdd 0) vsource dc=1.8"

    def test_pulse_source(self):
        s = SpectreSyntax()
        result = s.pulse_source(
            "v_din", "din", "0", 0, 1.8, "1n", 2e-10, 2e-10, 1e-8, 2e-8
        )
        assert "v_din (din 0) vsource type=pulse" in result
        assert "val0=0 val1=1.8" in result
        assert "delay=1n" in result

    def test_resistor(self):
        s = SpectreSyntax()
        result = s.resistor("r_fix", "pad", "v_fix", 50)
        assert result == "r_fix (pad v_fix) resistor r=50"

    def test_subcircuit_instance(self):
        s = SpectreSyntax()
        result = s.subcircuit_instance(
            "x_dut", ["pad", "vdd", "vss", "din", "en"], "buf_io"
        )
        assert result == "x_dut (pad vdd vss din en) buf_io"

    def test_dc_sweep(self):
        s = SpectreSyntax()
        result = s.dc_sweep("v_pad", -1.8, 3.6, 0.018)
        assert result == "dc_sweep dc dev=v_pad param=dc start=-1.8 stop=3.6 step=0.018"

    def test_transient(self):
        s = SpectreSyntax()
        result = s.transient(2e-8)
        assert result == "tran_sim tran stop=2e-08"

    def test_meas_cross(self):
        s = SpectreSyntax()
        result = s.meas_cross("meas_t20", "pad", "rise", 0.36, "t20_rise")
        assert "meas_t20 tran_sim cross sig=v_pad dir=rise" in result
        assert "val=0.36 name=t20_rise" in result

    def test_control_block_empty(self):
        s = SpectreSyntax()
        assert s.control_block("test") == ""

    def test_end_statement_empty(self):
        s = SpectreSyntax()
        assert s.end_statement() == ""

    def test_file_extension(self):
        s = SpectreSyntax()
        assert s.file_extension == ".scs"


class TestNgspiceSyntax:
    def test_comment(self):
        s = NgspiceSyntax()
        assert s.comment("hello") == "* hello"

    def test_header(self):
        s = NgspiceSyntax()
        h = s.header("pulldown", "typ", "tt_1.8V_25.0C")
        assert "* Auto-generated pulldown deck" in h
        assert "* Corner: typ (tt_1.8V_25.0C)" in h
        assert "simulator lang" not in h

    def test_global_options(self):
        s = NgspiceSyntax()
        assert s.global_options() == ".options\n"

    def test_include(self):
        s = NgspiceSyntax()
        assert s.include("models/nmos.cir") == '.include "models/nmos.cir"'

    def test_voltage_source(self):
        s = NgspiceSyntax()
        result = s.voltage_source("v_vdd", "vdd", "0", 1.8)
        assert result == "V_vdd vdd 0 DC 1.8"

    def test_voltage_source_capitalization(self):
        s = NgspiceSyntax()
        result = s.voltage_source("v_pad", "pad", "0", 0)
        assert result.startswith("V_pad")

    def test_pulse_source(self):
        s = NgspiceSyntax()
        result = s.pulse_source(
            "v_din", "din", "0", 0, 1.8, "1n", 2e-10, 2e-10, 1e-8, 2e-8
        )
        assert result.startswith("V_din din 0")
        assert "PULSE(0 1.8 1n" in result

    def test_resistor(self):
        s = NgspiceSyntax()
        result = s.resistor("r_fix", "pad", "v_fix", 50)
        assert result == "R_fix pad v_fix 50"

    def test_subcircuit_instance(self):
        s = NgspiceSyntax()
        result = s.subcircuit_instance(
            "x_dut", ["pad", "vdd", "vss", "din", "en"], "buf_io"
        )
        assert result == "X_dut pad vdd vss din en buf_io"

    def test_dc_sweep(self):
        s = NgspiceSyntax()
        result = s.dc_sweep("v_pad", -1.8, 3.6, 0.018)
        assert result == ".dc V_pad -1.8 3.6 0.018"

    def test_transient_with_tstep(self):
        s = NgspiceSyntax()
        result = s.transient(2e-8, tstep=1e-11)
        assert result == ".tran 1e-11 2e-08"

    def test_transient_auto_tstep(self):
        s = NgspiceSyntax()
        result = s.transient(2e-8)
        assert result == ".tran 2e-11 2e-08"

    def test_meas_cross_rise(self):
        s = NgspiceSyntax()
        result = s.meas_cross("meas_t20", "pad", "rise", 0.36, "t20_rise")
        assert result == ".meas tran t20_rise WHEN v(pad)=0.36 RISE=1"

    def test_meas_cross_fall(self):
        s = NgspiceSyntax()
        result = s.meas_cross("meas_t80", "pad", "fall", 1.44, "t80_fall")
        assert result == ".meas tran t80_fall WHEN v(pad)=1.44 FALL=1"

    def test_control_block(self):
        s = NgspiceSyntax()
        block = s.control_block("pulldown_tt")
        assert ".control" in block
        assert "set filetype=ascii" in block
        assert "run" in block
        assert "write pulldown_tt.raw" in block
        assert ".endc" in block

    def test_end_statement(self):
        s = NgspiceSyntax()
        assert s.end_statement() == ".end\n"

    def test_file_extension(self):
        s = NgspiceSyntax()
        assert s.file_extension == ".cir"


class TestGetSyntax:
    def test_get_spectre(self):
        s = get_syntax("spectre")
        assert isinstance(s, SpectreSyntax)

    def test_get_ngspice(self):
        s = get_syntax("ngspice")
        assert isinstance(s, NgspiceSyntax)

    def test_default_is_spectre(self):
        s = get_syntax()
        assert isinstance(s, SpectreSyntax)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown simulator"):
            get_syntax("hspice")

    def test_both_are_sim_syntax(self):
        assert isinstance(get_syntax("spectre"), SimSyntax)
        assert isinstance(get_syntax("ngspice"), SimSyntax)
