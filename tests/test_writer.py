"""Tests for the IBIS writer."""

from __future__ import annotations

from spice_to_ibis.models.ibis import (
    CornerFloat,
    IbisModel,
    Ramp,
    VIPoint,
    VTPoint,
    Waveform,
)
from spice_to_ibis.writer import format_ibis, write_ibis


class TestWriteIbisFile:
    def test_creates_file(self, tmp_path):
        output = tmp_path / "out.ibs"
        model = IbisModel(component_name="chip1", model_name="buf1")
        write_ibis(model, output)
        assert output.exists()

    def test_contains_required_sections(self, tmp_path):
        output = tmp_path / "out.ibs"
        model = IbisModel(component_name="chip1", model_name="buf1")
        write_ibis(model, output)
        content = output.read_text()
        assert "[IBIS Ver]" in content
        assert "[Component]" in content
        assert "[Model]" in content
        assert "[End]" in content


class TestFormatIbis:
    def test_header(self):
        model = IbisModel()
        text = format_ibis(model, "test.ibs")
        assert "[IBIS Ver]      7.0" in text
        assert "[File Name]     test.ibs" in text

    def test_component(self):
        model = IbisModel(component_name="my_chip", manufacturer="ACME")
        text = format_ibis(model)
        assert "[Component]     my_chip" in text
        assert "[Manufacturer]  ACME" in text

    def test_pin_table(self):
        model = IbisModel(
            pin_name="A1",
            signal_name="DATA0",
            model_name="io_buf",
        )
        text = format_ibis(model)
        assert "[Pin]" in text
        assert "A1" in text
        assert "DATA0" in text
        assert "io_buf" in text

    def test_model_section(self):
        model = IbisModel(
            model_name="buf1",
            model_type="I/O",
            polarity="Non-Inverting",
            enable="Active-High",
        )
        text = format_ibis(model)
        assert "[Model]         buf1" in text
        assert "Model_type      I/O" in text
        assert "Polarity        Non-Inverting" in text
        assert "Enable          Active-High" in text

    def test_voltage_range(self):
        model = IbisModel(
            voltage_range=CornerFloat(1.8, 1.62, 1.98)
        )
        text = format_ibis(model)
        assert "[Voltage Range]" in text
        assert "1.800000e+00" in text

    def test_temperature_range(self):
        model = IbisModel(
            temperature_range=CornerFloat(25.0, 125.0, -40.0)
        )
        text = format_ibis(model)
        assert "[Temperature Range]" in text

    def test_pulldown_vi_table(self):
        model = IbisModel(
            pulldown=[
                VIPoint(-1.0, 0.001, 0.0008, 0.0012),
                VIPoint(0.0, 0.0, 0.0, 0.0),
                VIPoint(1.0, -0.001, -0.0008, -0.0012),
            ]
        )
        text = format_ibis(model)
        assert "[Pulldown]" in text
        lines = text.split("\n")
        pulldown_lines = []
        in_pd = False
        for line in lines:
            if "[Pulldown]" in line:
                in_pd = True
                continue
            if in_pd:
                if line.startswith("[") or line == "":
                    break
                if not line.startswith("|"):
                    pulldown_lines.append(line)
        assert len(pulldown_lines) == 3

    def test_pullup_vi_table(self):
        model = IbisModel(
            pullup=[VIPoint(0.0, 0.0, 0.0, 0.0)]
        )
        text = format_ibis(model)
        assert "[Pullup]" in text

    def test_gnd_clamp(self):
        model = IbisModel(
            gnd_clamp=[VIPoint(-0.5, 0.001, 0.0008, 0.0012)]
        )
        text = format_ibis(model)
        assert "[GND Clamp]" in text

    def test_power_clamp(self):
        model = IbisModel(
            power_clamp=[VIPoint(0.5, -0.001, -0.0008, -0.0012)]
        )
        text = format_ibis(model)
        assert "[POWER Clamp]" in text

    def test_ramp(self):
        model = IbisModel(
            ramp=Ramp(
                dv_r=CornerFloat(1.08, 1.08, 1.08),
                dt_r=CornerFloat(0.5e-9, 0.6e-9, 0.4e-9),
                dv_f=CornerFloat(1.08, 1.08, 1.08),
                dt_f=CornerFloat(0.5e-9, 0.6e-9, 0.4e-9),
            )
        )
        text = format_ibis(model)
        assert "[Ramp]" in text
        assert "dV/dt_r" in text
        assert "dV/dt_f" in text

    def test_rising_waveform(self):
        model = IbisModel(
            rising_waveform=[
                Waveform(
                    r_fixture=50.0,
                    v_fixture=0.9,
                    points=[
                        VTPoint(0.0, 0.0, 0.0, 0.0),
                        VTPoint(1e-9, 0.9, 0.8, 1.0),
                        VTPoint(2e-9, 1.8, 1.62, 1.98),
                    ],
                )
            ]
        )
        text = format_ibis(model)
        assert "[Rising Waveform]" in text
        assert "R_fixture" in text
        assert "V_fixture" in text

    def test_falling_waveform(self):
        model = IbisModel(
            falling_waveform=[
                Waveform(
                    r_fixture=50.0,
                    v_fixture=0.9,
                    points=[
                        VTPoint(0.0, 1.8, 1.62, 1.98),
                        VTPoint(1e-9, 0.9, 0.8, 1.0),
                        VTPoint(2e-9, 0.0, 0.0, 0.0),
                    ],
                )
            ]
        )
        text = format_ibis(model)
        assert "[Falling Waveform]" in text

    def test_no_empty_tables(self):
        model = IbisModel()
        text = format_ibis(model)
        assert "[Pulldown]" not in text
        assert "[Pullup]" not in text
        assert "[GND Clamp]" not in text
        assert "[POWER Clamp]" not in text
        assert "[Rising Waveform]" not in text
        assert "[Falling Waveform]" not in text

    def test_end_marker(self):
        model = IbisModel()
        text = format_ibis(model)
        assert text.strip().endswith("[End]")
