<p align="center">
  <img src="assets/hero.svg" width="100%" alt="Ubuntu host extended to a Windows laptop and a Galaxy A56 through GNOME Wayland virtual monitors">
</p>

<h1 align="center">GNOME Wayland virtual monitors for Sunshine</h1>

<p align="center">
  Turn a Windows laptop and an Android phone into real extended displays.<br>
  One GNOME desktop, independent streams, mixed refresh rates.
</p>

<p align="center">
  <a href="https://github.com/lirenzzzin/gnome-wayland-virtual-monitors-sunshine/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/lirenzzzin/gnome-wayland-virtual-monitors-sunshine/ci.yml?branch=main&amp;style=flat-square&amp;label=checks&amp;color=6EE7F2"></a>
  <img alt="GNOME 46" src="https://img.shields.io/badge/GNOME-46-4A86CF?style=flat-square">
  <img alt="Wayland" src="https://img.shields.io/badge/session-Wayland-F6C85F?style=flat-square">
  <a href="LICENSE"><img alt="GPL 3.0" src="https://img.shields.io/badge/license-GPL--3.0-A78BFA?style=flat-square"></a>
</p>

> [!WARNING]
> This is an experimental GNOME/Mutter integration, validated on one GNOME 46 + NVIDIA system. It uses private D-Bus interfaces and isolated Sunshine processes. Read the [known sharp edges](#known-sharp-edges) before installing.

## What you get

| Real extension | One stream per device | Refresh stays independent |
| --- | --- | --- |
| Windows move naturally beyond the edge of the physical display. Nothing is mirrored. | Separate Sunshine identities capture the laptop and phone outputs at the same time. | The main display and phone run at 120 Hz while the laptop remains at 60 Hz. |

The validated desktop looks like this:

| Surface | Mode | GNOME placement | Client path |
| --- | ---: | --- | --- |
| Physical primary | **1920×1080 · 120 Hz** | center | local |
| Windows laptop | **1366×768 · 60 Hz** | left | Sunshine → Moonlight |
| Galaxy A56 | **2340×1080 · 120 Hz · ~175%** | centered below | Sunshine → Moonlight Android |

Under the hood, a user daemon asks Mutter for `RecordVirtual` outputs, keeps their PipeWire nodes alive, and applies the extended layout. Sunshine captures each output through its own XDG Portal session.

## Quick start

### 1. Install the host dependencies

```bash
sudo apt update
sudo apt install \
  python3-gi \
  gir1.2-gstreamer-1.0 \
  gstreamer1.0-pipewire \
  gstreamer1.0-tools \
  pipewire-bin
```

Install [Sunshine](https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html) on Ubuntu and [Moonlight](https://moonlight-stream.org/) on each client. The supplied service files expect native Sunshine at `/usr/bin/sunshine`.

### 2. Clone and inspect the host

```bash
git clone https://github.com/lirenzzzin/gnome-wayland-virtual-monitors-sunshine.git
cd gnome-wayland-virtual-monitors-sunshine
./scripts/doctor.sh
```

A fractional-scaling warning is expected before installation; the installer can enable the required Mutter feature.

### 3. Install the user service

```bash
./scripts/install-user.sh
${EDITOR:-nano} ~/.config/gnome-virtual-monitors/config.toml
PYTHONPATH="$HOME/.local/lib/gnome-wayland-virtual-monitors-sunshine" \
  python3 -m gnome_virtual_monitors \
  --config "$HOME/.config/gnome-virtual-monitors/config.toml" \
  --check-config
systemctl --user enable --now gnome-virtual-monitor.service
```

Before enabling the service:

- set the physical connector, width, height, and refresh for your primary display;
- give every virtual monitor a unique width/height pair; and
- remember that v0.1 manages one physical primary plus the configured virtual outputs.

The installer stays inside your home directory. It does not start a root daemon, replace a kernel module, overwrite an existing monitor config, or erase unrelated Mutter features during rollback.

### 4. Connect the clients

Keep the normal Sunshine instance for the Windows laptop. Install the isolated Android instance from `experimental/`, select the wide phone output in GNOME's Portal dialog, then add `HOST_IP:48049` in Moonlight Android.

For the Galaxy A56:

- enable **Display → Motion smoothness → Adaptive**;
- choose **2340×1080 at 120 FPS** in Moonlight;
- start around **28 Mbps**, H.264, lowest-latency frame pacing; and
- use touchscreen-as-trackpad for the non-primary output.

The full pairing, Portal, port, H.264/NVENC, MediaCodec, Windows, and Android walkthrough is in [Sunshine and Moonlight setup](docs/SUNSHINE.md).

## One button to avoid

> [!CAUTION]
> Do not click **Stop Sharing** in GNOME's monitor-with-arrow status indicator while the virtual displays are active. GNOME includes the daemon's virtual-output sessions there; stopping them destroys the outputs and may stale Sunshine's Portal tokens.

If it happens, stop both Sunshine instances, restart the virtual-monitor daemon, wait for `Display layout applied`, then restart and reauthorize only the instances that fail. The exact recovery commands are in [Troubleshooting](docs/TROUBLESHOOTING.md).

## Known sharp edges

- GNOME/Mutter only — this is not a compositor-independent Wayland protocol.
- Mutter 46 can corrupt the embedded cursor around 175% screencast scaling. The documented fallback keeps the UI size while trading some sharpness.
- XWayland applications may look softer under fractional scaling.
- `Meta-0` and `Meta-1` are temporary names; the daemon maps roles by unique resolution instead.
- Recreating virtual outputs can invalidate saved Portal selections.
- Two Sunshine processes isolate capture and state, not keyboard/pointer ownership.
- Suspend/resume and newer GNOME versions still need wider testing.

## Documentation

| Guide | Use it when… |
| --- | --- |
| [Project scope](docs/PROJECT_SCOPE.md) | you want the exact promises and non-goals |
| [Architecture](docs/ARCHITECTURE.md) | you want to understand Mutter, PipeWire, layout, and readiness |
| [Sunshine + Moonlight](docs/SUNSHINE.md) | you are pairing Windows or Android and tuning 60/120 FPS |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Portal, cursor, output selection, or FPS behaves incorrectly |
| [Testing](docs/TESTING.md) | you are validating a new machine or GNOME release |
| [Rollback](docs/ROLLBACK.md) | you want to remove the daemon without deleting client state |
| [Security](SECURITY.md) | you are reviewing tokens, ports, encryption, or input trust |
| [Prior art](PRIOR_ART.md) | you want the upstream work this integration builds upon |

<details>
<summary><strong>Validated stack</strong></summary>

- Zorin OS 18, based on Ubuntu 24.04
- GNOME Shell and Mutter 46.2 on Wayland
- NVIDIA GTX 1650, proprietary driver 595.71.05
- Sunshine 2026.516.143833 with XDG Portal capture
- PipeWire 1.0.5 and GStreamer `pipewiresrc`
- Windows laptop at 1366×768, 60 Hz
- Galaxy A56 landscape at 2340×1080, 120 Hz, approximately 175% GNOME scale
- Moonlight Android with H.264 hardware decoding

</details>

## Credit

Created and maintained by **Lina**. Licensed under [GPL-3.0-or-later](LICENSE).

This project is independent and is not affiliated with GNOME, Sunshine, LizardByte, Moonlight, NVIDIA, Microsoft, or Samsung.
