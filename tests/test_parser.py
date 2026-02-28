"""Tests for the Spectre subcircuit parser."""

from __future__ import annotations

from pathlib import Path

from spice_to_ibis.models.spice import PinRole
from spice_to_ibis.parser import SpiceParser

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseSubcircuit:
    def test_parse_reads_lines(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "buf_io.scs")
        assert len(result.raw_lines) > 0

    def test_parse_extracts_name(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "buf_io.scs")
        assert result.name == "buf_io"

    def test_parse_extracts_ports(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "buf_io.scs")
        assert result.ports == ["pad", "vdd", "vss", "din", "en"]

    def test_parse_extracts_parameters(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "buf_io.scs")
        assert result.parameters == {"wp": "2u", "wn": "1u"}

    def test_parse_extracts_includes(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "buf_io.scs")
        assert "models/nmos.scs" in result.include_paths
        assert "models/pmos.scs" in result.include_paths

    def test_parse_with_pin_map(self):
        parser = SpiceParser()
        pin_map = {
            "pad": PinRole.PAD,
            "vdd": PinRole.VDD,
            "vss": PinRole.VSS,
            "din": PinRole.INPUT,
            "en": PinRole.ENABLE,
        }
        result = parser.parse(FIXTURES / "buf_io.scs", pin_map=pin_map)
        assert result.pin_map["pad"] == PinRole.PAD
        assert result.pin_map["en"] == PinRole.ENABLE

    def test_parse_simple_subcircuit(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "simple.scs")
        assert result.name == "inverter"
        assert result.ports == ["out", "in", "vdd", "vss"]
        assert result.parameters == {}
        assert result.include_paths == []

    def test_parse_no_pin_map_by_default(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "simple.scs")
        assert result.pin_map == {}
