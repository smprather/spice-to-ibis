# spice-to-ibis

Converts SPICE circuit simulation models to IBIS (I/O Buffer Information Specification) format.

## Commands

```bash
# Install (editable with dev deps, using uv)
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test
pytest tests/test_parser.py::test_parse_reads_lines

# Lint
ruff check src/ tests/

# Lint with auto-fix
ruff check --fix src/ tests/

# Format
ruff format src/ tests/

# Run the CLI
spice-to-ibis <input.spice> <output.ibs>
```

## Architecture

The conversion pipeline is: **parser -> converter -> writer**

- `src/spice_to_ibis/parser.py` — `SpiceParser.parse()` reads a SPICE file into a `SpiceModel` dataclass
- `src/spice_to_ibis/converter.py` — `convert()` transforms a `SpiceModel` into an `IbisModel` dataclass
- `src/spice_to_ibis/writer.py` — `write_ibis()` serializes an `IbisModel` to an IBIS-formatted file
- `src/spice_to_ibis/cli.py` — CLI entry point that wires the pipeline together

## Conventions

- **src layout**: all package code lives under `src/spice_to_ibis/`
- **Testing**: pytest, test files in `tests/` mirror source modules (`test_parser.py`, etc.)
- **Linting**: ruff (rules: E, F, I, W), line length 88
- **Types**: use `from __future__ import annotations` for modern type syntax
- **Python**: requires >=3.10
