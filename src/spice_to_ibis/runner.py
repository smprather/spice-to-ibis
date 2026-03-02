"""Cadence Spectre simulation runner."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from spice_to_ibis.deckgen.base import SimDeck

log = logging.getLogger(__name__)


@dataclass
class SimResult:
    """Result of running a simulation."""

    deck: SimDeck
    return_code: int
    work_dir: Path
    stdout: str = ""
    stderr: str = ""
    simulator: str = "spectre"

    @property
    def success(self) -> bool:
        return self.return_code == 0

    @property
    def raw_dir(self) -> Path:
        """Path to the PSF raw data directory (Spectre)."""
        return self.work_dir / f"{self.deck.name}.raw"

    @property
    def raw_file(self) -> Path:
        """Path to the raw data file (NgSPICE)."""
        return self.work_dir / f"{self.deck.name}.raw"

    @property
    def log_path(self) -> Path:
        """Path to the simulation log file."""
        return self.work_dir / f"{self.deck.name}.log"


class SpectreRunner:
    """Run Cadence Spectre simulations."""

    def __init__(
        self,
        spectre_path: str = "spectre",
        timeout: int = 600,
    ):
        self.spectre_path = spectre_path
        self.timeout = timeout

    def write_deck(self, deck: SimDeck, output_dir: Path) -> Path:
        """Write a simulation deck to a file.

        Returns the path to the written .scs file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        deck_path = output_dir / f"{deck.name}.scs"
        deck_path.write_text(deck.content)
        return deck_path

    def run(self, deck: SimDeck, work_dir: Path) -> SimResult:
        """Run a Spectre simulation.

        Args:
            deck: The simulation deck to run.
            work_dir: Working directory for simulation files and results.

        Returns:
            SimResult with return code, stdout, stderr.
        """
        deck_path = self.write_deck(deck, work_dir)
        log_path = work_dir / f"{deck.name}.log"

        cmd = [
            self.spectre_path,
            str(deck_path),
            "-format",
            "psfascii",
            "-raw",
            str(work_dir / f"{deck.name}.raw"),
            "-log",
            str(log_path),
            "+mt0",
        ]

        log.info("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=work_dir,
            )
            return SimResult(
                deck=deck,
                return_code=result.returncode,
                work_dir=work_dir,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            log.error("Simulation timed out: %s", deck.name)
            return SimResult(
                deck=deck,
                return_code=-1,
                work_dir=work_dir,
                stderr=f"Simulation timed out after {self.timeout}s",
            )
        except FileNotFoundError:
            log.error("Spectre not found at: %s", self.spectre_path)
            return SimResult(
                deck=deck,
                return_code=-1,
                work_dir=work_dir,
                stderr=f"Spectre not found at: {self.spectre_path}",
            )

    def run_all(self, decks: list[SimDeck], work_dir: Path) -> list[SimResult]:
        """Run all simulation decks sequentially."""
        results = []
        for deck in decks:
            result = self.run(deck, work_dir)
            results.append(result)
        return results


class NgspiceRunner:
    """Run NgSPICE simulations."""

    def __init__(
        self,
        ngspice_path: str = "ngspice",
        timeout: int = 600,
    ):
        self.ngspice_path = ngspice_path
        self.timeout = timeout

    def write_deck(self, deck: SimDeck, output_dir: Path) -> Path:
        """Write a simulation deck to a .cir file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        deck_path = output_dir / f"{deck.name}.cir"
        deck_path.write_text(deck.content)
        return deck_path

    def run(self, deck: SimDeck, work_dir: Path) -> SimResult:
        """Run an NgSPICE simulation.

        Args:
            deck: The simulation deck to run.
            work_dir: Working directory for simulation files and results.

        Returns:
            SimResult with return code, stdout, stderr.
        """
        deck_path = self.write_deck(deck, work_dir)
        log_path = work_dir / f"{deck.name}.log"

        cmd = [
            self.ngspice_path,
            "-b",
            str(deck_path),
            "-o",
            str(log_path),
        ]

        log.info("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=work_dir,
            )
            return SimResult(
                deck=deck,
                return_code=result.returncode,
                work_dir=work_dir,
                stdout=result.stdout,
                stderr=result.stderr,
                simulator="ngspice",
            )
        except subprocess.TimeoutExpired:
            log.error("Simulation timed out: %s", deck.name)
            return SimResult(
                deck=deck,
                return_code=-1,
                work_dir=work_dir,
                stderr=f"Simulation timed out after {self.timeout}s",
                simulator="ngspice",
            )
        except FileNotFoundError:
            log.error("NgSPICE not found at: %s", self.ngspice_path)
            return SimResult(
                deck=deck,
                return_code=-1,
                work_dir=work_dir,
                stderr=f"NgSPICE not found at: {self.ngspice_path}",
                simulator="ngspice",
            )

    def run_all(self, decks: list[SimDeck], work_dir: Path) -> list[SimResult]:
        """Run all simulation decks sequentially."""
        results = []
        for deck in decks:
            result = self.run(deck, work_dir)
            results.append(result)
        return results


def get_runner(
    simulator: str = "spectre",
    path: str | None = None,
    timeout: int = 600,
) -> SpectreRunner | NgspiceRunner:
    """Factory to get the runner for a simulator.

    Args:
        simulator: "spectre" or "ngspice".
        path: Path to the simulator binary.
        timeout: Simulation timeout in seconds.

    Returns:
        Runner instance.
    """
    if simulator == "spectre":
        return SpectreRunner(spectre_path=path or "spectre", timeout=timeout)
    if simulator == "ngspice":
        return NgspiceRunner(ngspice_path=path or "ngspice", timeout=timeout)
    raise ValueError(f"Unknown simulator: {simulator!r}")
