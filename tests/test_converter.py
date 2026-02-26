"""Tests for the SPICE-to-IBIS converter."""

from spice_to_ibis.converter import IbisModel, convert
from spice_to_ibis.parser import SpiceModel


def test_ibis_model_defaults():
    model = IbisModel()
    assert model.component_name == ""
    assert model.model_name == ""
    assert model.model_type == ""
    assert model.vi_data == []


def test_convert_transfers_name():
    spice = SpiceModel(name="test_buffer", model_type="NPN")
    ibis = convert(spice)
    assert ibis.component_name == "test_buffer"
    assert ibis.model_name == "test_buffer"
    assert ibis.model_type == "NPN"
