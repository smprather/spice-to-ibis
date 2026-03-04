"""Command-line interface for spice-to-ibis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from spice_to_ibis.converter import convert
from spice_to_ibis.deckgen import (
    ClampDeckGen,
    FallingWaveformDeckGen,
    PulldownDeckGen,
    PullupDeckGen,
    RisingWaveformDeckGen,
)
from spice_to_ibis.deckgen.base import SimDeck
from spice_to_ibis.measparser import MeasParser, MeasResult
from spice_to_ibis.models.corners import Corner, CornerSet
from spice_to_ibis.models.spice import PinRole, SpiceSubcircuit
from spice_to_ibis.parser import get_parser
from spice_to_ibis.runner import SimResult, get_runner
from spice_to_ibis.syntax import get_syntax
from spice_to_ibis.writer import write_ibis


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="spice-to-ibis",
        description=("Generate IBIS models from SPICE subcircuit characterization."),
    )
    sub = parser.add_subparsers(dest="command")

    # --- characterize (end-to-end) ---
    p_char = sub.add_parser(
        "characterize",
        help="End-to-end: generate decks, simulate, parse, write IBIS.",
    )
    _add_subcircuit_args(p_char)
    _add_corner_args(p_char)
    _add_simulator_args(p_char)
    p_char.add_argument(
        "--spectre-path",
        default=None,
        help="Path to Spectre binary (deprecated, use --sim-path)",
    )
    p_char.add_argument(
        "--work-dir",
        type=Path,
        default=Path("work"),
        help="Working directory for sim files",
    )
    p_char.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output IBIS file path",
    )

    # --- generate ---
    p_gen = sub.add_parser("generate", help="Generate simulation deck files.")
    _add_subcircuit_args(p_gen)
    _add_corner_args(p_gen)
    _add_simulator_args(p_gen)
    p_gen.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        required=True,
        help="Directory for generated deck files",
    )

    # --- simulate ---
    p_sim = sub.add_parser("simulate", help="Run simulator on generated decks.")
    p_sim.add_argument(
        "--deck-dir",
        type=Path,
        required=True,
        help="Directory containing deck files",
    )
    _add_simulator_args(p_sim)
    p_sim.add_argument(
        "--spectre-path",
        default=None,
        help="Path to Spectre binary (deprecated, use --sim-path)",
    )
    p_sim.add_argument(
        "--work-dir",
        type=Path,
        default=Path("work"),
        help="Working directory for simulation results",
    )

    # --- parse-results ---
    p_parse = sub.add_parser(
        "parse-results", help="Parse simulation output into results JSON."
    )
    p_parse.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Working directory with simulation output",
    )
    _add_simulator_args(p_parse)
    p_parse.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output results JSON path",
    )

    # --- write-ibis ---
    p_write = sub.add_parser("write-ibis", help="Write IBIS file from results JSON.")
    p_write.add_argument(
        "--results",
        type=Path,
        required=True,
        help="Path to results JSON",
    )
    p_write.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output IBIS file path",
    )

    return parser


def _add_subcircuit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--subcircuit",
        type=Path,
        required=True,
        help="Path to subcircuit file (.scs or .cir)",
    )
    parser.add_argument(
        "--pin-map",
        type=str,
        required=True,
        help="Pin-to-role mapping: pad=pad,vdd=vdd,vss=vss,din=input,en=enable",
    )


def _add_corner_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--vdd-typ", type=float, default=1.8, help="Typical VDD (V)")
    parser.add_argument("--vdd-min", type=float, default=1.62, help="Min VDD (V)")
    parser.add_argument("--vdd-max", type=float, default=1.98, help="Max VDD (V)")
    parser.add_argument(
        "--temp-typ", type=float, default=25.0, help="Typical temperature (C)"
    )
    parser.add_argument(
        "--temp-min",
        type=float,
        default=125.0,
        help="Min corner temperature (C)",
    )
    parser.add_argument(
        "--temp-max",
        type=float,
        default=-40.0,
        help="Max corner temperature (C)",
    )


def _add_simulator_args(parser: argparse.ArgumentParser) -> None:
    """Add --simulator and --sim-path arguments."""
    parser.add_argument(
        "--simulator",
        choices=["spectre", "ngspice"],
        default="spectre",
        help="Simulator backend (default: spectre)",
    )
    parser.add_argument(
        "--sim-path",
        default=None,
        help="Path to simulator binary",
    )


def _resolve_sim_path(args: argparse.Namespace) -> str | None:
    """Resolve simulator path from --sim-path or legacy --spectre-path."""
    if args.sim_path is not None:
        return args.sim_path
    if hasattr(args, "spectre_path") and args.spectre_path is not None:
        return args.spectre_path
    return None


def _parse_pin_map(pin_map_str: str) -> dict[str, PinRole]:
    """Parse 'pad=pad,vdd=vdd,...' into {port: PinRole}."""
    mapping: dict[str, PinRole] = {}
    for pair in pin_map_str.split(","):
        port, _, role = pair.partition("=")
        mapping[port.strip()] = PinRole(role.strip())
    return mapping


def _build_corners(args: argparse.Namespace) -> CornerSet:
    return CornerSet(
        typ=Corner("typ", "tt", args.vdd_typ, args.temp_typ),
        min=Corner("min", "ss", args.vdd_min, args.temp_min),
        max=Corner("max", "ff", args.vdd_max, args.temp_max),
    )


def _infer_parser_type(filepath: Path) -> str:
    """Infer parser type from file extension."""
    ext = filepath.suffix.lower()
    if ext == ".cir":
        return "ngspice"
    return "spectre"


def _parse_subcircuit(args: argparse.Namespace) -> SpiceSubcircuit:
    pin_map = _parse_pin_map(args.pin_map)
    parser_type = _infer_parser_type(Path(args.subcircuit))
    parser = get_parser(parser_type)
    return parser.parse(args.subcircuit, pin_map=pin_map)


def _generate_decks(
    subcircuit: SpiceSubcircuit,
    corners: CornerSet,
    simulator: str = "spectre",
) -> list[SimDeck]:
    """Generate all simulation decks for all corners."""
    syntax = get_syntax(simulator)
    generators = [
        PulldownDeckGen(syntax=syntax),
        PullupDeckGen(syntax=syntax),
        ClampDeckGen(syntax=syntax),
        RisingWaveformDeckGen(syntax=syntax),
        FallingWaveformDeckGen(syntax=syntax),
    ]
    decks: list[SimDeck] = []
    for corner in corners:
        for gen in generators:
            decks.append(gen.generate(subcircuit, corner))
    return decks


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate simulation deck files."""
    subcircuit = _parse_subcircuit(args)
    corners = _build_corners(args)
    simulator = args.simulator
    decks = _generate_decks(subcircuit, corners, simulator=simulator)

    runner = get_runner(simulator, path=_resolve_sim_path(args))
    output_dir = Path(args.output_dir)
    for deck in decks:
        path = runner.write_deck(deck, output_dir)
        print(f"  Wrote {path}")

    print(f"Generated {len(decks)} deck files in {output_dir}")


