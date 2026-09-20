from __future__ import annotations

from dataclasses import replace
import unittest

from gnome_virtual_monitors.display_state import (
    apply_layout_payload,
    compose_layout,
    physical_anchor,
    resolve_virtual_roles,
    snapshot_layout,
    validate_preserved_modes,
)
from gnome_virtual_monitors.model import (
    DaemonConfig,
    PrimaryConfig,
    VirtualMonitorConfig,
)


def monitor(connector, width=1920, height=1080, refresh=143.9814453125, virtual=False):
    spec = (
        connector,
        "fake-vendor",
        "Virtual remote monitor" if virtual else "fake-model",
        "fake",
    )
    mode = (
        f"{connector}-exact-mode",
        width,
        height,
        refresh,
        1.0,
        [1.0, 1.5, 2.0],
        {"is-current": True},
    )
    return (spec, [mode], {})


def logical(output, x=0, y=0, scale=1.0, transform=0, primary=True):
    return (x, y, scale, transform, primary, [output[0]], {})


def configuration(**kwargs):
    return DaemonConfig(
        PrimaryConfig("primary", None, 1920, 1080, 60, 1),
        (
            VirtualMonitorConfig(
                "client", 1280, 720, 60, 1, "primary", "below", "start"
            ),
        ),
        1,
        1,
        15,
        **kwargs,
    )


