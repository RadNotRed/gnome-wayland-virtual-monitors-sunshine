"""Create Mutter virtual outputs and keep their PipeWire streams negotiated."""

from __future__ import annotations

import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gio, GLib, Gst

from .layout import choose_mode, choose_scale, place_monitors
from .model import DaemonConfig, ResolvedMonitor, VirtualMonitorConfig


@dataclass
class VirtualOutput:
    config: VirtualMonitorConfig
    stream: Gio.DBusProxy | None = None
    pipeline: Gst.Pipeline | None = None
    node_id: int | None = None
    ready: bool = False


class VirtualMonitorDaemon:
    def __init__(self, config: DaemonConfig):
        self.config = config
        self.loop = GLib.MainLoop()
        self.screen_cast: Gio.DBusProxy | None = None
        self.session: Gio.DBusProxy | None = None
        self.outputs = [VirtualOutput(monitor) for monitor in config.monitors]
        self.failed = False
        self.layout_attempts = 0
        self.preexisting_virtual_connectors: set[str] = set()
        runtime_dir = Path(
            os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        )
        self.ready_file = runtime_dir / "gnome-virtual-monitor.ready"

    def start(self) -> None:
        self.ready_file.unlink(missing_ok=True)
        Gst.init(None)
        self.preexisting_virtual_connectors = self._preflight_display()
        self.screen_cast = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.gnome.Mutter.ScreenCast",
            "/org/gnome/Mutter/ScreenCast",
            "org.gnome.Mutter.ScreenCast",
            None,
        )
        result = self.screen_cast.call_sync(
            "CreateSession",
            GLib.Variant("(a{sv})", ({},)),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
        session_path = result.unpack()[0]
        self.session = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.gnome.Mutter.ScreenCast",
            session_path,
            "org.gnome.Mutter.ScreenCast.Session",
            None,
        )

        for output in self.outputs:
            self._record_virtual(output)

        self.session.call_sync(
            "Start", None, Gio.DBusCallFlags.NONE, -1, None
        )
        requested = ", ".join(
            f"{output.config.name}={output.config.width}x{output.config.height}"
            f"@{output.config.refresh}"
            for output in self.outputs
        )
        print(f"Virtual monitors requested: {requested}", flush=True)

        GLib.timeout_add_seconds(self.config.startup_timeout, self._check_started)
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)
        self.loop.run()

    def _record_virtual(self, output: VirtualOutput) -> None:
        if self.session is None:
            raise RuntimeError("ScreenCast session has not been created")
        result = self.session.call_sync(
            "RecordVirtual",
            GLib.Variant(
                "(a{sv})",
                (
                    {
                        "is-platform": GLib.Variant("b", True),
                        "cursor-mode": GLib.Variant("u", 1),
                    },
                ),
            ),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
        stream_path = result.unpack()[0]
        output.stream = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.gnome.Mutter.ScreenCast",
            stream_path,
            "org.gnome.Mutter.ScreenCast.Stream",
            None,
        )
        output.stream.connect(
            "g-signal",
            lambda proxy, sender, signal_name, parameters, current=output: self._on_stream_signal(
                current, proxy, sender, signal_name, parameters
            ),
        )

    def _on_stream_signal(
        self,
        output: VirtualOutput,
        _proxy: Gio.DBusProxy,
        _sender: str,
        signal_name: str,
        parameters: GLib.Variant,
    ) -> None:
        if signal_name != "PipeWireStreamAdded" or output.node_id is not None:
            return

        try:
            output.node_id = parameters.unpack()[0]
            description = (
                f"pipewiresrc path={output.node_id} do-timestamp=true ! "
                f"video/x-raw,width={output.config.width},height={output.config.height},"
                f"max-framerate={output.config.refresh}/1 ! "
                "queue max-size-buffers=1 leaky=downstream ! fakesink sync=false"
            )
            output.pipeline = Gst.parse_launch(description)
            bus = output.pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_pipeline_message, output)
            if (
                output.pipeline.set_state(Gst.State.PLAYING)
                == Gst.StateChangeReturn.FAILURE
            ):
                raise RuntimeError(
                    f"GStreamer could not consume the {output.config.name} stream"
                )
            output.ready = True
        except (GLib.Error, RuntimeError) as error:
            print(
                f"Could not start virtual monitor {output.config.name}: {error}",
                file=sys.stderr,
                flush=True,
            )
            self.failed = True
            self.loop.quit()
            return

        print(
            f"Virtual monitor active: {output.config.name}, PipeWire node "
            f"{output.node_id}, {output.config.width}x{output.config.height}, "
            f"maximum {output.config.refresh} Hz",
            flush=True,
        )
        if all(item.ready for item in self.outputs):
            GLib.timeout_add(500, self._apply_layout)

    @staticmethod
    def _is_virtual(monitor: tuple[object, ...]) -> bool:
        spec = monitor[0]
        return str(spec[0]).startswith("Meta-") or spec[2] == "Virtual remote monitor"

    @staticmethod
    def _new_display_config_proxy() -> Gio.DBusProxy:
        return Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.gnome.Mutter.DisplayConfig",
            "/org/gnome/Mutter/DisplayConfig",
            "org.gnome.Mutter.DisplayConfig",
            None,
        )

    def _get_current_state(self) -> tuple[object, ...]:
        return self._new_display_config_proxy().call_sync(
            "GetCurrentState", None, Gio.DBusCallFlags.NONE, -1, None
        ).unpack()

    def _validate_layout_mode(self, properties: dict[str, object]) -> None:
        current_layout_mode = int(properties.get("layout-mode", 0))
        if current_layout_mode != self.config.layout_mode:
            raise RuntimeError(
                f"GNOME layout mode is {current_layout_mode}, expected "
                f"{self.config.layout_mode}; enable Mutter's "
                "scale-monitor-framebuffer feature first"
            )

    def _preflight_display(self) -> set[str]:
        _serial, monitors, logical_monitors, properties = self._get_current_state()
        self._validate_layout_mode(properties)
        self._resolve_primary_monitor(monitors, logical_monitors)
        return {
            monitor[0][0]
            for monitor in monitors
            if self._is_virtual(monitor)
        }

    def _resolve_primary_monitor(
        self,
        monitors: list[tuple[object, ...]],
        logical_monitors: list[tuple[object, ...]],
    ) -> ResolvedMonitor:
        physical_monitors = [
            monitor for monitor in monitors if not self._is_virtual(monitor)
        ]
        if not physical_monitors:
            raise RuntimeError("No physical monitor is available")

        current_primary_connector = next(
            (
                specs[0][0]
                for _x, _y, _scale, _transform, primary, specs, _props in logical_monitors
                if primary and specs
            ),
            None,
        )
        requested_connector = self.config.primary.connector or current_primary_connector
        primary_monitor = next(
            (
                monitor
                for monitor in physical_monitors
                if monitor[0][0] == requested_connector
            ),
            None,
        )
        if primary_monitor is None:
            raise RuntimeError(
                f"Primary connector {requested_connector!r} is not available"
            )
        primary_mode = choose_mode(
            primary_monitor[1],
            self.config.primary.width,
            self.config.primary.height,
            self.config.primary.refresh,
        )
        primary_scale = choose_scale(
            primary_mode[5],
            self.config.primary.scale,
        )
        return ResolvedMonitor(
            name=self.config.primary.name,
            connector=primary_monitor[0][0],
            mode_id=primary_mode[0],
            width=primary_mode[1],
            height=primary_mode[2],
            refresh=primary_mode[3],
            scale=primary_scale,
            primary=True,
        )

    def _resolve_monitors(
        self,
        monitors: list[tuple[object, ...]],
        logical_monitors: list[tuple[object, ...]],
    ) -> list[ResolvedMonitor]:
        virtual_candidates = [
            monitor
            for monitor in monitors
            if self._is_virtual(monitor)
            and monitor[0][0] not in self.preexisting_virtual_connectors
        ]
        resolved = [self._resolve_primary_monitor(monitors, logical_monitors)]

        used_connectors: set[str] = set()
        for profile in self.config.monitors:
            candidate = next(
                (
                    monitor
                    for monitor in virtual_candidates
                    if monitor[0][0] not in used_connectors
                    and any(
                        mode[1] == profile.width and mode[2] == profile.height
                        for mode in monitor[1]
                    )
                ),
                None,
            )
            if candidate is None:
                raise RuntimeError(
                    f"Virtual monitor {profile.name} ({profile.width}x{profile.height}) "
                    "has not appeared yet"
                )
            used_connectors.add(candidate[0][0])
            mode = choose_mode(
                candidate[1], profile.width, profile.height, profile.refresh
            )
            scale = choose_scale(mode[5], profile.scale)
            resolved.append(
                ResolvedMonitor(
                    name=profile.name,
                    connector=candidate[0][0],
                    mode_id=mode[0],
                    width=mode[1],
                    height=mode[2],
                    refresh=mode[3],
                    scale=scale,
                    primary=False,
                    relative_to=profile.relative_to,
                    position=profile.position,
                    alignment=profile.alignment,
                )
            )
        return resolved

    def _apply_layout(self) -> int:
        self.layout_attempts += 1
        try:
            display_config = self._new_display_config_proxy()
            serial, monitors, logical_monitors, properties = self._get_current_state()
            self._validate_layout_mode(properties)
            resolved = self._resolve_monitors(monitors, logical_monitors)
            placed = place_monitors(resolved)
            layout = [
                (
                    item.x,
                    item.y,
                    item.monitor.scale,
                    0,
                    item.monitor.primary,
                    [(item.monitor.connector, item.monitor.mode_id, {})],
                )
                for item in placed
            ]
            apply_properties = {
                "layout-mode": GLib.Variant("u", self.config.layout_mode)
            }
            for method in (0, 1):
                display_config.call_sync(
                    "ApplyMonitorsConfig",
                    GLib.Variant(
                        "(uua(iiduba(ssa{sv}))a{sv})",
                        (serial, method, layout, apply_properties),
                    ),
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                )
            self.ready_file.write_text("ready\n", encoding="utf-8")
            self.ready_file.chmod(0o600)
            summary = "; ".join(
                f"{item.monitor.name}/{item.monitor.connector} "
                f"{item.monitor.width}x{item.monitor.height}@{item.monitor.refresh:.3f} "
                f"scale={item.monitor.scale:.6g} pos={item.x},{item.y} "
                f"logical={item.logical_width}x{item.logical_height}"
                for item in placed
            )
            print(f"Display layout applied: {summary}", flush=True)
            return GLib.SOURCE_REMOVE
        except (GLib.Error, OSError, RuntimeError, StopIteration) as error:
            if self.layout_attempts < self.config.layout_retries:
                return GLib.SOURCE_CONTINUE
            print(
                f"Could not apply virtual monitor layout after "
                f"{self.layout_attempts} attempts: {error}",
                file=sys.stderr,
                flush=True,
            )
            self.failed = True
            self.loop.quit()
            return GLib.SOURCE_REMOVE

    def _on_pipeline_message(
        self, _bus: Gst.Bus, message: Gst.Message, output: VirtualOutput
    ) -> None:
        if message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            print(
                f"Virtual monitor {output.config.name} pipeline failed: "
                f"{error}; {debug}",
                file=sys.stderr,
                flush=True,
            )
            self.failed = True
            self.loop.quit()

    def _check_started(self) -> int:
        missing = [output.config.name for output in self.outputs if not output.ready]
        if missing:
            print(
                f"Virtual monitors did not produce PipeWire streams: {', '.join(missing)}",
                file=sys.stderr,
                flush=True,
            )
            self.failed = True
            self.loop.quit()
        return GLib.SOURCE_REMOVE

    def _on_signal(self, _signum: int, _frame: object) -> None:
        self.loop.quit()

    def stop(self) -> None:
        try:
            self.ready_file.unlink(missing_ok=True)
        except OSError:
            pass
        for output in self.outputs:
            if output.pipeline is not None:
                output.pipeline.set_state(Gst.State.NULL)
        if self.session is not None:
            try:
                self.session.call_sync(
                    "Stop", None, Gio.DBusCallFlags.NONE, 3000, None
                )
            except GLib.Error:
                pass
