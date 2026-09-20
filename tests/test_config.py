from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gnome_virtual_monitors.config import load_config


VALID_CONFIG = b"""
[daemon]
layout_mode = 1

[primary]
name = "aoc"
width = 1920
height = 1080
refresh = 120

[[monitor]]
name = "windows"
width = 1366
height = 768
relative_to = "aoc"
position = "left"

[[monitor]]
name = "android"
width = 2340
height = 1080
refresh = 120
scale = 1.75
relative_to = "aoc"
position = "below"
"""


class ConfigTests(unittest.TestCase):
    def load(self, content: bytes = VALID_CONFIG):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_bytes(content)
            return load_config(path)

    def test_loads_multi_monitor_configuration(self):
        config = self.load()
        self.assertEqual(
            (config.primary.width, config.primary.height),
            (1920, 1080),
        )
        self.assertEqual(config.primary.refresh, 120)
        self.assertEqual([monitor.name for monitor in config.monitors], ["windows", "android"])
        self.assertEqual(config.monitors[1].refresh, 120)
        self.assertEqual(config.monitors[1].scale, 1.75)

    def test_rejects_unknown_relative_monitor(self):
        with self.assertRaisesRegex(ValueError, "unknown monitor"):
            self.load(VALID_CONFIG.replace(b'relative_to = "aoc"', b'relative_to = "missing"', 1))

    def test_rejects_duplicate_names(self):
        with self.assertRaisesRegex(ValueError, "duplicate monitor"):
            self.load(VALID_CONFIG.replace(b'name = "android"', b'name = "windows"'))

    def test_rejects_physical_layout_mode(self):
        with self.assertRaisesRegex(ValueError, "physical layout"):
            self.load(VALID_CONFIG.replace(b"layout_mode = 1", b"layout_mode = 2"))

    def test_requires_layout_mode_to_be_the_literal_integer_one(self):
        for invalid in (b"1.9", b"true", b'"1"'):
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(ValueError, "literal integer 1"):
                    self.load(
                        VALID_CONFIG.replace(
                            b"layout_mode = 1",
                            b"layout_mode = " + invalid,
                        )
                    )

    def test_rejects_fractional_values_for_integer_fields(self):
        replacements = (
            (b"width = 2340", b"width = 0.5"),
            (b"height = 1080", b"height = 1.9"),
            (b"refresh = 120", b"refresh = 0.9"),
        )
        for original, invalid in replacements:
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    self.load(VALID_CONFIG.replace(original, invalid, 1))

    def test_rejects_non_finite_scale(self):
        with self.assertRaisesRegex(ValueError, "finite positive number"):
            self.load(VALID_CONFIG.replace(b"scale = 1.75", b"scale = inf"))

    def test_rejects_non_table_sections(self):
        invalid_configs = (
            (
                b'primary = "bad"\n'
                + VALID_CONFIG.replace(
                    b'[primary]\nname = "aoc"\nwidth = 1920\nheight = 1080\nrefresh = 120',
                    b'',
                ),
                r"\[primary\] must be a table",
            ),
            (
                VALID_CONFIG.replace(
                    b"[daemon]\nlayout_mode = 1",
                    b'daemon = "bad"',
                ),
                r"\[daemon\] must be a table",
            ),
        )
        for content, message in invalid_configs:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.load(content)

    def test_rejects_duplicate_virtual_resolutions(self):
        duplicate_resolution = VALID_CONFIG.replace(
            b"width = 1366\nheight = 768",
            b"width = 2340\nheight = 1080",
        )
        with self.assertRaisesRegex(ValueError, "unique width and height"):
            self.load(duplicate_resolution)

    def test_rejects_relative_placement_cycles(self):
        cyclic = VALID_CONFIG.replace(
            b'relative_to = "aoc"',
            b'relative_to = "android"',
            1,
        ).replace(
            b'relative_to = "aoc"',
            b'relative_to = "windows"',
            1,
        )
        with self.assertRaisesRegex(ValueError, "placement cycle"):
            self.load(cyclic)

    def test_preservation_defaults_to_true_and_accepts_false(self):
        self.assertTrue(self.load().preserve_physical_monitors)
        self.assertFalse(self.load(VALID_CONFIG.replace(
            b"layout_mode = 1", b"layout_mode = 1\npreserve_physical_monitors = false"
        )).preserve_physical_monitors)

    def test_preservation_requires_a_boolean(self):
        for value in (b'"true"', b"1"):
            with self.assertRaisesRegex(ValueError, "must be a boolean"):
                self.load(VALID_CONFIG.replace(
                    b"layout_mode = 1", b"layout_mode = 1\npreserve_physical_monitors = " + value
                ))

    def test_restore_defaults_to_false_and_accepts_true(self):
        self.assertFalse(self.load().restore_saved_layout)
        self.assertTrue(self.load(VALID_CONFIG.replace(
            b"layout_mode = 1", b"layout_mode = 1\nrestore_saved_layout = true"
        )).restore_saved_layout)

    def test_restore_requires_preservation_and_boolean(self):
        for settings in (b'restore_saved_layout = "true"',
                         b'restore_saved_layout = true\npreserve_physical_monitors = false'):
            with self.assertRaisesRegex(ValueError, "restore_saved_layout"):
                self.load(VALID_CONFIG.replace(b"layout_mode = 1", b"layout_mode = 1\n" + settings))
