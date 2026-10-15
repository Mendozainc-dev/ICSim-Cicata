import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

MAIN_DIR = Path(__file__).resolve().parent.parent
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

from icsim import ICSimLauncher


class ICSimLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.icsim_dir = self.repo_root / "ICSim-master"
        self.build_dir = self.icsim_dir / "builddir"
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.launcher = ICSimLauncher(repo_root=self.repo_root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_is_compiled_false_when_binaries_missing(self):
        self.assertFalse(self.launcher.is_compiled())

    def test_is_compiled_true_when_binaries_present(self):
        icsim_bin = self.build_dir / "icsim"
        controls_bin = self.build_dir / "controls"
        icsim_bin.write_text("#!/bin/sh\nexit 0\n")
        controls_bin.write_text("#!/bin/sh\nexit 0\n")
        icsim_bin.chmod(0o755)
        controls_bin.chmod(0o755)

        self.assertTrue(self.launcher.is_compiled())

    @patch("subprocess.run")
    def test_is_vcan_up(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(self.launcher.is_vcan_up("vcan0"))
        mock_run.assert_called_with(
            ["ip", "link", "show", "vcan0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        mock_run.return_value = MagicMock(returncode=1)
        self.assertFalse(self.launcher.is_vcan_up("vcan0"))

    @patch("subprocess.Popen")
    def test_start_and_stop_simulators(self, mock_popen):
        icsim_bin = self.build_dir / "icsim"
        controls_bin = self.build_dir / "controls"
        icsim_bin.write_text("")
        controls_bin.write_text("")
        icsim_bin.chmod(0o755)
        controls_bin.chmod(0o755)

        mock_proc1 = MagicMock()
        mock_proc1.poll.return_value = None
        mock_proc2 = MagicMock()
        mock_proc2.poll.return_value = None
        mock_popen.side_effect = [mock_proc1, mock_proc2]

        started = self.launcher.start_simulators("vcan0")
        self.assertTrue(started)
        self.assertEqual(len(self.launcher.managed_processes), 2)

        self.launcher.stop_simulators()
        mock_proc1.terminate.assert_called_once()
        mock_proc2.terminate.assert_called_once()
        self.assertEqual(len(self.launcher.managed_processes), 0)


if __name__ == "__main__":
    unittest.main()
