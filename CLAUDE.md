# spice-to-ibis

Generates IBIS (I/O Buffer Information Specification) models from SPICE subcircuit characterization.
Supports both Cadence Spectre and NgSPICE simulators.
Supports single-ended and differential (LVDS) I/O buffer topologies.

## Commands

```bash
# Install (editable with dev deps, using uv)
uv pip install -e ".[dev]"

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_parser.py::TestParseSubcircuit::test_parse_reads_lines

# Lint
uv run ruff check src/ tests/

# Lint with auto-fix
uv run ruff check --fix src/ tests/

# Format
uv run ruff format src/ tests/

# CLI subcommands (Spectre, default)
spice-to-ibis characterize   --subcircuit X.scs --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable --output Y.ibs
spice-to-ibis generate       --subcircuit X.scs --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable --output-dir D
spice-to-ibis simulate       --deck-dir D --spectre-path spectre --work-dir W
spice-to-ibis parse-results  --work-dir W --output results.json
spice-to-ibis write-ibis     --results results.json --output Y.ibs

# CLI subcommands (NgSPICE)
spice-to-ibis characterize   --simulator ngspice --subcircuit X.cir --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable --sim-path ngspice --output Y.ibs
spice-to-ibis generate       --simulator ngspice --subcircuit X.cir --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable --output-dir D
spice-to-ibis simulate       --simulator ngspice --deck-dir D --sim-path ngspice --work-dir W
spice-to-ibis parse-results  --simulator ngspice --work-dir W --output results.json
```

## Architecture

The pipeline is: **parser → deckgen → runner (spectre/ngspice) → measparser → converter → writer**

```text
src/spice_to_ibis/
├── __init__.py
├── cli.py                  # Subcommand CLI (characterize, generate, simulate, parse-results, write-ibis)
├── syntax.py               # SimSyntax ABC, SpectreSyntax, NgspiceSyntax adapters
├── models/
│   ├── __init__.py
│   ├── spice.py            # SpiceSubcircuit, PinRole dataclasses
│   ├── ibis.py             # IbisModel, VIPoint, VTPoint, Ramp, Waveform, CornerFloat
│   └── corners.py          # Corner, CornerSet dataclasses
├── parser.py               # SpiceParser (Spectre), NgspiceParser, get_parser() factory
├── deckgen/
│   ├── __init__.py
│   ├── base.py             # Abstract DeckGenerator base class, SimDeck dataclass
│   ├── dc_sweep.py         # PulldownDeckGen, PullupDeckGen, ClampDeckGen
│   └── transient.py        # RisingWaveformDeckGen, FallingWaveformDeckGen
├── runner.py               # SpectreRunner, NgspiceRunner, get_runner() factory
├── measparser.py           # Parse .mt0/.psf (Spectre) and .raw/.log (NgSPICE)
├── converter.py            # Assemble MeasResults across corners → IbisModel
└── writer.py               # Serialize IbisModel → IBIS-formatted file
```

- `syntax.py` — `SimSyntax` ABC with `SpectreSyntax` and `NgspiceSyntax`; `get_syntax()` factory
- `models/spice.py` — `SpiceSubcircuit`: parsed subcircuit (name, ports, pin_map, parameters, includes)
- `models/ibis.py` — `IbisModel`: full IBIS output with V-I tables, waveforms, ramp, corner data
- `models/corners.py` — `Corner`/`CornerSet`: PVT corner definitions (process/voltage/temperature)
- `parser.py` — `SpiceParser` (Spectre `.scs`), `NgspiceParser` (`.cir`), `get_parser()` factory
- `deckgen/` — generates 5 simulation deck types (pulldown, pullup, clamp, rising, falling) per corner; delegates syntax to `SimSyntax`
- `runner.py` — `SpectreRunner`, `NgspiceRunner`, `get_runner()` factory
- `measparser.py` — `MeasParser` parses Spectre `.mt0`/PSF and NgSPICE `.raw`/measurement logs
- `converter.py` — `convert()` assembles simulation results across typ/min/max corners into `IbisModel`
- `writer.py` — `write_ibis()` / `format_ibis()` serializes `IbisModel` to compliant IBIS text
- `cli.py` — subcommand CLI with `--simulator spectre|ngspice` and `--sim-path` flags

## Conventions

- **src layout**: all package code lives under `src/spice_to_ibis/`
- **Testing**: pytest, test files in `tests/` mirror source modules (`test_parser.py`, etc.)
- **Fixtures**: sample `.scs`, `.cir`, and simulator output files in `tests/fixtures/`
- **Linting**: ruff (rules: E, F, I, W), line length 110
- **Types**: use `from __future__ import annotations` for modern type syntax
- **Python**: requires >=3.14
- Use Python Click, and its wrapper rich-click, for CLI
- Always use Python Pathlib when possible
- Add type hints to all function declarations
