"""Tests for the CLI subcommands."""

from __future__ import annotations

from pathlib import Path

import pytest

from spice_to_ibis.cli import (
    _parse_pin_map,
    build_parser,
    cmd_generate,
    main,
)
from spice_to_ibis.models.spice import PinRole

FIXTURES = Path(__file__).parent / "fixtures"


class TestBuildParser:
    def test_subcommands_exist(self):
        parser = build_parser()
        # generate subcommand
        args = parser.parse_args([
            "generate",
            "--subcircuit", "test.scs",
            "--pin-map", "pad=pad,vdd=vdd",
            "--output-dir", "out",
        ])
        assert args.command == "generate"

    def test_characterize_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "characterize",
            "--subcircuit", "test.scs",
            "--pin-map", "pad=pad",
            "--output", "out.ibs",
        ])
        assert args.command == "characterize"
        assert args.output == Path("out.ibs")

    def test_simulate_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "simulate",
            "--deck-dir", "decks/",
            "--work-dir", "work/",
        ])
        assert args.command == "simulate"

    def test_parse_results_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "parse-results",
            "--work-dir", "work/",
            "--output", "results.json",
        ])
        assert args.command == "parse-results"

    def test_write_ibis_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "write-ibis",
            "--results", "results.json",
            "--output", "out.ibs",
        ])
        assert args.command == "write-ibis"

    def test_corner_defaults(self):
        parser = build_parser()
        args = parser.parse_args([
            "generate",
            "--subcircuit", "test.scs",
            "--pin-map", "pad=pad",
            "--output-dir", "out",
        ])
        assert args.vdd_typ == 1.8
        assert args.vdd_min == 1.62
        assert args.vdd_max == 1.98
        assert args.temp_typ == 25.0

    def test_custom_corners(self):
        parser = build_parser()
        args = parser.parse_args([
            "generate",
            "--subcircuit", "test.scs",
            "--pin-map", "pad=pad",
            "--output-dir", "out",
            "--vdd-typ", "3.3",
            "--vdd-min", "2.97",
            "--vdd-max", "3.63",
        ])
        assert args.vdd_typ == 3.3


class TestParsePinMap:
    def test_basic(self):
        result = _parse_pin_map("pad=pad,vdd=vdd,vss=vss")
        assert result["pad"] == PinRole.PAD
        assert result["vdd"] == PinRole.VDD
        assert result["vss"] == PinRole.VSS

    def test_full_mapping(self):
        result = _parse_pin_map(
            "pad=pad,vdd=vdd,vss=vss,din=input,en=enable"
        )
        assert result["din"] == PinRole.INPUT
        assert result["en"] == PinRole.ENABLE


class TestCmdGenerate:
    def test_generates_deck_files(self, tmp_path):
        parser = build_parser()
        output_dir = tmp_path / "decks"
        args = parser.parse_args([
            "generate",
            "--subcircuit", str(FIXTURES / "buf_io.scs"),
            "--pin-map", "pad=pad,vdd=vdd,vss=vss,din=input,en=enable",
            "--output-dir", str(output_dir),
        ])
        cmd_generate(args)

        scs_files = list(output_dir.glob("*.scs"))
        # 5 deck types × 3 corners = 15 files
        assert len(scs_files) == 15

    def test_deck_filenames(self, tmp_path):
        parser = build_parser()
        output_dir = tmp_path / "decks"
        args = parser.parse_args([
            "generate",
            "--subcircuit", str(FIXTURES / "buf_io.scs"),
            "--pin-map", "pad=pad,vdd=vdd,vss=vss,din=input,en=enable",
            "--output-dir", str(output_dir),
        ])
        cmd_generate(args)

        names = {f.stem for f in output_dir.glob("*.scs")}
        assert "pulldown_tt_1.8V_25.0C" in names
        assert "pullup_ss_1.62V_125.0C" in names
        assert "rising_ff_1.98V_-40.0C" in names


class TestMain:
    def test_no_command_exits(self):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1

    def test_generate_help(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["generate", "--help"])
        assert exc_info.value.code == 0

    def test_characterize_help(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["characterize", "--help"])
        assert exc_info.value.code == 0
