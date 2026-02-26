# spice-to-ibis

Convert SPICE circuit simulation models to IBIS (I/O Buffer Information Specification) format.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```bash
spice-to-ibis input.spice output.ibs
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check src/ tests/
```
