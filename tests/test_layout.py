from __future__ import annotations

import unittest

from gnome_virtual_monitors.layout import choose_mode, choose_scale, logical_size, place_monitors
from gnome_virtual_monitors.model import ResolvedMonitor


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.aoc = ResolvedMonitor(
            "aoc", "HDMI-1", "main", 1920, 1080, 120.003, 1.0, True
        )
        self.windows = ResolvedMonitor(
            "windows",
            "Meta-0",
            "windows-mode",
            1366,
            768,
            60.0,
            1.0,
            False,
            "aoc",
            "left",
            "center",
        )
        self.android = ResolvedMonitor(
            "android",
            "Meta-1",
            "android-mode",
            2340,
            1080,
            120.0,
            180 / 103,
            False,
            "aoc",
            "below",
            "center",
        )

    def test_places_windows_left_and_android_centered_below(self):
        placed = {
            item.monitor.name: item
            for item in place_monitors([self.aoc, self.windows, self.android])
        }
        self.assertEqual((placed["windows"].x, placed["windows"].y), (0, 156))
        self.assertEqual((placed["aoc"].x, placed["aoc"].y), (1366, 0))
        self.assertEqual((placed["android"].x, placed["android"].y), (1656, 1080))
        self.assertEqual(
            (placed["android"].logical_width, placed["android"].logical_height),
            (1339, 618),
        )

    def test_selects_mutters_nearest_fractional_scale(self):
        scale = choose_scale([1.0, 1.5, 180 / 103, 2.0], 1.75)
        self.assertAlmostEqual(scale, 180 / 103)
        self.assertEqual(logical_size(2340, 1080, scale), (1339, 618))

    def test_rejects_unavailable_fractional_scale(self):
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            choose_scale([1.0, 2.0], 1.75)

    def test_selects_closest_refresh_for_resolution(self):
        modes = [
            ("mode-60", 1920, 1080, 60.0),
            ("mode-120", 1920, 1080, 120.003),
            ("small", 1280, 720, 120.0),
        ]
        self.assertEqual(choose_mode(modes, 1920, 1080, 120)[0], "mode-120")

    def test_rejects_a_large_refresh_fallback(self):
        modes = [("mode-60", 1920, 1080, 60.0)]
        with self.assertRaisesRegex(RuntimeError, "No refresh near 120"):
            choose_mode(modes, 1920, 1080, 120)

    def test_rejects_cyclic_placement(self):
        first = ResolvedMonitor(
            "first", "Meta-0", "one", 800, 600, 60, 1, False, "second", "left"
        )
        second = ResolvedMonitor(
            "second", "Meta-1", "two", 800, 600, 60, 1, False, "first", "right"
        )
        with self.assertRaisesRegex(RuntimeError, "Cyclic"):
            place_monitors([self.aoc, first, second])
