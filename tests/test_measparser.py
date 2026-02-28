"""Tests for the measurement result parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from spice_to_ibis.measparser import MeasParser, MeasResult

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseMt0:
    def test_parse_mt0_file(self):
        parser = MeasParser()
        result = parser.parse_mt0(FIXTURES / "sample.mt0")
        assert "t20_rise" in result
        assert "t80_rise" in result
        assert result["t20_rise"] == pytest.approx(2.345e-9)
        assert result["t80_rise"] == pytest.approx(3.456e-9)

    def test_parse_mt0_text(self):
        parser = MeasParser()
        text = 'HEADER\nVALUE\n"meas1" 1.5e-9\n"meas2" 2.5e-9\nEND\n'
        result = parser._parse_mt0_text(text)
        assert result == {"meas1": 1.5e-9, "meas2": 2.5e-9}

    def test_parse_mt0_empty_value_section(self):
        parser = MeasParser()
        text = "HEADER\nVALUE\nEND\n"
        result = parser._parse_mt0_text(text)
        assert result == {}


class TestParsePsfAscii:
    def test_parse_dc_sweep_file(self):
        parser = MeasParser()
        voltages, currents = parser.parse_psf_ascii(FIXTURES / "sample_dc.txt")
        assert len(voltages) == 16
        assert len(currents) == 16
        assert voltages[0] == pytest.approx(-1.8)
        assert voltages[-1] == pytest.approx(3.6)

    def test_parse_transient_file(self):
        parser = MeasParser()
        times, voltages = parser.parse_psf_ascii(FIXTURES / "sample_tran.txt")
        assert len(times) == 11
        assert times[0] == pytest.approx(0.0)
        assert voltages[-1] == pytest.approx(1.8)

    def test_parse_psf_ascii_text(self):
        parser = MeasParser()
        text = "HEADER\nVALUE\n0.0 1.0\n0.5 2.0\n1.0 3.0\nEND\n"
        x, y = parser._parse_psf_ascii_text(text)
        assert x == [0.0, 0.5, 1.0]
        assert y == [1.0, 2.0, 3.0]


class TestParseDcSweep:
    def test_parse_dc_sweep(self):
        parser = MeasParser()
        result = parser.parse_dc_sweep(
            FIXTURES / "sample_dc.txt",
            deck_name="pulldown_tt",
            corner_label="typ",
        )
        assert isinstance(result, MeasResult)
        assert result.deck_name == "pulldown_tt"
        assert result.corner_label == "typ"
        assert len(result.sweep_voltage) == 16
        assert len(result.sweep_current) == 16


class TestParseTransient:
    def test_parse_transient_with_mt0(self):
        parser = MeasParser()
        result = parser.parse_transient(
            waveform_path=FIXTURES / "sample_tran.txt",
            mt0_path=FIXTURES / "sample.mt0",
            deck_name="rising_tt",
            corner_label="typ",
        )
        assert isinstance(result, MeasResult)
        assert len(result.waveform_time) == 11
        assert len(result.waveform_voltage) == 11
        assert "t20_rise" in result.measurements
        assert "t80_rise" in result.measurements

    def test_parse_transient_without_mt0(self):
        parser = MeasParser()
        result = parser.parse_transient(
            waveform_path=FIXTURES / "sample_tran.txt",
            deck_name="rising_tt",
            corner_label="typ",
        )
        assert result.measurements == {}
        assert len(result.waveform_time) == 11
