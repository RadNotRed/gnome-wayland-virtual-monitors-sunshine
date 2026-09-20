from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import unittest
from unittest import mock

from gnome_virtual_monitors.__main__ import main
from test_display_state import configuration


class SaveLayoutCliTests(unittest.TestCase):
    def test_save_uses_public_operation_without_starting_or_stopping_daemon(self):
        with (
            mock.patch("sys.argv", ["gnome_virtual_monitors", "--save-layout"]),
            mock.patch(
                "gnome_virtual_monitors.__main__.load_config",
                return_value=configuration(),
            ),
            mock.patch(
                "gnome_virtual_monitors.__main__.VirtualMonitorDaemon"
            ) as daemon,
            redirect_stdout(io.StringIO()) as output,
        ):
            daemon.return_value.save_layout.return_value = Path(
                "/fake/state/layout.json"
            )
            self.assertEqual(main(), 0)
            daemon.return_value.save_layout.assert_called_once_with()
            daemon.return_value.start.assert_not_called()
            daemon.return_value.stop.assert_not_called()
            self.assertIn("Layout saved to /fake/state/layout.json", output.getvalue())

    def test_failed_save_reports_clear_error(self):
        with (
            mock.patch("sys.argv", ["gnome_virtual_monitors", "--save-layout"]),
            mock.patch(
                "gnome_virtual_monitors.__main__.load_config",
                return_value=configuration(),
            ),
            mock.patch(
                "gnome_virtual_monitors.__main__.VirtualMonitorDaemon"
            ) as daemon,
            redirect_stderr(io.StringIO()) as output,
        ):
            daemon.return_value.save_layout.side_effect = RuntimeError(
                "missing virtual role"
            )
            self.assertEqual(main(), 1)
            self.assertIn(
                "Could not save layout: missing virtual role", output.getvalue()
            )
            daemon.return_value.start.assert_not_called()
            daemon.return_value.stop.assert_not_called()
