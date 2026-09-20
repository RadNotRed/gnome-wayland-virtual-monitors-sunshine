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
            preserve_physical_monitors=False,
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


class DaemonLayoutTests(unittest.TestCase):
    def make_daemon(self, directory, preserve=True):
        from test_display_state import configuration, logical, monitor
        from pathlib import Path
        daemon = VirtualMonitorDaemon(configuration(preserve_physical_monitors=preserve))
        daemon.ready_file = Path(directory) / "ready"
        physical = monitor("physical-A", refresh=60)
        second = monitor("physical-B", refresh=240.01971435546875)
        virtual = monitor("Meta-8", 1280, 720, 60, True)
        before = (1, [physical, second], [logical(physical), logical(second, x=1920, transform=1, primary=False)], {"layout-mode": 1})
        after = (2, [physical, second, virtual], before[2] + [logical(virtual, primary=False)], before[3])
        daemon._get_current_state = mock.Mock(return_value=before)
        daemon.preexisting_virtual_connectors = daemon._preflight_display()
        daemon._get_current_state.return_value = after
        return daemon

    def test_preserved_and_legacy_apply_payloads_and_readiness(self):
        for preserve in (True, False):
            with self.subTest(preserve=preserve), tempfile.TemporaryDirectory() as directory:
                daemon = self.make_daemon(directory, preserve)
                payloads = []
                def apply(_method, variant, *_args):
                    self.assertFalse(daemon.ready_file.exists())
                    payloads.append(variant.unpack())
                proxy = mock.Mock()
                proxy.call_sync.side_effect = apply
                daemon._new_display_config_proxy = mock.Mock(return_value=proxy)
                daemon._apply_layout()
                self.assertFalse(daemon.failed)
                self.assertTrue(daemon.ready_file.exists())
                self.assertEqual([p[1] for p in payloads], [0, 1])
                self.assertEqual(len(payloads[-1][2]), 3 if preserve else 2)
                if preserve:
                    self.assertEqual(payloads[-1][2][1][:5], (1920, 0, 1.0, 1, False))

    def test_failed_verification_does_not_apply_or_mark_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            daemon = self.make_daemon(directory)
            proxy = mock.Mock()
            proxy.call_sync.side_effect = RuntimeError("overlapping layout")
            daemon._new_display_config_proxy = mock.Mock(return_value=proxy)
            daemon._apply_layout()
            self.assertTrue(daemon.failed)
            self.assertFalse(daemon.ready_file.exists())
            self.assertEqual(proxy.call_sync.call_count, 1)
