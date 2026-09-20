"""Pure display-mode selection and relative layout calculations."""

from __future__ import annotations

from collections.abc import Sequence

from .model import PlacedMonitor, ResolvedMonitor


def choose_mode(
    modes: Sequence[Sequence[object]],
    width: int,
    height: int,
    target_refresh: float,
    *,
    maximum_refresh_error: float = 1.0,
) -> Sequence[object]:
    candidates = [mode for mode in modes if mode[1] == width and mode[2] == height]
    if not candidates:
        raise RuntimeError(f"No {width}x{height} mode is available")
    selected = min(
        candidates,
        key=lambda mode: abs(float(mode[3]) - target_refresh),
    )
    if abs(float(selected[3]) - target_refresh) > maximum_refresh_error:
        available = ", ".join(f"{float(mode[3]):.3f}" for mode in candidates)
        raise RuntimeError(
            f"No refresh near {target_refresh:g} Hz is available for "
            f"{width}x{height}; available: {available} Hz"
        )
    return selected


def choose_scale(
    supported_scales: Sequence[float],
    requested_scale: float,
    *,
    maximum_error: float = 0.05,
) -> float:
    if not supported_scales:
        raise RuntimeError("The selected mode reports no supported scales")
    selected = min(supported_scales, key=lambda scale: abs(scale - requested_scale))
    if abs(selected - requested_scale) > maximum_error:
        rendered = ", ".join(f"{scale:.4g}" for scale in supported_scales)
        raise RuntimeError(
            f"Requested scale {requested_scale:.4g} is unavailable; supported: {rendered}"
        )
    return float(selected)


def logical_size(width: int, height: int, scale: float) -> tuple[int, int]:
    return round(width / scale), round(height / scale)


def _alignment_offset(container: int, child: int, alignment: str) -> int:
    if alignment == "start":
        return 0
    if alignment == "center":
        return round((container - child) / 2)
    if alignment == "end":
        return container - child
    raise RuntimeError(f"Unknown alignment: {alignment}")


def place_monitors(
    monitors: Sequence[ResolvedMonitor],
    *,
    origin: tuple[int, int] = (0, 0),
    normalize: bool = True,
) -> list[PlacedMonitor]:
    primary_monitors = [monitor for monitor in monitors if monitor.primary]
    if len(primary_monitors) != 1:
        raise RuntimeError("Exactly one primary monitor is required")

    primary = primary_monitors[0]
    primary_width, primary_height = logical_size(
        primary.width, primary.height, primary.scale
    )
    placed: dict[str, PlacedMonitor] = {
        primary.name: PlacedMonitor(primary, *origin, primary_width, primary_height)
    }

    pending = {monitor.name: monitor for monitor in monitors if not monitor.primary}
    while pending:
        progressed = False
        for name, monitor in tuple(pending.items()):
            reference = placed.get(monitor.relative_to or "")
            if reference is None:
                continue

            width, height = logical_size(monitor.width, monitor.height, monitor.scale)
            if monitor.position == "left":
                x = reference.x - width
                y = reference.y + _alignment_offset(
                    reference.logical_height, height, monitor.alignment
                )
            elif monitor.position == "right":
                x = reference.x + reference.logical_width
                y = reference.y + _alignment_offset(
                    reference.logical_height, height, monitor.alignment
                )
            elif monitor.position == "above":
                x = reference.x + _alignment_offset(
                    reference.logical_width, width, monitor.alignment
                )
                y = reference.y - height
            elif monitor.position == "below":
                x = reference.x + _alignment_offset(
                    reference.logical_width, width, monitor.alignment
                )
                y = reference.y + reference.logical_height
            else:
                raise RuntimeError(f"Unknown position: {monitor.position}")

            placed[name] = PlacedMonitor(monitor, x, y, width, height)
            del pending[name]
            progressed = True

        if not progressed:
            unresolved = ", ".join(sorted(pending))
            raise RuntimeError(f"Cyclic or unresolved monitor placement: {unresolved}")

    if not normalize:
        return [placed[monitor.name] for monitor in monitors]

    min_x = min(item.x for item in placed.values())
    min_y = min(item.y for item in placed.values())
    normalized = {
        name: PlacedMonitor(
            item.monitor,
            item.x - min_x,
            item.y - min_y,
            item.logical_width,
            item.logical_height,
        )
        for name, item in placed.items()
    }
    return [normalized[monitor.name] for monitor in monitors]
