"""Tests for the SPICE parser."""

from spice_to_ibis.parser import SpiceModel, SpiceParser


def test_spice_model_defaults():
    model = SpiceModel()
    assert model.name == ""
    assert model.model_type == ""
    assert model.parameters == {}
    assert model.raw_lines == []


def test_parse_reads_lines(tmp_path):
    spice_file = tmp_path / "test.spice"
    spice_file.write_text(".model NPN NPN\n+ BF=100\n")

    parser = SpiceParser()
    model = parser.parse(spice_file)

    assert len(model.raw_lines) == 2
    assert model.raw_lines[0] == ".model NPN NPN"
