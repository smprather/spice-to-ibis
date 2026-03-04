"""Assemble simulation results across corners into an IbisModel."""

from __future__ import annotations

from spice_to_ibis.measparser import MeasResult
from spice_to_ibis.models.corners import CornerSet
from spice_to_ibis.models.ibis import (
    CornerFloat,
    IbisModel,
    Ramp,
    VIPoint,
    VTPoint,
    Waveform,
)
from spice_to_ibis.models.spice import SpiceSubcircuit


def convert(
    subcircuit: SpiceSubcircuit,
    corners: CornerSet,
    results: dict[str, list[MeasResult]],
) -> IbisModel:
    """Convert simulation results to an IbisModel.

    Args:
        subcircuit: The parsed subcircuit.
        corners: The PVT corner set used.
        results: Mapping of corner label ("typ"/"min"/"max") to list of
                 MeasResult objects (one per deck type).

    Returns:
        Populated IbisModel instance.
    """
    model = IbisModel(
        component_name=subcircuit.name,
        model_name=subcircuit.name,
        pin_name=_find_pad_pin(subcircuit),
        signal_name=_find_pad_pin(subcircuit),
        voltage_range=CornerFloat(
            typ=corners.typ.voltage,
            min=corners.min.voltage,
            max=corners.max.voltage,
        ),
        temperature_range=CornerFloat(
            typ=corners.typ.temperature,
            min=corners.min.temperature,
            max=corners.max.temperature,
        ),
    )

    # Index results by (corner_label, deck_type)
    indexed: dict[tuple[str, str], MeasResult] = {}
    for label, result_list in results.items():
        for r in result_list:
            indexed[(label, r.deck_type)] = r

    # Build V-I tables
    model.pulldown = _build_vi_table(indexed, "pulldown")
    model.pullup = _build_vi_table(indexed, "pullup")

    # Build clamp tables (split from clamp sweep)
    gnd_clamp, power_clamp = _build_clamp_tables(indexed, corners)
    model.gnd_clamp = gnd_clamp
    model.power_clamp = power_clamp

    # Build waveforms and ramp
    model.rising_waveform = _build_waveforms(indexed, "rising", corners)
    model.falling_waveform = _build_waveforms(indexed, "falling", corners)
    model.ramp = _build_ramp(indexed, corners)

    return model


def _find_pad_pin(subcircuit: SpiceSubcircuit) -> str:
    from spice_to_ibis.models.spice import PinRole

    for port, role in subcircuit.pin_map.items():
        if role == PinRole.PAD:
            return port
    # Differential: use pad_p as the primary pad pin
    for port, role in subcircuit.pin_map.items():
        if role == PinRole.PAD_P:
            return port
    if "pad" in subcircuit.ports:
        return "pad"
    return subcircuit.ports[0] if subcircuit.ports else "pad"


def _is_differential(subcircuit: SpiceSubcircuit) -> bool:
    from spice_to_ibis.models.spice import PinRole

    roles = set(subcircuit.pin_map.values())
    return PinRole.PAD_P in roles and PinRole.PAD_N in roles


def _build_vi_table(
    indexed: dict[tuple[str, str], MeasResult],
    deck_type: str,
) -> list[VIPoint]:
    """Build a V-I table from typ/min/max DC sweep results."""
    typ_r = indexed.get(("typ", deck_type))
    min_r = indexed.get(("min", deck_type))
    max_r = indexed.get(("max", deck_type))

    if typ_r is None:
        return []

    points: list[VIPoint] = []
    for i, voltage in enumerate(typ_r.sweep_voltage):
        typ_i = typ_r.sweep_current[i]
        min_i = (
            min_r.sweep_current[i]
            if min_r and i < len(min_r.sweep_current)
            else typ_i
        )
        max_i = (
            max_r.sweep_current[i]
            if max_r and i < len(max_r.sweep_current)
            else typ_i
        )
        points.append(VIPoint(
            voltage=voltage,
            typ_current=typ_i,
            min_current=min_i,
            max_current=max_i,
        ))
    return points


def _build_clamp_tables(
    indexed: dict[tuple[str, str], MeasResult],
    corners: CornerSet,
) -> tuple[list[VIPoint], list[VIPoint]]:
    """Split clamp sweep into GND clamp (V < 0) and POWER clamp (V > VDD).

    GND clamp: voltages referenced to VSS (0V).
    POWER clamp: voltages referenced to VDD.
    """
    typ_r = indexed.get(("typ", "clamp"))
    min_r = indexed.get(("min", "clamp"))
    max_r = indexed.get(("max", "clamp"))

    if typ_r is None:
        return [], []

    gnd_points: list[VIPoint] = []
    pwr_points: list[VIPoint] = []

    for i, voltage in enumerate(typ_r.sweep_voltage):
        typ_i = typ_r.sweep_current[i]
        min_i = (
            min_r.sweep_current[i]
            if min_r and i < len(min_r.sweep_current)
            else typ_i
        )
        max_i = (
            max_r.sweep_current[i]
            if max_r and i < len(max_r.sweep_current)
            else typ_i
        )

        # GND clamp: below VSS region
        if voltage <= 0:
            gnd_points.append(VIPoint(
                voltage=voltage,
                typ_current=typ_i,
                min_current=min_i,
                max_current=max_i,
            ))

        # POWER clamp: above VDD region, referenced to VDD
        if voltage >= corners.typ.voltage:
            pwr_points.append(VIPoint(
                voltage=voltage - corners.typ.voltage,
                typ_current=typ_i,
                min_current=min_i,
                max_current=max_i,
            ))

    return gnd_points, pwr_points


