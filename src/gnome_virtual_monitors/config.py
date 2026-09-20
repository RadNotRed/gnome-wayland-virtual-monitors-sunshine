"""Load and validate the daemon TOML configuration."""

from __future__ import annotations

import math
import tomllib
from pathlib import Path

from .model import DaemonConfig, PrimaryConfig, VirtualMonitorConfig

POSITIONS = {"left", "right", "above", "below"}
ALIGNMENTS = {"start", "center", "end"}


def _positive_number(value: object, label: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{label} must be a finite positive number")
    return float(value)


def _positive_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def load_config(path: str | Path) -> DaemonConfig:
    config_path = Path(path).expanduser()
    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    primary_data = data.get("primary", {})
    if not isinstance(primary_data, dict):
        raise ValueError("[primary] must be a table")
    primary = PrimaryConfig(
        name=str(primary_data.get("name", "primary")),
        connector=(
            str(primary_data["connector"]) if primary_data.get("connector") else None
        ),
        width=_positive_integer(primary_data.get("width"), "primary.width"),
        height=_positive_integer(primary_data.get("height"), "primary.height"),
        refresh=_positive_integer(primary_data.get("refresh", 60), "primary.refresh"),
        scale=_positive_number(primary_data.get("scale", 1.0), "primary.scale"),
    )

    raw_monitors = data.get("monitor", [])
    if not isinstance(raw_monitors, list) or not raw_monitors:
        raise ValueError("at least one [[monitor]] entry is required")

    monitors: list[VirtualMonitorConfig] = []
    names = {primary.name}
    resolutions: set[tuple[int, int]] = set()
    for index, raw in enumerate(raw_monitors):
        if not isinstance(raw, dict):
            raise ValueError(f"monitor entry {index} must be a table")
        name = str(raw.get("name", "")).strip()
        if not name:
            raise ValueError(f"monitor entry {index} requires a name")
        if name in names:
            raise ValueError(f"duplicate monitor name: {name}")
        names.add(name)

        position = str(raw.get("position", "right"))
        alignment = str(raw.get("alignment", "center"))
        if position not in POSITIONS:
            raise ValueError(f"{name}.position must be one of {sorted(POSITIONS)}")
        if alignment not in ALIGNMENTS:
            raise ValueError(f"{name}.alignment must be one of {sorted(ALIGNMENTS)}")

        width = _positive_integer(raw.get("width"), f"{name}.width")
        height = _positive_integer(raw.get("height"), f"{name}.height")
        resolution = (width, height)
        if resolution in resolutions:
            raise ValueError(
                "virtual monitors require unique width and height pairs; "
                f"{width}x{height} is duplicated"
            )
        resolutions.add(resolution)

        monitors.append(
            VirtualMonitorConfig(
                name=name,
                width=width,
                height=height,
                refresh=_positive_integer(raw.get("refresh", 60), f"{name}.refresh"),
                scale=_positive_number(raw.get("scale", 1.0), f"{name}.scale"),
                relative_to=str(raw.get("relative_to", primary.name)),
                position=position,
                alignment=alignment,
            )
        )

    known_names = {primary.name, *(monitor.name for monitor in monitors)}
    for monitor in monitors:
        if monitor.relative_to not in known_names:
            raise ValueError(
                f"{monitor.name}.relative_to references unknown monitor "
                f"{monitor.relative_to!r}"
            )

    parents = {monitor.name: monitor.relative_to for monitor in monitors}
    for monitor in monitors:
        seen: set[str] = set()
        path: list[str] = []
        current = monitor.name
        while current != primary.name:
            if current in seen:
                chain = " -> ".join((*path, current))
                raise ValueError(f"relative monitor placement cycle: {chain}")
            seen.add(current)
            path.append(current)
            current = parents[current]

    daemon_data = data.get("daemon", {})
    if not isinstance(daemon_data, dict):
        raise ValueError("[daemon] must be a table")
    layout_mode = daemon_data.get("layout_mode", 1)
    if not isinstance(layout_mode, int) or isinstance(layout_mode, bool):
        raise ValueError("daemon.layout_mode must be the literal integer 1")
    if layout_mode != 1:
        raise ValueError(
            "daemon.layout_mode must be 1 (logical); physical layout is not "
            "supported because it cannot provide per-monitor fractional scaling"
        )

    preserve = daemon_data.get("preserve_physical_monitors", True)
    if not isinstance(preserve, bool):
        raise ValueError("daemon.preserve_physical_monitors must be a boolean")

    restore = daemon_data.get("restore_saved_layout", False)
    if not isinstance(restore, bool):
        raise ValueError("daemon.restore_saved_layout must be a boolean")
    if restore and not preserve:
        raise ValueError(
            "restore_saved_layout requires preserve_physical_monitors = true"
        )

    return DaemonConfig(
        restore_saved_layout=restore,
        preserve_physical_monitors=preserve,
        primary=primary,
        monitors=tuple(monitors),
        layout_mode=layout_mode,
        layout_retries=_positive_integer(
            daemon_data.get("layout_retries", 20), "daemon.layout_retries"
        ),
        startup_timeout=_positive_integer(
            daemon_data.get("startup_timeout", 15), "daemon.startup_timeout"
        ),
    )
