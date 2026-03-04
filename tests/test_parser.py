"""Tests for the Spectre and NgSPICE subcircuit parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

from spice_to_ibis.models.spice import PinRole
from spice_to_ibis.parser import NgspiceParser, SpiceParser, get_parser

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


class TestNgspiceParser:
    def test_parse_reads_lines(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "buf_io.cir")
        assert len(result.raw_lines) > 0

    def test_parse_extracts_name(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "buf_io.cir")
        assert result.name == "buf_io"

    def test_parse_extracts_ports(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "buf_io.cir")
        assert result.ports == ["pad", "vdd", "vss", "din", "en"]

    def test_parse_extracts_inline_parameters(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "buf_io.cir")
        assert result.parameters == {"wp": "2u", "wn": "1u"}

    def test_parse_extracts_includes(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "buf_io.cir")
        assert "models/nmos.cir" in result.include_paths
        assert "models/pmos.cir" in result.include_paths

    def test_parse_with_pin_map(self):
        parser = NgspiceParser()
        pin_map = {
            "pad": PinRole.PAD,
            "vdd": PinRole.VDD,
            "vss": PinRole.VSS,
            "din": PinRole.INPUT,
            "en": PinRole.ENABLE,
        }
        result = parser.parse(FIXTURES / "buf_io.cir", pin_map=pin_map)
        assert result.pin_map["pad"] == PinRole.PAD
        assert result.pin_map["en"] == PinRole.ENABLE

    def test_parse_no_pin_map_by_default(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "buf_io.cir")
        assert result.pin_map == {}


class TestParseLvdsSpectre:
    def test_parse_extracts_name(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "lvds_driver.scs")
        assert result.name == "lvds_driver"

    def test_parse_extracts_differential_ports(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "lvds_driver.scs")
        assert result.ports == ["outp", "outn", "vdd", "vss", "din", "en"]

    def test_parse_extracts_parameters(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "lvds_driver.scs")
        assert result.parameters == {"iref": "175u", "lmin": "180n"}

    def test_parse_includes(self):
        parser = SpiceParser()
        result = parser.parse(FIXTURES / "lvds_driver.scs")
        assert "models/nmos.scs" in result.include_paths
        assert "models/pmos.scs" in result.include_paths

    def test_parse_with_differential_pin_map(self):
        parser = SpiceParser()
        pin_map = {
            "outp": PinRole.PAD,
            "outn": PinRole.PAD,
            "vdd": PinRole.VDD,
            "vss": PinRole.VSS,
            "din": PinRole.INPUT,
            "en": PinRole.ENABLE,
        }
        result = parser.parse(FIXTURES / "lvds_driver.scs", pin_map=pin_map)
        assert result.pin_map["outp"] == PinRole.PAD
        assert result.pin_map["outn"] == PinRole.PAD


class TestParseLvdsNgspice:
    def test_parse_extracts_name(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "lvds_driver.cir")
        assert result.name == "lvds_driver"

    def test_parse_extracts_differential_ports(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "lvds_driver.cir")
        assert result.ports == ["outp", "outn", "vdd", "vss", "din", "en"]

    def test_parse_extracts_parameters(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "lvds_driver.cir")
        assert result.parameters == {"iref": "175u", "lmin": "180n"}

    def test_parse_includes(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "lvds_driver.cir")
        assert "models/nmos.cir" in result.include_paths
        assert "models/pmos.cir" in result.include_paths

    def test_six_ports(self):
        parser = NgspiceParser()
        result = parser.parse(FIXTURES / "lvds_driver.cir")
        assert len(result.ports) == 6

    def test_ports_match_spectre_version(self):
        sp = SpiceParser().parse(FIXTURES / "lvds_driver.scs")
        ng = NgspiceParser().parse(FIXTURES / "lvds_driver.cir")
        assert sp.ports == ng.ports
        assert sp.name == ng.name
        assert sp.parameters == ng.parameters


class TestGetParser:
    def test_get_spectre_parser(self):
        parser = get_parser("spectre")
        assert isinstance(parser, SpiceParser)

    def test_get_ngspice_parser(self):
        parser = get_parser("ngspice")
        assert isinstance(parser, NgspiceParser)

    def test_default_is_spectre(self):
        parser = get_parser()
        assert isinstance(parser, SpiceParser)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown simulator"):
            get_parser("hspice")
