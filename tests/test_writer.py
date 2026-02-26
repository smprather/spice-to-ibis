"""Tests for the IBIS writer."""

from spice_to_ibis.converter import IbisModel
from spice_to_ibis.writer import write_ibis


def test_write_ibis_creates_file(tmp_path):
    output = tmp_path / "out.ibs"
    model = IbisModel(component_name="chip1", model_name="buf1", model_type="I/O")

    write_ibis(model, output)

    assert output.exists()
    content = output.read_text()
    assert "[IBIS Ver]" in content
    assert "[Component]     chip1" in content
    assert "[Model]         buf1" in content
    assert "Model_type      I/O" in content
    assert "[End]" in content
