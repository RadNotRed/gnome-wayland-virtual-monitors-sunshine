"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys

from gi.repository import GLib

from .config import load_config
from .daemon import VirtualMonitorDaemon


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create GNOME/Mutter virtual monitors for Sunshine"
    )
    parser.add_argument(
        "--config",
        default="~/.config/gnome-virtual-monitors/config.toml",
        help="TOML configuration path",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="validate the configuration without creating monitors",
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
            f"primary refresh {config.primary.refresh} Hz"
        )
        return 0

    daemon = VirtualMonitorDaemon(config)
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
