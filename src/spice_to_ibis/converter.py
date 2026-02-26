"""SPICE-to-IBIS conversion logic."""

from __future__ import annotations

from dataclasses import dataclass, field

from spice_to_ibis.parser import SpiceModel


@dataclass
class IbisModel:
    """Representation of an IBIS model."""

    component_name: str = ""
    model_name: str = ""
    model_type: str = ""
    vi_data: list[tuple[float, float]] = field(default_factory=list)


def convert(spice_model: SpiceModel) -> IbisModel:
    """Convert a SpiceModel to an IbisModel.

    Args:
        spice_model: Parsed SPICE model data.

    Returns:
        Converted IbisModel instance.
    """
    return IbisModel(
        component_name=spice_model.name,
        model_name=spice_model.name,
        model_type=spice_model.model_type,
    )
