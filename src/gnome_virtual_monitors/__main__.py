"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys

from gi.repository import GLib

from .config import load_config
from .daemon import VirtualMonitorDaemon
from .saved_layout import capture_saved_layout, default_state_path, write_saved_layout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create GNOME/Mutter virtual monitors for Sunshine"
    )
    parser.add_argument(
        "--config",
        default="~/.config/gnome-virtual-monitors/config.toml",
        help="TOML configuration path",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--check-config",
        action="store_true",
        help="validate the configuration without creating monitors",
    )
    action.add_argument(
        "--save-layout",
        action="store_true",
        help="save the active layout for optional restoration on future daemon starts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as error:
        print(f"Invalid configuration: {error}", file=sys.stderr)
        return 2

    if args.check_config:
        print(
            f"Configuration valid: {len(config.monitors)} virtual monitor(s), "
            + (
                "preserving active physical displays"
                if config.preserve_physical_monitors
                else f"primary refresh {config.primary.refresh} Hz"
            )
        )
        return 0

    daemon = VirtualMonitorDaemon(config)
    if args.save_layout:
        try:
            _serial, monitors, logical, properties = daemon._get_current_state()
            daemon._validate_layout_mode(properties)
            state = capture_saved_layout(config, monitors, logical)
            path = default_state_path()
            write_saved_layout(path, state)
        except (GLib.Error, OSError, RuntimeError, ValueError) as error:
            print(f"Could not save layout: {error}", file=sys.stderr)
            return 1
        print(f"Layout saved to {path}")
        return 0

    try:
        daemon.start()
    except GLib.Error as error:
        print(f"Could not create GNOME virtual monitors: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Virtual monitor daemon failed: {error}", file=sys.stderr)
        return 1
    finally:
        daemon.stop()
    return 1 if daemon.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
