"""Simulator syntax adapters for Spectre and NgSPICE."""

from __future__ import annotations

import abc


class SimSyntax(abc.ABC):
    """Abstract base for simulator-specific syntax."""

    @abc.abstractmethod
    def comment(self, text: str) -> str:
        """Format a comment line."""

    @abc.abstractmethod
    def header(self, deck_type: str, corner_label: str, corner_suffix: str) -> str:
        """File header with simulator preamble."""

    @abc.abstractmethod
    def global_options(self) -> str:
        """Simulator global options."""

    @abc.abstractmethod
    def include(self, path: str) -> str:
        """Include statement for a model file."""

    @abc.abstractmethod
    def voltage_source(
        self, name: str, nplus: str, nminus: str, dc_value: float | int
    ) -> str:
        """DC voltage source."""

    @abc.abstractmethod
    def pulse_source(
        self,
        name: str,
        nplus: str,
        nminus: str,
        val0: float | int,
        val1: float | int,
        delay: str,
        rise: float,
        fall: float,
        width: float,
        period: float,
    ) -> str:
        """Pulse voltage source."""

    @abc.abstractmethod
    def resistor(self, name: str, n1: str, n2: str, value: float | int) -> str:
        """Resistor element."""

    @abc.abstractmethod
    def subcircuit_instance(
        self, inst_name: str, ports: list[str], subckt_name: str
    ) -> str:
        """Subcircuit instantiation."""

    @abc.abstractmethod
    def dc_sweep(
        self,
        source_name: str,
        start: float | int,
        stop: float | int,
        step: float | int,
    ) -> str:
        """DC sweep analysis statement."""

    @abc.abstractmethod
    def transient(self, stop: float, tstep: float | None = None) -> str:
        """Transient analysis statement."""

    @abc.abstractmethod
    def meas_cross(
        self,
        meas_name: str,
        signal: str,
        direction: str,
        value: float,
        result_name: str,
    ) -> str:
        """Measurement at a signal crossing."""

    @abc.abstractmethod
    def control_block(self, deck_name: str) -> str:
        """Simulator control block (NgSPICE .control/.endc)."""

    @abc.abstractmethod
    def end_statement(self) -> str:
        """End-of-file statement."""

    @property
    @abc.abstractmethod
    def file_extension(self) -> str:
        """File extension for deck files."""


class SpectreSyntax(SimSyntax):
    """Cadence Spectre syntax."""

    def comment(self, text: str) -> str:
        return f"// {text}"

    def header(self, deck_type: str, corner_label: str, corner_suffix: str) -> str:
        return (
            f"// Auto-generated {deck_type} deck\n"
            f"// Corner: {corner_label} ({corner_suffix})\n"
            f"simulator lang=spectre\n"
        )

    def global_options(self) -> str:
        return "simulatorOptions options rawfmt=psfascii\n"

    def include(self, path: str) -> str:
        return f'include "{path}"'

    def voltage_source(
        self, name: str, nplus: str, nminus: str, dc_value: float | int
    ) -> str:
        return f"{name} ({nplus} {nminus}) vsource dc={dc_value}"

    def pulse_source(
        self,
        name: str,
        nplus: str,
        nminus: str,
        val0: float | int,
        val1: float | int,
        delay: str,
        rise: float,
        fall: float,
        width: float,
        period: float,
    ) -> str:
        return (
            f"{name} ({nplus} {nminus}) vsource type=pulse "
            f"val0={val0} val1={val1} "
            f"delay={delay} rise={rise} fall={fall} "
            f"width={width} period={period}"
        )

    def resistor(self, name: str, n1: str, n2: str, value: float | int) -> str:
        return f"{name} ({n1} {n2}) resistor r={value}"

    def subcircuit_instance(
        self, inst_name: str, ports: list[str], subckt_name: str
    ) -> str:
        port_str = " ".join(ports)
        return f"{inst_name} ({port_str}) {subckt_name}"

    def dc_sweep(
        self,
        source_name: str,
        start: float | int,
        stop: float | int,
        step: float | int,
    ) -> str:
        return (
            f"dc_sweep dc dev={source_name} param=dc "
            f"start={start} stop={stop} step={step}"
        )

    def transient(self, stop: float, tstep: float | None = None) -> str:
        return f"tran_sim tran stop={stop}"

    def meas_cross(
        self,
        meas_name: str,
        signal: str,
        direction: str,
        value: float,
        result_name: str,
    ) -> str:
        return (
            f"{meas_name} tran_sim cross sig={signal} dir={direction} "
            f"val={value} name={result_name}"
        )

    def control_block(self, deck_name: str) -> str:
        return ""

    def end_statement(self) -> str:
        return ""

    @property
    def file_extension(self) -> str:
        return ".scs"


