"""Tests for the simulation-results-to-IBIS converter."""

from __future__ import annotations

import pytest

from spice_to_ibis.converter import convert
from spice_to_ibis.measparser import MeasResult
from spice_to_ibis.models.corners import Corner, CornerSet
from spice_to_ibis.models.ibis import IbisModel
from spice_to_ibis.models.spice import PinRole, SpiceSubcircuit


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
    )


@pytest.fixture
def corners():
    return CornerSet(
        typ=Corner("typ", "tt", 1.8, 25.0),
        min=Corner("min", "ss", 1.62, 125.0),
        max=Corner("max", "ff", 1.98, -40.0),
    )


def _make_dc_result(corner_label: str, deck_type: str) -> MeasResult:
    """Create a fake DC sweep MeasResult."""
    voltages = [-1.8, -0.9, 0.0, 0.9, 1.8, 2.7, 3.6]
    currents = [1e-3, 5e-4, 1e-7, -5e-4, -1e-3, -1.5e-3, -2e-3]
    return MeasResult(
        deck_name=f"{deck_type}_{corner_label}",
        deck_type=deck_type,
        corner_label=corner_label,
        sweep_voltage=voltages,
        sweep_current=currents,
    )


def _make_clamp_result(corner_label: str) -> MeasResult:
    """Create a fake clamp DC sweep MeasResult."""
    voltages = [-1.8, -0.9, 0.0, 0.9, 1.8, 2.7, 3.6]
    currents = [5e-4, 2e-4, 1e-8, 1e-8, 1e-8, -2e-4, -5e-4]
    return MeasResult(
        deck_name=f"clamp_{corner_label}",
        deck_type="clamp",
        corner_label=corner_label,
        sweep_voltage=voltages,
        sweep_current=currents,
    )


def _make_transient_result(
    corner_label: str, deck_type: str
) -> MeasResult:
    """Create a fake transient MeasResult."""
    times = [0.0, 1e-9, 2e-9, 3e-9, 4e-9, 5e-9]
    voltages = [0.0, 0.2, 0.7, 1.3, 1.7, 1.8]
    if deck_type == "falling":
        voltages = [1.8, 1.6, 1.1, 0.5, 0.1, 0.0]
    meas = {}
    if deck_type == "rising":
        meas = {"t20_rise": 1.5e-9, "t80_rise": 3.0e-9}
    elif deck_type == "falling":
        meas = {"t80_fall": 1.2e-9, "t20_fall": 2.8e-9}
    return MeasResult(
        deck_name=f"{deck_type}_{corner_label}",
        deck_type=deck_type,
        corner_label=corner_label,
        measurements=meas,
        waveform_time=times,
        waveform_voltage=voltages,
    )


def _full_results() -> dict[str, list[MeasResult]]:
    """Build a full set of results across all corners."""
    results: dict[str, list[MeasResult]] = {}
    for label in ("typ", "min", "max"):
        results[label] = [
            _make_dc_result(label, "pulldown"),
            _make_dc_result(label, "pullup"),
            _make_clamp_result(label),
            _make_transient_result(label, "rising"),
            _make_transient_result(label, "falling"),
        ]
    return results


