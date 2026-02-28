from __future__ import annotations

from spice_to_ibis.models.corners import Corner, CornerSet
from spice_to_ibis.models.ibis import (
    CornerFloat,
    IbisModel,
    Ramp,
    VIPoint,
    VTPoint,
    Waveform,
)
from spice_to_ibis.models.spice import PinRole, SpiceSubcircuit


class TestSpiceSubcircuit:
    def test_defaults(self):
        s = SpiceSubcircuit()
        assert s.name == ""
        assert s.ports == []
        assert s.pin_map == {}
        assert s.parameters == {}
        assert s.include_paths == []
        assert s.raw_lines == []

    def test_pin_roles(self):
        assert PinRole.PAD.value == "pad"
        assert PinRole.VDD.value == "vdd"
        assert PinRole.VSS.value == "vss"
        assert PinRole.INPUT.value == "input"
        assert PinRole.ENABLE.value == "enable"

    def test_populated(self):
        s = SpiceSubcircuit(
            name="buf_io",
            ports=["pad", "vdd", "vss", "din", "en"],
            pin_map={"pad": PinRole.PAD, "vdd": PinRole.VDD},
            parameters={"wp": "2u", "wn": "1u"},
        )
        assert s.name == "buf_io"
        assert len(s.ports) == 5
        assert s.pin_map["pad"] == PinRole.PAD


class TestCorners:
    def test_corner_suffix(self):
        c = Corner("typ", "tt", 1.8, 25.0)
        assert c.suffix == "tt_1.8V_25.0C"

    def test_corner_set_defaults(self):
        cs = CornerSet()
        assert cs.typ.process == "tt"
        assert cs.min.process == "ss"
        assert cs.max.process == "ff"

    def test_corner_set_iterable(self):
        cs = CornerSet()
        labels = [c.label for c in cs]
        assert labels == ["typ", "min", "max"]

    def test_custom_corner_set(self):
        cs = CornerSet(
            typ=Corner("typ", "tt", 3.3, 25.0),
            min=Corner("min", "ss", 2.97, 125.0),
            max=Corner("max", "ff", 3.63, -40.0),
        )
        assert cs.typ.voltage == 3.3
        assert cs.min.temperature == 125.0


class TestIbisModel:
    def test_defaults(self):
        m = IbisModel()
        assert m.ibis_version == "7.0"
        assert m.model_type == "I/O"
        assert m.pulldown == []
        assert m.pullup == []
        assert m.gnd_clamp == []
        assert m.power_clamp == []
        assert m.rising_waveform == []
        assert m.falling_waveform == []

    def test_vi_point(self):
        p = VIPoint(
            voltage=-1.0, typ_current=0.001,
            min_current=0.0008, max_current=0.0012,
        )
        assert p.voltage == -1.0
        assert p.typ_current == 0.001

    def test_vt_point(self):
        p = VTPoint(time=1e-9, typ_voltage=0.5, min_voltage=0.4, max_voltage=0.6)
        assert p.time == 1e-9

    def test_corner_float(self):
        cf = CornerFloat(typ=1.8, min=1.62, max=1.98)
        assert cf.typ == 1.8
        assert cf.min == 1.62
        assert cf.max == 1.98

    def test_ramp(self):
        r = Ramp(
            dv_r=CornerFloat(1.08, 0.972, 1.188),
            dt_r=CornerFloat(0.5e-9, 0.6e-9, 0.4e-9),
        )
        assert r.dv_r is not None
        assert r.dt_f is None

    def test_waveform(self):
        w = Waveform(
            r_fixture=50.0,
            v_fixture=0.9,
            points=[
                VTPoint(0.0, 0.0, 0.0, 0.0),
                VTPoint(1e-9, 1.8, 1.62, 1.98),
            ],
        )
        assert len(w.points) == 2
        assert w.r_fixture == 50.0