def cmd_simulate(args: argparse.Namespace) -> None:
    """Run simulator on all deck files in a directory."""
    deck_dir = Path(args.deck_dir)
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    simulator = args.simulator
    runner = get_runner(simulator, path=_resolve_sim_path(args))

    ext = "*.cir" if simulator == "ngspice" else "*.scs"
    deck_files = sorted(deck_dir.glob(ext))
    if not deck_files:
        print(f"No {ext} files found in {deck_dir}", file=sys.stderr)
        sys.exit(1)

    for deck_file in deck_files:
        name = deck_file.stem
        parts = name.split("_", 1)
        deck_type = parts[0] if parts else "unknown"
        corner = Corner("unknown", "tt", 1.8, 25.0)

        deck = SimDeck(
            name=name,
            deck_type=deck_type,
            corner=corner,
            content=deck_file.read_text(),
        )
        result = runner.run(deck, work_dir)
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {name}")


def cmd_parse_results(args: argparse.Namespace) -> None:
    """Parse simulation results into JSON."""
    work_dir = Path(args.work_dir)
    simulator = args.simulator
    meas_parser = MeasParser()

    results_data: list[dict] = []

    if simulator == "ngspice":
        for raw_file in sorted(work_dir.glob("*.raw")):
            deck_name = raw_file.stem
            log_file = work_dir / f"{deck_name}.log"
            # Try DC sweep first
            voltages, currents = meas_parser.parse_ngspice_raw(raw_file)
            entry: dict = {
                "file": str(raw_file),
                "deck_name": deck_name,
                "voltages": len(voltages),
            }
            if log_file.exists():
                measurements = meas_parser.parse_ngspice_meas_log(log_file)
                entry["measurements"] = measurements
            results_data.append(entry)
    else:
        for mt0_file in sorted(work_dir.glob("*.mt0")):
            measurements = meas_parser.parse_mt0(mt0_file)
            results_data.append(
                {
                    "file": str(mt0_file),
                    "measurements": measurements,
                }
            )

    output = Path(args.output)
    output.write_text(json.dumps(results_data, indent=2))
    print(f"Wrote results to {output}")


