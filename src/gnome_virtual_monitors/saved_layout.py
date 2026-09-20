"""Versioned, connector-independent virtual layout persistence.

Only geometry, physical connectors, and configured virtual role identities are
saved. Portal tokens, monitor serials and transient virtual connectors are not.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path

from .display_state import is_virtual, resolve_virtual_roles, snapshot_layout
from .model import DaemonConfig, LogicalMonitor, MonitorMode, ResolvedMonitor

STATE_VERSION = 1


def default_state_path() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    if not root.is_absolute():
        raise ValueError("XDG_STATE_HOME must be an absolute path")
    return root / "gnome-wayland-virtual-monitors-sunshine" / "layout.json"


def _role_definitions(config: DaemonConfig) -> dict:
    return {
        role.name: {"width": role.width, "height": role.height, "refresh": role.refresh}
        for role in config.monitors
    }


def capture_saved_layout(
    config: DaemonConfig, monitors: Sequence, logical: Sequence
) -> dict:
    roles = resolve_virtual_roles(config, monitors, set(), use_configured_scale=False)
    by_connector = {role.connector: role.name for role in roles}
    virtual = {m[0][0] for m in monitors if is_virtual(m)}
    groups = []
    for group in snapshot_layout(monitors, logical):
        outputs = []
        for output in group.monitors:
            if output.connector in virtual:
                role = by_connector.get(output.connector)
                if role is None:
                    raise RuntimeError(
                        "Cannot save layout containing an unconfigured virtual output"
                    )
                kind, identity, mode_id = "virtual", role, None
            else:
                kind, identity, mode_id = "physical", output.connector, output.mode_id
            outputs.append(
                {
                    "kind": kind,
                    "identity": identity,
                    "mode_id": mode_id,
                    "width": output.width,
                    "height": output.height,
                    "refresh": output.refresh,
                }
            )
        groups.append(
            {
                "x": group.x,
                "y": group.y,
                "scale": group.scale,
                "transform": group.transform,
                "primary": group.primary,
                "outputs": outputs,
            }
        )
    state = {
        "version": STATE_VERSION,
        "roles": _role_definitions(config),
        "logical_monitors": groups,
    }
    validate_saved_layout(state)
    return state


def _integer(value: object, minimum: int = 0, maximum: int = 2**31 - 1) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _positive(value: object) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


def _name(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_saved_layout(state: object) -> None:
    """Reject malformed state before touching Mutter or replacing a good save."""

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(f"Invalid saved layout: {message}")

    require(isinstance(state, dict), "expected an object")
    require(
        type(state.get("version")) is int and state["version"] == STATE_VERSION,
        "unsupported version",
    )
    roles = state.get("roles")
    require(isinstance(roles, dict) and bool(roles), "missing virtual role definitions")
    for name, role in roles.items():
        require(_name(name) and isinstance(role, dict), "invalid role definition")
        require(
            _integer(role.get("width"), 1)
            and _integer(role.get("height"), 1)
            and _positive(role.get("refresh")),
            f"invalid mode for role {name!r}",
        )
    groups = state.get("logical_monitors")
    require(isinstance(groups, list) and bool(groups), "missing logical monitors")
    identities: set[tuple[str, str]] = set()
    primary_count = 0
    for group in groups:
        require(isinstance(group, dict), "invalid logical monitor")
        require(
            _integer(group.get("x")) and _integer(group.get("y")), "invalid position"
        )
        require(_positive(group.get("scale")), "invalid scale")
        require(_integer(group.get("transform"), 0, 7), "invalid transform")
        require(type(group.get("primary")) is bool, "invalid primary flag")
        primary_count += group["primary"]
        outputs = group.get("outputs")
        require(isinstance(outputs, list) and bool(outputs), "empty logical group")
        for output in outputs:
            require(isinstance(output, dict), "invalid output")
            kind, identity = output.get("kind"), output.get("identity")
            require(
                kind in ("physical", "virtual") and _name(identity), "invalid identity"
            )
            require((kind, identity) not in identities, "duplicate output identity")
            identities.add((kind, identity))
            require(
                _integer(output.get("width"), 1)
                and _integer(output.get("height"), 1)
                and _positive(output.get("refresh")),
                "invalid output mode",
            )
            if kind == "physical":
                require(_name(output.get("mode_id")), "missing physical mode ID")
            else:
                require(output.get("mode_id") is None, "virtual mode IDs are transient")
    require(primary_count == 1, "exactly one primary logical monitor is required")
    require(
        {name for kind, name in identities if kind == "virtual"} == set(roles),
        "virtual roles must each appear in exactly one active group",
    )


def write_saved_layout(path: Path, state: dict) -> None:
    validate_saved_layout(state)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".layout-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_saved_layout(path: Path) -> dict | None:
    try:
        with path.open(encoding="utf-8") as stream:
            state = json.load(stream)
    except FileNotFoundError:
        return None
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid saved layout at {path}: {error}") from error
    validate_saved_layout(state)
    return state


def _resolve_saved_mode(saved: dict, monitor: Sequence, scale: float) -> MonitorMode:
    identity = saved["identity"]
    matching = [
        mode
        for mode in monitor[1]
        if mode[1] == saved["width"]
        and mode[2] == saved["height"]
        and abs(mode[3] - saved["refresh"]) < 0.001
        and (saved["kind"] == "virtual" or mode[0] == saved["mode_id"])
    ]
    if len(matching) != 1:
        raise RuntimeError(f"Saved mode for {identity!r} is unavailable or ambiguous")
    mode = matching[0]
    if not any(abs(supported - scale) < 1e-6 for supported in mode[5]):
        raise RuntimeError(f"Saved scale for {identity!r} is unavailable")
    return MonitorMode(monitor[0][0], *mode[:4])


def validate_saved_setup(
    state: dict,
    config: DaemonConfig,
    monitors: Sequence,
    logical: Sequence,
) -> None:
    """Check stable identities before creating any temporary virtual outputs."""
    validate_saved_layout(state)
    if state["roles"] != _role_definitions(config):
        raise RuntimeError(
            "Saved virtual role definitions differ from configuration; save the layout again"
        )
    available = {m[0][0]: m for m in monitors if not is_virtual(m)}
    saved_physical = {
        output["identity"]
        for group in state["logical_monitors"]
        for output in group["outputs"]
        if output["kind"] == "physical"
    }
    for connector in saved_physical:
        if connector not in available:
            raise RuntimeError(
                f"Saved layout references physical connector {connector}, "
                "but it is not currently available."
            )
    for group in state["logical_monitors"]:
        for output in group["outputs"]:
            if output["kind"] == "physical":
                _resolve_saved_mode(
                    output, available[output["identity"]], group["scale"]
                )
    active_physical = {
        spec[0] for group in logical for spec in group[5] if spec[0] in available
    }
    if active_physical - saved_physical:
        raise RuntimeError(
            "Saved layout omits active connectors "
            f"{sorted(active_physical - saved_physical)}; save the layout again"
        )


def restore_layout(
    state: dict,
    config: DaemonConfig,
    monitors: Sequence,
    logical: Sequence,
    roles: Sequence[ResolvedMonitor],
) -> list[LogicalMonitor]:
    validate_saved_setup(state, config, monitors, logical)
    available = {m[0][0]: m for m in monitors}
    role_connectors = {role.name: role.connector for role in roles}
    if set(role_connectors) != set(state["roles"]):
        raise RuntimeError("Saved layout references a missing virtual role")
    result = []
    used: set[str] = set()
    for group in state["logical_monitors"]:
        outputs = []
        for saved in group["outputs"]:
            identity = saved["identity"]
            connector = (
                identity if saved["kind"] == "physical" else role_connectors[identity]
            )
            monitor = available.get(connector)
            if monitor is None or is_virtual(monitor) != (saved["kind"] == "virtual"):
                raise RuntimeError(
                    f"Saved layout references {saved['kind']} connector {connector}, "
                    "but it is not currently available."
                )
            if connector in used:
                raise RuntimeError(
                    f"Saved layout maps multiple identities to {connector}"
                )
            used.add(connector)
            outputs.append(_resolve_saved_mode(saved, monitor, group["scale"]))
        result.append(
            LogicalMonitor(
                group["x"],
                group["y"],
                group["scale"],
                group["transform"],
                group["primary"],
                tuple(outputs),
            )
        )
    active = {spec[0] for group in logical for spec in group[5]}
    if active - used:
        raise RuntimeError(
            f"Saved layout omits active connectors {sorted(active - used)}; save the layout again"
        )
    return result
