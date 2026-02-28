# spice-to-ibis

Generates IBIS (I/O Buffer Information Specification) models from Cadence Spectre subcircuit characterization.
Also supports NgSPICE.
Create a SPICE subckt of an LVDS driver to validate differential support.

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

# CLI subcommands
spice-to-ibis characterize   --subcircuit X.scs --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable --output Y.ibs
spice-to-ibis generate       --subcircuit X.scs --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable --output-dir D
spice-to-ibis simulate       --deck-dir D --spectre-path spectre --work-dir W
spice-to-ibis parse-results  --work-dir W --output results.json
spice-to-ibis write-ibis     --results results.json --output Y.ibs
```

## Architecture

The pipeline is: **parser → deckgen → runner (spectre) → measparser → converter → writer**

```
src/spice_to_ibis/
├── __init__.py
├── cli.py                  # Subcommand CLI (characterize, generate, simulate, parse-results, write-ibis)
├── models/
│   ├── __init__.py
│   ├── spice.py            # SpiceSubcircuit, PinRole dataclasses
│   ├── ibis.py             # IbisModel, VIPoint, VTPoint, Ramp, Waveform, CornerFloat
│   └── corners.py          # Corner, CornerSet dataclasses
├── parser.py               # Parse Spectre .scs subckt → SpiceSubcircuit
├── deckgen/
│   ├── __init__.py
│   ├── base.py             # Abstract DeckGenerator base class, SimDeck dataclass
│   ├── dc_sweep.py         # PulldownDeckGen, PullupDeckGen, ClampDeckGen
│   └── transient.py        # RisingWaveformDeckGen, FallingWaveformDeckGen
├── runner.py               # SpectreRunner: invoke spectre via subprocess
├── measparser.py           # Parse .meas logs, .mt0 files, ASCII PSF waveforms
├── converter.py            # Assemble MeasResults across corners → IbisModel
└── writer.py               # Serialize IbisModel → IBIS-formatted file
```

- `models/spice.py` — `SpiceSubcircuit`: parsed subcircuit (name, ports, pin_map, parameters, includes)
- `models/ibis.py` — `IbisModel`: full IBIS output with V-I tables, waveforms, ramp, corner data
- `models/corners.py` — `Corner`/`CornerSet`: PVT corner definitions (process/voltage/temperature)
- `parser.py` — `SpiceParser.parse()` reads a Spectre `.scs` file into a `SpiceSubcircuit`
- `deckgen/` — generates 5 simulation deck types (pulldown, pullup, clamp, rising, falling) per corner
- `runner.py` — `SpectreRunner` invokes Cadence Spectre via subprocess
- `measparser.py` — `MeasParser` parses `.mt0` files and PSF ASCII waveform data
- `converter.py` — `convert()` assembles simulation results across typ/min/max corners into `IbisModel`
- `writer.py` — `write_ibis()` / `format_ibis()` serializes `IbisModel` to compliant IBIS text
- `cli.py` — subcommand CLI wiring the pipeline together

## Conventions

- **src layout**: all package code lives under `src/spice_to_ibis/`
- **Testing**: pytest, test files in `tests/` mirror source modules (`test_parser.py`, etc.)
- **Fixtures**: sample `.scs` and Spectre output files in `tests/fixtures/`
- **Linting**: ruff (rules: E, F, I, W), line length 88
- **Types**: use `from __future__ import annotations` for modern type syntax
- **Python**: requires >=3.10
