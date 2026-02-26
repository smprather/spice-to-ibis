"""Command-line interface for spice-to-ibis."""

from __future__ import annotations

import argparse

from spice_to_ibis.converter import convert
from spice_to_ibis.parser import SpiceParser
from spice_to_ibis.writer import write_ibis


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="spice-to-ibis",
        description="Convert SPICE circuit simulation models to IBIS format.",
    )
    parser.add_argument("input", help="Path to input SPICE model file")
    parser.add_argument("output", help="Path to output IBIS file")
    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    spice_parser = SpiceParser()
    spice_model = spice_parser.parse(args.input)
    ibis_model = convert(spice_model)
    write_ibis(ibis_model, args.output)

    print(f"Converted {args.input} -> {args.output}")


if __name__ == "__main__":
    main()
