"""Tests for the Spectre runner (mocked subprocess)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from spice_to_ibis.deckgen.base import SimDeck
from spice_to_ibis.models.corners import Corner
from spice_to_ibis.runner import NgspiceRunner, SimResult, SpectreRunner, get_runner


@pytest.fixture
def deck():
    corner = Corner("typ", "tt", 1.8, 25.0)
    return SimDeck(
        name="pulldown_tt_1.8V_25.0C",
        deck_type="pulldown",
        corner=corner,
        content="// test deck content\nsimulator lang=spectre\n",
    )


class TestSpectreRunner:
    def test_write_deck(self, deck, tmp_path):
        runner = SpectreRunner()
        path = runner.write_deck(deck, tmp_path)
        assert path.exists()
        assert path.name == "pulldown_tt_1.8V_25.0C.scs"
        assert "test deck content" in path.read_text()

    def test_write_deck_creates_dir(self, deck, tmp_path):
        runner = SpectreRunner()
        out_dir = tmp_path / "sub" / "dir"
        path = runner.write_deck(deck, out_dir)
        assert path.exists()

    @patch("spice_to_ibis.runner.subprocess.run")
    def test_run_success(self, mock_run, deck, tmp_path):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Simulation complete"
        mock_run.return_value.stderr = ""

        runner = SpectreRunner()
        result = runner.run(deck, tmp_path)

        assert isinstance(result, SimResult)
        assert result.success
        assert result.return_code == 0
        mock_run.assert_called_once()

    @patch("spice_to_ibis.runner.subprocess.run")
    def test_run_failure(self, mock_run, deck, tmp_path):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Error in simulation"

        runner = SpectreRunner()
        result = runner.run(deck, tmp_path)

        assert not result.success
        assert result.return_code == 1

    @patch("spice_to_ibis.runner.subprocess.run")
    def test_run_spectre_command(self, mock_run, deck, tmp_path):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        runner = SpectreRunner(spectre_path="/opt/cadence/spectre")
        runner.run(deck, tmp_path)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/opt/cadence/spectre"
        assert "-format" in cmd
        assert "psfascii" in cmd

    @patch(
        "spice_to_ibis.runner.subprocess.run",
        side_effect=FileNotFoundError,
    )
    def test_run_spectre_not_found(self, mock_run, deck, tmp_path):
        runner = SpectreRunner()
        result = runner.run(deck, tmp_path)
        assert not result.success
        assert "not found" in result.stderr

    @patch("spice_to_ibis.runner.subprocess.run")
    def test_run_all(self, mock_run, tmp_path):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        corner = Corner("typ", "tt", 1.8, 25.0)
        decks = [
            SimDeck(name=f"deck_{i}", deck_type="pulldown", corner=corner, content="x")
            for i in range(3)
        ]
        runner = SpectreRunner()
        results = runner.run_all(decks, tmp_path)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_sim_result_properties(self, deck, tmp_path):
        result = SimResult(deck=deck, return_code=0, work_dir=tmp_path)
        assert result.raw_dir == tmp_path / "pulldown_tt_1.8V_25.0C.raw"
        assert result.log_path == tmp_path / "pulldown_tt_1.8V_25.0C.log"

    def test_sim_result_default_simulator(self, deck, tmp_path):
        result = SimResult(deck=deck, return_code=0, work_dir=tmp_path)
        assert result.simulator == "spectre"


class TestNgspiceRunner:
    def test_write_deck(self, deck, tmp_path):
        runner = NgspiceRunner()
        path = runner.write_deck(deck, tmp_path)
        assert path.exists()
        assert path.name == "pulldown_tt_1.8V_25.0C.cir"
        assert "test deck content" in path.read_text()

    def test_write_deck_creates_dir(self, deck, tmp_path):
        runner = NgspiceRunner()
        out_dir = tmp_path / "sub" / "dir"
        path = runner.write_deck(deck, out_dir)
        assert path.exists()

    @patch("spice_to_ibis.runner.subprocess.run")
    def test_run_success(self, mock_run, deck, tmp_path):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "NgSPICE done"
        mock_run.return_value.stderr = ""

        runner = NgspiceRunner()
        result = runner.run(deck, tmp_path)

        assert isinstance(result, SimResult)
        assert result.success
        assert result.simulator == "ngspice"
        mock_run.assert_called_once()

    @patch("spice_to_ibis.runner.subprocess.run")
    def test_run_failure(self, mock_run, deck, tmp_path):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Error"

        runner = NgspiceRunner()
        result = runner.run(deck, tmp_path)

        assert not result.success
        assert result.simulator == "ngspice"

    @patch("spice_to_ibis.runner.subprocess.run")
    def test_run_ngspice_command(self, mock_run, deck, tmp_path):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        runner = NgspiceRunner(ngspice_path="/usr/bin/ngspice")
        runner.run(deck, tmp_path)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/usr/bin/ngspice"
        assert "-b" in cmd

    @patch(
        "spice_to_ibis.runner.subprocess.run",
        side_effect=FileNotFoundError,
    )
    def test_run_ngspice_not_found(self, mock_run, deck, tmp_path):
        runner = NgspiceRunner()
        result = runner.run(deck, tmp_path)
        assert not result.success
        assert "not found" in result.stderr
        assert result.simulator == "ngspice"

    @patch("spice_to_ibis.runner.subprocess.run")
    def test_run_all(self, mock_run, tmp_path):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        corner = Corner("typ", "tt", 1.8, 25.0)
        decks = [
            SimDeck(name=f"deck_{i}", deck_type="pulldown", corner=corner, content="x")
            for i in range(3)
        ]
        runner = NgspiceRunner()
        results = runner.run_all(decks, tmp_path)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(r.simulator == "ngspice" for r in results)

    def test_sim_result_raw_file(self, deck, tmp_path):
        result = SimResult(
            deck=deck, return_code=0, work_dir=tmp_path, simulator="ngspice"
        )
        assert result.raw_file == tmp_path / "pulldown_tt_1.8V_25.0C.raw"


class TestGetRunner:
    def test_get_spectre_runner(self):
        runner = get_runner("spectre")
        assert isinstance(runner, SpectreRunner)

    def test_get_ngspice_runner(self):
        runner = get_runner("ngspice")
        assert isinstance(runner, NgspiceRunner)

    def test_default_is_spectre(self):
        runner = get_runner()
        assert isinstance(runner, SpectreRunner)

    def test_custom_path(self):
        runner = get_runner("ngspice", path="/opt/ngspice/bin/ngspice")
        assert isinstance(runner, NgspiceRunner)
        assert runner.ngspice_path == "/opt/ngspice/bin/ngspice"

    def test_custom_timeout(self):
        runner = get_runner("spectre", timeout=1200)
        assert runner.timeout == 1200

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown simulator"):
            get_runner("hspice")