def cmd_write_ibis(args: argparse.Namespace) -> None:
    """Write IBIS file from results JSON."""
    results_path = Path(args.results)
    results_data = json.loads(results_path.read_text())

    # Build a minimal IbisModel from results JSON
    from spice_to_ibis.models.ibis import IbisModel

    model = IbisModel(
        component_name=results_data.get("component_name", "unknown"),
        model_name=results_data.get("model_name", "unknown"),
    )

    write_ibis(model, Path(args.output))
    print(f"Wrote IBIS file to {args.output}")


def cmd_characterize(args: argparse.Namespace) -> None:
    """End-to-end characterization pipeline."""
    subcircuit = _parse_subcircuit(args)
    corners = _build_corners(args)
    simulator = args.simulator
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate decks
    decks = _generate_decks(subcircuit, corners, simulator=simulator)
    print(f"Generated {len(decks)} simulation decks")

    # 2. Run simulations
    runner = get_runner(simulator, path=_resolve_sim_path(args))
    sim_results = runner.run_all(decks, work_dir)

    failed = [r for r in sim_results if not r.success]
    if failed:
        for r in failed:
            print(f"  FAIL: {r.deck.name}: {r.stderr}", file=sys.stderr)
        print(
            f"{len(failed)}/{len(sim_results)} simulations failed",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"All {len(sim_results)} simulations passed")

    # 3. Parse results
    meas_parser = MeasParser()
    results: dict[str, list[MeasResult]] = {}

    for corner in corners:
        corner_results: list[MeasResult] = []
        for sim_result in sim_results:
            if sim_result.deck.corner.label != corner.label:
                continue
            deck = sim_result.deck
            if simulator == "ngspice":
                _parse_ngspice_result(
                    meas_parser, sim_result, deck, corner, corner_results
                )
            else:
                _parse_spectre_result(
                    meas_parser, sim_result, deck, corner, corner_results
                )
        results[corner.label] = corner_results

    # 4. Convert to IBIS
    ibis_model = convert(subcircuit, corners, results)

    # 5. Write IBIS
    write_ibis(ibis_model, Path(args.output))
    print(f"Wrote IBIS file to {args.output}")


def _parse_spectre_result(
    meas_parser: MeasParser,
    sim_result: SimResult,
    deck: SimDeck,
    corner: Corner,
    corner_results: list[MeasResult],
) -> None:
    """Parse Spectre simulation results."""
    if deck.deck_type in ("pulldown", "pullup", "clamp"):
        dc_file = sim_result.raw_dir / "dc_sweep.dc"
        if dc_file.exists():
            mr = meas_parser.parse_dc_sweep(dc_file, deck.name, corner.label)
            mr.deck_type = deck.deck_type
            corner_results.append(mr)
    elif deck.deck_type in ("rising", "falling"):
        tran_file = sim_result.raw_dir / "tran_sim.tran"
        mt0_file = sim_result.work_dir / f"{deck.name}.mt0"
        if tran_file.exists():
            mr = meas_parser.parse_transient(
                tran_file,
                mt0_file if mt0_file.exists() else None,
                deck.name,
                corner.label,
            )
            mr.deck_type = deck.deck_type
            corner_results.append(mr)


def _parse_ngspice_result(
    meas_parser: MeasParser,
    sim_result: SimResult,
    deck: SimDeck,
    corner: Corner,
    corner_results: list[MeasResult],
) -> None:
    """Parse NgSPICE simulation results."""
    raw_file = sim_result.raw_file
    log_file = sim_result.log_path
    if deck.deck_type in ("pulldown", "pullup", "clamp"):
        if raw_file.exists():
            mr = meas_parser.parse_dc_sweep_ngspice(raw_file, deck.name, corner.label)
            mr.deck_type = deck.deck_type
            corner_results.append(mr)
    elif deck.deck_type in ("rising", "falling"):
        if raw_file.exists():
            mr = meas_parser.parse_transient_ngspice(
                raw_file,
                log_file if log_file.exists() else None,
                deck.name,
                corner.label,
            )
            mr.deck_type = deck.deck_type
            corner_results.append(mr)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "characterize": cmd_characterize,
        "generate": cmd_generate,
        "simulate": cmd_simulate,
        "parse-results": cmd_parse_results,
        "write-ibis": cmd_write_ibis,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
