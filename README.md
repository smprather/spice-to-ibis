# spice-to-ibis

Generate [IBIS](https://ibis.org/) (I/O Buffer Information Specification) models from SPICE subcircuit characterization. Automates the entire flow from a transistor-level subcircuit definition through simulation and measurement extraction to a standards-compliant `.ibs` file.

Supports both **Cadence Spectre** and **NgSPICE** as simulation backends.

## Why

Creating IBIS models by hand is tedious and error-prone. It requires setting up dozens of simulation decks (DC sweeps for V-I curves, transient analyses for waveform tables), running them across process/voltage/temperature (PVT) corners, parsing the results, and formatting everything to the IBIS specification. `spice-to-ibis` automates this entire pipeline so you can go from a subcircuit netlist to a validated `.ibs` file in a single command.

## Features

- **Automatic deck generation** — Produces all 5 required simulation types (pulldown, pullup, clamp, rising waveform, falling waveform) for each PVT corner (typ/min/max), yielding 15 simulation decks by default.
- **Dual simulator support** — Works with Cadence Spectre (`.scs`) or NgSPICE (`.cir`) via a syntax adapter pattern. The simulation *intent* is identical; only the netlist syntax differs.
- **Full PVT corner coverage** — Configurable voltage and temperature corners for typ (tt), min (ss), and max (ff) process corners.
- **IBIS-compliant output** — Generates V-I tables (pulldown, pullup, GND clamp, POWER clamp), ramp rates (dV/dt), and rising/falling waveform tables per the IBIS 7.0 specification.
- **Modular pipeline** — Each stage (parse, generate, simulate, measure, convert, write) can be run independently via CLI subcommands, enabling integration into existing EDA workflows.
- **Pin-role mapping** — Flexible mapping from subcircuit port names to IBIS roles (pad, vdd, vss, input, enable) so the tool works with any naming convention.

## Installation

Requires Python 3.10 or later.

```bash
# Using uv (recommended)
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

This installs the `spice-to-ibis` CLI command and development dependencies (pytest, ruff).

## Quick Start

### End-to-end characterization (single command)

```bash
# Using Spectre (default)
spice-to-ibis characterize \
  --subcircuit my_buffer.scs \
  --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable \
  --output my_buffer.ibs

# Using NgSPICE
spice-to-ibis characterize \
  --simulator ngspice \
  --subcircuit my_buffer.cir \
  --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable \
  --sim-path /usr/bin/ngspice \
  --output my_buffer.ibs
```

This runs the full pipeline: parse the subcircuit, generate 15 simulation decks (5 types x 3 corners), run them all, parse the results, and write the IBIS file.

### Step-by-step workflow

For more control, run each stage independently:

```bash
# 1. Generate simulation decks
spice-to-ibis generate \
  --subcircuit my_buffer.scs \
  --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable \
  --output-dir decks/

# 2. Run simulations
spice-to-ibis simulate \
  --deck-dir decks/ \
  --spectre-path /opt/cadence/spectre \
  --work-dir work/

# 3. Parse simulation results
spice-to-ibis parse-results \
  --work-dir work/ \
  --output results.json

# 4. Write IBIS file
spice-to-ibis write-ibis \
  --results results.json \
  --output my_buffer.ibs
```

### Custom PVT corners

Override the default voltage and temperature corners:

```bash
spice-to-ibis characterize \
  --subcircuit my_buffer.scs \
  --pin-map pad=pad,vdd=vdd,vss=vss,din=input,en=enable \
  --vdd-typ 3.3 --vdd-min 2.97 --vdd-max 3.63 \
  --temp-typ 25 --temp-min 125 --temp-max -40 \
  --output my_buffer.ibs
```

## CLI Reference

### Global options

| Option | Description | Default |
|---|---|---|
| `--simulator` | Simulator backend: `spectre` or `ngspice` | `spectre` |
| `--sim-path` | Path to simulator binary | auto-detected |
| `--spectre-path` | Legacy alias for `--sim-path` (Spectre only) | `spectre` |

### Subcommands

#### `characterize`

End-to-end pipeline: generate decks, simulate, parse results, write IBIS.

```
spice-to-ibis characterize --subcircuit FILE --pin-map MAP --output FILE
    [--simulator spectre|ngspice] [--sim-path PATH]
    [--work-dir DIR] [--vdd-typ V] [--vdd-min V] [--vdd-max V]
    [--temp-typ T] [--temp-min T] [--temp-max T]
```

#### `generate`

Generate simulation deck files without running them.

```
spice-to-ibis generate --subcircuit FILE --pin-map MAP --output-dir DIR
    [--simulator spectre|ngspice]
    [--vdd-typ V] [--vdd-min V] [--vdd-max V]
    [--temp-typ T] [--temp-min T] [--temp-max T]
```

#### `simulate`

Run the simulator on pre-generated deck files.

```
spice-to-ibis simulate --deck-dir DIR
    [--simulator spectre|ngspice] [--sim-path PATH]
    [--work-dir DIR]
```

#### `parse-results`

Parse simulation output files into a JSON results file.

```
spice-to-ibis parse-results --work-dir DIR --output FILE
    [--simulator spectre|ngspice]
```

#### `write-ibis`

Write an IBIS file from a previously generated results JSON.

```
spice-to-ibis write-ibis --results FILE --output FILE
```

### Pin map format

The `--pin-map` argument maps subcircuit port names to their IBIS roles:

```
--pin-map port1=role1,port2=role2,...
```

Available roles:

| Role | Description |
|---|---|
| `pad` | The I/O pad (output pin under test) |
| `vdd` | Power supply |
| `vss` | Ground |
| `input` | Data input to the driver |
| `enable` | Output enable (active high) |
| `output` | Output (for input buffer characterization) |

Example: `--pin-map io=pad,VDD=vdd,GND=vss,D=input,OE=enable`

## Architecture

The pipeline flows through six stages:

```
subcircuit file ──> parser ──> deckgen ──> runner ──> measparser ──> converter ──> writer ──> .ibs file
                     │            │          │           │              │            │
                  SpiceParser  DeckGen   SpectreRunner  MeasParser   convert()   write_ibis()
                  NgspiceParser  (x5)    NgspiceRunner
```

### Project structure

```
src/spice_to_ibis/
├── __init__.py              # Package exports and version
├── cli.py                   # Argument parsing and subcommand dispatch
├── syntax.py                # SimSyntax ABC with SpectreSyntax / NgspiceSyntax
├── parser.py                # SpiceParser (.scs) and NgspiceParser (.cir)
├── deckgen/
│   ├── __init__.py
│   ├── base.py              # DeckGenerator ABC, SimDeck dataclass
│   ├── dc_sweep.py          # PulldownDeckGen, PullupDeckGen, ClampDeckGen
│   └── transient.py         # RisingWaveformDeckGen, FallingWaveformDeckGen
├── runner.py                # SpectreRunner, NgspiceRunner, SimResult
├── measparser.py            # Parse Spectre PSF/.mt0 and NgSPICE .raw/.log
├── converter.py             # Assemble MeasResults into IbisModel
├── writer.py                # Serialize IbisModel to IBIS text format
└── models/
    ├── __init__.py
    ├── spice.py             # SpiceSubcircuit, PinRole
    ├── ibis.py              # IbisModel, VIPoint, VTPoint, Ramp, Waveform
    └── corners.py           # Corner, CornerSet
```

### Key design decisions

**Syntax adapter pattern.** Rather than duplicating the 5 deck generator classes for each simulator, a `SimSyntax` abstract base class defines all syntax operations (voltage sources, resistors, analysis statements, etc.). `SpectreSyntax` and `NgspiceSyntax` implement these with their respective netlist formats. Each deck generator receives a syntax object and delegates all formatting to it.

**Simulator-agnostic downstream.** Everything after `MeasResult` (the converter and writer) is completely simulator-agnostic. Both Spectre and NgSPICE results are parsed into the same `MeasResult` dataclass, so the IBIS model assembly and output formatting work identically regardless of which simulator produced the data.

**Factory functions.** `get_syntax()`, `get_parser()`, and `get_runner()` provide simple factories that accept a `"spectre"` or `"ngspice"` string, making it easy to add new simulators in the future.

### Simulation types

The tool generates 5 simulation types per corner:

| Type | Analysis | Purpose |
|---|---|---|
| **Pulldown** | DC sweep V(pad), din=LOW, en=HIGH | V-I curve with driver pulling low |
| **Pullup** | DC sweep V(pad), din=HIGH, en=HIGH | V-I curve with driver pulling high |
| **Clamp** | DC sweep V(pad), en=LOW (tri-state) | GND clamp and POWER clamp V-I curves |
| **Rising** | Transient, din pulse LOW→HIGH, R_fix=50Ω | Rising waveform + 20%/80% crossing times |
| **Falling** | Transient, din pulse HIGH→LOW, R_fix=50Ω | Falling waveform + 80%/20% crossing times |

Each type is generated for 3 PVT corners (typ/min/max), yielding 15 simulations total.

## Subcircuit requirements

Your SPICE subcircuit should be a standard I/O buffer with these ports:

- **pad** — The I/O pad (bidirectional output)
- **vdd** — Power supply
- **vss** — Ground reference
- **input** — Data input controlling the output driver
- **enable** — Output enable (active-high; low = tri-state)

The port names can be anything; the `--pin-map` argument maps them to their roles.

### Spectre format (`.scs`)

```spectre
simulator lang=spectre

include "models/nmos.scs" section=tt
include "models/pmos.scs" section=tt

subckt buf_io (pad vdd vss din en)
parameters wp=2u wn=1u

    mp0 (pad din_b vdd vdd) pmos w=wp l=100n
    mn0 (pad din_i vss vss) nmos w=wn l=100n
    // ... internal logic ...

ends buf_io
```

### NgSPICE format (`.cir`)

```spice
* Buffer I/O subcircuit

.include "models/nmos.cir"
.include "models/pmos.cir"

.subckt buf_io pad vdd vss din en wp=2u wn=1u

Mp0 pad din_b vdd vdd pmos w=wp l=100n
Mn0 pad din_i vss vss nmos w=wn l=100n
* ... internal logic ...

.ends buf_io
```

## Development

### Running tests

```bash
# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_parser.py

# Run a specific test
uv run pytest tests/test_deckgen.py::TestPulldownDeckGen::test_din_driven_low

# Run with verbose output
uv run pytest -v
```

### Linting and formatting

```bash
# Check for lint errors
uv run ruff check src/ tests/

# Auto-fix lint errors
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/
```

### Test structure

Tests mirror the source module structure:

| Source module | Test file | Coverage |
|---|---|---|
| `syntax.py` | `tests/test_syntax.py` | Both syntax adapters, factory |
| `parser.py` | `tests/test_parser.py` | Spectre and NgSPICE parsers |
| `deckgen/` | `tests/test_deckgen.py` | All 5 generators, both syntaxes |
| `runner.py` | `tests/test_runner.py` | Both runners (mocked subprocess) |
| `measparser.py` | `tests/test_measparser.py` | PSF, .mt0, .raw, .log parsers |
| `converter.py` | `tests/test_converter.py` | V-I table, clamp, waveform, ramp assembly |
| `writer.py` | `tests/test_writer.py` | IBIS text serialization |
| `cli.py` | `tests/test_cli.py` | All subcommands, both simulators |
| `models/` | `tests/test_models.py` | Dataclass construction and properties |

Test fixtures are in `tests/fixtures/` and include sample Spectre `.scs` files, NgSPICE `.cir` files, and mock simulator output files (`.mt0`, `.raw`, `.log`).

## License

MIT
