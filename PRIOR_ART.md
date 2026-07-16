# Prior art

This project does not claim invention of virtual monitors on GNOME Wayland.

- [Mutter MR !1698](https://gitlab.gnome.org/GNOME/mutter/-/merge_requests/1698) introduced `RecordVirtual` in 2021 for network screens and remote desktops.
- [GNOME Remote Desktop MR !69](https://gitlab.gnome.org/GNOME/gnome-remote-desktop/-/merge_requests/69) added virtual-monitor RDP support in 2022.
- [Mirror Hall](https://gitlab.com/nokun/mirrorhall) published `CreateSession -> RecordVirtual -> PipeWireStreamAdded -> pipewiresrc` before this project.
- [Immersed Linux Virtual Monitors](https://github.com/augustoicaro/Immersed-Linux-Virtual-Monitors/blob/main/scripts/wayland-scripts/dbus_virtual_monitor_mutter.py) published a Python/GStreamer implementation.
- [Breezy Desktop](https://github.com/wheaney/breezy-desktop/blob/013690580c37e5ec23378e689a25e62050f400ac/ui/src/virtualdisplay.py) uses `pipewiresrc ... ! fakesink` to keep a virtual output alive.
- [Sunshine PR #4417](https://github.com/LizardByte/Sunshine/pull/4417) added XDG Portal/PipeWire capture in 2026.
- [Punktfunk](https://git.unom.io/unom/punktfunk/commit/9fe7b7877fdb0059aa08780a00242d1d76036c50) combined `RecordVirtual` with `ApplyMonitorsConfig` in 2026.
- [project-monitorize](https://github.com/vinnavannewton/project-monitorize) also combines virtual GNOME outputs and layout management, with its own streamer.
- [Sunshine issue #5266](https://github.com/LizardByte/Sunshine/issues/5266) records that Sunshine does not itself create virtual displays.

The integration documented here was implemented independently. Its useful scope is a reproducible live GNOME session with mixed refresh, fractional scale, persistent user services, current Sunshine Portal capture, and different simultaneous Moonlight clients.
