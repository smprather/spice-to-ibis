from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CornerFloat:
    """A value at typ/min/max corners."""

    typ: float
    min: float
    max: float


@dataclass
class VIPoint:
    """Voltage-current point for V-I tables."""

    voltage: float
    typ_current: float
    min_current: float
    max_current: float


@dataclass
class VTPoint:
    """Voltage-time point for waveform tables."""

    time: float
    typ_voltage: float
    min_voltage: float
    max_voltage: float


@dataclass
class Ramp:
    """Ramp rate data (dV/dt) for rising and falling edges."""

    dv_r: CornerFloat | None = None
    dt_r: CornerFloat | None = None
    dv_f: CornerFloat | None = None
    dt_f: CornerFloat | None = None


@dataclass
class Waveform:
    """Rising or falling waveform table."""

    r_fixture: float = 50.0
    v_fixture: float = 0.0
    points: list[VTPoint] = field(default_factory=list)


@dataclass
class IbisModel:
    """Full IBIS model for output."""

    ibis_version: str = "7.0"
    file_name: str = ""
    file_revision: str = "0.1"

    component_name: str = ""
    manufacturer: str = ""
    package_r: CornerFloat | None = None
    package_l: CornerFloat | None = None
    package_c: CornerFloat | None = None

    pin_name: str = ""
    signal_name: str = ""

    model_name: str = ""
    model_type: str = "I/O"
    polarity: str = "Non-Inverting"
    enable: str = "Active-High"

    vinl: float = 0.8
    vinh: float = 2.0

    c_comp: CornerFloat | None = None

    voltage_range: CornerFloat | None = None
    temperature_range: CornerFloat | None = None

    pulldown: list[VIPoint] = field(default_factory=list)
    pullup: list[VIPoint] = field(default_factory=list)
    gnd_clamp: list[VIPoint] = field(default_factory=list)
    power_clamp: list[VIPoint] = field(default_factory=list)

    ramp: Ramp | None = None

    rising_waveform: list[Waveform] = field(default_factory=list)
    falling_waveform: list[Waveform] = field(default_factory=list)