def _build_waveforms(
    indexed: dict[tuple[str, str], MeasResult],
    deck_type: str,
    corners: CornerSet,
) -> list[Waveform]:
    """Build waveform tables from transient results."""
    typ_r = indexed.get(("typ", deck_type))
    min_r = indexed.get(("min", deck_type))
    max_r = indexed.get(("max", deck_type))

    if typ_r is None:
        return []

    v_fixture = corners.typ.voltage / 2
    points: list[VTPoint] = []
    for i, time in enumerate(typ_r.waveform_time):
        typ_v = typ_r.waveform_voltage[i]
        min_v = (
            min_r.waveform_voltage[i]
            if min_r and i < len(min_r.waveform_voltage)
            else typ_v
        )
        max_v = (
            max_r.waveform_voltage[i]
            if max_r and i < len(max_r.waveform_voltage)
            else typ_v
        )
        points.append(VTPoint(
            time=time,
            typ_voltage=typ_v,
            min_voltage=min_v,
            max_voltage=max_v,
        ))

    waveform = Waveform(
        r_fixture=50.0,
        v_fixture=v_fixture,
        points=points,
    )
    return [waveform]


def _build_ramp(
    indexed: dict[tuple[str, str], MeasResult],
    corners: CornerSet,
) -> Ramp:
    """Build ramp data from transient measurement results (20%/80% crossings)."""
    ramp = Ramp()

    rise_typ = indexed.get(("typ", "rising"))
    rise_min = indexed.get(("min", "rising"))
    rise_max = indexed.get(("max", "rising"))

    fall_typ = indexed.get(("typ", "falling"))
    fall_min = indexed.get(("min", "falling"))
    fall_max = indexed.get(("max", "falling"))

    vdd = corners.typ.voltage

    # Single-ended: use t20/t80 thresholds; differential: use t_cross zero-crossing
    rise_has_se = (
        rise_typ
        and "t20_rise" in rise_typ.measurements
        and "t80_rise" in rise_typ.measurements
    )
    rise_has_diff = rise_typ and "t_cross_rise" in rise_typ.measurements

    if rise_has_se:
        dv = vdd * 0.6  # 80% - 20%

        def _rise_dt(r: MeasResult | None) -> float:
            if r and "t20_rise" in r.measurements and "t80_rise" in r.measurements:
                return abs(r.measurements["t80_rise"] - r.measurements["t20_rise"])
            return 0.0

        ramp.dv_r = CornerFloat(typ=dv, min=dv, max=dv)
        ramp.dt_r = CornerFloat(
            typ=_rise_dt(rise_typ),
            min=_rise_dt(rise_min),
            max=_rise_dt(rise_max),
        )
    elif rise_has_diff:
        # Differential: report crossing time directly (no 20/80 threshold pair)
        def _rise_cross(r: MeasResult | None) -> float:
            if r and "t_cross_rise" in r.measurements:
                return r.measurements["t_cross_rise"]
            return 0.0

        ramp.dv_r = CornerFloat(typ=vdd, min=vdd, max=vdd)
        ramp.dt_r = CornerFloat(
            typ=_rise_cross(rise_typ),
            min=_rise_cross(rise_min),
            max=_rise_cross(rise_max),
        )

    fall_has_se = (
        fall_typ
        and "t80_fall" in fall_typ.measurements
        and "t20_fall" in fall_typ.measurements
    )
    fall_has_diff = fall_typ and "t_cross_fall" in fall_typ.measurements

    if fall_has_se:
        dv = vdd * 0.6

        def _fall_dt(r: MeasResult | None) -> float:
            if r and "t80_fall" in r.measurements and "t20_fall" in r.measurements:
                return abs(r.measurements["t20_fall"] - r.measurements["t80_fall"])
            return 0.0

        ramp.dv_f = CornerFloat(typ=dv, min=dv, max=dv)
        ramp.dt_f = CornerFloat(
            typ=_fall_dt(fall_typ),
            min=_fall_dt(fall_min),
            max=_fall_dt(fall_max),
        )
    elif fall_has_diff:
        def _fall_cross(r: MeasResult | None) -> float:
            if r and "t_cross_fall" in r.measurements:
                return r.measurements["t_cross_fall"]
            return 0.0

        ramp.dv_f = CornerFloat(typ=vdd, min=vdd, max=vdd)
        ramp.dt_f = CornerFloat(
            typ=_fall_cross(fall_typ),
            min=_fall_cross(fall_min),
            max=_fall_cross(fall_max),
        )

    return ramp
