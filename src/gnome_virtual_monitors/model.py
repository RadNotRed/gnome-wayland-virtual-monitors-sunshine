"""Configuration and resolved display model types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrimaryConfig:
    name: str
    connector: str | None
    refresh: int
    scale: float


@dataclass(frozen=True)
class VirtualMonitorConfig:
    name: str
    width: int
    height: int
    refresh: int
    scale: float
    relative_to: str
    position: str
    alignment: str


@dataclass(frozen=True)
class DaemonConfig:
    primary: PrimaryConfig
    monitors: tuple[VirtualMonitorConfig, ...]
    layout_mode: int
    layout_retries: int
    startup_timeout: int


@dataclass(frozen=True)
class ResolvedMonitor:
    name: str
    connector: str
    mode_id: str
    width: int
    height: int
    refresh: float
    scale: float
    primary: bool
    relative_to: str | None = None
    position: str | None = None
    alignment: str = "center"


@dataclass(frozen=True)
class PlacedMonitor:
    monitor: ResolvedMonitor
    x: int
    y: int
    logical_width: int
    logical_height: int
