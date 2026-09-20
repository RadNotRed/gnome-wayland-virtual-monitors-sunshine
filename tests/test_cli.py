from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from gnome_virtual_monitors.__main__ import main
from gnome_virtual_monitors.saved_layout import read_saved_layout
from test_display_state import configuration, logical, monitor


class SaveLayoutCliTests(unittest.TestCase):
    def invoke(self, directory, monitors, groups):
        path = Path(directory) / "layout.json"
        with (
            mock.patch("sys.argv", ["gnome_virtual_monitors", "--save-layout"]),
            mock.patch(
                "gnome_virtual_monitors.__main__.load_config",
                return_value=configuration(),
            ),
            mock.patch(
                "gnome_virtual_monitors.__main__.default_state_path", return_value=path
            ),
            mock.patch(
                "gnome_virtual_monitors.__main__.VirtualMonitorDaemon"
            ) as daemon,
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()),
        ):
            daemon.return_value._get_current_state.return_value = (
                1,
                monitors,
                groups,
                {"layout-mode": 1},
            )
            result = main()
            daemon.return_value.start.assert_not_called()
            daemon.return_value.stop.assert_not_called()
        return result, path

    def test_save_reads_active_layout_without_creating_or_stopping_sessions(self):
        physical = monitor("physical-A")
        virtual = monitor("Meta-4", 1280, 720, 60, True)
        with tempfile.TemporaryDirectory() as directory:
            result, path = self.invoke(
                directory,
                [physical, virtual],
                [logical(physical), logical(virtual, primary=False)],
            )
            self.assertEqual(result, 0)
            self.assertEqual(set(read_saved_layout(path)["roles"]), {"client"})

    def test_failed_capture_does_not_overwrite_a_saved_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "layout.json"
            path.write_text("previous state")
            result, _ = self.invoke(directory, [], [])
            self.assertEqual(result, 1)
            self.assertEqual(path.read_text(), "previous state")