class TestConvert:
    def test_returns_ibis_model(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert isinstance(model, IbisModel)

    def test_component_name(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert model.component_name == "buf_io"
        assert model.model_name == "buf_io"

    def test_pin_name(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert model.pin_name == "pad"

    def test_voltage_range(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert model.voltage_range is not None
        assert model.voltage_range.typ == 1.8
        assert model.voltage_range.min == 1.62
        assert model.voltage_range.max == 1.98

    def test_temperature_range(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert model.temperature_range is not None
        assert model.temperature_range.typ == 25.0

    def test_pulldown_vi_table(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert len(model.pulldown) == 7
        assert model.pulldown[0].voltage == -1.8
        assert model.pulldown[0].typ_current == 1e-3

    def test_pullup_vi_table(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert len(model.pullup) == 7

    def test_gnd_clamp_table(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        # GND clamp: voltages <= 0 → indices 0, 1, 2 (-1.8, -0.9, 0.0)
        assert len(model.gnd_clamp) == 3
        assert model.gnd_clamp[0].voltage == -1.8

    def test_power_clamp_table(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        # POWER clamp: voltages >= VDD(1.8) → indices 4, 5, 6
        # Referenced to VDD: 0.0, 0.9, 1.8
        assert len(model.power_clamp) == 3
        assert model.power_clamp[0].voltage == pytest.approx(0.0)
        assert model.power_clamp[1].voltage == pytest.approx(0.9)

    def test_rising_waveform(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert len(model.rising_waveform) == 1
        wf = model.rising_waveform[0]
        assert wf.r_fixture == 50.0
        assert wf.v_fixture == pytest.approx(0.9)
        assert len(wf.points) == 6

    def test_falling_waveform(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert len(model.falling_waveform) == 1
        wf = model.falling_waveform[0]
        assert len(wf.points) == 6
        assert wf.points[0].typ_voltage == 1.8

    def test_ramp_rising(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert model.ramp is not None
        assert model.ramp.dv_r is not None
        assert model.ramp.dv_r.typ == pytest.approx(1.08)  # 0.6 * 1.8
        assert model.ramp.dt_r is not None
        assert model.ramp.dt_r.typ == pytest.approx(1.5e-9)  # 3.0e-9 - 1.5e-9

    def test_ramp_falling(self, subcircuit, corners):
        model = convert(subcircuit, corners, _full_results())
        assert model.ramp is not None
        assert model.ramp.dv_f is not None
        assert model.ramp.dt_f is not None
        assert model.ramp.dt_f.typ == pytest.approx(1.6e-9)  # 2.8e-9 - 1.2e-9

    def test_empty_results(self, subcircuit, corners):
        model = convert(subcircuit, corners, {"typ": [], "min": [], "max": []})
        assert model.pulldown == []
        assert model.pullup == []
        assert model.gnd_clamp == []
        assert model.power_clamp == []
        assert model.rising_waveform == []
        assert model.falling_waveform == []


class TestDifferentialConvert:
    """Test converter with differential (LVDS) subcircuit."""

    @pytest.fixture
    def diff_subcircuit(self):
        return SpiceSubcircuit(
            name="lvds_driver",
            ports=["outp", "outn", "vdd", "vss", "din", "en"],
            pin_map={
                "outp": PinRole.PAD_P,
                "outn": PinRole.PAD_N,
                "vdd": PinRole.VDD,
                "vss": PinRole.VSS,
                "din": PinRole.INPUT,
                "en": PinRole.ENABLE,
            },
        )

    @pytest.fixture
    def corners(self):
        return CornerSet(
            typ=Corner("typ", "tt", 1.8, 25.0),
            min=Corner("min", "ss", 1.62, 125.0),
            max=Corner("max", "ff", 1.98, -40.0),
        )

    @staticmethod
    def _make_diff_transient(corner_label: str, deck_type: str) -> MeasResult:
        times = [0.0, 1e-9, 2e-9, 3e-9, 4e-9, 5e-9]
        voltages = [-0.35, -0.2, 0.0, 0.2, 0.3, 0.35]
        if deck_type == "falling":
            voltages = [0.35, 0.2, 0.0, -0.2, -0.3, -0.35]
        meas = {}
        if deck_type == "rising":
            meas = {"t_cross_rise": 2.0e-9}
        elif deck_type == "falling":
            meas = {"t_cross_fall": 2.1e-9}
        return MeasResult(
            deck_name=f"{deck_type}_{corner_label}",
            deck_type=deck_type,
            corner_label=corner_label,
            measurements=meas,
            waveform_time=times,
            waveform_voltage=voltages,
        )

    def _diff_results(self) -> dict[str, list[MeasResult]]:
        results: dict[str, list[MeasResult]] = {}
        for label in ("typ", "min", "max"):
            results[label] = [
                _make_dc_result(label, "pulldown"),
                _make_dc_result(label, "pullup"),
                _make_clamp_result(label),
                self._make_diff_transient(label, "rising"),
                self._make_diff_transient(label, "falling"),
            ]
        return results

    def test_pin_name_uses_pad_p(self, diff_subcircuit, corners):
        model = convert(diff_subcircuit, corners, self._diff_results())
        assert model.pin_name == "outp"

    def test_component_name(self, diff_subcircuit, corners):
        model = convert(diff_subcircuit, corners, self._diff_results())
        assert model.component_name == "lvds_driver"

    def test_ramp_rising_diff(self, diff_subcircuit, corners):
        model = convert(diff_subcircuit, corners, self._diff_results())
        assert model.ramp is not None
        assert model.ramp.dt_r is not None
        assert model.ramp.dt_r.typ == pytest.approx(2.0e-9)

    def test_ramp_falling_diff(self, diff_subcircuit, corners):
        model = convert(diff_subcircuit, corners, self._diff_results())
        assert model.ramp is not None
        assert model.ramp.dt_f is not None
        assert model.ramp.dt_f.typ == pytest.approx(2.1e-9)

    def test_vi_tables_still_work(self, diff_subcircuit, corners):
        model = convert(diff_subcircuit, corners, self._diff_results())
        assert len(model.pulldown) == 7
        assert len(model.pullup) == 7
