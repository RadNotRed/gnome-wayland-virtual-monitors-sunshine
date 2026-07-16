# GNOME Wayland virtual monitors for Sunshine

Create real extended virtual monitors inside an active GNOME Wayland session, then stream a different output to each Moonlight client.

> [!WARNING]
> This is experimental. It was validated on one GNOME 46/NVIDIA system and depends on private Mutter D-Bus APIs plus isolated Sunshine processes. Expect to renew Portal permissions after GNOME, Mutter, or display-layout changes.

```text
Laptop virtual 1366x768@60  <-  Physical monitor 1920x1080@120
                                      |
                              Phone virtual 2340x1080@120
                              logical 1339x618 (~175% scale)
```

The tested layout puts a Windows laptop on the physical left and a landscape Galaxy A56 centered below the primary monitor. The primary remains at 120 Hz, the laptop runs at 60 Hz, and the phone can run at 120 Hz.

## What this project does

The user daemon:

1. asks Mutter for multiple `RecordVirtual` streams;
2. keeps their PipeWire nodes negotiated at the requested modes;
3. discovers the new `Meta-*` outputs without depending on their connector numbers;
4. applies a mixed-refresh, per-monitor-scale extended layout; and
5. leaves capture to isolated Sunshine/XDG Portal sessions.

This project did **not** invent Mutter virtual monitors, `RecordVirtual`, PipeWire mode negotiation, or `ApplyMonitorsConfig`. Its contribution is packaging and validating those pieces together with two simultaneous Sunshine/Moonlight clients. See [Prior art](PRIOR_ART.md).

## Validated stack

- Zorin OS 18 (Ubuntu 24.04 base)
- GNOME Shell/Mutter 46.2 on Wayland
- NVIDIA GTX 1650 with proprietary driver 595.71.05
- Sunshine 2026.516.143833 using XDG Portal capture
- PipeWire 1.0.5 and GStreamer's `pipewiresrc`
- Windows laptop at 1366x768, 60 Hz
- Galaxy A56 landscape at 2340x1080, 120 Hz, approximately 175% GNOME scale
- Moonlight Android using H.264 hardware decoding

Other GNOME/Mutter versions, GPUs, resolutions, and codecs may behave differently.

## Requirements

- An active GNOME **Wayland** session
- Mutter exposing `org.gnome.Mutter.ScreenCast.RecordVirtual`
- Python 3.11+, PyGObject, GStreamer, and the PipeWire GStreamer plugin
- Sunshine configured with `capture = portal`
- Moonlight on each client
- Mutter fractional scaling through `scale-monitor-framebuffer`

On Ubuntu/Zorin, the daemon dependencies are typically:

```bash
sudo apt update
sudo apt install python3-gi gir1.2-gstreamer-1.0 gstreamer1.0-pipewire gstreamer1.0-tools pipewire-bin
```

Install [Sunshine](https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html) and [Moonlight](https://moonlight-stream.org/) from their official projects. Run the preflight check before installing this daemon. A fractional-scaling warning is expected until the installer enables the feature:

```bash
./scripts/doctor.sh
```

## Install the virtual-monitor daemon

```bash
./scripts/install-user.sh
${EDITOR:-nano} ~/.config/gnome-virtual-monitors/config.toml
PYTHONPATH="$HOME/.local/lib/gnome-wayland-virtual-monitors-sunshine" \
  python3 -m gnome_virtual_monitors \
  --config "$HOME/.config/gnome-virtual-monitors/config.toml" \
  --check-config
systemctl --user enable --now gnome-virtual-monitor.service
```

The installer does not start the daemon automatically. It records whether it added Mutter's fractional-scaling feature for a non-destructive rollback and does not overwrite an existing monitor configuration.

Before enabling the service, edit the example for your hardware:

- replace `HDMI-1` with your physical connector, or remove `connector` to use GNOME's current primary monitor;
- request only refresh rates that the corresponding displays support;
- give every virtual monitor a unique width/height pair; and
- include every physical monitor you need. This version omits unconfigured physical outputs from the applied layout.

Verify the result:

```bash
journalctl --user -u gnome-virtual-monitor.service -n 30 --no-pager
./scripts/doctor.sh
```

The service log reports each physical/virtual mode, scale, logical size, and position. Requested fractional scales are matched dynamically against Mutter's supported values; do not hard-code the approximate value returned by one resolution.

## Stream one output per client

A Sunshine process has one selected capture output. To send different outputs to two clients, keep the default Sunshine instance for the laptop and create the isolated Android instance under `experimental/`.

Follow [Sunshine and Moonlight setup](docs/SUNSHINE.md) for exact copy, service, Portal, pairing, and 120 FPS instructions. The important rules are:

- each Sunshine instance needs a distinct config root, port family, Portal app ID, credentials, certificates, pairing state, and `portal_token`;
- select exactly one virtual output in each GNOME Portal dialog;
- set both the phone virtual monitor and Moonlight to 120 FPS;
- on a Galaxy A56, enable **Settings > Display > Motion smoothness > Adaptive**;
- never copy a `portal_token` between instances.

## Important GNOME warning

Do **not** click **Stop Sharing** in GNOME's monitor-with-arrow status indicator while the virtual monitors are active. The daemon's `RecordVirtual` sessions appear as screen-sharing sessions; stopping them destroys the virtual outputs and invalidates Sunshine's saved Portal selection.

If this happens, stop both Sunshine instances, restart the virtual-monitor service and wait for the layout, then start each Sunshine instance and renew only tokens that fail. See [Troubleshooting](docs/TROUBLESHOOTING.md).

## Known limitations

- GNOME/Mutter only; this is not a generic Wayland protocol.
- Mutter's ScreenCast and DisplayConfig interfaces are private and may change.
- Fractional scaling can blur XWayland applications.
- Mutter 46 has a known embedded-cursor corruption bug with fractional screencast scaling, observed here at 175%.
- Virtual connector names such as `Meta-0` are not stable identities.
- Portal restore tokens can become stale whenever virtual outputs are recreated.
- Multiple Sunshine instances are experimental and share one GNOME input seat.
- Absolute touchscreen coordinates on a selected non-primary Linux output are unreliable; use Moonlight's trackpad behavior.
- Extra unconfigured physical monitors are omitted from the layout applied by this version.
- Suspend/resume and future GNOME releases need broader testing.

See [Project scope](docs/PROJECT_SCOPE.md), [Architecture](docs/ARCHITECTURE.md), [Testing](docs/TESTING.md), [Troubleshooting](docs/TROUBLESHOOTING.md), and [Rollback](docs/ROLLBACK.md).

## Credits

Created and maintained by **Lina**.

## Safety and license

Everything installs under the current user's home directory. No root daemon or kernel module is added. Review [Security](SECURITY.md) before publishing logs or configuration files.

GPL-3.0-or-later. This project is not affiliated with GNOME, Sunshine, LizardByte, Moonlight, NVIDIA, Microsoft, or Samsung.
