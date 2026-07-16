from __future__ import annotations

import tempfile
import unittest
from unittest import mock

from gi.repository import Gio

from gnome_virtual_monitors.daemon import VirtualMonitorDaemon
from gnome_virtual_monitors.model import (
    DaemonConfig,
    PrimaryConfig,
    VirtualMonitorConfig,
)


class StaticDisplayStateDaemon(VirtualMonitorDaemon):
    def _get_current_state(self):
        specification = ("HDMI-1", "vendor", "model", "serial")
        mode = (
            "1920x1080@60",
            1920,
            1080,
            60.0,
            1.0,
            [1.0],
            {"is-current": True},
        )
        monitors = [(specification, [mode], {})]
        logical_monitors = [
            (0, 0, 1.0, 0, True, [specification], {})
        ]
        return 1, monitors, logical_monitors, {"layout-mode": 1}


class DaemonPreflightTests(unittest.TestCase):
    def test_rejects_an_unavailable_primary_mode_before_creating_outputs(self):
        config = DaemonConfig(
            primary=PrimaryConfig(
                name="primary",
                connector="HDMI-1",
                width=1920,
                height=1080,
                refresh=120,
                scale=1.0,
            ),
            monitors=(
                VirtualMonitorConfig(
                    name="phone",
                    width=2340,
                    height=1080,
                    refresh=120,
                    scale=1.75,
                    relative_to="primary",
                    position="below",
                    alignment="center",
                ),
            ),
            layout_mode=1,
            layout_retries=20,
            startup_timeout=15,
        )
        with tempfile.TemporaryDirectory() as runtime_directory:
            with mock.patch.dict(
                "os.environ",
                {"XDG_RUNTIME_DIR": runtime_directory},
            ):
                daemon = StaticDisplayStateDaemon(config)
                with mock.patch.object(
                    Gio.DBusProxy,
                    "new_for_bus_sync",
                    side_effect=AssertionError(
                        "D-Bus output creation happened before preflight"
                    ),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "No refresh near 120",
                    ):
                        daemon.start()