class NgspiceSyntax(SimSyntax):
    """NgSPICE syntax."""

    @staticmethod
    def _ngspice_name(name: str) -> str:
        """Capitalize the first letter for NgSPICE element naming."""
        if not name:
            return name
        return name[0].upper() + name[1:]

    def comment(self, text: str) -> str:
        return f"* {text}"

    def header(self, deck_type: str, corner_label: str, corner_suffix: str) -> str:
        return (
            f"* Auto-generated {deck_type} deck\n"
            f"* Corner: {corner_label} ({corner_suffix})\n"
        )

    def global_options(self) -> str:
        return ".options\n"

    def include(self, path: str) -> str:
        return f'.include "{path}"'

    def voltage_source(
        self, name: str, nplus: str, nminus: str, dc_value: float | int
    ) -> str:
        ng_name = self._ngspice_name(name)
        return f"{ng_name} {nplus} {nminus} DC {dc_value}"

    def pulse_source(
        self,
        name: str,
        nplus: str,
        nminus: str,
        val0: float | int,
        val1: float | int,
        delay: str,
        rise: float,
        fall: float,
        width: float,
        period: float,
    ) -> str:
        ng_name = self._ngspice_name(name)
        return (
            f"{ng_name} {nplus} {nminus} "
            f"PULSE({val0} {val1} {delay} {rise} {fall} "
            f"{width} {period})"
        )

    def resistor(self, name: str, n1: str, n2: str, value: float | int) -> str:
        ng_name = self._ngspice_name(name)
        return f"{ng_name} {n1} {n2} {value}"

    def subcircuit_instance(
        self, inst_name: str, ports: list[str], subckt_name: str
    ) -> str:
        ng_name = self._ngspice_name(inst_name)
        port_str = " ".join(ports)
        return f"{ng_name} {port_str} {subckt_name}"

    def dc_sweep(
        self,
        source_name: str,
        start: float | int,
        stop: float | int,
        step: float | int,
    ) -> str:
        ng_name = self._ngspice_name(source_name)
        return f".dc {ng_name} {start} {stop} {step}"

    def transient(self, stop: float, tstep: float | None = None) -> str:
        if tstep is None:
            tstep = stop / 1000
        return f".tran {tstep} {stop}"

    def meas_cross(
        self,
        meas_name: str,
        signal: str,
        direction: str,
        value: float,
        result_name: str,
    ) -> str:
        rise_fall = "RISE" if direction == "rise" else "FALL"
        return f".meas tran {result_name} WHEN v({signal})={value} {rise_fall}=1"

    def control_block(self, deck_name: str) -> str:
        return f".control\nset filetype=ascii\nrun\nwrite {deck_name}.raw\n.endc\n"

    def end_statement(self) -> str:
        return ".end\n"

    @property
    def file_extension(self) -> str:
        return ".cir"


def get_syntax(simulator: str = "spectre") -> SimSyntax:
    """Factory to get the syntax adapter for a simulator.

    Args:
        simulator: "spectre" or "ngspice".

    Returns:
        SimSyntax instance.
    """
    if simulator == "spectre":
        return SpectreSyntax()
    if simulator == "ngspice":
        return NgspiceSyntax()
    raise ValueError(f"Unknown simulator: {simulator!r}")
