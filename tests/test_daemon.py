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
        logical_monitors = [(0, 0, 1.0, 0, True, [specification], {})]
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

        daemon = VirtualMonitorDaemon(
            configuration(preserve_physical_monitors=preserve)
        )
        daemon.ready_file = Path(directory) / "ready"
        physical = monitor("physical-A", refresh=60)
        second = monitor("physical-B", refresh=240.01971435546875)
        virtual = monitor("Meta-8", 1280, 720, 60, True)
        before = (
            1,
            [physical, second],
            [logical(physical), logical(second, x=1920, transform=1, primary=False)],
            {"layout-mode": 1},
        )
        after = (
            2,
            [physical, second, virtual],
            before[2] + [logical(virtual, primary=False)],
            before[3],
        )
        daemon._get_current_state = mock.Mock(return_value=before)
        daemon.preexisting_virtual_connectors = daemon._preflight_display()
        daemon._get_current_state.return_value = after
        return daemon

    def test_preserved_and_legacy_apply_payloads_and_readiness(self):
        for preserve in (True, False):
            with (
                self.subTest(preserve=preserve),
                tempfile.TemporaryDirectory() as directory,
            ):
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

    def test_saved_layout_is_applied_before_ready(self):
        from gnome_virtual_monitors.saved_layout import capture_saved_layout
        from test_display_state import logical

        with tempfile.TemporaryDirectory() as directory:
            daemon = self.make_daemon(directory)
            _serial, monitors, groups, _props = daemon._get_current_state()
            groups = [(*group[:4], False, *group[5:]) for group in groups[:-1]]
            groups.append(logical(monitors[-1], x=3000, y=100, scale=1.5, transform=3))
            daemon.saved_layout = capture_saved_layout(daemon.config, monitors, groups)
            proxy = mock.Mock()
            payloads = []

            def apply(_method, variant, *_args):
                self.assertFalse(daemon.ready_file.exists())
                payloads.append(variant.unpack())

            proxy.call_sync.side_effect = apply
            daemon._new_display_config_proxy = mock.Mock(return_value=proxy)
            daemon._apply_layout()
            self.assertTrue(daemon.ready_file.exists())
            self.assertEqual(payloads[-1][2][-1][:5], (3000, 100, 1.5, 3, True))

    def test_invalid_saved_restore_never_calls_apply_or_marks_ready(self):
        from gnome_virtual_monitors.saved_layout import capture_saved_layout

        with tempfile.TemporaryDirectory() as directory:
            daemon = self.make_daemon(directory)
            _serial, monitors, groups, _props = daemon._get_current_state()
            daemon.saved_layout = capture_saved_layout(daemon.config, monitors, groups)
            daemon.saved_layout["logical_monitors"][0]["outputs"][0][
                "identity"
            ] = "missing"
            proxy = mock.Mock()
            daemon._new_display_config_proxy = mock.Mock(return_value=proxy)
            daemon._apply_layout()
            self.assertTrue(daemon.failed)
            self.assertFalse(daemon.ready_file.exists())
            proxy.call_sync.assert_not_called()

    def test_restore_without_state_uses_normal_placement(self):
        from dataclasses import replace

        with tempfile.TemporaryDirectory() as directory:
            daemon = self.make_daemon(directory)
            daemon.config = replace(daemon.config, restore_saved_layout=True)
            with mock.patch(
                "gnome_virtual_monitors.daemon.read_saved_layout", return_value=None
            ):
                daemon._preflight_display()
            self.assertIsNone(daemon.saved_layout)
            self.assertIsNotNone(daemon.anchor)

    def test_invalid_saved_identities_fail_preflight_before_creation(self):
        from dataclasses import replace
        from gnome_virtual_monitors.saved_layout import capture_saved_layout

        with tempfile.TemporaryDirectory() as directory:
            daemon = self.make_daemon(directory)
            daemon.config = replace(daemon.config, restore_saved_layout=True)
            _serial, monitors, groups, _props = daemon._get_current_state()
            saved = capture_saved_layout(daemon.config, monitors, groups)
            saved["logical_monitors"][0]["outputs"][0]["identity"] = "missing"
            with mock.patch(
                "gnome_virtual_monitors.daemon.read_saved_layout", return_value=saved
            ):
                with self.assertRaisesRegex(RuntimeError, "physical connector missing"):
                    daemon._preflight_display()

    def test_new_active_connector_during_startup_is_not_disabled(self):
        from test_display_state import logical, monitor

        with tempfile.TemporaryDirectory() as directory:
            daemon = self.make_daemon(directory)
            serial, monitors, groups, props = daemon._get_current_state()
            new = monitor("new-physical")
            daemon._get_current_state.return_value = (
                serial,
                [*monitors, new],
                [*groups, logical(new, primary=False)],
                props,
            )
            proxy = mock.Mock()
            daemon._new_display_config_proxy = mock.Mock(return_value=proxy)
            daemon._apply_layout()
            self.assertTrue(daemon.failed)
            self.assertFalse(daemon.ready_file.exists())
            proxy.call_sync.assert_not_called()

    def test_save_captures_active_state_without_changing_readiness(self):
        from pathlib import Path
        from gnome_virtual_monitors.saved_layout import read_saved_layout

        with tempfile.TemporaryDirectory() as directory:
            daemon = self.make_daemon(directory)
            daemon.ready_file.write_text("ready\n")
            path = Path(directory) / "layout.json"
            with mock.patch(
                "gnome_virtual_monitors.daemon.default_state_path", return_value=path
            ):
                self.assertEqual(daemon.save_layout(), path)
            self.assertEqual(set(read_saved_layout(path)["roles"]), {"client"})
            self.assertEqual(daemon.ready_file.read_text(), "ready\n")

    def test_failed_save_does_not_replace_previous_state(self):
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            daemon = self.make_daemon(directory)
            daemon._get_current_state.return_value = (1, [], [], {"layout-mode": 1})
            path = Path(directory) / "layout.json"
            path.write_text("previous state")
            with mock.patch(
                "gnome_virtual_monitors.daemon.default_state_path", return_value=path
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "could not be uniquely matched"
                ):
                    daemon.save_layout()
            self.assertEqual(path.read_text(), "previous state")

    def test_unavailable_saved_physical_mode_fails_preflight(self):
        from dataclasses import replace
        from gnome_virtual_monitors.saved_layout import capture_saved_layout

        with tempfile.TemporaryDirectory() as directory:
            daemon = self.make_daemon(directory)
            daemon.config = replace(daemon.config, restore_saved_layout=True)
            _serial, monitors, groups, _props = daemon._get_current_state()
            saved = capture_saved_layout(daemon.config, monitors, groups)
            saved["logical_monitors"][0]["outputs"][0]["mode_id"] = "unavailable"
            with mock.patch(
                "gnome_virtual_monitors.daemon.read_saved_layout", return_value=saved
            ):
                with self.assertRaisesRegex(RuntimeError, "Saved mode"):
                    daemon._preflight_display()
