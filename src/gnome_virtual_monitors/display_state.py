"""Pure transformations of Mutter state into complete logical layouts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from .layout import choose_mode, choose_scale, place_monitors
from .model import DaemonConfig, LogicalMonitor, MonitorMode, ResolvedMonitor


def is_virtual(monitor: Sequence[object]) -> bool:
    spec = monitor[0]
    return str(spec[0]).startswith("Meta-") or spec[2] == "Virtual remote monitor"


def snapshot_layout(monitors: Sequence, logical_monitors: Sequence) -> tuple[LogicalMonitor, ...]:
    """Capture active groups and exact current modes, including mirrored outputs."""
    by_connector = {monitor[0][0]: monitor for monitor in monitors}
    result = []
    for x, y, scale, transform, primary, specs, _props in logical_monitors:
        outputs = []
        for spec in specs:
            monitor = by_connector.get(spec[0])
            current = [] if monitor is None else [
                mode for mode in monitor[1] if mode[6].get("is-current", False)
            ]
            if len(current) != 1:
                raise RuntimeError(f"Cannot uniquely resolve current mode for {spec[0]}")
            mode = current[0]
            outputs.append(MonitorMode(spec[0], *mode[:4]))
        if not outputs:
            raise RuntimeError("An active logical monitor has no outputs")
        result.append(LogicalMonitor(x, y, scale, transform, primary, tuple(outputs)))
    return tuple(result)


def validate_preserved_modes(layout: Sequence[LogicalMonitor], monitors: Sequence) -> None:
    """Never fall back to a different physical mode after hotplug or recreation."""
    available = {monitor[0][0]: monitor for monitor in monitors}
    for logical in layout:
        for output in logical.monitors:
            monitor = available.get(output.connector)
            if monitor is None:
                raise RuntimeError(f"Preserved connector {output.connector} is no longer available")
            modes = [mode for mode in monitor[1] if tuple(mode[:4]) == (
                output.mode_id, output.width, output.height, output.refresh
            )]
            if len(modes) != 1 or logical.scale not in modes[0][5]:
                raise RuntimeError(f"Preserved mode/scale for {output.connector} is no longer available")


def resolve_virtual_roles(
    config: DaemonConfig, monitors: Sequence, excluded: set[str],
    *, use_configured_scale: bool = True,
) -> list[ResolvedMonitor]:
    candidates = [m for m in monitors if is_virtual(m) and m[0][0] not in excluded]
    resolved = []
    used: set[str] = set()
    for profile in config.monitors:
        matches = [m for m in candidates if any(
            mode[1] == profile.width and mode[2] == profile.height for mode in m[1]
        )]
        if len(matches) != 1 or matches[0][0][0] in used:
            raise RuntimeError(
                f"Virtual monitor role {profile.name!r} could not be uniquely matched "
                f"to a newly created output ({profile.width}x{profile.height}; "
                f"candidates: {[m[0][0] for m in matches]})"
            )
        candidate = matches[0]
        used.add(candidate[0][0])
        mode = choose_mode(candidate[1], profile.width, profile.height, profile.refresh)
        resolved.append(ResolvedMonitor(
            profile.name, candidate[0][0], *mode[:4],
            choose_scale(mode[5], profile.scale) if use_configured_scale else float(mode[4]), False,
            profile.relative_to, profile.position, profile.alignment,
        ))
    return resolved


def physical_anchor(
    config: DaemonConfig, layout: Sequence[LogicalMonitor], monitors: Sequence
) -> tuple[LogicalMonitor, ResolvedMonitor]:
    physical = {m[0][0] for m in monitors if not is_virtual(m)}
    matches = [(group, output) for group in layout for output in group.monitors
               if output.connector in physical and (
                   output.connector == config.primary.connector
                   if config.primary.connector else group.primary
               )]
    if not matches:
        raise RuntimeError("No active physical placement anchor; set primary.connector")
    group, output = matches[0]
    width, height = output.width, output.height
    if group.transform in (1, 3, 5, 7):
        width, height = height, width
    return group, ResolvedMonitor(
        config.primary.name, output.connector, output.mode_id, width, height,
        output.refresh, group.scale, True,
    )


def compose_layout(
    preserved: Sequence[LogicalMonitor],
    anchor: tuple[LogicalMonitor, ResolvedMonitor],
    virtuals: Sequence[ResolvedMonitor],
) -> list[LogicalMonitor]:
    group, reference = anchor
    placed = place_monitors([reference, *virtuals], origin=(group.x, group.y), normalize=False)
    layout = list(preserved)
    for item in placed[1:]:
        monitor = item.monitor
        layout.append(LogicalMonitor(item.x, item.y, monitor.scale, 0, False, (
            MonitorMode(monitor.connector, monitor.mode_id, monitor.width,
                        monitor.height, monitor.refresh),
        )))
    # Mutter requires a non-negative desktop origin. Translate the entire
    # arrangement only when necessary; never flatten individual physical groups.
    min_x = min(0, *(group.x for group in layout))
    min_y = min(0, *(group.y for group in layout))
    return [replace(group, x=group.x - min_x, y=group.y - min_y) for group in layout]


def apply_layout_payload(layout: Sequence[LogicalMonitor]) -> list[tuple]:
    return [(group.x, group.y, group.scale, group.transform, group.primary,
             [(output.connector, output.mode_id, {}) for output in group.monitors])
            for group in layout]