class DisplayStateTests(unittest.TestCase):
    def test_one_two_and_three_physical_monitors_are_preserved_exactly(self):
        for count in (1, 2, 3):
            with self.subTest(count=count):
                physical = [
                    monitor(f"physical-{i}", refresh=60.001 + i * 83.98)
                    for i in range(count)
                ]
                groups = [
                    logical(m, x=1920 * i, primary=i == 0)
                    for i, m in enumerate(physical)
                ]
                original = snapshot_layout(physical, groups)
                virtual = monitor("Meta-5", 1280, 720, 60, True)
                roles = resolve_virtual_roles(
                    configuration(), physical + [virtual], set()
                )
                result = compose_layout(
                    original,
                    physical_anchor(configuration(), original, physical),
                    roles,
                )
                self.assertEqual(result[:count], list(original))
                self.assertEqual(len(result), count + 1)
                self.assertEqual(sum(g.primary for g in result), 1)

    def test_portrait_scale_and_current_mode_drive_anchor_geometry(self):
        physical = monitor("physical-A", refresh=240.01971435546875)
        groups = snapshot_layout(
            [physical], [logical(physical, scale=1.5, transform=1)]
        )
        virtual = monitor("Meta-7", 1280, 720, 60, True)
        roles = resolve_virtual_roles(configuration(), [virtual], set())
        result = compose_layout(
            groups, physical_anchor(configuration(), groups, [physical]), roles
        )
        self.assertEqual(result[0], groups[0])
        self.assertEqual(result[1].y, 1280)
        self.assertEqual(result[0].monitors[0].refresh, 240.01971435546875)

    def test_mirrored_physical_group_keeps_all_connectors(self):
        first, second = monitor("physical-A"), monitor("physical-B")
        group = (*logical(first)[:5], [first[0], second[0]], {})
        layout = snapshot_layout([first, second], [group])
        payload = apply_layout_payload(layout)
        self.assertEqual([o[0] for o in payload[0][5]], ["physical-A", "physical-B"])
        self.assertEqual(payload[0][5][1][1], "physical-B-exact-mode")

    def test_mixed_scales_and_transforms(self):
        outputs = [monitor("physical-A"), monitor("physical-B")]
        layout = snapshot_layout(
            outputs,
            [
                logical(outputs[0]),
                logical(outputs[1], x=1920, scale=2, transform=3, primary=False),
            ],
        )
        validate_preserved_modes(layout, outputs)
        self.assertEqual([g.scale for g in layout], [1, 2])
        self.assertEqual([g.transform for g in layout], [0, 3])

    def test_additional_physical_and_preexisting_virtual_are_not_role_candidates(self):
        outputs = [
            monitor("physical-A", 1280, 720, 60),
            monitor("Meta-0", 1280, 720, 60, True),
            monitor("Meta-9", 1280, 720, 60, True),
        ]
        self.assertEqual(
            resolve_virtual_roles(configuration(), outputs, {"Meta-0"})[0].connector,
            "Meta-9",
        )

    def test_recreated_role_uses_new_connector(self):
        for name in ("Meta-0", "Meta-9"):
            role = resolve_virtual_roles(
                configuration(), [monitor(name, 1280, 720, 60, True)], set()
            )[0]
            self.assertEqual((role.name, role.connector), ("client", name))

    def test_ambiguous_virtual_role_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "could not be uniquely matched"):
            resolve_virtual_roles(
                configuration(),
                [monitor(name, 1280, 720, 60, True) for name in ("Meta-0", "Meta-1")],
                set(),
            )

    def test_missing_current_mode_is_rejected(self):
        output = monitor("physical-A")
        output[1][0][6].clear()
        with self.assertRaisesRegex(RuntimeError, "current mode"):
            snapshot_layout([output], [logical(output)])

    def test_disconnected_physical_or_changed_mode_is_rejected(self):
        output = monitor("physical-A")
        layout = snapshot_layout([output], [logical(output)])
        for outputs in ([], [monitor("physical-A", refresh=60)]):
            with self.assertRaisesRegex(RuntimeError, "no longer available"):
                validate_preserved_modes(layout, outputs)

    def test_left_placement_translates_all_groups_by_same_offset_only(self):
        outputs = [monitor("physical-A"), monitor("physical-B")]
        layout = snapshot_layout(
            outputs, [logical(outputs[0]), logical(outputs[1], x=1920, primary=False)]
        )
        config = configuration()
        config = replace(
            config, monitors=(replace(config.monitors[0], position="left"),)
        )
        virtuals = resolve_virtual_roles(
            config, [monitor("Meta-8", 1280, 720, 60, True)], set()
        )
        result = compose_layout(
            layout, physical_anchor(config, layout, outputs), virtuals
        )
        self.assertEqual([g.x for g in result], [1280, 3200, 0])
        self.assertEqual(result[1].x - result[0].x, 1920)

    def test_chained_virtual_roles_keep_relative_placement(self):
        config = configuration()
        second = replace(
            config.monitors[0],
            name="second",
            width=800,
            height=600,
            relative_to="client",
            position="right",
        )
        config = replace(config, monitors=(*config.monitors, second))
        physical = monitor("physical-A")
        baseline = snapshot_layout([physical], [logical(physical)])
        roles = resolve_virtual_roles(
            config,
            [
                monitor("Meta-7", 1280, 720, 60, True),
                monitor("Meta-8", 800, 600, 60, True),
            ],
            set(),
        )
        layout = compose_layout(
            baseline, physical_anchor(config, baseline, [physical]), roles
        )
        self.assertEqual(
            [(g.x, g.y) for g in layout], [(0, 0), (0, 1080), (1280, 1080)]
        )

    def test_preexisting_virtual_group_is_retained_but_not_reused(self):
        physical = monitor("physical-A")
        old = monitor("Meta-2", 1280, 720, 60, True)
        baseline = snapshot_layout(
            [physical, old], [logical(physical), logical(old, x=1920, primary=False)]
        )
        roles = resolve_virtual_roles(
            configuration(),
            [physical, old, monitor("Meta-3", 1280, 720, 60, True)],
            {"Meta-2"},
        )
        layout = compose_layout(
            baseline, physical_anchor(configuration(), baseline, [physical, old]), roles
        )
        self.assertEqual(layout[:2], list(baseline))
        self.assertEqual(layout[-1].monitors[0].connector, "Meta-3")
