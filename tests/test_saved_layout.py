from __future__ import annotations

import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from gnome_virtual_monitors.display_state import resolve_virtual_roles
from gnome_virtual_monitors.saved_layout import (
    capture_saved_layout,
    default_state_path,
    read_saved_layout,
    restore_layout,
    validate_saved_layout,
    write_saved_layout,
)
from test_display_state import configuration, logical, monitor


class SavedLayoutTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.physical = monitor("physical-A")
        self.virtual = monitor("Meta-0", 1280, 720, 60, True)
        self.monitors = [self.physical, self.virtual]
        self.logical = [
            logical(self.physical, primary=False),
            logical(self.virtual, x=1920, y=120, scale=1.5, transform=3),
        ]
        self.state = capture_saved_layout(self.config, self.monitors, self.logical)

    def restore(
        self, state=None, monitors=None, logical_groups=None, roles=None, config=None
    ):
        monitors = monitors if monitors is not None else self.monitors
        config = config or self.config
        roles = (
            roles
            if roles is not None
            else resolve_virtual_roles(config, monitors, set())
        )
        return restore_layout(
            state or self.state,
            config,
            monitors,
            self.logical if logical_groups is None else logical_groups,
            roles,
        )

    def test_save_and_restore_recreated_virtual_with_all_geometry(self):
        recreated = monitor("Meta-9", 1280, 720, 60, True)
        monitors = [self.physical, recreated]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state" / "layout.json"
            write_saved_layout(path, self.state)
            state = read_saved_layout(path)
            result = self.restore(
                state,
                monitors,
                [logical(self.physical), logical(recreated, primary=False)],
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertNotIn("Meta-", path.read_text())
            self.assertNotIn("fake-vendor", path.read_text())
        self.assertEqual(result[0].monitors[0].connector, "physical-A")
        self.assertEqual(result[0].monitors[0].refresh, 143.9814453125)
        self.assertFalse(result[0].primary)
        group = result[1]
        self.assertEqual(
            (group.x, group.y, group.scale, group.transform, group.primary),
            (1920, 120, 1.5, 3, True),
        )
        self.assertEqual(group.monitors[0].connector, "Meta-9")
        self.assertEqual(group.monitors[0].mode_id, "Meta-9-exact-mode")

    def test_missing_physical_connector(self):
        with self.assertRaisesRegex(
            RuntimeError, "physical connector physical-A.*not currently available"
        ):
            self.restore(monitors=[self.virtual])

    def test_physical_identity_cannot_be_replaced_by_same_resolution(self):
        with self.assertRaisesRegex(RuntimeError, "physical connector physical-A"):
            self.restore(monitors=[monitor("physical-B"), self.virtual])

    def test_missing_virtual_role(self):
        with self.assertRaisesRegex(RuntimeError, "missing virtual role"):
            self.restore(roles=[])

    def test_ambiguous_virtual_match(self):
        with self.assertRaisesRegex(RuntimeError, "could not be uniquely matched"):
            self.restore(
                monitors=self.monitors + [monitor("Meta-3", 1280, 720, 60, True)]
            )

    def test_changed_role_config_is_rejected(self):
        changed = replace(
            self.config, monitors=(replace(self.config.monitors[0], refresh=59),)
        )
        with self.assertRaisesRegex(RuntimeError, "definitions differ"):
            self.restore(config=changed)

    def test_missing_state_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(read_saved_layout(Path(directory) / "missing.json"))

    def test_malformed_state_file(self):
        for content in (b"{", b"\xff", b"[]", b'{"version": 99}'):
            with (
                self.subTest(content=content),
                tempfile.TemporaryDirectory() as directory,
            ):
                path = Path(directory) / "layout.json"
                path.write_bytes(content)
                with self.assertRaisesRegex(ValueError, "Invalid saved layout"):
                    read_saved_layout(path)

    def test_invalid_geometry_and_mode_fields(self):
        cases = [
            ("scale", float("nan")),
            ("scale", -1),
            ("scale", True),
            ("transform", 8),
            ("transform", True),
            ("x", -1),
            ("x", 1.5),
            ("primary", "true"),
            ("outputs", []),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                state = copy.deepcopy(self.state)
                state["logical_monitors"][0][field] = value
                with self.assertRaisesRegex(ValueError, "Invalid saved layout"):
                    validate_saved_layout(state)

    def test_duplicate_identity_or_missing_primary_is_rejected(self):
        state = copy.deepcopy(self.state)
        state["logical_monitors"].append(state["logical_monitors"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_saved_layout(state)
        state = copy.deepcopy(self.state)
        state["logical_monitors"][1]["primary"] = False
        with self.assertRaisesRegex(ValueError, "exactly one primary"):
            validate_saved_layout(state)

    def test_changed_physical_mode_is_not_rounded_to_another_refresh(self):
        with self.assertRaisesRegex(RuntimeError, "Saved mode"):
            self.restore(monitors=[monitor("physical-A", refresh=144), self.virtual])

    def test_unavailable_scale_is_rejected(self):
        state = copy.deepcopy(self.state)
        state["logical_monitors"][1]["scale"] = 1.75
        with self.assertRaisesRegex(RuntimeError, "Saved scale"):
            self.restore(state)

    def test_new_active_physical_is_not_silently_disabled(self):
        extra = monitor("physical-B")
        with self.assertRaisesRegex(RuntimeError, "omits active connectors"):
            self.restore(
                monitors=self.monitors + [extra],
                logical_groups=self.logical + [logical(extra, primary=False)],
            )

    def test_save_rejects_foreign_virtual_output(self):
        extra = monitor("Meta-3", 800, 600, 60, True)
        with self.assertRaisesRegex(RuntimeError, "unconfigured virtual"):
            capture_saved_layout(
                self.config,
                self.monitors + [extra],
                self.logical + [logical(extra, primary=False)],
            )

    def test_inactive_role_cannot_be_saved(self):
        with self.assertRaisesRegex(ValueError, "each appear"):
            capture_saved_layout(self.config, self.monitors, [logical(self.physical)])

    def test_failed_write_preserves_existing_state_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "layout.json"
            write_saved_layout(path, self.state)
            original = path.read_bytes()
            with mock.patch("os.replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    write_saved_layout(path, self.state)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_state_path_honors_xdg(self):
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": "/tmp/fake-state"}):
            self.assertEqual(
                default_state_path(),
                Path(
                    "/tmp/fake-state/gnome-wayland-virtual-monitors-sunshine/layout.json"
                ),
            )
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": "relative"}):
            with self.assertRaisesRegex(ValueError, "absolute"):
                default_state_path()

    def test_mirrored_group_survives_save_restore(self):
        other = monitor("physical-B")
        groups = [
            (*self.logical[0][:5], [self.physical[0], other[0]], {}),
            self.logical[1],
        ]
        monitors = self.monitors + [other]
        state = capture_saved_layout(self.config, monitors, groups)
        result = self.restore(state, monitors, groups)
        self.assertEqual(
            [m.connector for m in result[0].monitors], ["physical-A", "physical-B"]
        )
